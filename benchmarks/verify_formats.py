"""DSL vs JSON format A/B for `quinny verify`.

The open product question: does Quinny really need its own DSL (`.qn`),
or is a plain structured format (JSON, YAML) enough? The right answer
depends on a measured, not felt, comparison.

Quinny already accepts both `.qn` DSL and `.json` — `parse_file`
auto-detects. So the head-to-head this benchmark runs is:

  Given the SAME acceptance criteria, expressed once in each format,
  do we get:
    (a) the same extracted criteria set?  (parse equivalence)
    (b) the same verify verdict on the same impl using the same
        committed suite?                  (gate equivalence)

If both hold → the DSL is a matter of taste, not capability. Users
who prefer JSON can use it and lose nothing. If either fails → we've
learned something specific about where the formats diverge.

The fixture is subtle/spec.qn + subtle/spec.json (auto-generated via
ast_to_json). The impl is variants.source() (correct version) — same
committed suite as verify_subtle.py runs against.

    python benchmarks/verify_formats.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "fixtures" / "subtle"))
from quinny.contract import extract_criteria, run_saved  # noqa: E402
from quinny.parser import parse_file  # noqa: E402
import variants  # noqa: E402

FIXTURE = ROOT / "benchmarks" / "fixtures" / "subtle"
SPEC_DSL = FIXTURE / "spec.qn"
SPEC_JSON = FIXTURE / "spec.json"
SUITE = FIXTURE / "suite.py"


def _criteria(spec_path: Path) -> list[tuple[int, str]]:
    project = parse_file(spec_path)
    return [(c.index, c.text) for c in extract_criteria(project)]


def _verdict(spec_path: Path) -> dict[int, str]:
    d = Path(tempfile.mkdtemp(prefix=f"fmt_{spec_path.suffix.strip('.')}_"))
    (d / "subtle_kv.py").write_text(variants.source())
    results = run_saved(spec_path, d, SUITE)
    shutil.rmtree(d, ignore_errors=True)
    return {r.criterion.index: r.status for r in results
            if r.criterion.kind == "test"}


def main() -> int:
    if not SUITE.exists():
        print(f"[skip] committed suite missing at {SUITE.relative_to(ROOT)}. "
              f"Run: python benchmarks/verify_subtle.py --emit", file=sys.stderr)
        return 2
    if not SPEC_JSON.exists():
        print(f"[skip] JSON spec missing at {SPEC_JSON.relative_to(ROOT)}. "
              f"Generate via: python -c "
              f"'from quinny.parser import parse_file; "
              f"from quinny.json_format import ast_to_json; "
              f"print(ast_to_json(parse_file(\"{SPEC_DSL}\")))' > {SPEC_JSON}",
              file=sys.stderr)
        return 2

    dsl_crit = _criteria(SPEC_DSL)
    json_crit = _criteria(SPEC_JSON)

    print("=== Parse equivalence ===")
    print(f"  DSL   ({SPEC_DSL.name}):  {len(dsl_crit)} criteria")
    print(f"  JSON  ({SPEC_JSON.name}): {len(json_crit)} criteria")
    parse_match = dsl_crit == json_crit
    print(f"  Extracted criteria match: {parse_match}")

    print("\n=== Gate equivalence (against correct impl + committed suite) ===")
    dsl_v = _verdict(SPEC_DSL)
    json_v = _verdict(SPEC_JSON)
    print(f"  DSL   verdicts: {dsl_v}")
    print(f"  JSON  verdicts: {json_v}")
    verdict_match = dsl_v == json_v
    print(f"  Verdicts match: {verdict_match}")

    print("\n=== Summary ===")
    if parse_match and verdict_match:
        print("  ✓ Formats are equivalent — DSL is a matter of taste, not capability.")
        return 0
    else:
        print("  ✗ Divergence detected. Investigate before shipping.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
