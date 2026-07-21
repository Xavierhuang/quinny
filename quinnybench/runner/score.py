"""Aggregate a run's index.json into per-model / per-category tables.

    python -m runner.score results/2026-07-21-1830/

Prints a Markdown table by default; add --json to emit machine-readable output
for the site builder.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import defaultdict


def aggregate(results: list[dict]) -> dict:
    """Return {per_model: {model_id: {overall_pct, per_category: {...}}}}."""
    by_model = defaultdict(lambda: {"passed": 0, "total": 0,
                                    "by_cat": defaultdict(lambda: {"passed": 0, "total": 0})})
    _TAG = {"code-from-md": "md", "code-from-qn": "qn", "qn-from-md": "auth"}
    for r in results:
        if r.get("status") != "graded":
            continue
        # Track suffix so md/qn/auth show as separate rows on the chart.
        # Legacy runs (no `mode` field) render without a suffix.
        suffix = f":{_TAG[r['mode']]}" if r.get("mode") in _TAG else ""
        key = f"{r['provider']}:{r['model']}{suffix}"
        m = by_model[key]
        m["passed"] += r["criteria_passed"]
        m["total"] += r["criteria_total"]
        cat = r.get("category", "uncategorized")
        m["by_cat"][cat]["passed"] += r["criteria_passed"]
        m["by_cat"][cat]["total"] += r["criteria_total"]

    def pct(p, t): return round(100.0 * p / t, 1) if t else 0.0

    out = {}
    for key, m in by_model.items():
        out[key] = {
            "overall_pct": pct(m["passed"], m["total"]),
            "criteria_passed": m["passed"],
            "criteria_total": m["total"],
            "per_category": {c: {"pct": pct(v["passed"], v["total"]),
                                 "passed": v["passed"], "total": v["total"]}
                             for c, v in m["by_cat"].items()},
        }
    return out


def render_markdown(agg: dict) -> str:
    cats = sorted({c for m in agg.values() for c in m["per_category"]})
    header = ["Model", "Overall"] + cats
    rows = [header, ["---"] * len(header)]
    for model in sorted(agg, key=lambda k: -agg[k]["overall_pct"]):
        row = [model, f"{agg[model]['overall_pct']:.1f}"]
        for c in cats:
            v = agg[model]["per_category"].get(c)
            row.append(f"{v['pct']:.1f}" if v else "—")
        rows.append(row)
    return "\n".join("| " + " | ".join(r) + " |" for r in rows)


def cli(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir", type=pathlib.Path)
    p.add_argument("--json", action="store_true",
                   help="Emit the aggregate as JSON instead of a Markdown table.")
    args = p.parse_args(argv)

    index = args.run_dir / "index.json"
    if not index.exists():
        print(f"no index.json under {args.run_dir}", file=sys.stderr)
        sys.exit(2)
    agg = aggregate(json.loads(index.read_text()))
    if args.json:
        print(json.dumps(agg, indent=2))
    else:
        print(render_markdown(agg))


if __name__ == "__main__":
    cli()
