"""JSON representation of a Quinny plan.

Same 10 concepts as the DSL, expressed as a JSON object that a JSON Schema
can validate deterministically. The `PLAN_SCHEMA` is what we send to the
Anthropic API's structured-output mode so the model's output is
guaranteed-conforming JSON.

Downstream compiler stages (graph builder, generator, verifier) all consume
the same `Project` AST as the DSL parser — we just have an extra front-end
that reads JSON instead of the indented DSL. The rest of the pipeline is
format-agnostic.
"""

from __future__ import annotations

import json
from typing import Any

from quinny.nodes import (
    Component,
    Field,
    NameField,
    Project,
    ProseField,
    Task,
)


# JSON Schema — enforced when the model produces a plan via structured output.
# Kept small on purpose: the semantic checks (cycles, unresolved refs, missing
# goals) still happen in `quinny.graph.build_graph`, which schema can't express.
_NAME_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]*$"

# Anthropic's structured output rejects self-referencing schemas, so we
# flatten to a fixed shape: no recursive `subtasks`/`subcomponents`.
# Hierarchical decomposition is still expressible in the DSL; it just
# doesn't survive the JSON round-trip. In practice benchmarks and most
# real projects use the flat form, so this is a minor loss.
PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["project", "declarations"],
    "properties": {
        "project": {"type": "string", "pattern": _NAME_PATTERN},
        "declarations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "name", "goal"],
                "properties": {
                    "kind": {"type": "string", "enum": ["task", "component"]},
                    "name": {"type": "string", "pattern": _NAME_PATTERN},
                    "goal": {"type": "string"},
                    "constraint": {"type": "array", "items": {"type": "string"}},
                    "test":       {"type": "array", "items": {"type": "string"}},
                    "success":    {"type": "array", "items": {"type": "string"}},
                    "input":   {"type": "array",
                                "items": {"type": "string", "pattern": _NAME_PATTERN}},
                    "output":  {"type": "array",
                                "items": {"type": "string", "pattern": _NAME_PATTERN}},
                    "depends": {"type": "array",
                                "items": {"type": "string", "pattern": _NAME_PATTERN}},
                    "uses":    {"type": "array",
                                "items": {"type": "string", "pattern": _NAME_PATTERN}},
                },
            },
        },
    },
}


class JsonPlanError(Exception):
    pass


def json_to_ast(source: str | dict) -> Project:
    """Parse a JSON plan into the shared Project AST."""
    data = json.loads(source) if isinstance(source, str) else source
    if not isinstance(data, dict) or "project" not in data or "declarations" not in data:
        raise JsonPlanError("Plan must be an object with `project` and `declarations`.")
    decls = tuple(_decl_from_json(d) for d in data["declarations"])
    return Project(name=data["project"], declarations=decls)


def _decl_from_json(node: dict) -> Task | Component:
    kind = node.get("kind")
    name = node.get("name")
    if kind not in ("task", "component"):
        raise JsonPlanError(f"declaration `kind` must be 'task' or 'component', got {kind!r}")
    if not isinstance(name, str) or not name:
        raise JsonPlanError("declaration missing `name`")

    fields: list[Field] = []
    goal = node.get("goal")
    if goal:
        fields.append(ProseField(kind="goal", lines=(goal,)))
    for prose_kind in ("constraint", "test", "success"):
        if node.get(prose_kind):
            fields.append(ProseField(kind=prose_kind,
                                     lines=tuple(node[prose_kind])))
    for name_kind in ("input", "output", "depends", "uses"):
        if node.get(name_kind):
            fields.append(NameField(kind=name_kind,
                                    names=tuple(node[name_kind])))

    subtasks = tuple(_decl_from_json(x) for x in node.get("subtasks", [])
                     if x.get("kind") == "task")
    subcomponents = tuple(_decl_from_json(x) for x in node.get("subcomponents", [])
                          if x.get("kind") == "component")

    if kind == "task":
        return Task(name=name, fields=tuple(fields),
                    subtasks=subtasks, subcomponents=subcomponents)
    return Component(name=name, fields=tuple(fields),
                     subtasks=subtasks, subcomponents=subcomponents)


def ast_to_json(project: Project) -> str:
    """Round-trip a Project AST into JSON (used by tests + the CLI)."""
    return json.dumps({
        "project": project.name,
        "declarations": [_decl_to_json(d) for d in project.declarations],
    }, indent=2)


def _decl_to_json(decl: Task | Component) -> dict:
    kind = "task" if isinstance(decl, Task) else "component"
    out: dict[str, Any] = {"kind": kind, "name": decl.name}
    for f in decl.fields:
        if isinstance(f, ProseField):
            if f.kind == "goal":
                out["goal"] = f.lines[0] if f.lines else ""
            else:
                out[f.kind] = list(f.lines)
        elif isinstance(f, NameField):
            out[f.kind] = list(f.names)
    if decl.subtasks:
        out["subtasks"] = [_decl_to_json(s) for s in decl.subtasks]
    if decl.subcomponents:
        out["subcomponents"] = [_decl_to_json(s) for s in decl.subcomponents]
    return out
