"""Verify generated code.

Two tiers, both driven by the same NodeCheck / VerifyResult / repair loop:

* **Fast (default)** — `compile()` for syntax and a subprocess `import <mod>`
  for import resolution. Never runs user code; safe to run on anything.

* **Full (`full=True`)** — after fast passes, actually run each file with
  `python <file>` under a timeout. The generator's system prompt places
  every task's tests in an `if __name__ == "__main__":` block, so running
  the file executes those tests. Catches runtime bugs the fast tier misses,
  at the cost of flaking on files that need real DBs, sockets, env vars, etc.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from quinny.generator import GenerationResult


@dataclass
class NodeCheck:
    name: str
    filename: str
    passed: bool
    stage: str          # "syntax" | "import" | "run" | "skipped" | "ok"
    log: str


@dataclass
class VerifyResult:
    target: str
    checks: list[NodeCheck] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failures(self) -> list[NodeCheck]:
        return [c for c in self.checks if not c.passed]


def verify_python_file(
    file_path: Path,
    out_dir: Path,
    *,
    timeout: int = 15,
    full: bool = False,
) -> NodeCheck:
    name = file_path.stem
    source = file_path.read_text()

    # 1. Syntax.
    try:
        compile(source, str(file_path), "exec")
    except SyntaxError as e:
        return NodeCheck(
            name=name, filename=file_path.name, passed=False,
            stage="syntax", log=f"{e.__class__.__name__}: {e}",
        )

    # 2. Import via subprocess so a bad module can't crash the verifier
    #    process. PYTHONPATH lets `from <sibling> import X` resolve.
    module = file_path.stem
    env = os.environ.copy()
    env["PYTHONPATH"] = str(out_dir) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(out_dir), env=env,
        )
    except subprocess.TimeoutExpired:
        return NodeCheck(
            name=name, filename=file_path.name, passed=False,
            stage="import", log=f"Import timed out after {timeout}s.",
        )

    if result.returncode != 0:
        return NodeCheck(
            name=name, filename=file_path.name, passed=False,
            stage="import", log=result.stderr.strip() or result.stdout.strip(),
        )

    # 3. Full mode — run the file so its `if __name__ == "__main__":`
    #    test block executes. Missing `__main__` blocks are fine; the file
    #    just runs to completion silently.
    if full:
        try:
            # Absolute path so `cwd=out_dir` doesn't turn a relative
            # path like `.smoke_out/foo.py` into `.smoke_out/.smoke_out/foo.py`.
            run = subprocess.run(
                [sys.executable, str(file_path.resolve())],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(out_dir), env=env,
            )
        except subprocess.TimeoutExpired:
            return NodeCheck(
                name=name, filename=file_path.name, passed=False,
                stage="run", log=f"Execution timed out after {timeout}s.",
            )
        if run.returncode != 0:
            return NodeCheck(
                name=name, filename=file_path.name, passed=False,
                stage="run",
                log=run.stderr.strip() or run.stdout.strip()
                    or f"exit code {run.returncode}",
            )

    return NodeCheck(
        name=name, filename=file_path.name, passed=True, stage="ok",
        log="",
    )


def verify(
    generation: GenerationResult,
    out_dir: Path,
    *,
    full: bool = False,
) -> VerifyResult:
    """Verify every file the generator produced."""
    vr = VerifyResult(target=generation.target)
    if generation.target != "python":
        for f in generation.files:
            vr.checks.append(NodeCheck(
                name=f.name, filename=f.filename, passed=True,
                stage="skipped",
                log=f"Verifier for target '{generation.target}' not implemented yet.",
            ))
        return vr
    for f in generation.files:
        vr.checks.append(
            verify_python_file(out_dir / f.filename, out_dir, full=full)
        )
    return vr
