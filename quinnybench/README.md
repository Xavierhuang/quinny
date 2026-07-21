# QuinnyBench

A coding benchmark for the **Quinny language**. Scores LLMs on three complementary tracks, all graded deterministically (no LLM in the grader path):

| Track          | Input to model      | Output       | Grade                                    | Measures                                                     |
|----------------|---------------------|--------------|------------------------------------------|--------------------------------------------------------------|
| `code-from-md` | `prompt.md` (prose) | `impl.py`    | frozen pytest suite                      | Baseline: HumanEval-style spec-following from prose.         |
| `code-from-qn` | `contract.qn`       | `impl.py`    | same frozen pytest suite                 | **Does giving the model a Quinny contract help?**            |
| `qn-from-md`   | `prompt.md`         | `contract.qn`| structural checks (parses + shape)       | **Can the model author a Quinny contract from a spec?**      |

The interesting comparison is `md` vs `qn` on the same model. If the `qn` bar is higher, that's evidence Quinny contracts help models produce spec-compliant code. If lower, that's evidence too — worth knowing.

## Status

40 tasks across 8 categories, 3 tracks. 397 code criteria + 200 authoring criteria = 597 grader criteria total. See `PLAN.md`.

## Architecture

```
quinnybench/
├── tasks/<NN-slug>/
│   ├── contract.qn          # Quinny contract — the acceptance criteria
│   ├── prompt.md            # what we send to each model
│   ├── suite.py             # frozen pytest suite (emitted once by `quinny verify --emit`, committed)
│   ├── reference/           # a known-passing implementation (proves the suite is achievable)
│   └── meta.json            # {category, difficulty, language, entrypoint}
├── runner/
│   ├── providers/           # thin adapters — anthropic, openai, google, xai, deepseek, openrouter
│   ├── run.py               # (task × model) grid: prompt → save code → verify → JSON
│   ├── rescore.py           # replay a saved run's code through quinny (no LLM calls)
│   └── score.py             # aggregate result JSON → per-model / per-category pass rates
├── viz/
│   ├── build.py             # renders results/ → static HTML with SVG bar charts
│   └── demo.py              # fabricates a preview run so the chart can be seen without API calls
├── results/<YYYY-MM-DD-HHMM>/  # per-run JSON + generated code (auditable)
└── PLAN.md                  # roadmap: task list, providers, remaining work
```

## Design decisions

- **Grader determinism.** Each task's `suite.py` is generated once via `quinny verify --emit`, reviewed, and committed. Benchmark runs use `quinny verify --suite suite.py` — no LLM in the grader. Only the *implementation* varies between runs.
- **Reproducibility.** Every result JSON references the exact task commit + suite hash. Re-running yields the same numbers unless a model provider changes behind the API.
- **Rescoring.** Model outputs are saved verbatim. `rescore.py` re-runs the same code through the (possibly updated) suite — cheap, no API calls.
- **Categories.** Each task has a `category`. Sub-scores are aggregated per-category so the output chart can show "state machines", "parsers", "business rules" etc. as separate bars (like the reference screenshot).

## Running

One-shot end-to-end from a fresh clone:

```bash
cd quinnybench
cp .env.example .env       # then fill in whichever provider keys you have
./reproduce.sh             # creates .venv, installs deps, runs, renders site
```

`reproduce.sh` runs exactly the providers whose keys are present in `.env` — no key, no call. Renders the static site to `viz/out/` when finished.

Manual, per-track:

```bash
export ANTHROPIC_API_KEY=sk-…
RUN=results/manual-run
python -m runner.run --provider anthropic --model claude-opus-4-7 --mode code-from-md --run-dir $RUN
python -m runner.run --provider anthropic --model claude-opus-4-7 --mode code-from-qn --run-dir $RUN
python -m runner.run --provider anthropic --model claude-opus-4-7 --mode qn-from-md   --run-dir $RUN
python -m runner.score $RUN                                       # per-track Markdown table
python -m viz.build $RUN                                          # static site → viz/out/index.html
open viz/out/index.html
```

Track results share a `--run-dir` so the leaderboard shows all three side-by-side (`model:md`, `model:qn`, `model:auth` rows).

Preview the chart without spending API calls (all fabricated):

```bash
python -m viz.demo                                               # → results/demo/index.json + fake impls
python -m viz.build results/demo/
open viz/out/index.html
```

Rescore an old run against the current suites (no API calls, useful when a suite is fixed or extended):

```bash
python -m runner.rescore results/2026-07-21-1830/
python -m viz.build results/2026-07-21-1830/                     # re-render with updated numbers
```

## API keys

Copy `.env.example` → `.env` and fill in the providers you have keys for. Missing keys skip that provider silently instead of erroring. Six adapters ship: `anthropic`, `openai`, `google`, `xai`, `deepseek`, `openrouter`.

## Publishing

`viz/out/` is a plain static site — zero JS build step, no server needed. Anywhere that serves static HTML works.

**GitHub Pages** (simplest):

```bash
# One-time setup: create a docs branch pointing at viz/out
git subtree push --prefix quinnybench/viz/out origin gh-pages

# Then in the repo settings enable Pages → source = gh-pages, path = /
# Or configure Pages → source = "GitHub Actions" and use the actions/upload-pages-artifact workflow.
```

**Vercel / Netlify / any static host:** point them at `quinnybench/viz/out/` as the publish directory. No build command needed — the files are pre-rendered.

The site's URL structure:
- `index.html` — overall leaderboard + per-category panels
- `m/<slug>.html` — per-model summary (all tasks, pct each)
- `d/<slug>--<task>.html` — per (model, task) drilldown (code + per-criterion PASS/FAIL)

## Reproducibility notes

- Every task ships with a committed `suite.py` that is deterministic pytest — no LLM in the grader path.
- Model outputs (`impl.py`) are saved verbatim under `results/<run>/<task>/<provider>--<model>/`. You can `git commit` them for audit trails.
- Re-running the same benchmark yields the same aggregate ± any provider-side non-determinism (temperature is pinned to 0.0 by default; some providers still return slightly different tokens across identical requests).
- The bench itself is versioned by the repo's commit hash. To pin a benchmark reference, tag the commit.
