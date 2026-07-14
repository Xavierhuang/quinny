"""Token accounting for Claude API calls.

The generator/planner/repair/assembler all funnel their responses through
`UsageTracker.record()`. At the end of a `quinny build`, `total_cost()`
prints a per-stage / per-model summary — this is how you tell whether a
heterogeneous model mix (Opus for design, Sonnet/Haiku for per-node work)
actually saves money on your real projects.

Pricing table is a cached snapshot (2026-04). For live capability lookup
use the Models API.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


# USD per 1M tokens. Cache reads are ~0.1x the input price; cache writes are
# ~1.25x (5min TTL) or 2x (1h TTL) — we ignore cache pricing for now since
# Quinny's per-node prompts are usually below the cacheable minimum.
_MODEL_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4-7":   (5.00, 25.00),
    "claude-opus-4-6":   (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5":  (1.00,  5.00),
}


@dataclass
class UsageCall:
    stage: str          # "planner" | "types" | "node" | "repair" | "assemble"
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        price = _MODEL_PRICES.get(self.model)
        if not price:
            return 0.0
        in_price, out_price = price
        # Cache-read tokens billed at ~10% of input price.
        input_cost = (
            self.input_tokens * in_price
            + self.cache_creation_input_tokens * in_price * 1.25
            + self.cache_read_input_tokens * in_price * 0.1
        ) / 1_000_000
        output_cost = self.output_tokens * out_price / 1_000_000
        return input_cost + output_cost


@dataclass
class UsageTracker:
    calls: list[UsageCall] = field(default_factory=list)
    # Guards `calls` — the generator now fans out per-node calls across a
    # thread pool, and multiple threads may `record()` concurrently.
    _lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    def record(self, stage: str, model: str, response: Any) -> None:
        """Record one API response. `response` is an anthropic.types.Message."""
        u = getattr(response, "usage", None)
        if u is None:
            return
        call = UsageCall(
            stage=stage, model=model,
            input_tokens=int(getattr(u, "input_tokens", 0) or 0),
            output_tokens=int(getattr(u, "output_tokens", 0) or 0),
            cache_read_input_tokens=int(getattr(u, "cache_read_input_tokens", 0) or 0),
            cache_creation_input_tokens=int(
                getattr(u, "cache_creation_input_tokens", 0) or 0
            ),
        )
        with self._lock:
            self.calls.append(call)

    @property
    def total_cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    def by_stage(self) -> dict[str, dict[str, Any]]:
        """Aggregate calls into a stage-keyed summary."""
        acc: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "calls": 0, "input": 0, "output": 0, "cache_read": 0,
            "models": set(),
        })
        for c in self.calls:
            row = acc[c.stage]
            row["calls"] += 1
            row["input"] += c.input_tokens
            row["output"] += c.output_tokens
            row["cache_read"] += c.cache_read_input_tokens
            row["models"].add(c.model)
        return dict(acc)

    def report(self) -> str:
        """Human-readable per-stage token table for stdout."""
        if not self.calls:
            return "(no API calls recorded)"
        by = self.by_stage()
        lines = ["Stage      Calls   In tokens   Out tokens   Total tokens  Model(s)"]
        lines.append("-" * 78)
        for stage in ("planner", "types", "node", "repair", "assemble"):
            if stage not in by:
                continue
            r = by[stage]
            total = r["input"] + r["output"]
            models = ",".join(sorted(r["models"]))
            lines.append(
                f"{stage:<10} {r['calls']:>5}  {r['input']:>10,}  "
                f"{r['output']:>10,}   {total:>12,}  {models}"
            )
        lines.append("-" * 78)
        total_in = sum(c.input_tokens for c in self.calls)
        total_out = sum(c.output_tokens for c in self.calls)
        lines.append(
            f"{'TOTAL':<10} {len(self.calls):>5}  {total_in:>10,}  "
            f"{total_out:>10,}   {total_in + total_out:>12,}"
        )
        return "\n".join(lines)
