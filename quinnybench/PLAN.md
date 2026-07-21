# QuinnyBench roadmap

## Phase 7 — three-track benchmark (done)

The initial framing (a bench that *used* Quinny only as the grader) has been
extended so QuinnyBench actually exercises the Quinny language:

- [x] `code-from-md` — send `prompt.md`, grade `impl.py` with pytest. (Baseline.)
- [x] `code-from-qn` — send `contract.qn`, grade `impl.py` with the same pytest.
      Measures whether the contract-as-input helps the model produce spec-compliant code.
- [x] `qn-from-md` — send `prompt.md`, grade the returned `contract.qn` structurally
      (5 mechanical checks: parses, has task block, has criteria, module + entity constraints).
      Measures whether the model can *author* Quinny.
- [x] Runner takes `--mode`; results carry a `mode` field; score aggregator suffixes
      the model label with `:md` / `:qn` / `:auth` so all three appear side-by-side on the chart.
- [x] Demo (`viz/demo.py`) fabricates all three tracks with a plausible track bias
      (Quinny contract as input is a small help; authoring is harder).
- [x] `reproduce.sh` runs all three tracks by default; `MODES="code-from-md" ./reproduce.sh`
      subsets it.

## Phase 1 — walking skeleton (this commit)

- [x] Directory layout + README
- [x] 1 task: `001-shipping-cost` (contract.qn, prompt.md, reference solution, hand-authored suite.py placeholder)
- [x] Provider ABC + Anthropic adapter
- [x] Runner: (task, model) → generate code → run Quinny → JSON result
- [x] `rescore.py`: replay saved code through current suite
- [x] `score.py`: aggregate JSON → per-model/per-category table

## Phase 2 — freeze the first task's real suite

- [ ] Export `ANTHROPIC_API_KEY`, run `quinny verify tasks/001-shipping-cost/contract.qn tasks/001-shipping-cost/reference/ --emit tasks/001-shipping-cost/suite.py`
- [ ] Review the emitted `suite.py`; confirm the reference passes all criteria
- [ ] Commit the frozen suite; the placeholder in phase 1 is replaced

## Phase 3 — add providers (done)

- [x] `runner/providers/openai.py` — `gpt-4o`, `gpt-4.1`, o-series reasoning models
- [x] `runner/providers/google.py` — Gemini 2.5 Pro / Flash
- [x] `runner/providers/xai.py` — Grok
- [x] `runner/providers/deepseek.py` — DeepSeek Chat / Coder
- [x] `runner/providers/openrouter.py` — Kimi, other long-tail models

xAI, DeepSeek, and OpenRouter are OpenAI-compatible; they subclass `OpenAIProvider` and only override `name`, `env_var`, and `base_url`. SDK imports are lazy inside each `complete()` — you only need to `pip install` the SDKs for the providers you actually run.

## Phase 4 — task suite (target: 40 tasks across 8 categories, ~5 each)

Each task = `contract.qn` + `prompt.md` + reference solution + frozen `suite.py`.

- [x] Business rules (5): shipping cost, tax brackets, subscription proration, discount stacking, insurance premium
- [x] State machines (5): traffic light, order lifecycle, elevator, TCP handshake, vending machine
- [x] Parsers (5): CSV row, semver, HTTP query string, INI file, cron minute-field
- [x] Validators (5): Luhn, password policy, email RFC 5322 subset, phone E.164, IBAN (mod-97)
- [x] Data transforms (5): flatten nested dict, group-by, dedupe preserving order, top-k (stable), pivot table
- [x] Date/time (5): business-day offset, age-from-DOB, ISO-week, weekend-count, format-duration
- [x] Small algorithms (5): LRU cache, interval merge, topological sort, sliding-window max, token-bucket rate limiter
- [x] CLI arg handling (5): key=value flags, subcommand dispatcher, env-var fallback, GNU-style short/long with values, help renderer

**Category coverage: 8/8, depth-5. Task count: 40/40 ✓. Criteria total: 397.**

## Phase 5 — static site (done)

- [x] `viz/build.py`: read `results/<run>/index.json` → render `viz/out/`:
  - [x] `index.html` — overall leaderboard + per-category panels (SVG bars, winner in accent)
  - [x] `m/<slug>.html` — per-model summary: every task with per-task pct + drilldown link
  - [x] `d/<slug>--<task>.html` — drilldown: generated code on the left, ✓/✗ per criterion on the right
  - [x] Cross-links: model names on the index → model pages → drilldowns; back-crumbs on every page
  - [x] Zero JS / zero build step — inline SVG + one CSS file
- [x] `viz/demo.py`: fabricate a plausible multi-model `results/demo/index.json` for preview (`python -m viz.demo`) — clearly labelled, seed-stable. Also seeds fabricated `impl.py` copies + real test-name pass/fail lists so drilldown demos aren't empty.

## Phase 6 — publish (done)

- [x] `reproduce.sh` — end-to-end script from a fresh clone: creates the venv, installs only the SDKs whose keys are set in `.env`, runs the (task × configured-provider) grid, builds the site, prints the aggregate.
- [x] README documents the deploy paths for GitHub Pages / Vercel / any static host. `viz/out/` is a pre-rendered static site — no build step on the host side.

## Cost estimate (per full benchmark run)

- 40 tasks × ~6 models = 240 calls
- Avg ~2k input + ~1k output tokens
- Rough $20–$60 depending on model mix
- Rescoring is free (no API calls)
