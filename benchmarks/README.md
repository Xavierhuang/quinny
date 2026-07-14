# Quinny benchmark

Measures whether the per-stage heterogeneous model config (Opus for design,
Sonnet/Haiku for per-node work) actually saves tokens without dropping code
quality, on real generation tasks.

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
