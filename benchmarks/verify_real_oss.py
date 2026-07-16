"""Real-OSS benchmark for `quinny verify`.

Every other verify_* benchmark exercises code I authored. That's useful
but weak evidence — a critic can reasonably say "of course the gate
catches bugs you wrote, you knew what to write."

This benchmark points verify at a REAL, published library that I didn't
write. It ships with cachetools as the reference case, but the harness
is library-agnostic — anyone can drop a new fixture directory in and
have it picked up automatically. See fixtures/real_oss/README.md for
the 5-step contribution recipe.

Per-library layout under fixtures/real_oss/<name>/:

  spec.qn              — acceptance criteria for the library's API
  pristine_wrapper.py  — thin wrapper around the pip-installed library
  mutated_wrapper.py   — same wrapper with one narrowly-injected bug
  manifest.py          — declares VARIANTS + GROUND_TRUTH + IMPORT_CHECK
  suite.py             — the emitted pytest suite (committed after --emit)

Expected outcome per library:

  pristine    all-PASS  → gate does not cry wolf on real, shipping code
  mutated     exactly one FAIL, matching the injected defect
                        → gate is surgical, not just noisy

Runs in two modes:

  --emit          generate the suite once (needs API key + credit)
  --suite <path>  re-run a committed suite deterministically — NO API

    QUINNY_MODEL=claude-haiku-4-5 python benchmarks/verify_real_oss.py --emit
    python benchmarks/verify_real_oss.py --library cachetools \\
        --suite benchmarks/fixtures/real_oss/cachetools/suite.py
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from quinny.contract import run_saved, verify  # noqa: E402

MODEL = os.environ.get("QUINNY_MODEL", "claude-haiku-4-5")
REAL_OSS_ROOT = ROOT / "benchmarks" / "fixtures" / "real_oss"


def _load_manifest(fixture_dir: Path):
    """Load the per-library manifest.py without polluting sys.modules."""
    manifest_path = fixture_dir / "manifest.py"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Missing manifest at {manifest_path}. See "
            f"{REAL_OSS_ROOT / 'README.md'} for the fixture layout.")
    spec = importlib.util.spec_from_file_location(
        f"real_oss_manifest_{fixture_dir.name}", manifest_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _list_libraries() -> list[str]:
    """Discover every library fixture that has a manifest.py."""
    if not REAL_OSS_ROOT.exists():
        return []
    return sorted(p.name for p in REAL_OSS_ROOT.iterdir()
                  if p.is_dir() and (p / "manifest.py").exists())


def _score(results) -> dict[int, bool]:
    gating = [r for r in results if r.criterion.kind == "test"]
    return {r.criterion.index: (r.status == "PASS") for r in gating}


def _run_variant(fixture_dir: Path, name: str, wrapper: str,
                 suite_path: Path | None) -> dict[int, bool]:
    d = Path(tempfile.mkdtemp(prefix=f"real_oss_{fixture_dir.name}_{name}_"))
    shutil.copy(fixture_dir / wrapper, d / "cache_api.py")
    spec = fixture_dir / "spec.qn"
    if suite_path and suite_path.exists():
        results = run_saved(spec, d, suite_path)
    else:
        results = verify(spec, d, MODEL)
    shutil.rmtree(d, ignore_errors=True)
    return _score(results)


def _preflight(manifest) -> tuple[bool, str]:
    check = getattr(manifest, "IMPORT_CHECK", None)
    if not check:
        return True, "no preflight import declared"
    try:
        m = importlib.import_module(check)
        ver = getattr(m, "__version__", "?")
        return True, f"{check} {ver}"
    except ImportError:
        return False, f"{check} not installed — pip install {check}"


def _run_one_library(library: str, args) -> int:
    fixture_dir = REAL_OSS_ROOT / library
    if not fixture_dir.exists():
        print(f"[skip] no fixture dir at {fixture_dir}", file=sys.stderr)
        return 2
    manifest = _load_manifest(fixture_dir)
    default_suite = fixture_dir / "suite.py"
    ok, ver = _preflight(manifest)

    if args.dry_run:
        key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        suite_ready = (args.suite and args.suite.exists()) or default_suite.exists()
        print(f"Library:         {getattr(manifest, 'LIBRARY', library)} "
              f"— {getattr(manifest, 'DESCRIPTION', '')}")
        print(f"Spec:            {(fixture_dir / 'spec.qn').relative_to(ROOT)}")
        print(f"Committed suite: "
              f"{'present at ' + str(default_suite.relative_to(ROOT)) if default_suite.exists() else 'not yet emitted'}")
        print(f"Preflight:       {ver}")
        print(f"Credentials:     {'present' if key else 'MISSING'}")
        print(f"Model:           {MODEL}")
        print(f"Variants:        {', '.join(manifest.VARIANTS)}")
        if suite_ready:
            print("\n→ ready to run offline via --suite")
        elif key and ok:
            print("\n→ ready to emit + run via --emit (~1 Claude call)")
        else:
            print("\n→ NOT ready: install the library + set credentials "
                  "(or supply --suite)")
        return 0

    if not ok:
        print(f"[skip {library}] {ver}", file=sys.stderr)
        return 2

    suite_path: Path | None = args.suite
    if args.emit:
        d = Path(tempfile.mkdtemp(prefix=f"real_oss_emit_{library}_"))
        shutil.copy(fixture_dir / manifest.VARIANTS["pristine"], d / "cache_api.py")
        default_suite.parent.mkdir(parents=True, exist_ok=True)
        verify(fixture_dir / "spec.qn", d, MODEL, emit=default_suite)
        shutil.rmtree(d, ignore_errors=True)
        suite_path = default_suite
        print(f"[emit {library}] suite written to {default_suite.relative_to(ROOT)}")

    if suite_path is None or not suite_path.exists():
        print(f"[{library}] no committed suite. Pass --emit (needs API key) "
              "or --suite <path>.", file=sys.stderr)
        return 2

    print(f"\n=== {getattr(manifest, 'LIBRARY', library)} ===")
    print(f"{'variant':<28} {'criteria row':<14} {'truth':<14} verdict")
    print("-" * 78)
    false_pass = false_fail = 0

    for name, wrapper in manifest.VARIANTS.items():
        verdict = _run_variant(fixture_dir, name, wrapper, suite_path)
        truth = manifest.GROUND_TRUTH.get(name, {})
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


def main() -> int:
    libs = _list_libraries()
    p = argparse.ArgumentParser()
    p.add_argument("--library", default=None,
                   help=f"Library fixture to run. Available: {', '.join(libs) or '(none)'}. "
                        "Omit to run all.")
    p.add_argument("--emit", action="store_true",
                   help="Emit the suite once (needs API key) against the "
                        "pristine wrapper, then reuse it for every variant.")
    p.add_argument("--suite", type=Path, default=None,
                   help="Path to a previously-emitted suite (offline).")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would run without calling the API.")
    args = p.parse_args()

    if not libs:
        print("No fixtures under benchmarks/fixtures/real_oss/. See "
              f"{REAL_OSS_ROOT / 'README.md'} to add one.", file=sys.stderr)
        return 2

    targets = [args.library] if args.library else libs
    unknown = [t for t in targets if t not in libs]
    if unknown:
        print(f"Unknown library/libraries: {unknown}. Available: {libs}",
              file=sys.stderr)
        return 2

    rc = 0
    for lib in targets:
        r = _run_one_library(lib, args)
        rc = max(rc, r)
    return rc


if __name__ == "__main__":
    sys.exit(main())
