"""Does the embedded verify loop make the agent produce better code?

A/B on the same weak model (Haiku — the kind the app runs):
  A (one-shot)   : write the module from the prompt. Stop. (No Quinny.)
  B (verify-loop): write it, run `quinny verify` against a contract, feed the
                   FAILED criteria back, fix, re-verify — up to a few rounds.
                   (This is exactly the loop LingCode Baby now embeds.)

Both graded by an INDEPENDENT hand-written held-out suite (never shown to the
model, and NOT the verify contract) — so an improvement means genuinely more
spec-conforming code, not teaching-to-its-own-test. If B > A, embedding Quinny
measurably improves correctness.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import bench  # noqa: E402
from quinny.contract import verify, run_saved  # noqa: E402
from quinny._capabilities import make_client, thinking_kwargs  # noqa: E402

TASK = os.environ.get("QUINNY_TASK", "mini_sheet")
PROMPT = (ROOT / "benchmarks" / "prompts" / f"{TASK}.txt").read_text().strip()
PLAN = ROOT / "benchmarks" / "plans" / f"{TASK}.good.qn"
MODEL = os.environ.get("QUINNY_MODEL", "claude-haiku-4-5")
RUNS = int(os.environ.get("QUINNY_RUNS", "3"))
MAX_FIX = int(os.environ.get("QUINNY_MAX_FIX", "3"))


def _call(user: str) -> str:
    c = make_client()
    # Low-level streaming: keep bytes flowing (the LingModel/Kimi proxy 524s a
    # single non-streaming reply >~100s) AND collect text deltas ourselves —
    # Kimi emits `thinking` blocks whose deltas crash the SDK's high-level
    # text_stream accumulator (`content.thinking += None`). We just skip them.
    stream = c.messages.create(model=MODEL, max_tokens=16000,
                               system=bench._RAW_SYSTEM_PROMPT,
                               messages=[{"role": "user", "content": user}],
                               stream=True, **thinking_kwargs(MODEL))
    parts = []
    for ev in stream:
        if (ev.type == "content_block_delta"
                and getattr(ev.delta, "type", None) == "text_delta"):
            parts.append(ev.delta.text)
    return "".join(parts)


def _write(files, d):
    bench._fresh_dir(d)
    for fn, src in files.items():
        p = d / fn
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src if src.endswith("\n") else src + "\n")


_EMIT = ("Emit the project now, each file in its own "
         "```python\\n# filename.py\\n...\\n``` block. No prose.")


def generate(d):
    files = bench._parse_raw_files(_call(f"Requirement:\n{PROMPT}\n\n{_EMIT}"))
    _write(files, d)
    return files


def fix(d, files, failed):
    src = "\n\n".join(f"```python\n# {fn}\n{s}\n```" for fn, s in files.items())
    fb = "\n".join(f"- {t}" for t in failed)
    # Ship the smallest diff that addresses the flagged failures. The
    # earlier prompt ("Fix it. Re-emit the ENTIRE project.") licensed
    # total rewrites — and on tasks where the one-shot was mostly-right
    # (e.g. fsheet at 94% one-shot correctness), the rewrite regressed
    # unrelated behaviors that the contract didn't explicitly test.
    # This prompt narrows the surface: minimal patch, preserve working
    # behavior, no broad-except panic patterns.
    nf = bench._parse_raw_files(_call(
        f"Requirement:\n{PROMPT}\n\n"
        f"Your code FAILS these acceptance criteria:\n{fb}\n\n"
        f"Current code:\n{src}\n\n"
        f"Make the SMALLEST possible change that addresses ONLY the failures "
        f"above. Do NOT rewrite unrelated functions. Do NOT introduce broad "
        f"exception handlers (never `except Exception: return SENTINEL` — that "
        f"masks bugs as sentinel values). Every behavior that currently works "
        f"must keep working. Re-emit the ENTIRE project so it can be re-run, "
        f"but the diff vs current code should be as small as possible. {_EMIT}"))
    if nf:
        files = nf
        _write(files, d)
    return files


def one_shot():
    d = Path(tempfile.mkdtemp(prefix="A_"))
    generate(d)
    return bench.grade_holdout(d, TASK)


def loop():
    d = Path(tempfile.mkdtemp(prefix="B_"))
    # Compile the contract into a suite ONCE and reuse it every round, so the
    # gate is deterministic and pass-counts are comparable across rounds (a
    # freshly-generated suite each round would make "did this round improve?"
    # meaningless). This is the emit→--suite pattern the CLI ships.
    suite = Path(str(d) + "__contract_suite.py")

    def check(first):
        res = (verify(PLAN, d, MODEL, emit=suite) if first
               else run_saved(PLAN, d, suite))
        res = [r for r in res if r.criterion.kind == "test"]
        passed = sum(1 for r in res if r.status == "PASS")
        failed = [r.criterion.text for r in res if r.status != "PASS"]
        return passed, failed

    files = generate(d)
    passed, failed = check(first=True)
    # keep-best: never return code worse than the best version we've seen.
    best_passed, best_files = passed, dict(files)
    rounds = 0
    stale = 0  # consecutive rounds without progress
    while failed and rounds < MAX_FIX:
        rounds += 1
        files = fix(d, files, failed)
        passed, failed = check(first=False)
        if passed > best_passed:
            best_passed, best_files = passed, dict(files)  # progress → adopt
            stale = 0
        else:
            stale += 1
            # Tolerate ONE plateau round (a slow recovery often needs to
            # reorient), but stop on sustained no-progress — that's thrashing,
            # not recovering. keep-best still protects correctness either way.
            if stale >= 2:
                break
    _write(best_files, d)  # grade the best version, never a regressed one
    suite.unlink(missing_ok=True)
    return bench.grade_holdout(d, TASK), rounds


def main() -> int:
    print(f"Task: {TASK}  ·  model: {MODEL}  ·  {RUNS} runs each\n")
    a_scores, b_scores = [], []
    tot = None
    for i in range(RUNS):
        (ap, at) = one_shot()
        a_scores.append(ap); tot = at
        print(f"  A one-shot     run {i}:  {ap}/{at} held-out")
    for i in range(RUNS):
        (bp, bt), rounds = loop()
        b_scores.append(bp)
        print(f"  B verify-loop  run {i}:  {bp}/{bt} held-out  ({rounds} fix round(s))")
    import statistics
    a = statistics.mean(a_scores)
    b = statistics.mean(b_scores)
    print("\n" + "=" * 56)
    print(f"A  one-shot (no Quinny)    : {a:.1f}/{tot}  = {100*a/tot:.0f}%")
    print(f"B  verify-loop (embedded)  : {b:.1f}/{tot}  = {100*b/tot:.0f}%")
    delta = 100 * (b - a) / tot
    print(f"Δ  {'+' if delta>=0 else ''}{delta:.0f} percentage points from the verify loop")
    print("=" * 56)
    return 0


if __name__ == "__main__":
    sys.exit(main())
