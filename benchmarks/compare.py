"""Head-to-head: champion (Opus one-shot) vs challenger (a weaker model + the
Quinny verify loop), held-out graded. Reports mean, worst-case, and best-case
correctness so a lucky single run can't carry the claim.

Thesis: challenger mean >= champion mean on a shared benchmark. It only becomes a
*beat* (>), rather than a tie, on a task where the champion one-shot is itself
below 100% (otherwise 100% is the ceiling and the best a challenger can do is match).

Usage:
    python benchmarks/compare.py <task> --challenger 14/18,15/18,18/18 [--champion 14/18,...]
If --champion is omitted, Opus one-shot is loaded from benchmarks/.work/raw-opus-cli.
"""
import sys
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import bench  # noqa: E402


def opus_oneshot(task):
    out = []
    for d in sorted((ROOT / "benchmarks" / ".work" / "raw-opus-cli").glob(f"{task}_run*")):
        if list(d.glob("*.py")):
            out.append(bench.grade_holdout(d, task))
    return out


def parse_scores(s):
    return [tuple(int(x) for x in pair.split("/")) for pair in s.split(",")]


def summarize(scores):
    fr = [p / t for p, t in scores if t]
    tot = scores[0][1] if scores else 0
    return {
        "n": len(fr), "total": tot,
        "mean": statistics.mean(fr) if fr else 0.0,
        "worst": min(fr) if fr else 0.0,
        "best": max(fr) if fr else 0.0,
        "raw": scores,
    }


def main():
    if len(sys.argv) < 2:
        print("usage: compare.py <task> --challenger p/t,... [--champion p/t,...]")
        return 2
    task = sys.argv[1]
    args = sys.argv[2:]
    champ = chall = None
    for i, a in enumerate(args):
        if a == "--champion" and i + 1 < len(args):
            champ = parse_scores(args[i + 1])
        if a == "--challenger" and i + 1 < len(args):
            chall = parse_scores(args[i + 1])
    if champ is None:
        champ = opus_oneshot(task)          # Opus one-shot, held-out, from .work
    if not champ or not chall:
        print("Need both champion (Opus one-shot .work or --champion) and --challenger.")
        return 2

    C = summarize(champ)
    K = summarize(chall)
    print(f"\nTask: {task}   (held-out /{C['total']})\n")
    hdr = f"{'':30} {'runs':>4} {'mean':>7} {'worst':>7} {'best':>7}   raw"
    print(hdr); print("-" * len(hdr))
    for label, S in [("Opus one-shot (champion)", C),
                     ("weak+Quinny loop (challenger)", K)]:
        raw = " ".join(f"{p}/{t}" for p, t in S["raw"])
        print(f"{label:30} {S['n']:>4} {S['mean']:>6.0%} {S['worst']:>6.0%} "
              f"{S['best']:>6.0%}   {raw}")
    print("-" * len(hdr))
    ge = K["mean"] >= C["mean"]
    gt = K["mean"] > C["mean"]
    tie_ceiling = abs(C["mean"] - 1.0) < 1e-9 and abs(K["mean"] - 1.0) < 1e-9
    verdict = ("BEATS" if gt else "MATCHES (≥)" if ge else "loses to")
    print(f"\nChallenger {verdict} champion "
          f"({K['mean']:.0%} vs {C['mean']:.0%}).")
    if tie_ceiling:
        print("Note: both at the 100% ceiling — this is a TIE, not a beat. To show a "
              "beat, use a task where Opus one-shot is < 100%.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
