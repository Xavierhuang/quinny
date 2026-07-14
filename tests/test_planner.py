"""Tests for the English -> Quinny planner.

The Anthropic client is stubbed out — we're testing the retry/fence-stripping
logic, not the model itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from quinny.planner import PlanResult, PlannerError, _strip_fences, plan_from_english


@dataclass
class _FakeBlock:
    type: str
    text: str


@dataclass
class _FakeResponse:
    content: list[_FakeBlock]


class _FakeMessages:
    def __init__(self, replies: list[str]) -> None:
        self._replies = replies
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs) -> _FakeResponse:
        self.calls.append(kwargs)
        text = self._replies[len(self.calls) - 1]
        return _FakeResponse(content=[_FakeBlock(type="text", text=text)])


class _FakeClient:
    def __init__(self, replies: list[str]) -> None:
        self.messages = _FakeMessages(replies)


VALID_QUINNY = (
    "project Tiny\n\n"
    "task T\n"
    "    goal\n"
    "        Do the thing.\n"
)


def test_strip_fences_removes_markdown_fence():
    text = "```quinny\nproject P\n\ntask T\n    goal\n        Do X.\n```"
    assert _strip_fences(text).startswith("project P")


def test_strip_fences_leaves_bare_source_alone():
    assert _strip_fences("project P\n\ntask T\n    goal\n        Do X.\n").startswith("project P")


def test_plan_succeeds_on_first_try():
    client = _FakeClient(replies=[VALID_QUINNY])
    result = plan_from_english("build a tiny thing", client=client)
    assert isinstance(result, PlanResult)
    assert result.project.name == "Tiny"
    assert result.attempts == 1


def test_plan_recovers_on_bad_output():
    bad = "task T\n    goal\n        Missing project header.\n"
    client = _FakeClient(replies=[bad, VALID_QUINNY])
    result = plan_from_english("build a tiny thing", client=client)
    assert result.attempts == 2
    # The second turn should include the compiler's error as a fix-it prompt.
    followup = client.messages.calls[1]["messages"][-1]
    assert "Fix it" in followup["content"]


def test_plan_gives_up_after_max_retries():
    bad = "definitely not quinny\n"
    client = _FakeClient(replies=[bad] * 3)
    with pytest.raises(PlannerError, match="failed to produce valid Quinny"):
        plan_from_english("build a tiny thing", client=client, max_retries=3)


def test_plan_uses_configured_model_and_adaptive_thinking():
    client = _FakeClient(replies=[VALID_QUINNY])
    plan_from_english("x", client=client, model="claude-sonnet-4-6")
    call = client.messages.calls[0]
    assert call["model"] == "claude-sonnet-4-6"
    assert call["thinking"] == {"type": "adaptive"}
