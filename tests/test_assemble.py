"""Tests for the assembly step (main.py + requirements.txt + README.md).

The deterministic pieces (requirements, README) don't touch the network. The
main.py path uses a stubbed Anthropic client.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from quinny.assemble import (
    AssembleError,
    assemble,
    derive_readme,
    derive_requirements,
)
from quinny.generator import GeneratedFile, GenerationResult
from quinny.parser import parse


SAMPLE_QUINNY = (
    "project Chain\n\n"
    "component Base\n"
    "    goal\n"
    "        Shared helper.\n\n"
    "task Consumer\n"
    "    goal\n"
    "        Uses the helper.\n"
    "    depends\n"
    "        Base\n"
)


def _gen(files: list[tuple[str, str, str]]) -> GenerationResult:
    """files = [(name, filename, source), …]"""
    return GenerationResult(
        project="Chain", target="python",
        files=[GeneratedFile(name=n, kind="task", filename=fn, source=src)
               for n, fn, src in files],
    )


# ------------- requirements.txt (deterministic, no Claude) --------------

def test_requirements_filters_stdlib_and_siblings():
    gen = _gen([
        ("Base",     "base.py",     "import os\nimport json\n"),
        ("Consumer", "consumer.py", "import requests\nfrom base import x\n"),
    ])
    reqs = derive_requirements(gen)
    assert "requests" in reqs
    assert "os" not in reqs           # stdlib
    assert "json" not in reqs         # stdlib
    assert "base" not in reqs         # sibling


def test_requirements_handles_dotted_imports():
    gen = _gen([
        ("A", "a.py", "from anthropic.types import Message\nimport lark.indenter\n"),
    ])
    reqs = derive_requirements(gen)
    assert "anthropic" in reqs
    assert "lark" in reqs


def test_requirements_returns_placeholder_when_empty():
    gen = _gen([("A", "a.py", "x = 1\n")])
    reqs = derive_requirements(gen)
    assert reqs.startswith("#")   # comment placeholder


def test_requirements_skips_files_with_syntax_errors():
    # A broken file shouldn't crash the AST walk — just gets skipped.
    gen = _gen([
        ("Bad",  "bad.py",  "def broken(:\n"),
        ("Good", "good.py", "import requests\n"),
    ])
    reqs = derive_requirements(gen)
    assert "requests" in reqs


# ------------- README.md (deterministic, no Claude) --------------------

def test_readme_lists_every_declaration_with_goal():
    project = parse(SAMPLE_QUINNY)
    gen = _gen([
        ("Base",     "base.py",     "x = 1\n"),
        ("Consumer", "consumer.py", "y = 2\n"),
    ])
    readme = derive_readme(project, gen)
    assert "# Chain" in readme
    assert "`base.py`" in readme
    assert "`consumer.py`" in readme
    assert "Shared helper" in readme
    assert "Uses the helper" in readme
    assert "python main.py" in readme


# ------------- main.py (Claude-generated, stubbed) ----------------------

@dataclass
class _FakeBlock:
    type: str
    text: str


@dataclass
class _FakeResponse:
    content: list[_FakeBlock]


class _FakeMessages:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs) -> _FakeResponse:
        self.calls.append(kwargs)
        return _FakeResponse(content=[_FakeBlock(type="text", text=self.reply)])


class _FakeClient:
    def __init__(self, reply: str) -> None:
        self.messages = _FakeMessages(reply)


def test_assemble_produces_all_three_files(tmp_path: Path):
    project = parse(SAMPLE_QUINNY)
    gen = _gen([
        ("Base",     "base.py",     "def hello():\n    return 'hi'\n"),
        ("Consumer", "consumer.py", "from base import hello\n"),
    ])
    good_main = (
        "from base import hello\n"
        "\n"
        "if __name__ == \"__main__\":\n"
        "    print(hello())\n"
    )
    client = _FakeClient(good_main)
    result = assemble(project, gen, client=client)
    assert "hello" in result.main_py
    assert "# No third-party" in result.requirements_txt or "requests" not in result.requirements_txt
    assert "# Chain" in result.readme_md

    result.write(tmp_path)
    assert (tmp_path / "main.py").exists()
    assert (tmp_path / "requirements.txt").exists()
    assert (tmp_path / "README.md").exists()


def test_assemble_falls_back_when_main_wont_compile(tmp_path: Path):
    project = parse(SAMPLE_QUINNY)
    gen = _gen([("Base", "base.py", "x = 1\n")])
    # Model returns junk that won't parse.
    client = _FakeClient("this is not python (:\n")
    result = assemble(project, gen, client=client)
    # Fallback stub is a valid import-only main.
    compile(result.main_py, "main.py", "exec")
    assert "import base" in result.main_py


def test_assemble_rejects_non_python_target():
    project = parse(SAMPLE_QUINNY)
    gen = GenerationResult(project="X", target="typescript", files=[])
    with pytest.raises(AssembleError):
        assemble(project, gen, client=_FakeClient(""))
