"""Tests for the Quinny code generator (Anthropic client stubbed)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from quinny.generator import (
    GenerationResult,
    GeneratorError,
    _snake_case,
    generate,
    load_existing_generation,
    regenerate_node,
)
from quinny.parser import parse


@dataclass
class _FakeBlock:
    type: str
    text: str


@dataclass
class _FakeResponse:
    content: list[_FakeBlock]


class _FakeMessages:
    def __init__(self, responder) -> None:
        self._responder = responder
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs) -> _FakeResponse:
        self.calls.append(kwargs)
        return _FakeResponse(
            content=[_FakeBlock(type="text", text=self._responder(kwargs))]
        )


class _FakeClient:
    def __init__(self, responder) -> None:
        self.messages = _FakeMessages(responder)


SAMPLE_QUINNY = (
    "project Chain\n\n"
    "component Base\n"
    "    goal\n"
    "        A shared helper.\n"
    "    output\n"
    "        helper_value\n\n"
    "task Consumer\n"
    "    goal\n"
    "        Uses the base helper.\n"
    "    input\n"
    "        helper_value\n"
    "    depends\n"
    "        Base\n"
)


def _stub_responder(call):
    # Types-synthesis calls have no "Filename for this node:" — return an
    # empty shared_types module. Per-node calls extract their filename.
    text = call["messages"][0]["content"]
    if "Filename for this node:" not in text:
        return "# shared_types.py — no shared types needed\n"
    line = next(l for l in text.splitlines() if l.startswith("Filename for this node:"))
    fname = line.split(":", 1)[1].strip()
    return f"# {fname}\ndef main():\n    return 42\n"


def test_snake_case_conversion():
    assert _snake_case("AuthService") == "auth_service"
    assert _snake_case("Login") == "login"
    assert _snake_case("JWTToken") == "jwt_token"


def test_generate_walks_in_topological_order():
    project = parse(SAMPLE_QUINNY)
    client = _FakeClient(_stub_responder)
    result = generate(project, client=client, shared_types=False)
    assert isinstance(result, GenerationResult)
    names = [f.name for f in result.files]
    assert names.index("Base") < names.index("Consumer")


def test_generate_passes_dependency_source_downstream():
    project = parse(SAMPLE_QUINNY)
    client = _FakeClient(_stub_responder)
    generate(project, client=client, shared_types=False)
    # Consumer's prompt (second call) must include Base's generated source.
    consumer_prompt = client.messages.calls[1]["messages"][0]["content"]
    assert "### Base" in consumer_prompt
    assert "def main" in consumer_prompt  # from Base's stubbed output


def test_generate_typescript_uses_camel_case_filenames():
    project = parse(SAMPLE_QUINNY)
    client = _FakeClient(_stub_responder)
    result = generate(project, client=client, target="typescript", shared_types=False)
    filenames = {f.filename for f in result.files}
    assert filenames == {"base.ts", "consumer.ts"}


def test_generate_with_shared_types_synthesizes_types_first():
    project = parse(SAMPLE_QUINNY)
    client = _FakeClient(_stub_responder)
    result = generate(project, client=client, shared_types=True)
    # Types file first, then Base, then Consumer.
    filenames = [f.filename for f in result.files]
    assert filenames[0] == "shared_types.py"
    assert filenames[1:] == ["base.py", "consumer.py"]
    # The shared types module is included in the CACHEABLE system block so
    # every node sees it without re-sending. Check the system message shape.
    consumer_system = client.messages.calls[-1]["system"]
    # system is now a list of cache-controlled text blocks.
    assert isinstance(consumer_system, list)
    joined = "".join(b["text"] for b in consumer_system)
    assert "shared_types.py" in joined


def test_generate_rejects_unknown_target():
    project = parse(SAMPLE_QUINNY)
    client = _FakeClient(_stub_responder)
    with pytest.raises(GeneratorError, match="Unsupported target"):
        generate(project, client=client, target="rust")


def test_generation_result_writes_files(tmp_path):
    project = parse(SAMPLE_QUINNY)
    client = _FakeClient(_stub_responder)
    result = generate(project, client=client, shared_types=False)
    result.write(tmp_path)
    assert (tmp_path / "base.py").read_text().startswith("# base.py")
    assert (tmp_path / "consumer.py").read_text().startswith("# consumer.py")


def test_load_existing_generation_reads_files_from_disk(tmp_path):
    project = parse(SAMPLE_QUINNY)
    (tmp_path / "shared_types.py").write_text("# shared\n")
    (tmp_path / "base.py").write_text("BASE = 1\n")
    (tmp_path / "consumer.py").write_text("from base import BASE\n")
    existing = load_existing_generation(project, tmp_path)
    names = [f.name for f in existing.files]
    assert names == ["_shared_types", "Base", "Consumer"]
    assert existing.files[1].source == "BASE = 1\n"


def test_regenerate_node_only_touches_one_file(tmp_path):
    project = parse(SAMPLE_QUINNY)
    (tmp_path / "base.py").write_text("BASE = 1\n")
    (tmp_path / "consumer.py").write_text("OLD = True\n")
    existing = load_existing_generation(project, tmp_path)

    client = _FakeClient(_stub_responder)
    fixed = regenerate_node(project, "Consumer", existing, client=client)
    assert fixed.name == "Consumer"
    assert fixed.filename == "consumer.py"
    # Exactly one Claude call — no types synthesis, no touching Base.
    assert len(client.messages.calls) == 1


def test_regenerate_node_rejects_unknown_name(tmp_path):
    project = parse(SAMPLE_QUINNY)
    (tmp_path / "base.py").write_text("BASE = 1\n")
    (tmp_path / "consumer.py").write_text("x = 1\n")
    existing = load_existing_generation(project, tmp_path)
    client = _FakeClient(_stub_responder)
    with pytest.raises(GeneratorError, match="no existing file"):
        regenerate_node(project, "NoSuchNode", existing, client=client)
