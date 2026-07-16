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
import ast
import os
import re
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


# Well-known Excel-style error sentinels that a spreadsheet impl might
# reasonably use for defensive code paths, even if the spec doesn't name
# them explicitly. Allowed by default so the lint doesn't fight common
# idioms. Novel Haiku-invented tokens like "#PARSE!" are still rejected.
_STANDARD_SENTINELS: frozenset[str] = frozenset({
    "#DIV/0!", "#N/A", "#NAME?", "#NULL!", "#NUM!", "#REF!", "#VALUE!",
})

_SPEC_SENTINELS_CACHE: set[str] | None = None


def _spec_sentinels() -> set[str]:
    """Union of: sentinels named in the .qn contract, sentinels mentioned
    in the natural-language prompt, and the well-known Excel standard
    set. The lint's "invented sentinel" test rejects only tokens
    outside this union — genuinely novel error strings that the model
    is inventing to make a failing case look like an expected error."""
    global _SPEC_SENTINELS_CACHE
    if _SPEC_SENTINELS_CACHE is None:
        sources = [PLAN.read_text()]
        prompt_path = ROOT / "benchmarks" / "prompts" / f"{TASK}.txt"
        if prompt_path.exists():
            sources.append(prompt_path.read_text())
        pattern = re.compile(r"#[A-Z][A-Z0-9!/?]*")
        found: set[str] = set(_STANDARD_SENTINELS)
        for src in sources:
            found |= set(pattern.findall(src))
        _SPEC_SENTINELS_CACHE = found
    return _SPEC_SENTINELS_CACHE


def _invented_sentinel(files) -> str | None:
    """Return a description of an invented sentinel, or None if clean.

    Walks every string constant in the emitted files, keeps the ones
    that look like sheet-style error sentinels (`#UPPER!`), and flags
    any that are NOT declared in the spec. See _spec_sentinels above."""
    allowed = _spec_sentinels()
    if not allowed:
        return None  # spec doesn't use sentinels at all → nothing to check
    for fn, src in files.items():
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant):
                continue
            v = node.value
            if not (isinstance(v, str) and re.fullmatch(r"#[A-Z][A-Z0-9!/]*", v)):
                continue
            if v not in allowed:
                return (f"{fn}: invented sentinel {v!r} — not in spec "
                        f"(allowed: {sorted(allowed)}). Model is masking a "
                        f"real bug as a fake expected error.")
    return None


def _panic_pattern(files):
    """Return a description of a bug-masking antipattern, or None if clean.

    The specific pattern we caught Haiku adding on fsheet under fix-round
    pressure: a `try` block with BOTH a narrow handler (e.g.
    `except ZeroDivisionError: return "#DIV/0!"`) AND a broad
    `except Exception: return "#DIV/0!"` returning the SAME sentinel.
    That makes every non-DIV bug (parser NameError, missing cell, etc.)
    silently look like a legitimate divide-by-zero — 7 held-out tests
    regressed on fsheet from exactly this shape.

    We do NOT flag broad excepts that return a DIFFERENT sentinel than
    any narrower handler in the same try (e.g. `#VALUE!` when the narrow
    branch returns `#DIV/0!` is arguably reasonable and doesn't hide
    bugs as fake DIV/0s).
    """
    def _sentinel_return(handler):
        # Walk the handler body for any Return of a sentinel string.
        for stmt in handler.body:
            if isinstance(stmt, ast.Return) and stmt.value is not None:
                v = stmt.value
                if (isinstance(v, ast.Constant)
                        and isinstance(v.value, str)
                        and v.value.startswith("#")):
                    return v.value
        return None

    def _is_broad(handler):
        return (handler.type is None
                or (isinstance(handler.type, ast.Name)
                    and handler.type.id in ("Exception", "BaseException")))

    for fn, src in files.items():
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            broad_sentinels = {_sentinel_return(h): h
                               for h in node.handlers if _is_broad(h)}
            narrow_sentinels = {_sentinel_return(h)
                                for h in node.handlers if not _is_broad(h)}
            broad_sentinels.pop(None, None)   # ignore broad excepts without sentinel
            narrow_sentinels.discard(None)
            overlap = set(broad_sentinels) & narrow_sentinels
            if overlap:
                sent = next(iter(overlap))
                return (f"{fn}: broad `except Exception` returns {sent!r} — "
                        f"same sentinel as a narrower handler in the same try. "
                        f"Real bugs will be silently masked as {sent!r}.")
    return None


def _fix_prompt_sentinels_clause() -> str:
    """Build an explicit "allowed sentinels" clause so Haiku doesn't have
    to guess and invent new ones on the fly. Returns "" if the task has
    no sentinels at all."""
    allowed = sorted(_spec_sentinels())
    if not allowed:
        return ""
    tokens = ", ".join(repr(s) for s in allowed)
    return (
        f"When you need to signal an error condition, use ONE of these "
        f"exact strings: {tokens}. Do NOT invent new tokens. If none of "
        f"these fits, ask yourself whether an existing sentinel should "
        f"propagate through your code path (e.g. arithmetic on a cell "
        f"that returned a sentinel returns the SAME sentinel — errors "
        f"flow through operators, they don't become new errors).\n\n"
    )


def fix(d, files, failed):
    src = "\n\n".join(f"```python\n# {fn}\n{s}\n```" for fn, s in files.items())
    fb = "\n".join(f"- {t}" for t in failed)
    sentinels_clause = _fix_prompt_sentinels_clause()
    # Ship the smallest diff that addresses the flagged failures. The
    # earlier prompt ("Fix it. Re-emit the ENTIRE project.") licensed
    # total rewrites — and on tasks where the one-shot was mostly-right
    # (e.g. fsheet at 94% one-shot correctness), the rewrite regressed
    # unrelated behaviors that the contract didn't explicitly test.
    # This prompt narrows the surface: minimal patch, preserve working
    # behavior, no broad-except panic patterns, and gives Haiku the
    # exact set of allowed sentinels so it doesn't invent new ones.
    nf = bench._parse_raw_files(_call(
        f"Requirement:\n{PROMPT}\n\n"
        f"Your code FAILS these acceptance criteria:\n{fb}\n\n"
        f"Current code:\n{src}\n\n"
        f"{sentinels_clause}"
        f"Make the SMALLEST possible change that addresses ONLY the failures "
        f"above. Do NOT rewrite unrelated functions. Do NOT introduce broad "
        f"exception handlers (never `except Exception: return SENTINEL` — that "
        f"masks bugs as sentinel values). Every behavior that currently works "
        f"must keep working. Re-emit the ENTIRE project so it can be re-run, "
        f"but the diff vs current code should be as small as possible. {_EMIT}"))
    # Lint the model's response; if it violated a rule, RETRY ONCE with
    # explicit feedback about the rejection instead of silently discarding
    # (which stalled the loop on tasks where the model kept trying the
    # same invalid sentinel).
    for attempt in ("first", "retry"):
        if not nf:
            return files
        panic = _panic_pattern(nf)
        invented = _invented_sentinel(nf)
        if not (panic or invented):
            files = nf
            _write(files, d)
            return files
        reason = panic or invented
        print(f"  [reject/{attempt}] {reason}", flush=True)
        if attempt == "retry":
            # Give up gracefully — keep previous round's code.
            return files
        # Retry the fix with a spelled-out correction.
        nf = bench._parse_raw_files(_call(
            f"Your previous fix was REJECTED by the loop's lint:\n{reason}\n\n"
            f"Requirement:\n{PROMPT}\n\n"
            f"Failing criteria:\n{fb}\n\n"
            f"Current code:\n{src}\n\n"
            f"{sentinels_clause}"
            f"Try again. Address the rejection reason above. Do not repeat "
            f"the mistake. Same minimal-diff rules apply. {_EMIT}"))
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
        # Carry the expected-vs-got detail so the fix turn learns WHAT was wrong,
        # not just THAT it failed — this is what breaks a re-guessing stall.
        failed = [r.criterion.text + (f"\n    → {r.detail}" if r.detail else "")
                  for r in res if r.status != "PASS"]
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
