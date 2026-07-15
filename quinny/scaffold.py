"""`quinny scaffold` — from a plain-English idea, scope out the part where
correctness actually matters (the logic: calculations, rules, state, validation),
draft a Quinny contract for *just that*, and stub the module so you go straight
to implement → verify.

This bridges "I can only say build me X" to "…and here's a gate on the money
logic": the user never hand-writes a contract, and Quinny deliberately ignores
UI/pages/styling (which `verify` can't gate anyway) and targets the testable core.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from quinny._capabilities import make_client, thinking_kwargs

_EXT = {"python": "py", "js": "js"}
_STUB_RULE = {
    "python": "a Python module; function/method bodies are `raise NotImplementedError`; "
              "start the block with `# <module>.py`",
    "js": "a JavaScript module using `module.exports`; bodies `throw new Error(\"not implemented\")`; "
          "start the block with `// <module>.js`",
}


@dataclass
class Scaffold:
    idea: str
    qn_path: Path
    stub_path: Path
    project: str
    criteria: int


_SYSTEM = """You scope the VERIFIABLE LOGIC out of a software idea and write a \
Quinny acceptance contract for it.

From the idea, pick the one core piece where CORRECTNESS matters — calculations, \
rules, state transitions, validation (e.g. cart totals, pricing, discounts, \
inventory, auth). IGNORE UI, pages, styling, routing, and glue: those can't be \
unit-verified and are the agent's job, not the contract's.

Output EXACTLY two fenced blocks, in this order, and NOTHING else:

1. ```qn — a Quinny contract that MUST start with a `project <Name>` line, then \
one `component` with a `goal`, `constraint` lines pinning a concrete public API \
(a single module exposing named functions or a class), and 4-8 concrete `test` \
criteria covering normal behavior AND edge cases (invalid input, boundaries, \
errors that must be raised).

2. ```<lang> — a stub of that module: {stub_rule}. Include every function/method \
from the API with a one-line docstring/comment, but no real implementation."""


def _block(text: str, *tags: str) -> str | None:
    for tag in tags:
        m = re.search(rf"```{tag}\s*\n(.*?)\n```", text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


_FIELD_KW = {"goal", "input", "output", "constraint", "depends", "uses",
             "test", "success"}


def _normalize_qn(qn: str) -> str:
    """Small models often write fields inline as `test: <text>`; Quinny wants the
    keyword on its own line with the text indented below. Rewrite that shape."""
    out = []
    for line in qn.splitlines():
        m = re.match(r"^(\s*)(\w+):[ \t]*(.*)$", line)
        if m and m.group(2) in _FIELD_KW:
            indent, kw, text = m.groups()
            out.append(f"{indent}{kw}")
            if text.strip():
                out.append(f"{indent}    {text.strip()}")
        else:
            out.append(line)
    return "\n".join(out)


def _module_filename(stub: str, lang: str, fallback: str) -> str:
    m = re.search(r"^\s*(?:#|//)\s*([A-Za-z_]\w*\.\w+)", stub, re.M)
    if m:
        return m.group(1)
    return f"{fallback}.{_EXT[lang]}"


def scaffold(idea: str, out_dir: Path, lang: str = "python",
             model: str = "claude-haiku-4-5") -> Scaffold:
    from quinny.parser import parse_file
    from quinny.contract import extract_criteria

    client = make_client()
    resp = client.messages.create(
        model=model, max_tokens=4000,
        system=_SYSTEM.format(stub_rule=_STUB_RULE[lang]),
        messages=[{"role": "user", "content":
                   f"Idea: {idea}\n\nTarget language: {lang}. Emit the two blocks now."}],
        **thinking_kwargs(model),
    )
    raw = "\n".join(b.text for b in resp.content
                    if getattr(b, "type", None) == "text")
    qn = _block(raw, "qn", "quinny")
    stub = _block(raw, lang, "python", "javascript", "js")
    if not qn or not stub:
        raise ValueError("scaffold: model did not return both a contract and a stub")

    qn = _normalize_qn(qn)
    # Safety net: a contract must open with `project <Name>`.
    if not re.match(r"\s*project\b", qn):
        name = re.sub(r"\W+", "", idea.title())[:32] or "Scaffold"
        qn = f"project {name}\n\n{qn}"

    out_dir.mkdir(parents=True, exist_ok=True)
    stub_name = _module_filename(stub, lang, "core")
    base = stub_name.rsplit(".", 1)[0]
    qn_path = out_dir / f"{base}.qn"
    stub_path = out_dir / stub_name
    qn_path.write_text(qn if qn.endswith("\n") else qn + "\n")
    stub_path.write_text(stub if stub.endswith("\n") else stub + "\n")

    project = parse_file(qn_path)
    return Scaffold(idea=idea, qn_path=qn_path, stub_path=stub_path,
                    project=project.name, criteria=len(extract_criteria(project)))
