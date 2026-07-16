"""Real-OSS benchmark for `quinny verify`.

Every existing verify_* benchmark exercises code I authored: fixtures
shaped like CVEs, hand-picked subtle defects, synthetic KV impls. That's
useful but weak evidence — a critic can reasonably say "of course the
gate catches bugs you wrote, you knew what to write."

This benchmark points verify at cachetools, a real, popular library
(github.com/tkem/cachetools, ~2k stars, 15+ years old). I did not write
it. I only wrote:

  - a small .qn contract describing documented LRUCache + TTLCache
    behavior (fixtures/real_oss/cachetools/spec.qn),
  - a thin pristine wrapper that forwards to the pip-installed library
    (pristine_wrapper.py),
  - a mutated wrapper with one narrowly-injected bug (mutated_wrapper.py).

Expected outcome:

  pristine    all-PASS  → gate does not cry wolf on real, shipping code
  mutated     exactly one FAIL, matching the injected defect
                        → gate is surgical, not just noisy

Runs in two modes:

  --emit          generate the suite once (needs API key + credit)
  --suite <path>  re-run a committed suite deterministically — NO API

Emit-once → commit → --suite everywhere else, same as verify_subtle.

    QUINNY_MODEL=claude-haiku-4-5 python benchmarks/verify_real_oss.py --emit
    python benchmarks/verify_real_oss.py --suite benchmarks/fixtures/real_oss/cachetools/suite.py
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
from quinny.contract import run_saved, verify  # noqa: E402

MODEL = os.environ.get("QUINNY_MODEL", "claude-haiku-4-5")
FIXTURE = ROOT / "benchmarks" / "fixtures" / "real_oss" / "cachetools"
SPEC = FIXTURE / "spec.qn"
DEFAULT_SUITE = FIXTURE / "suite.py"


VARIANTS: dict[str, str] = {
    "pristine": "pristine_wrapper.py",
    "mutated_lru_no_recency": "mutated_wrapper.py",
}

# Ground truth: which criterion indices should PASS per variant.
# From spec.qn: 1-5 = LRU tests, 6-8 = TTL tests. The mutation targets
# criterion 3 (LRU order after read).
GROUND_TRUTH: dict[str, dict[int, bool]] = {
    "pristine": {i: True for i in range(1, 9)},
    "mutated_lru_no_recency": {
        1: True, 2: True, 3: False, 4: True, 5: True,
        6: True, 7: True, 8: True,
    },
}


def _score(results) -> dict[int, bool]:
    gating = [r for r in results if r.criterion.kind == "test"]
    return {r.criterion.index: (r.status == "PASS") for r in gating}


def _run_variant(name: str, wrapper: str, suite_path: Path | None) -> dict[int, bool]:
    d = Path(tempfile.mkdtemp(prefix=f"real_oss_{name}_"))
    # The wrapper is copied into the impl dir under a stable name so the
    # emitted suite's imports don't depend on which variant is in play.
    shutil.copy(FIXTURE / wrapper, d / "cache_api.py")
    if suite_path and suite_path.exists():
        results = run_saved(SPEC, d, suite_path)
    else:
        results = verify(SPEC, d, MODEL)
    shutil.rmtree(d, ignore_errors=True)
    return _score(results)


def _preflight_ok() -> tuple[bool, str]:
    try:
        import cachetools  # noqa: F401
        return True, f"cachetools {cachetools.__version__}"
    except ImportError:
        return False, "cachetools not installed — pip install cachetools"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--emit", action="store_true",
                   help="Emit the suite once (needs API key) against the "
                        "pristine wrapper, then reuse it for every variant.")
    p.add_argument("--suite", type=Path, default=None,
                   help="Path to a previously-emitted suite (offline).")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would run without calling the API.")
    args = p.parse_args()

    ok, ver = _preflight_ok()

    if args.dry_run:
        key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        suite_ready = (args.suite and args.suite.exists()) or DEFAULT_SUITE.exists()
        print(f"Spec:            {SPEC.relative_to(ROOT)}  "
              f"({'present' if SPEC.exists() else 'MISSING'})")
        print(f"Committed suite: {'present at ' + str(DEFAULT_SUITE.relative_to(ROOT)) if DEFAULT_SUITE.exists() else 'not yet emitted'}")
        print(f"cachetools:      {ver}")
        print(f"Credentials:     {'present' if key else 'MISSING'}")
        print(f"Model:           {MODEL}")
        print(f"Variants:        {', '.join(VARIANTS)}")
        if suite_ready:
            print("\n→ ready to run offline via --suite")
        elif key and ok:
            print("\n→ ready to emit + run via --emit (~1 Claude call)")
        else:
            print("\n→ NOT ready: install cachetools + set credentials (or "
                  "supply --suite)")
        return 0

    if not ok:
        print(f"[skip] {ver}", file=sys.stderr)
        return 2

    suite_path: Path | None = args.suite
    if args.emit:
        d = Path(tempfile.mkdtemp(prefix="real_oss_emit_"))
        shutil.copy(FIXTURE / VARIANTS["pristine"], d / "cache_api.py")
        emit_at = DEFAULT_SUITE
        emit_at.parent.mkdir(parents=True, exist_ok=True)
        verify(SPEC, d, MODEL, emit=emit_at)
        shutil.rmtree(d, ignore_errors=True)
        suite_path = emit_at
        print(f"[emit] suite written to {emit_at.relative_to(ROOT)}")

    if suite_path is None or not suite_path.exists():
        print("No committed suite found. Pass --emit (needs API key) or "
              "--suite <path>.", file=sys.stderr)
        return 2

    print(f"{'variant':<28} {'criteria row':<14} {'truth':<14} verdict")
    print("-" * 78)
    false_pass = false_fail = 0

    for name, wrapper in VARIANTS.items():
        verdict = _run_variant(name, wrapper, suite_path)
        truth = GROUND_TRUTH[name]
        idxs = sorted(verdict)
        row = "".join("P" if verdict[i] else "F" for i in idxs)
        trow = "".join("P" if truth.get(i, True) else "F" for i in idxs)
        misses = []
        for i in idxs:
            got, want = verdict[i], truth.get(i, True)
            if got and not want:
                false_pass += 1; misses.append(f"missed C{i}")
            if not got and want:
                false_fail += 1; misses.append(f"cried-wolf C{i}")
        tag = "OK" if not misses else " ".join(misses)
        print(f"{name:<28} {row:<14} {trow:<14} {tag}")

    print("-" * 78)
    print(f"False-PASS (missed a real-library defect): {false_pass}   <- dangerous")
    print(f"False-FAIL (cried wolf on real code):      {false_fail}")
    suite_display = suite_path.resolve()
    try:
        suite_display = suite_display.relative_to(ROOT)
    except ValueError:
        pass
    print(f"Model: {MODEL}   Suite: {suite_display}")
    return 1 if false_pass else 0


if __name__ == "__main__":
    sys.exit(main())
