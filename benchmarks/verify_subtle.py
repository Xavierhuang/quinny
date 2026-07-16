"""Subtle-bug benchmark for `quinny verify`.

`verify_usability.py` covers gross feature omissions (whole subsystems
missing). This one covers the class humans reliably miss in code review:

  - off-by-one at LRU capacity boundary
  - silent NaN in aggregations
  - unicode NFC vs NFD key confusion
  - wrong exception type (bare Exception vs KeyError)
  - integer overflow in TTL calculation
  - ttl=0 treated as "no ttl" instead of "already expired"

For each defect, an impl with only that defect enabled should fail exactly
the one matching criterion — nothing else. That "surgical FAIL" property
is what makes verify useful for CI: it tells you *which* invariant broke,
not just "something broke."

Runs in two modes:

  --emit  first, generates the suite once (needs an API key + credit)
  --suite <path>  re-runs the committed suite deterministically — NO API

The intended workflow is emit-once → commit → --suite everywhere else.
Once the suite is committed, this benchmark is fully offline.

    QUINNY_MODEL=claude-haiku-4-5 python benchmarks/verify_subtle.py --emit
    python benchmarks/verify_subtle.py --suite benchmarks/fixtures/subtle/suite.py
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "fixtures" / "subtle"))
from quinny.contract import run_saved, verify  # noqa: E402
import variants  # noqa: E402

MODEL = os.environ.get("QUINNY_MODEL", "claude-haiku-4-5")
SPEC = ROOT / "benchmarks" / "fixtures" / "subtle" / "spec.qn"
DEFAULT_SUITE = ROOT / "benchmarks" / "fixtures" / "subtle" / "suite.py"


# variant name -> defect flags (True means that defect is enabled)
VARIANTS: dict[str, dict[str, bool]] = {"correct": {}}
for defect in variants.DEFECTS:
    VARIANTS[f"only_{defect}"] = {defect: True}


def _score(results) -> dict[int, bool]:
    gating = [r for r in results if r.criterion.kind == "test"]
    return {r.criterion.index: (r.status == "PASS") for r in gating}


def _run_variant(name: str, flags: dict, suite_path: Path | None) -> tuple[dict, dict]:
    """Return (verdict-by-criterion, ground-truth-by-criterion)."""
    d = Path(tempfile.mkdtemp(prefix=f"subtle_{name}_"))
    (d / "subtle_kv.py").write_text(variants.source(**flags))
    if suite_path and suite_path.exists():
        results = run_saved(SPEC, d, suite_path)
    else:
        results = verify(SPEC, d, MODEL)
    shutil.rmtree(d, ignore_errors=True)
    return _score(results), variants.ground_truth(flags)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--emit", action="store_true",
                   help="Emit the suite once (needs API key), then run all "
                        "variants against it. Also writes the suite to "
                        f"{DEFAULT_SUITE.relative_to(ROOT)} for future --suite runs.")
    p.add_argument("--suite", type=Path, default=None,
                   help="Path to a previously-emitted suite. Runs fully "
                        "offline (no API calls).")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would run without calling the API.")
    args = p.parse_args()

    if args.dry_run:
        print(f"Subtle-bug variants ({len(VARIANTS)} total):")
        for name in VARIANTS:
            print(f"  {name}")
        key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        suite_ready = (args.suite and args.suite.exists()) or DEFAULT_SUITE.exists()
        print(f"\nSpec:        {SPEC.relative_to(ROOT)}  "
              f"({'present' if SPEC.exists() else 'MISSING'})")
        print(f"Committed suite: {'present at ' + str(DEFAULT_SUITE.relative_to(ROOT)) if DEFAULT_SUITE.exists() else 'not yet emitted'}")
        print(f"Credentials: {'present' if key else 'MISSING'}")
        print(f"Model:       {MODEL}")
        if suite_ready:
            print("\n→ ready to run offline via --suite")
        elif key:
            print("\n→ ready to emit + run via --emit (~1 Claude call)")
        else:
            print("\n→ NOT ready: need either a committed suite or credentials")
        return 0

    suite_path: Path | None = args.suite
    if args.emit:
        # Emit against the correct impl (canonical shape) to produce the
        # suite once, then reuse the same suite for every variant.
        d = Path(tempfile.mkdtemp(prefix="subtle_emit_"))
        (d / "subtle_kv.py").write_text(variants.source())
        emit_at = DEFAULT_SUITE
        emit_at.parent.mkdir(parents=True, exist_ok=True)
        verify(SPEC, d, MODEL, emit=emit_at)
        shutil.rmtree(d, ignore_errors=True)
        suite_path = emit_at
        print(f"[emit] suite written to {emit_at.relative_to(ROOT)}")

    if suite_path is None or not suite_path.exists():
        print("No committed suite found. Pass --emit (to generate one, "
              "needs API key) or --suite <path> (to reuse an existing one).",
              file=sys.stderr)
        return 2

    print(f"{'variant':<28} {'criteria row':<14} {'truth':<14} verdict")
    print("-" * 78)
    false_pass = false_fail = 0

    for name, flags in VARIANTS.items():
        verdict, truth = _run_variant(name, flags, suite_path)
        idxs = sorted(verdict)
        row = "".join("P" if verdict[i] else "F" for i in idxs)
        trow = "".join("P" if truth[i] else "F" for i in idxs)
        misses = []
        for i in idxs:
            got, want = verdict[i], truth[i]
            if got and not want:
                false_pass += 1; misses.append(f"missed C{i}")
            if not got and want:
                false_fail += 1; misses.append(f"cried-wolf C{i}")
        tag = "OK" if not misses else " ".join(misses)
        print(f"{name:<28} {row:<14} {trow:<14} {tag}")

    print("-" * 78)
    print(f"False-PASS (missed a subtle defect): {false_pass}   <- dangerous")
    print(f"False-FAIL (failed correct code):    {false_fail}")
    print(f"Model: {MODEL}   Suite: {suite_path.relative_to(ROOT)}")
    return 1 if false_pass else 0


if __name__ == "__main__":
    sys.exit(main())
