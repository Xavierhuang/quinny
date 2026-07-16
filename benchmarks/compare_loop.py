"""Head-to-head reporter for verify_loop.py runs.

The thesis under test is:
    weak model + Quinny verify-loop  ≥  strong frontier model one-shot

verify_loop.py already prints per-run holdout scores. This script parses
one or more of those log files, groups them by (task, model, condition),
and prints a mean / worst-case / total table so different runs from
different sessions can be compared without a database.

    python benchmarks/compare_loop.py /tmp/loop_kimi_kv.log /tmp/opus_mini_sheet.log ...

Log lines this reader understands (verify_loop.py's plain output):

    Task: <task>  ·  model: <model>  ·  <N> runs each
      A one-shot     run <i>:  <p>/<t> held-out
      B verify-loop  run <i>:  <p>/<t> held-out  (<r> fix round(s))
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

RE_HEADER = re.compile(r"Task:\s*(\S+)\s*·\s*model:\s*(\S+)")
RE_ROW = re.compile(
    r"^\s*(A one-shot|B verify-loop)\s+run\s+(\d+):\s+(\d+)/(\d+)")


def parse_log(path: Path):
    """Yield tuples (task, model, condition, run_index, passed, total)."""
    task = model = None
    for line in path.read_text().splitlines():
        m = RE_HEADER.search(line)
        if m:
            task, model = m.group(1), m.group(2)
            continue
        m = RE_ROW.match(line)
        if m and task and model:
            cond = "one-shot" if m.group(1).startswith("A") else "verify-loop"
            yield task, model, cond, int(m.group(2)), int(m.group(3)), int(m.group(4))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("logs", nargs="+", type=Path,
                   help="verify_loop.py log files to compare.")
    args = p.parse_args()

    # (task, model, cond) -> list of (passed, total)
    buckets: dict[tuple[str, str, str], list[tuple[int, int]]] = defaultdict(list)
    for log in args.logs:
        if not log.exists():
            print(f"[skip] missing {log}", file=sys.stderr)
            continue
        for task, model, cond, _idx, p_, t_ in parse_log(log):
            buckets[(task, model, cond)].append((p_, t_))

    if not buckets:
        print("No parsable runs found. Log format changed?", file=sys.stderr)
        return 2

    print(f"{'task':<14} {'model':<24} {'condition':<14} "
          f"{'runs':>5} {'mean%':>7} {'worst%':>7} {'best%':>7}")
    print("-" * 82)
    rows = []
    for (task, model, cond), pairs in sorted(buckets.items()):
        pcts = [100 * p / t for p, t in pairs if t]
        if not pcts:
            continue
        mean = statistics.mean(pcts)
        worst = min(pcts)
        best = max(pcts)
        rows.append((task, model, cond, len(pairs), mean, worst, best))
        print(f"{task:<14} {model:<24} {cond:<14} "
              f"{len(pairs):>5} {mean:>6.0f}% {worst:>6.0f}% {best:>6.0f}%")

    # Thesis check: for each task, is any weak+Quinny row ≥ any one-shot row?
    print("\n=== Thesis check: weak+Quinny loop ≥ any one-shot? ===")
    by_task: dict[str, list[tuple[str, str, float, float]]] = defaultdict(list)
    for task, model, cond, _n, mean, worst, _best in rows:
        by_task[task].append((model, cond, mean, worst))
    for task, entries in by_task.items():
        loops = [(m, mean, worst) for m, c, mean, worst in entries if c == "verify-loop"]
        oneshots = [(m, mean, worst) for m, c, mean, worst in entries if c == "one-shot"]
        if not loops or not oneshots:
            print(f"  {task}: need both conditions to compare — skipped")
            continue
        best_loop = max(loops, key=lambda x: x[1])
        best_oneshot = max(oneshots, key=lambda x: x[1])
        verdict = "✓ VALIDATED" if best_loop[1] >= best_oneshot[1] else "✗ not validated"
        print(f"  {task}:  best loop {best_loop[0]} = {best_loop[1]:.0f}%"
              f"   vs   best one-shot {best_oneshot[0]} = {best_oneshot[1]:.0f}%"
              f"   → {verdict}")
        # Reliability angle: compare worst-case
        print(f"    worst-case: loop={best_loop[2]:.0f}%  vs  one-shot={best_oneshot[2]:.0f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
