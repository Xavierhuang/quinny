"""Tests for the verifier — real subprocess execution, no Claude calls."""

from __future__ import annotations

from pathlib import Path

import pytest

from quinny.generator import GeneratedFile, GenerationResult
from quinny.verifier import verify, verify_python_file


def _write(tmp_path: Path, name: str, source: str) -> Path:
    p = tmp_path / name
    p.write_text(source)
    return p


def test_verify_python_file_passes_on_clean_module(tmp_path):
    path = _write(tmp_path, "good.py", "x = 1\n")
    check = verify_python_file(path, tmp_path)
    assert check.passed
    assert check.stage == "ok"


def test_verify_catches_syntax_error(tmp_path):
    path = _write(tmp_path, "bad.py", "def broken(:\n")
    check = verify_python_file(path, tmp_path)
    assert not check.passed
    assert check.stage == "syntax"
    assert "SyntaxError" in check.log


def test_verify_catches_missing_import(tmp_path):
    path = _write(tmp_path, "missing.py", "import definitely_not_a_real_module_xyz\n")
    check = verify_python_file(path, tmp_path)
    assert not check.passed
    assert check.stage == "import"
    assert "ModuleNotFoundError" in check.log or "No module" in check.log


def test_verify_resolves_sibling_imports_via_pythonpath(tmp_path):
    _write(tmp_path, "base.py", "def hello():\n    return 'hi'\n")
    consumer = _write(tmp_path, "consumer.py", "from base import hello\n")
    check = verify_python_file(consumer, tmp_path)
    assert check.passed, check.log


def test_verify_result_aggregates_pass_and_fail(tmp_path):
    _write(tmp_path, "ok.py", "x = 1\n")
    _write(tmp_path, "broken.py", "import nope_nope_nope\n")
    generation = GenerationResult(
        project="Mixed",
        target="python",
        files=[
            GeneratedFile(name="Ok", kind="task", filename="ok.py", source=""),
            GeneratedFile(name="Broken", kind="task", filename="broken.py", source=""),
        ],
    )
    vr = verify(generation, tmp_path)
    assert not vr.all_passed
    assert len(vr.failures) == 1
    assert vr.failures[0].filename == "broken.py"


def test_full_verify_catches_runtime_failure(tmp_path):
    # Import passes (module loads), but the __main__ block raises.
    path = _write(tmp_path, "boom.py",
        "def go():\n"
        "    return 1 / 0\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    go()\n"
    )
    fast = verify_python_file(path, tmp_path, full=False)
    assert fast.passed and fast.stage == "ok"

    full = verify_python_file(path, tmp_path, full=True)
    assert not full.passed
    assert full.stage == "run"
    assert "ZeroDivisionError" in full.log


def test_full_verify_passes_when_main_succeeds(tmp_path):
    path = _write(tmp_path, "greet.py",
        "if __name__ == '__main__':\n"
        "    print('hi')\n"
    )
    check = verify_python_file(path, tmp_path, full=True)
    assert check.passed and check.stage == "ok"


def test_verify_skips_non_python_targets(tmp_path):
    generation = GenerationResult(
        project="TS",
        target="typescript",
        files=[GeneratedFile(name="X", kind="task", filename="x.ts", source="")],
    )
    vr = verify(generation, tmp_path)
    assert vr.all_passed
    assert vr.checks[0].stage == "skipped"
