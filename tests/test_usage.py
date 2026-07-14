"""Tests for the token/cost usage tracker."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from quinny.usage import UsageCall, UsageTracker


@dataclass
class _FakeUsage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class _FakeResponse:
    usage: _FakeUsage


def test_records_calls_with_stage_and_model():
    t = UsageTracker()
    t.record("planner", "claude-opus-4-7",
             _FakeResponse(_FakeUsage(input_tokens=1000, output_tokens=500)))
    t.record("node", "claude-haiku-4-5",
             _FakeResponse(_FakeUsage(input_tokens=2000, output_tokens=800)))
    assert len(t.calls) == 2
    assert t.calls[0].stage == "planner"
    assert t.calls[1].stage == "node"


def test_cost_uses_correct_model_pricing():
    # Opus 4.7: $5 in / $25 out per 1M
    call = UsageCall(stage="planner", model="claude-opus-4-7",
                     input_tokens=1_000_000, output_tokens=1_000_000)
    assert call.cost_usd == pytest.approx(5.0 + 25.0)

    # Haiku 4.5: $1 in / $5 out per 1M
    call = UsageCall(stage="node", model="claude-haiku-4-5",
                     input_tokens=1_000_000, output_tokens=1_000_000)
    assert call.cost_usd == pytest.approx(1.0 + 5.0)


def test_cache_read_discount_applied():
    # Cache reads billed at ~10% of input price.
    call = UsageCall(stage="node", model="claude-sonnet-4-6",
                     input_tokens=0, output_tokens=0,
                     cache_read_input_tokens=1_000_000)
    assert call.cost_usd == pytest.approx(3.0 * 0.1)  # 0.30


def test_unknown_model_costs_zero_without_crashing():
    call = UsageCall(stage="node", model="some-future-model",
                     input_tokens=999_999, output_tokens=999_999)
    assert call.cost_usd == 0.0


def test_by_stage_aggregates_multiple_calls():
    t = UsageTracker()
    for _ in range(3):
        t.record("node", "claude-haiku-4-5",
                 _FakeResponse(_FakeUsage(input_tokens=100, output_tokens=50)))
    t.record("planner", "claude-opus-4-7",
             _FakeResponse(_FakeUsage(input_tokens=500, output_tokens=200)))
    by = t.by_stage()
    assert by["node"]["calls"] == 3
    assert by["node"]["input"] == 300
    assert by["planner"]["calls"] == 1


def test_report_renders_without_calls():
    t = UsageTracker()
    assert "no API calls" in t.report()


def test_report_includes_total_line():
    t = UsageTracker()
    t.record("node", "claude-haiku-4-5",
             _FakeResponse(_FakeUsage(input_tokens=100, output_tokens=50)))
    report = t.report()
    assert "TOTAL" in report
    assert "node" in report


def test_response_without_usage_attribute_is_ignored():
    t = UsageTracker()
    t.record("node", "claude-opus-4-7", object())   # no `.usage`
    assert t.calls == []
