"""Quinny's verification layer: compile a plan's acceptance criteria (the
`test` and `success` fields) into an executable test suite and run it against
ANY implementation — human- or agent-written, in any supported language.

This is the inverse of code generation. Instead of asking a model to *write*
code from intent (which one-shot models already do better than a decomposing
pipeline), Quinny turns intent into an objective, model-agnostic *gate* that
verifies whatever code you point it at. Verification is the thing LLMs are bad
at doing for themselves, so a durable, reviewable `.qn` contract is worth having.

Language targets (`--lang`): `python` (pytest) and `js` (Node's built-in
`node:test`, no npm). The `.qn` contract is language-agnostic; only the emitted
suite differs.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from quinny.nodes import Project, ProseField
from quinny.parser import parse_file
from quinny._capabilities import make_client, thinking_kwargs


@dataclass
class Criterion:
    index: int
    node: str
    kind: str      # "test" | "success"
    text: str


@dataclass
class CriterionResult:
    criterion: Criterion
    status: str    # "PASS" | "FAIL" | "ERROR" | "MISSING"


def extract_criteria(project: Project) -> list[Criterion]:
    out: list[Criterion] = []
    for decl in project.all_declarations():
        for f in decl.fields:
            if isinstance(f, ProseField) and f.kind in ("test", "success"):
                for line in f.lines:
                    line = line.strip()
                    if line:
                        out.append(Criterion(len(out) + 1, decl.name, f.kind, line))
    return out


# ---------------------------- language targets ----------------------------

def _surface_py(impl_dir: Path) -> str:
    parts = []
    for py in sorted(impl_dir.glob("*.py")):
        if py.name.startswith("_") or py.name == "main.py":
            continue
        try:
            tree = ast.parse(py.read_text())
        except SyntaxError:
            continue
        names = [n.name for n in tree.body
                 if isinstance(n, (ast.ClassDef, ast.FunctionDef))]
        if names:
            parts.append(f"- {py.name}: {', '.join(names)}")
    return "\n".join(parts) or "(no importable modules found)"


def _surface_js(impl_dir: Path) -> str:
    parts = []
    for js in sorted(impl_dir.glob("*.js")):
        if js.name.endswith(".test.js") or js.name == "main.js":
            continue
        text = js.read_text()
        names = set(re.findall(r"\b(?:class|function)\s+([A-Za-z_]\w*)", text))
        names |= set(re.findall(r"exports\.([A-Za-z_]\w*)", text))
        for block in re.findall(r"module\.exports\s*=\s*{([^}]*)}", text):
            names |= set(re.findall(r"([A-Za-z_]\w*)", block))
        if names:
            parts.append(f"- {js.name}: exports {', '.join(sorted(names))}")
    return "\n".join(parts) or "(no modules found)"


def _parse_pytest(out: str) -> dict[int, str]:
    status = {}
    for m in re.finditer(r"test_c(\d+)\b.*?(PASSED|FAILED|ERROR)", out):
        status[int(m.group(1))] = {"PASSED": "PASS", "FAILED": "FAIL",
                                   "ERROR": "ERROR"}[m.group(2)]
    return status


def _parse_tap(out: str) -> dict[int, str]:
    status = {}
    for line in out.splitlines():
        m = re.match(r"(not ok|ok)\b.*?\bc(\d+)\b", line.strip())
        if m:
            status[int(m.group(2))] = "PASS" if m.group(1) == "ok" else "FAIL"
    return status


_SYSTEM_PY = """You write a pytest acceptance suite that checks whether an \
implementation satisfies a specification. Output ONLY one Python module — no \
prose, no markdown fences.

Rules:
- Import the public API from the implementation's ACTUAL modules (listed below).
- Write EXACTLY one test function per numbered criterion, named test_c01, \
test_c02, ... matching the numbers. Put the criterion text in the docstring.
- Each test asserts the described behavior; use `pytest.raises` for errors.
- Only standard library + pytest. Do not test anything outside the criteria."""

_SYSTEM_JS = """You write a Node.js acceptance suite (using the built-in \
`node:test` and `node:assert`, no npm packages) that checks whether an \
implementation satisfies a specification. Output ONLY one JavaScript file — no \
prose, no markdown fences.

Rules:
- `require` the public API from the implementation's ACTUAL modules (listed below).
- Write EXACTLY one `test('c01', () => { ... })` per numbered criterion, named \
c01, c02, ... matching the numbers.
- Each test asserts the described behavior with `node:assert`; use \
`assert.throws` for error criteria.
- Only Node built-ins. Do not test anything outside the criteria."""


LANGS = {
    "python": {
        "system": _SYSTEM_PY, "surface": _surface_py, "parse": _parse_pytest,
        "suffix": "_quinny_contract_test.py",
        "cmd": lambda p: [sys.executable, "-m", "pytest", str(p), "-v", "--tb=no",
                          "-o", "addopts=", "-p", "no:cacheprovider"],
        "env": lambda impl: {"PYTHONPATH": str(impl)},
    },
    "js": {
        "system": _SYSTEM_JS, "surface": _surface_js, "parse": _parse_tap,
        "suffix": ".quinny.contract.test.js",
        "cmd": lambda p: ["node", "--test", "--test-reporter=tap", str(p)],
        "env": lambda impl: {},
    },
}


def build_suite(spec_text: str, impl_dir: Path, criteria: list[Criterion],
                model: str, lang: str = "python") -> str:
    cfg = LANGS[lang]
    listing = cfg["surface"](impl_dir)
    crit_block = "\n".join(f"{c.index}. [{c.node}/{c.kind}] {c.text}"
                           for c in criteria)
    user = (
        f"Implementation modules and their public names:\n{listing}\n\n"
        f"Specification (for context):\n{spec_text}\n\n"
        f"Criteria to test (one test each):\n{crit_block}\n\n"
        f"Emit the {lang} test module now."
    )
    client = make_client()
    resp = client.messages.create(
        model=model, max_tokens=8000, system=cfg["system"],
        messages=[{"role": "user", "content": user}],
        **thinking_kwargs(model),
    )
    raw = "\n".join(b.text for b in resp.content
                    if getattr(b, "type", None) == "text")
    m = re.match(r"```(?:\w+)?\s*\n(.*?)\n```", raw, re.DOTALL)
    return m.group(1) if m else raw.strip()


def run_suite(impl_dir: Path, suite_src: str, criteria: list[Criterion],
              lang: str = "python") -> list[CriterionResult]:
    cfg = LANGS[lang]
    status = {c.index: "MISSING" for c in criteria}
    with tempfile.NamedTemporaryFile("w", suffix=cfg["suffix"],
                                     dir=str(impl_dir), delete=False) as fh:
        fh.write(suite_src)
        suite_path = Path(fh.name)
    try:
        env = {**os.environ, **cfg["env"](impl_dir)}
        r = subprocess.run(cfg["cmd"](suite_path), cwd=str(impl_dir), env=env,
                           capture_output=True, text=True, timeout=120)
        status.update(cfg["parse"](r.stdout + r.stderr))
    finally:
        suite_path.unlink(missing_ok=True)
    return [CriterionResult(c, status[c.index]) for c in criteria]


def verify(plan_path: Path, impl_dir: Path, model: str,
           emit: Path | None = None, lang: str = "python") -> list[CriterionResult]:
    project = parse_file(plan_path)
    criteria = extract_criteria(project)
    if not criteria:
        return []
    suite = build_suite(plan_path.read_text(), impl_dir, criteria, model, lang)
    if emit is not None:
        emit.write_text(suite if suite.endswith("\n") else suite + "\n")
    return run_suite(impl_dir, suite, criteria, lang)


def run_saved(plan_path: Path, impl_dir: Path, suite_path: Path,
              lang: str = "python") -> list[CriterionResult]:
    """Re-run a previously emitted suite — no LLM call. Emit once, review, then
    run deterministically forever (this is how you lock a contract into CI)."""
    project = parse_file(plan_path)
    criteria = extract_criteria(project)
    return run_suite(impl_dir, suite_path.read_text(), criteria, lang)
