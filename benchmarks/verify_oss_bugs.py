"""OSS-bug-shape reproduction benchmark for `quinny verify`.

Every fixture in `benchmarks/fixtures/oss_bugs/<name>/` models a bug pattern
seen in real-world open-source post-mortems / CVEs:

  - cart_negative_qty  — checkout accepts negative quantity → self-credit exploit
  - discount_stacking  — coupon codes multiply instead of "best wins"
  - session_expiry     — token check ignores TTL (JWT "none" family)
  - zip_slip           — extractor writes files outside the destination
  - rate_limit         — off-by-one allows N+1 requests per window, ignores key

Each fixture ships:
  spec.qn       — the contract (test criteria describing correct behavior)
  correct.py    — an impl that satisfies the contract
  buggy.py      — an impl exhibiting the bug pattern

We score `quinny verify` on both. A useful gate must:
  - PASS every criterion on `correct.py` (no false-FAILs)
  - FAIL ≥1 criterion on `buggy.py` (no false-PASSes on real bugs)

The report table matches the format used by `verify_usability.py` /
`verify_realworld.py` so results plug into the README the same way.

Run:
    QUINNY_MODEL=claude-haiku-4-5 python benchmarks/verify_oss_bugs.py
    python benchmarks/verify_oss_bugs.py --dry-run    # readiness check, no API
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
from quinny.contract import verify  # noqa: E402

FIXTURES = ROOT / "benchmarks" / "fixtures" / "oss_bugs"
MODEL = os.environ.get("QUINNY_MODEL", "claude-haiku-4-5")

FIXTURE_NAMES = [
    "cart_negative_qty",
    "discount_stacking",
    "session_expiry",
    "zip_slip",
    "rate_limit",
]


def _copy_impl(fixture_name: str, which: str) -> Path:
    """Materialize <fixture>/<which>.py as `<project_module>.py` in a temp
    dir so the emitted suite can `import <project_module>` cleanly. We name
    the module after the .qn project so the generated test file's imports
    line up regardless of correct/buggy."""
    src = FIXTURES / fixture_name / f"{which}.py"
    spec_path = FIXTURES / fixture_name / "spec.qn"
    # Extract project name from the .qn — first non-comment line
    project = _project_name(spec_path)
    d = Path(tempfile.mkdtemp(prefix=f"oss_{fixture_name}_{which}_"))
    module_name = _snake(project)
    (d / f"{module_name}.py").write_text(src.read_text())
    # Also drop the file at its own basename so imports that guess the file
    # name (e.g. from the fixture's own naming) still resolve.
    (d / f"{which}.py").write_text(src.read_text())
    return d


def _project_name(spec_path: Path) -> str:
    for line in spec_path.read_text().splitlines():
        s = line.strip()
        if s.startswith("project "):
            return s.split(None, 1)[1].strip()
    raise ValueError(f"no project in {spec_path}")


def _snake(camel: str) -> str:
    out = []
    for i, ch in enumerate(camel):
        if ch.isupper() and i > 0 and not camel[i - 1].isupper():
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def _score(results, which: str) -> tuple[int, int, str]:
    """Return (passed, total, row-string).  Row is P/F per gating criterion."""
    gating = [r for r in results if r.criterion.kind == "test"]
    passed = sum(1 for r in gating if r.status == "PASS")
    row = "".join("P" if r.status == "PASS" else "F" for r in gating)
    return passed, len(gating), row


def _dry_run() -> int:
    """Validate fixtures + environment without touching the API. Prints a
    readiness table so a caller can tell whether a live run would succeed."""
    print(f"{'fixture':<22} {'spec.qn':<10} {'correct.py':<12} {'buggy.py':<10}")
    print("-" * 60)
    ok = True
    for name in FIXTURE_NAMES:
        d = FIXTURES / name
        s = "✓" if (d / "spec.qn").exists() else "MISSING"
        c = "✓" if (d / "correct.py").exists() else "MISSING"
        b = "✓" if (d / "buggy.py").exists() else "MISSING"
        if "MISSING" in (s, c, b):
            ok = False
        print(f"{name:<22} {s:<10} {c:<12} {b:<10}")
    print("-" * 60)
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    print(f"Credentials: {'present' if key else 'MISSING (needed for live run)'}")
    print(f"Model:       {MODEL}")
    print(f"Fixtures:    {sum(1 for n in FIXTURE_NAMES if (FIXTURES / n / 'spec.qn').exists())}"
          f" / {len(FIXTURE_NAMES)}")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true",
                   help="Validate fixtures + env, don't call the API.")
    args = p.parse_args()
    if args.dry_run:
        return _dry_run()

    print(f"{'fixture':<22} {'which':<8} {'pass/total':<12} {'row':<12} verdict")
    print("-" * 74)
    false_pass = false_fail = 0
    fixtures_covered = 0

    for name in FIXTURE_NAMES:
        spec = FIXTURES / name / "spec.qn"
        if not spec.exists():
            print(f"[skip] {name}: no spec.qn")
            continue
        fixtures_covered += 1

        # Correct impl: expect every criterion PASS.
        d_ok = _copy_impl(name, "correct")
        res_ok = verify(spec, d_ok, MODEL)
        p_ok, t_ok, row_ok = _score(res_ok, "correct")
        verdict_ok = "OK" if p_ok == t_ok else f"FALSE-FAIL ({t_ok - p_ok})"
        if p_ok != t_ok:
            false_fail += t_ok - p_ok
        print(f"{name:<22} {'correct':<8} {p_ok}/{t_ok:<10} {row_ok:<12} {verdict_ok}")

        # Buggy impl: expect ≥1 FAIL (the bug the fixture models).
        d_bad = _copy_impl(name, "buggy")
        res_bad = verify(spec, d_bad, MODEL)
        p_bad, t_bad, row_bad = _score(res_bad, "buggy")
        caught = t_bad - p_bad
        # A single FALSE-PASS on a buggy impl is the dangerous outcome —
        # verify green-lit a real bug. Count it.
        if caught == 0:
            false_pass += 1
            verdict_bad = "FALSE-PASS (missed the bug)"
        else:
            verdict_bad = f"caught {caught} defect(s)"
        print(f"{name:<22} {'buggy':<8} {p_bad}/{t_bad:<10} {row_bad:<12} {verdict_bad}")

        shutil.rmtree(d_ok, ignore_errors=True)
        shutil.rmtree(d_bad, ignore_errors=True)

    print("-" * 74)
    print(f"Fixtures: {fixtures_covered}/{len(FIXTURE_NAMES)}")
    print(f"False-PASS (green-lit a real bug):  {false_pass}/{fixtures_covered}"
          "  <- the dangerous one")
    print(f"False-FAIL (failed correct code):    {false_fail} criteria")
    print(f"Model: {MODEL}")
    return 1 if false_pass else 0


if __name__ == "__main__":
    sys.exit(main())
