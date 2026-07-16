# Quinny benchmarks

Two families of benchmarks live here.

## `verify_*` — the primary story (does `quinny verify` actually gate?)

Every `verify_*.py` measures a specific correctness or usability claim about
`quinny verify`. Results feed the tables in the project README.

| Script | Question it answers | Needs LLM? |
|---|---|---|
| `verify_usability.py`  | Gross feature omissions — does verify catch when a whole subsystem is missing? | yes |
| `verify_realworld.py`  | Does verify agree with an INDEPENDENT held-out suite on model-generated impls? | yes |
| `verify_determinism.py`| Does an emitted `--suite` give the same verdict on every re-run? | first emit, then no |
| `verify_crosslang.py`  | Does the same `.qn` gate Python + JS impls with the same 0-false-PASS property? | yes |
| `verify_loop.py`       | If the model is given verify as a feedback signal, does its output actually get more correct? | yes |
| `verify_oss_bugs.py`   | **NEW.** Does verify catch bugs shaped like real-world CVEs / post-mortems? | yes |
| `verify_scale.py`      | **NEW.** Does the flow hold up at 50–100 acceptance criteria per spec? | yes |
| `verify_subtle.py`     | **NEW.** Off-by-one, silent NaN, unicode, wrong exception, TTL overflow — the class of bugs humans miss in review. Fully offline once a suite is emitted. | first emit, then no |

Everything under `fixtures/` is committed source used by these scripts —
never generated at run time (so you can `git blame` a defect back to a
line, and a spec is always reviewable before it runs).

```bash
# Run everything with a single command (skips subtle if no committed suite):
QUINNY_MODEL=claude-haiku-4-5 ./benchmarks/run-new.sh

# Or generate the subtle-suite once, then re-run offline forever:
python benchmarks/verify_subtle.py --emit
python benchmarks/verify_subtle.py --suite benchmarks/fixtures/subtle/suite.py
```

`run-new.sh` prints the raw per-fixture rows; `verify_realworld.py` /
`verify_usability.py` produce the same aggregate metric shape (false-PASS,
false-FAIL, accuracy, consistency) already used in the README.

---

## Model-config benchmark (legacy, code-gen era)

Measures whether the per-stage heterogeneous model config (Opus for design,
Sonnet/Haiku for per-node work) actually saves tokens without dropping code
quality, on real generation tasks. This benchmark predates the verify pivot
and is kept for reference — new decisions should use the verify_* family.

## Method

For each prompt in `prompts/`:

1. Generate the Quinny plan **once** using Opus and cache it to `plans/<name>.qn`.
   Reusing the cached plan across every config keeps the comparison
   apples-to-apples — we're only measuring the downstream generator, not the
   planner.
2. For each **config** (see `scripts/bench.py`), run `quinny build
   --full-verify --assemble` N times and record:
   - Total input / output / total tokens across all stages.
   - Fast-verify pass rate (% of files that compile + import).
   - Full-verify pass rate (% of files whose `__main__` runs cleanly).
   - Whether the assembled `python main.py` exits 0.
3. Aggregate mean + std per (prompt × config) cell and print a table.

## Configs

| id | planner | types | node | repair | assemble |
|---|---|---|---|---|---|
| `all-opus`      | opus | opus | opus   | opus   | opus   |
| `opus+sonnet`   | opus | opus | sonnet | sonnet | sonnet |
| `opus+haiku`    | opus | opus | haiku  | haiku  | sonnet |
| `opus+mixed`    | opus | opus | sonnet | haiku  | sonnet |
| `all-sonnet`    | sonnet | sonnet | sonnet | sonnet | sonnet |

## Run

```bash
export ANTHROPIC_API_KEY=...

# Warm the plan cache (~$1 in Opus calls total for the 3 prompts).
python scripts/bench.py --warm-plans

# Full benchmark: 5 configs × 3 prompts × 3 runs = 45 build attempts.
python scripts/bench.py --runs 3

# Faster smoke check: 1 run each, only two configs.
python scripts/bench.py --runs 1 --configs all-opus opus+haiku
```

Results print to stdout as a text table and also get saved to
`benchmarks/results/<timestamp>.json` for later analysis.
