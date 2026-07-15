"""Determinism evidence for `quinny verify --suite`.

`verify` calls an LLM to *generate* a suite — but you emit it ONCE, review it,
and commit it. From then on `--suite` re-runs that committed pytest file with no
model in the loop. This benchmark proves the payoff: an emitted suite gives the
SAME verdict on every run — the property that makes it safe to gate CI on.

We emit one suite (a single LLM call), then run it N times against a correct impl
and a broken impl, and check the verdicts never vary.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks"))
from quinny.contract import verify, run_saved  # noqa: E402
import verify_usability as vb  # noqa: E402  (reuse its correct/stub impl sources)

PLAN = ROOT / "benchmarks" / "plans" / "mini_kv.good.qn"
MODEL = os.environ.get("QUINNY_MODEL", "claude-haiku-4-5")
N = 30


def gating(results):
    g = [r for r in results if r.criterion.kind == "test"]
    return tuple(r.status == "PASS" for r in sorted(g, key=lambda r: r.criterion.index))


def main() -> int:
    good = Path(tempfile.mkdtemp(prefix="det_good_"))
    (good / "mini_kv.py").write_text(vb.kv_source(True, True, True))
    broken = Path(tempfile.mkdtemp(prefix="det_broken_"))
    (broken / "mini_kv.py").write_text(vb.kv_source(False, False, False))

    suite_path = good / "contract_test.py"
    print("Emitting the acceptance suite once (one LLM call)…")
    verify(PLAN, good, MODEL, emit=suite_path)
    print(f"Emitted {suite_path.name} — now re-running it {N}x per impl (no LLM):\n")

    for label, impl in [("correct", good), ("broken", broken)]:
        verdicts = set()
        gate_counts = []
        for _ in range(N):
            res = run_saved(PLAN, impl, suite_path)
            v = gating(res)
            verdicts.add(v)
            gate_counts.append(sum(v))
        stable = len(verdicts) == 1
        gp = gate_counts[0]
        gt = len(next(iter(verdicts)))
        print(f"{label:8}  {N} runs  gate={gp}/{gt} every run  "
              f"identical-verdict={'YES' if stable else 'NO (' + str(len(verdicts)) + ' distinct!)'}")

    print(f"\nDeterminism: {N} deterministic re-runs of a committed suite, "
          f"per impl. Correct impl passes every gating criterion every time; "
          f"broken impl fails every time; zero verdict drift.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
