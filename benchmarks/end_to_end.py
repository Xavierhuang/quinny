"""End-to-end: does the FORMAT change the OVERALL RESULT (does a bug ship)?

The narrow ablation (format_ablation.py) shows gate quality is format-neutral
once criteria are extracted. This asks the broader question: with a realistic
authoring slip, does the choice of format change whether a real bug ships?

Same criteria, ONE fat-fingered criterion. Build the gate from each format's
extraction, then run it against an impl that has a bug in the slipped criterion's
behavior. Markdown silently drops the malformed criterion (pure parsing, no LLM),
so its gate has no test for that behavior and the bug PASSES the gate and ships.
`.qn` (and JSON) preserve it, so the bug is caught. A worse overall result caused
purely by the format's failure to preserve the spec.

Run: QUINNY_REF_DIR=<dir with textkit.py> python benchmarks/end_to_end.py
     QUINNY_TRIALS=5   # repeat to show reproducibility
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from quinny.parser import parse_file  # noqa: E402
from quinny.contract import (  # noqa: E402
    Criterion, extract_criteria, build_suite, run_suite,
)

MODEL = os.environ.get("QUINNY_MODEL", "claude-haiku-4-5")
TRIALS = int(os.environ.get("QUINNY_TRIALS", "1"))
SCRATCH = Path(os.environ["QUINNY_REF_DIR"])  # dir holding textkit.py


def _mutant():
    """A textkit impl a developer might ship: correct EXCEPT roman() is broken."""
    d = Path(tempfile.mkdtemp(prefix="e2e_"))
    src = (SCRATCH / "textkit.py").read_text().replace(
        "def roman(n):", "def roman(n):\n    return ''  # BUG\ndef _x(n):", 1)
    (d / "textkit.py").write_text(src)
    (d / "main.py").write_text("import textkit\n")
    return d


def _gate_catches(criteria, impl):
    cobjs = [Criterion(i + 1, "C", "test", c) for i, c in enumerate(criteria)]
    suite = build_suite("\n".join(criteria), impl, cobjs, MODEL)
    res = [r for r in run_suite(impl, suite, cobjs) if r.criterion.kind == "test"]
    return sum(1 for r in res if r.status != "PASS") > 0  # caught the shipped bug


def run():
    crits = [c.text for c in extract_criteria(
        parse_file(ROOT / "benchmarks/plans/textkit.good.qn")) if c.kind == "test"]
    tgt = next(i for i, c in enumerate(crits) if "roman" in c.lower())
    qn_criteria = list(crits)                                    # grammar keeps all
    md_criteria = [c for i, c in enumerate(crits) if i != tgt]   # markdown drops one
    print(f"{len(crits)} criteria; authoring slip drops #{tgt+1} (roman). "
          f".qn keeps {len(qn_criteria)}, md keeps {len(md_criteria)}.\n")

    qn_caught = md_caught = 0
    for t in range(TRIALS):
        impl = _mutant()
        qc, mc = _gate_catches(qn_criteria, impl), _gate_catches(md_criteria, impl)
        qn_caught += qc
        md_caught += mc
        print(f"  trial {t+1}: .qn {'CAUGHT' if qc else 'MISSED — bug ships'} | "
              f"md {'CAUGHT' if mc else 'MISSED — bug ships'}", flush=True)
    print(f"\n=== OVERALL RESULT over {TRIALS} trial(s) ===")
    print(f"  .qn gate caught the bug: {qn_caught}/{TRIALS}")
    print(f"  md  gate caught the bug: {md_caught}/{TRIALS}  "
          f"(markdown silently dropped the criterion → no test → bug ships)")


if __name__ == "__main__":
    run()
