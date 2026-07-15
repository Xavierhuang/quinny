"""Quinny's verification layer: compile a plan's acceptance criteria (the
`test` and `success` fields) into an executable pytest suite and run it against
ANY implementation — human-written, agent-written, whatever.

This is the inverse of code generation. Instead of asking a model to *write*
code from intent (which one-shot models already do better than a decomposing
pipeline), Quinny turns intent into an objective, model-agnostic *gate* that
verifies whatever code you point it at. Verification is the thing LLMs are bad
at doing for themselves, so a durable, reviewable `.qn` contract is worth having.
"""
from __future__ import annotations

import ast
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
    """Every line of every `test`/`success` field, in plan order."""
    out: list[Criterion] = []
    for decl in project.all_declarations():
        for f in decl.fields:
            if isinstance(f, ProseField) and f.kind in ("test", "success"):
                for line in f.lines:
                    line = line.strip()
                    if line:
                        out.append(Criterion(len(out) + 1, decl.name, f.kind, line))
    return out


def impl_surface(impl_dir: Path) -> str:
    """List each .py file and its top-level class/def names, so the test
    generator imports from the modules that actually exist."""
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


_SYSTEM = """You write a pytest acceptance suite that checks whether an \
implementation satisfies a specification. Output ONLY one Python module — no \
prose, no markdown fences.

Rules:
- Import the public API from the implementation's ACTUAL modules (listed below).
- Write EXACTLY one test function per numbered criterion, named test_c01, \
test_c02, ... matching the numbers. Put the criterion text in the docstring.
- Each test asserts the described behavior; use `pytest.raises` for errors.
- Only standard library + pytest. Do not test anything outside the criteria."""


def build_suite(spec_text: str, impl_dir: Path, criteria: list[Criterion],
                model: str) -> str:
    listing = impl_surface(impl_dir)
    crit_block = "\n".join(f"{c.index}. [{c.node}/{c.kind}] {c.text}"
                           for c in criteria)
    user = (
        f"Implementation modules and their public names:\n{listing}\n\n"
        f"Specification (for context):\n{spec_text}\n\n"
        f"Criteria to test (one test function each):\n{crit_block}\n\n"
        f"Emit the pytest module now."
    )
    client = make_client()
    resp = client.messages.create(
        model=model, max_tokens=8000, system=_SYSTEM,
        messages=[{"role": "user", "content": user}],
        **thinking_kwargs(model),
    )
    raw = "\n".join(b.text for b in resp.content
                    if getattr(b, "type", None) == "text")
    m = re.match(r"```(?:python)?\s*\n(.*?)\n```", raw, re.DOTALL)
    return m.group(1) if m else raw.strip()


_RESULT_RE = re.compile(r"test_c(\d+)\b.*?(PASSED|FAILED|ERROR)")


def run_suite(impl_dir: Path, suite_src: str,
              criteria: list[Criterion]) -> list[CriterionResult]:
    status = {c.index: "MISSING" for c in criteria}
    with tempfile.NamedTemporaryFile("w", suffix="_contract_test.py",
                                     dir=str(impl_dir), delete=False) as fh:
        fh.write(suite_src)
        suite_path = Path(fh.name)
    try:
        env = {"PYTHONPATH": str(impl_dir)}
        import os
        env = {**os.environ, **env}
        r = subprocess.run(
            [sys.executable, "-m", "pytest", str(suite_path), "-v", "--tb=no",
             "-o", "addopts=", "-p", "no:cacheprovider"],
            cwd=str(impl_dir), env=env, capture_output=True, text=True, timeout=120,
        )
        for line in (r.stdout + r.stderr).splitlines():
            m = _RESULT_RE.search(line)
            if m:
                idx = int(m.group(1))
                status[idx] = {"PASSED": "PASS", "FAILED": "FAIL",
                               "ERROR": "ERROR"}[m.group(2)]
    finally:
        suite_path.unlink(missing_ok=True)
    return [CriterionResult(c, status[c.index]) for c in criteria]


def verify(plan_path: Path, impl_dir: Path, model: str,
           emit: Path | None = None) -> list[CriterionResult]:
    project = parse_file(plan_path)
    criteria = extract_criteria(project)
    if not criteria:
        return []
    suite = build_suite(plan_path.read_text(), impl_dir, criteria, model)
    if emit is not None:
        emit.write_text(suite if suite.endswith("\n") else suite + "\n")
    return run_suite(impl_dir, suite, criteria)


def run_saved(plan_path: Path, impl_dir: Path,
              suite_path: Path) -> list[CriterionResult]:
    """Re-run a previously emitted suite — no LLM call. This is how you lock a
    contract into CI: emit once, review, then run deterministically forever."""
    project = parse_file(plan_path)
    criteria = extract_criteria(project)
    return run_suite(impl_dir, suite_path.read_text(), criteria)
