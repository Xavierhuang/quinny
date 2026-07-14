"""Quinny -> target-language code generator.

Walks the task graph in topological order and asks Claude to emit one file per
node. Each generation is given (1) the node's own goal/constraints/tests, and
(2) the source of every dependency that was already generated — so downstream
tasks can call upstream APIs by their actual names.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from quinny._capabilities import thinking_kwargs, make_client
from quinny._interface import extract_interface
from quinny.graph import TaskGraph, build_graph
from quinny.nodes import Component, Declaration, Field, NameField, Project, ProseField, Task
from quinny.usage import UsageTracker


SUPPORTED_TARGETS = ("python", "typescript")

_TARGET_META = {
    "python": {
        "language_name": "Python 3.11",
        "file_ext": "py",
        "module_case": "snake_case",
        "extra_rules": (
            "- Standard library only unless a `constraint` names a package.\n"
            "- Use type hints on every function.\n"
            "- Prefer dataclasses over dicts for structured returns."
        ),
    },
    "typescript": {
        "language_name": "TypeScript (Node 20+)",
        "file_ext": "ts",
        "module_case": "camelCase",
        "extra_rules": (
            "- Use ES module syntax (`import`, `export`).\n"
            "- Prefer `type`/`interface` for structured data.\n"
            "- Standard library + Node built-ins only unless a `constraint`\n"
            "  names a package."
        ),
    },
}


class GeneratorError(Exception):
    pass


@dataclass
class GeneratedFile:
    name: str          # declaration name
    kind: str          # "task" | "component"
    filename: str      # e.g. "login.py"
    source: str


@dataclass
class GenerationResult:
    project: str
    target: str
    files: list[GeneratedFile] = field(default_factory=list)

    def write(self, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        for f in self.files:
            (out_dir / f.filename).write_text(f.source + "\n")


_FENCE_RE = re.compile(
    r"^\s*```[a-zA-Z0-9_+-]*\s*\n(.*?)\n\s*```\s*$", re.DOTALL
)


def _strip_fences(text: str) -> str:
    m = _FENCE_RE.match(text)
    return m.group(1) if m else text.strip()


def _snake_case(name: str) -> str:
    """CamelCase -> snake_case."""
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s).lower()


def _camel_case(name: str) -> str:
    """CamelCase -> camelCase (lowercase first letter)."""
    return name[:1].lower() + name[1:] if name else name


def _module_name(name: str, target: str) -> str:
    return _snake_case(name) if _TARGET_META[target]["module_case"] == "snake_case" else _camel_case(name)


def _fields_by_kind(fields: tuple[Field, ...], kind: str) -> list[str]:
    for f in fields:
        if isinstance(f, ProseField) and f.kind == kind:
            return list(f.lines)
        if isinstance(f, NameField) and f.kind == kind:
            return list(f.names)
    return []


def _render_spec(decl: Declaration) -> str:
    """Human-readable spec block passed to the model for one node."""
    kind = "task" if isinstance(decl, Task) else "component"
    lines: list[str] = [f"{kind} {decl.name}"]
    for field_kind in ("goal", "input", "output", "constraint",
                        "depends", "uses", "test", "success"):
        values = _fields_by_kind(decl.fields, field_kind)
        if not values:
            continue
        lines.append(f"  {field_kind}:")
        for v in values:
            lines.append(f"    - {v}")
    return "\n".join(lines)


def _render_deps_context(
    decl: Declaration,
    generated: dict[str, GeneratedFile],
    target: str = "python",
) -> str:
    """Render dependency source for the current node's prompt.

    For Python targets we send only the *public interface* (function
    signatures, class shapes, module constants) — extracted via AST — rather
    than the full implementation source. This cuts per-node prompts to a
    fraction of their previous size without losing the API surface the
    downstream node actually needs to import against.
    """
    edge_names: list[str] = []
    if isinstance(decl, Task):
        edge_names.extend(decl.depends)
    elif isinstance(decl, Component):
        edge_names.extend(decl.uses)
        edge_names.extend(decl.depends)
    if not edge_names:
        return "(none — this node has no dependencies)"
    parts: list[str] = []
    for name in edge_names:
        gf = generated.get(name)
        if gf is None:
            continue
        payload = (
            extract_interface(gf.source) if target == "python" else gf.source
        )
        parts.append(f"### {name} — file: {gf.filename}\n```\n{payload}\n```")
    return "\n\n".join(parts) if parts else "(none)"


_SYSTEM_PROMPT = (
    "You implement one node of a Quinny task graph. Output ONLY the source "
    "of the single file requested — no prose, no fences. Rules: "
    "(1) satisfy every test line in the spec (executable in "
    '`if __name__ == "__main__":`); '
    "(2) import dep symbols by the exact names shown in Dependency interface; "
    "(3) import shared types from `shared_types` when a Shared types section "
    "is present, don't redefine them; "
    "(4) do NOT invent constraints not in the spec."
)


_TYPES_SYSTEM_PROMPT = """You design the shared type layer for a project.

Given a whole Quinny project spec, emit a single Python module
`shared_types.py` that declares the dataclasses / TypedDicts / enums that
multiple nodes will share. This module is imported by every subsequent
node's generated file.

Rules:
1. Output ONLY the source of `shared_types.py`. No prose, no markdown fences.
2. Use `@dataclass(frozen=True)` for value objects; use `Enum` for closed
   sets of choices.
3. Include ONLY types the project's `input` / `output` fields suggest are
   crossing node boundaries — do not invent extras.
4. If nothing crosses boundaries, emit a comment-only module explaining why
   it's empty. Do not fabricate types.
5. Keep it minimal — this is a header file, not a domain model."""


def _needs_shared_types(project: Project) -> bool:
    """Return True iff at least one declaration crosses a node boundary via
    an `input` or `output` field. If nothing crosses, `shared_types.py`
    would be empty by definition — skip the Claude call.
    """
    for decl in project.all_declarations():
        for f in decl.fields:
            if isinstance(f, NameField) and f.kind in ("input", "output"):
                if f.names:
                    return True
    return False


def _generate_types(
    project: Project,
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int,
    tracker: "UsageTracker | None" = None,
) -> str:
    """Emit a shared types.py for the whole project (one Claude call)."""
    spec_lines: list[str] = [f"project {project.name}"]
    for decl in project.all_declarations():
        spec_lines.append("")
        spec_lines.append(_render_spec(decl))
    spec = "\n".join(spec_lines)

    user_msg = (
        f"Full project spec:\n\n{spec}\n\n"
        f"Emit `shared_types.py` — the shared type layer imported by every "
        f"generated node file."
    )
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=_TYPES_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        **thinking_kwargs(model),
    )
    if tracker is not None:
        tracker.record("types", model, response)
    raw = "\n".join(
        b.text for b in response.content if getattr(b, "type", None) == "text"
    )
    return _strip_fences(raw)


def load_existing_generation(
    project: Project,
    out_dir: Path,
    *,
    target: str = "python",
) -> GenerationResult:
    """Reconstruct a GenerationResult from files already on disk.

    Used by incremental regeneration — the caller wants to touch one node
    but reuse the rest of a previous build as dep context.
    """
    if target not in SUPPORTED_TARGETS:
        raise GeneratorError(f"Unsupported target '{target}'.")
    meta = _TARGET_META[target]
    result = GenerationResult(project=project.name, target=target)

    # 1. Shared types module (if present on disk).
    types_path = out_dir / "shared_types.py"
    if target == "python" and types_path.exists():
        result.files.append(GeneratedFile(
            name="_shared_types", kind="types", filename="shared_types.py",
            source=types_path.read_text(),
        ))

    # 2. One file per declaration, in the graph's topo order.
    graph = build_graph(project)
    for name in graph.topo_order():
        decl = graph.declaration(name)
        filename = f"{_module_name(name, target)}.{meta['file_ext']}"
        path = out_dir / filename
        source = path.read_text() if path.exists() else ""
        result.files.append(GeneratedFile(
            name=name,
            kind="task" if isinstance(decl, Task) else "component",
            filename=filename,
            source=source,
        ))
    return result


def regenerate_node(
    project: Project,
    node_name: str,
    existing: GenerationResult,
    *,
    client: anthropic.Anthropic | None = None,
    model: str = "claude-opus-4-7",
    max_tokens: int = 4096,
    tracker: "UsageTracker | None" = None,
) -> GeneratedFile:
    """Regenerate one node against the current on-disk deps.

    Unlike `regenerate_file`, this does a fresh generation (no failing prior
    source, no error log). Used by `quinny build --only <name>`.
    """
    if client is None:
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            raise GeneratorError("ANTHROPIC_API_KEY is not set.")
        client = make_client()

    generated = {f.name: f for f in existing.files}
    if node_name not in generated:
        raise GeneratorError(
            f"'{node_name}' has no existing file to regenerate. "
            f"Run a full `quinny build` first."
        )

    graph = build_graph(project)
    decl = graph.declaration(node_name)
    meta = _TARGET_META[existing.target]
    filename = f"{_module_name(node_name, existing.target)}.{meta['file_ext']}"

    types_source = None
    types_file = generated.get("_shared_types")
    if types_file:
        types_source = types_file.source

    source = _generate_one(
        project, decl, filename, existing.target, generated, types_source,
        client, model, max_tokens, tracker=tracker,
    )
    return GeneratedFile(
        name=node_name,
        kind="task" if isinstance(decl, Task) else "component",
        filename=filename,
        source=source,
    )


def regenerate_file(
    project: Project,
    node_name: str,
    current: GeneratedFile,
    error_log: str,
    *,
    generated_context: dict[str, GeneratedFile] | None = None,
    types_source: str | None = None,
    target: str = "python",
    client: anthropic.Anthropic | None = None,
    model: str = "claude-opus-4-7",
    max_tokens: int = 4096,
    tracker: "UsageTracker | None" = None,
) -> GeneratedFile:
    """Ask Claude to fix a file that failed verification.

    Passes the original spec, the failing source, and the exact error log
    from the verifier. Returns a new GeneratedFile with the same filename.
    """
    if target not in SUPPORTED_TARGETS:
        raise GeneratorError(f"Unsupported target '{target}'.")
    if client is None:
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            raise GeneratorError("ANTHROPIC_API_KEY is not set.")
        client = make_client()

    from quinny.graph import build_graph
    graph = build_graph(project)
    decl = graph.declaration(node_name)
    meta = _TARGET_META[target]
    spec = _render_spec(decl)
    deps_context = _render_deps_context(decl, generated_context or {}, target)

    system_blocks = _project_system_blocks(project.name, meta, types_source)

    user_msg = (
        f"Filename: {current.filename}\n\n"
        f"Node spec:\n{spec}\n\n"
        f"Dependency interface (import from these):\n"
        f"{deps_context}\n\n"
        f"Your previous version of this file:\n"
        f"```\n{current.source}\n```\n\n"
        f"It failed verification with:\n"
        f"```\n{error_log}\n```\n\n"
        f"Rewrite the file so this error goes away. Do not weaken the spec. "
        f"Output only the corrected source of `{current.filename}` — no prose, "
        f"no markdown fences."
    )

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_blocks,
        messages=[{"role": "user", "content": user_msg}],
        **thinking_kwargs(model),
    )
    if tracker is not None:
        tracker.record("repair", model, response)
    raw = "\n".join(
        b.text for b in response.content if getattr(b, "type", None) == "text"
    )
    return GeneratedFile(
        name=current.name,
        kind=current.kind,
        filename=current.filename,
        source=_strip_fences(raw),
    )


def generate(
    project: Project,
    *,
    target: str = "python",
    client: anthropic.Anthropic | None = None,
    model: str = "claude-opus-4-7",
    types_model: str | None = None,
    node_model: str | None = None,
    max_tokens: int = 4096,
    shared_types: bool = True,
    tracker: "UsageTracker | None" = None,
    batch_tiny_leaves: bool = False,
) -> GenerationResult:
    """Generate one file per declaration, in dependency order.

    Model routing:
      * `model` — fallback used for any stage not explicitly overridden.
      * `types_model` — used for the shared_types synthesis (design step
        with high blast radius; usually worth spending on).
      * `node_model` — used for every per-node code generation call
        (usually a cheaper model — small scoped tasks are what small
        models do well).

    Pass a `UsageTracker` to accumulate per-call token counts and costs.
    """

    if target not in SUPPORTED_TARGETS:
        raise GeneratorError(
            f"Unsupported target '{target}'. Supported: {SUPPORTED_TARGETS}"
        )
    if client is None:
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            raise GeneratorError(
                "ANTHROPIC_API_KEY is not set. Export it or pass a client."
            )
        client = make_client()

    types_model = types_model or model
    node_model = node_model or model

    graph: TaskGraph = build_graph(project)
    meta = _TARGET_META[target]
    result = GenerationResult(project=project.name, target=target)
    generated: dict[str, GeneratedFile] = {}

    # 1. Shared types module (Python only for v0.1). Skip the Claude call
    #    entirely when no `input`/`output` fields exist — there is nothing
    #    crossing node boundaries so a types module wouldn't have anything
    #    to declare.
    types_source: str | None = None
    if shared_types and target == "python" and _needs_shared_types(project):
        types_source = _generate_types(
            project, client, types_model, max_tokens, tracker=tracker,
        )
        result.files.append(GeneratedFile(
            name="_shared_types", kind="types", filename="shared_types.py",
            source=types_source,
        ))
        # Make types visible to the dep-context renderer too.
        generated["_shared_types"] = result.files[-1]

    # 2. One file per node. Layer-by-layer: nodes within the same
    #    topological layer are independent of each other, so we generate
    #    them in parallel using a thread pool. Within a layer, tiny leaf
    #    nodes are collapsed into a single batched call to amortise the
    #    fixed prompt overhead across several small files.
    from concurrent.futures import ThreadPoolExecutor

    def _mk_gf(name: str, source: str) -> GeneratedFile:
        decl = graph.declaration(name)
        return GeneratedFile(
            name=name,
            kind="task" if isinstance(decl, Task) else "component",
            filename=f"{_module_name(name, target)}.{meta['file_ext']}",
            source=source,
        )

    for layer in graph.execution_layers():
        deps_snapshot = dict(generated)

        # Split this layer into batches of tiny leaves + solo nodes. A
        # "batchable" node has a short spec and no downstream deps.
        #
        # BATCHING IS OFF BY DEFAULT — empirically it regresses per-file
        # quality on Haiku (the model writes buggier code when asked to
        # emit multiple files in one response), and the fallback-to-per-node
        # path negates the token savings. Kept as `batch_tiny_leaves=True`
        # for prompts where you've verified it helps.
        if batch_tiny_leaves:
            batches, solos = _partition_layer(layer, graph)
        else:
            batches, solos = [], list(layer)

        jobs = []
        for solo_name in solos:
            jobs.append(("solo", solo_name))
        for batch in batches:
            jobs.append(("batch", batch))

        def _job(item):
            kind, payload = item
            if kind == "solo":
                name = payload
                decl = graph.declaration(name)
                filename = f"{_module_name(name, target)}.{meta['file_ext']}"
                source = _generate_one(
                    project, decl, filename, target, deps_snapshot,
                    types_source, client, node_model, max_tokens,
                    tracker=tracker,
                )
                return [(name, _mk_gf(name, source))]
            # batch
            names = payload
            batch_decls = [(n, graph.declaration(n),
                             f"{_module_name(n, target)}.{meta['file_ext']}")
                            for n in names]
            sources = _generate_batch(
                project, batch_decls, target, deps_snapshot, types_source,
                client, node_model, max_tokens, tracker=tracker,
            )
            return [(n, _mk_gf(n, sources[n])) for n, _decl, _fn in batch_decls]

        if len(jobs) == 1:
            batch_results = _job(jobs[0])
        else:
            with ThreadPoolExecutor(max_workers=min(len(jobs), 8)) as pool:
                batch_results = []
                for r in pool.map(_job, jobs):
                    batch_results.extend(r)

        for name, gf in batch_results:
            generated[name] = gf
            result.files.append(gf)

    return result


def _partition_layer(
    layer: list[str], graph: TaskGraph,
) -> tuple[list[list[str]], list[str]]:
    """Split a layer into (batches_of_tiny_leaves, solo_nodes).

    A batchable node has (a) no children in the DAG, so its output doesn't
    become dep context for anything downstream, and (b) a spec that fits in
    a small budget. Batches are capped at 4 nodes each — larger batches
    make the response prone to truncation and harder to repair.
    """
    def _is_batchable(name: str) -> bool:
        if graph.dag.out_degree(name) > 0:
            return False
        decl = graph.declaration(name)
        spec_size = len(_render_spec(decl))
        return spec_size <= 400   # empirically small; most real specs blow past

    batchable = sorted(n for n in layer if _is_batchable(n))
    solos = [n for n in layer if n not in batchable]
    batches: list[list[str]] = []
    for i in range(0, len(batchable), 4):
        batches.append(batchable[i:i + 4])
    # Batches of 1 aren't actually batches — fold into solos.
    for b in list(batches):
        if len(b) == 1:
            solos.append(b[0])
            batches.remove(b)
    return batches, solos


_BATCH_FENCE_RE = re.compile(
    r"###\s*FILE:\s*([A-Za-z0-9_./-]+)\s*###\s*\n(.*?)(?=\n###\s*FILE:|\Z)",
    re.DOTALL,
)


def _generate_batch(
    project: Project,
    batch: list[tuple[str, Declaration, str]],
    target: str,
    generated: dict[str, GeneratedFile],
    types_source: str | None,
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int,
    tracker: "UsageTracker | None" = None,
) -> dict[str, str]:
    """Generate multiple tiny leaf nodes in a single Claude call.

    Falls back to per-node generation if the batched response is missing
    files — never returns fewer files than requested.
    """
    meta = _TARGET_META[target]
    system_blocks = _project_system_blocks(project.name, meta, types_source)

    spec_blocks: list[str] = []
    for _name, decl, filename in batch:
        deps = _render_deps_context(decl, generated, target)
        spec_blocks.append(
            f"### FILE: {filename} ###\n"
            f"Node spec:\n{_render_spec(decl)}\n\n"
            f"Dependency interface:\n{deps}\n"
        )
    user_msg = (
        "Emit the following files. Output each file EXACTLY like this:\n"
        "```\n### FILE: <filename> ###\n<file source>\n```\n"
        "Repeat the marker for every file. No prose, no markdown fences.\n\n"
        + "\n".join(spec_blocks)
    )

    response = client.messages.create(
        model=model, max_tokens=max_tokens,
        system=system_blocks,
        messages=[{"role": "user", "content": user_msg}],
        **thinking_kwargs(model),
    )
    if tracker is not None:
        tracker.record("node", model, response)
    raw = "\n".join(
        b.text for b in response.content if getattr(b, "type", None) == "text"
    )

    # Parse the delimited response.
    sources: dict[str, str] = {}
    for match in _BATCH_FENCE_RE.finditer(raw):
        fname, body = match.group(1).strip(), match.group(2)
        # Strip a stray leading/trailing code fence the model sometimes adds.
        body = re.sub(r"^\s*```[a-zA-Z0-9_+-]*\s*\n?", "", body)
        body = re.sub(r"\n?\s*```\s*$", "", body)
        sources[fname] = body.rstrip() + "\n"

    # Fallback: any missing file gets a per-node generation.
    for name, decl, filename in batch:
        if filename not in sources:
            src = _generate_one(
                project, decl, filename, target, generated, types_source,
                client, model, max_tokens, tracker=tracker,
            )
            sources[filename] = src

    # Return keyed by NODE name, not filename.
    return {name: sources[filename] for name, _decl, filename in batch}


def _generate_one(
    project: Project,
    decl: Declaration,
    filename: str,
    target: str,
    generated: dict[str, GeneratedFile],
    types_source: str | None,
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int,
    tracker: "UsageTracker | None" = None,
) -> str:
    meta = _TARGET_META[target]
    spec = _render_spec(decl)
    deps_context = _render_deps_context(decl, generated, target)

    # Everything stable across all node calls in ONE project goes into the
    # system message so the prompt cache can hit it. Per-node variance
    # (spec, filename, deps) stays in the user message.
    system_blocks = _project_system_blocks(
        project.name, meta, types_source,
    )

    user_msg = (
        f"Filename for this node: {filename}\n\n"
        f"Node spec:\n{spec}\n\n"
        f"Dependency interface (import from these):\n"
        f"{deps_context}\n\n"
        f"Emit only the source of `{filename}`."
    )

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_blocks,
        messages=[{"role": "user", "content": user_msg}],
        **thinking_kwargs(model),
    )
    if tracker is not None:
        tracker.record("node", model, response)
    raw = "\n".join(
        b.text for b in response.content if getattr(b, "type", None) == "text"
    )
    return _strip_fences(raw)


def _project_system_blocks(
    project_name: str,
    meta: dict,
    types_source: str | None,
) -> list[dict]:
    """Assemble the per-project stable system message with a cache breakpoint.

    Ordered so the cache-eligible prefix contains everything that doesn't
    change across nodes: base system prompt, target rules, project name,
    and the shared types module. The last block carries `cache_control` so
    the Anthropic API caches this prefix and reuses it across every
    subsequent node call in the same project.
    """
    text = (
        _SYSTEM_PROMPT
        + "\n\nTarget: " + meta["language_name"]
        + "\nRules for this target:\n" + meta["extra_rules"]
        + f"\n\nProject: {project_name}"
    )
    if types_source:
        text += (
            "\n\nShared types (`shared_types.py` — import from this):\n"
            f"```\n{types_source}\n```"
        )
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]
