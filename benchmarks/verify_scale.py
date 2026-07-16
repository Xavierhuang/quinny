"""Scale benchmark for `quinny verify`.

Existing benchmarks (`mini_kv`, `mini_sheet`) each carry 5–15 criteria. This
one asks: does the flow hold up at 50 / 100 / 200 criteria?

Method: generate a synthetic `.qn` on the fly (an in-memory KV with N
distinct feature knobs, each contributing 1–2 acceptance criteria). Also
generate a matching correct impl. For each target N in `SCALES`:

  1. Emit the suite with `--emit`. Record: emit-time, emit-tokens.
  2. Re-run the emitted suite with `run_saved`. Record: run-time (no LLM).
  3. Score verdicts against ground truth (all-pass on the correct impl).

The interesting numbers: does emit-time scale linearly with N? Does the
generated suite stay coherent past ~50 criteria, or start missing entries?
Does `run_saved` stay in the deterministic-and-fast regime?

Run:
    QUINNY_MODEL=claude-haiku-4-5 python benchmarks/verify_scale.py
    # or restrict to smaller sweeps for a smoke test:
    QUINNY_SCALES=10,25 python benchmarks/verify_scale.py
    # or check readiness without spending tokens:
    python benchmarks/verify_scale.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from quinny.contract import run_saved, verify  # noqa: E402

MODEL = os.environ.get("QUINNY_MODEL", "claude-haiku-4-5")
DEFAULT_SCALES = (10, 25, 50, 100)


def _scales() -> list[int]:
    env = os.environ.get("QUINNY_SCALES")
    if env:
        return [int(x) for x in env.split(",") if x.strip()]
    return list(DEFAULT_SCALES)


def build_spec(n: int) -> str:
    """A KV where each of N features contributes one strict acceptance test.

    Format: `set_k<i>(v)` stores value at key i; `get_k<i>()` retrieves it.
    Each test asserts round-trip for feature i. Every criterion is tiny and
    independent, so we can grow N without ballooning the fixture."""
    lines = [f"project ScaleKV_{n}", ""]
    lines.append("component Store")
    lines.append("    goal")
    lines.append(f"        In-memory KV supporting {n} independent named slots.")
    lines.append("")
    lines.append("task API")
    lines.append("    goal")
    lines.append(f"        Round-trip API for {n} named slots (k0…k{n-1}).")
    lines.append("    depends")
    lines.append("        Store")
    for i in range(n):
        lines.append("    test")
        lines.append(f"        set_k{i}(\"v{i}\") then get_k{i}() returns \"v{i}\".")
    return "\n".join(lines) + "\n"


def build_correct_impl(n: int) -> str:
    """A single-file module that satisfies every criterion in build_spec(n)."""
    lines = ["_store = {}", ""]
    for i in range(n):
        lines.append(f"def set_k{i}(v): _store[{i}] = v")
        lines.append(f"def get_k{i}(): return _store[{i}]")
    return "\n".join(lines) + "\n"


def _score(results) -> tuple[int, int]:
    gating = [r for r in results if r.criterion.kind == "test"]
    passed = sum(1 for r in gating if r.status == "PASS")
    return passed, len(gating)


def _dry_run() -> int:
    """Show what the live run would do, without calling the API."""
    scales = _scales()
    print("Scale sweep — would generate one spec + impl per N:")
    for n in scales:
        spec_len = len(build_spec(n).splitlines())
        impl_len = len(build_correct_impl(n).splitlines())
        crit = 2 + n     # goal(0) + n test lines (well, one per feature)
        print(f"  N={n:>4}  spec={spec_len:>4} lines  impl={impl_len:>4} lines  "
              f"~{crit:>3} criteria")
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    print(f"\nCredentials: {'present' if key else 'MISSING (needed for live run)'}")
    print(f"Model:       {MODEL}")
    print(f"Estimated cost: 1 emit + 1 run per N × {len(scales)} N-values "
          f"(largest N dominates)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true",
                   help="Preview the sweep without calling the API.")
    args = p.parse_args()
    if args.dry_run:
        return _dry_run()

    scales = _scales()
    print(f"{'N':>5} {'emit_s':>8} {'suite_lines':>12} "
          f"{'run_s':>8} {'pass/total':>12} {'coverage':>9}")
    print("-" * 62)

    for n in scales:
        d = Path(tempfile.mkdtemp(prefix=f"scale_{n}_"))
        spec_path = d / "spec.qn"
        spec_path.write_text(build_spec(n))
        (d / f"scale_kv_{n}.py").write_text(build_correct_impl(n))

        emit_path = d / "suite.py"
        t0 = time.time()
        emit_results = verify(spec_path, d, MODEL, emit=emit_path)
        emit_dt = time.time() - t0
        suite_lines = len(emit_path.read_text().splitlines()) if emit_path.exists() else 0

        # Re-run the committed suite — this is the model-free path CI uses.
        t0 = time.time()
        run_results = run_saved(spec_path, d, emit_path)
        run_dt = time.time() - t0
        passed, total = _score(run_results)
        coverage = f"{100 * total // n}%" if n else "-"

        print(f"{n:>5} {emit_dt:>8.1f} {suite_lines:>12} "
              f"{run_dt:>8.2f} {passed}/{total:<11} {coverage:>9}")

        shutil.rmtree(d, ignore_errors=True)

    print("-" * 62)
    print(f"Model: {MODEL}   (set QUINNY_SCALES=10,25 to restrict)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
