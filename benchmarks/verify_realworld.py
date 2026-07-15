"""Real-world evidence for `quinny verify`.

The synthetic benchmark (verify_usability.py) shows verify catches KNOWN defects.
This one is harder: does verify's verdict agree with an INDEPENDENT ground truth
on REAL, model-generated implementations of varying quality?

For every implementation produced during the codegen benchmarks, we compare:
  - held-out grade: a hand-written pytest suite the generator never saw (truth),
  - verify gate:    quinny verify compiling the .qn's `test` criteria and running
                    them against that same implementation.

If the two track each other — high verify score on high-quality code, low on
broken code — then a .qn contract is a valid, model-agnostic quality signal.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import bench  # noqa: E402
from quinny.contract import verify  # noqa: E402

MODEL = os.environ.get("QUINNY_MODEL", "claude-haiku-4-5")
TASKS = ["mini_kv", "mini_sheet", "minilang"]
WORK = ROOT / "benchmarks" / ".work"
PLANS = ROOT / "benchmarks" / "plans"


def gate_score(plan: Path, impl: Path) -> tuple[int, int]:
    results = [r for r in verify(plan, impl, MODEL) if r.criterion.kind == "test"]
    passed = sum(1 for r in results if r.status == "PASS")
    return passed, len(results)


def main() -> int:
    rows = []
    for task in TASKS:
        plan = PLANS / f"{task}.good.qn"
        if not plan.exists() or bench._holdout_test_file(task) is None:
            continue
        impls = sorted(WORK.glob(f"*/{task}_run*"))
        for impl in impls:
            if not list(impl.glob("*.py")):
                continue
            config = impl.parent.name
            hp, ht = bench.grade_holdout(impl, task)          # ground truth
            gp, gt = gate_score(plan, impl)                    # verify gate
            hpct = hp / ht if ht else 0.0
            gpct = gp / gt if gt else 0.0
            rows.append((task, config, impl.name, hp, ht, hpct, gp, gt, gpct))

    print(f"{'task':11} {'config':17} {'run':>4}  {'held-out':>10}  {'verify gate':>12}  agree")
    print("-" * 72)
    agree = 0
    for (task, config, run, hp, ht, hpct, gp, gt, gpct) in rows:
        # "agree" = same side of a 60% quality line (both good, or both bad)
        same = (hpct >= 0.6) == (gpct >= 0.6)
        agree += same
        run_n = run.split("_run")[-1]
        print(f"{task:11} {config:17} {run_n:>4}  {hp:>2}/{ht:<2} {hpct:>5.0%}  "
              f"{gp:>2}/{gt:<2} {gpct:>6.0%}   {'✓' if same else '✗'}")
    print("-" * 72)
    n = len(rows)
    if n:
        # Rank correlation-ish: does verify order impls the same as held-out?
        print(f"\nImplementations checked: {n}")
        print(f"verify agrees with held-out ground truth (good/bad): {agree}/{n} "
              f"= {100*agree/n:.0f}%")
        goods = [r for r in rows if r[5] >= 0.6]
        bads = [r for r in rows if r[5] < 0.6]
        if goods:
            print(f"  mean verify gate on GOOD impls (held-out ≥60%): "
                  f"{100*sum(r[8] for r in goods)/len(goods):.0f}%")
        if bads:
            print(f"  mean verify gate on BROKEN impls (held-out <60%): "
                  f"{100*sum(r[8] for r in bads)/len(bads):.0f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
