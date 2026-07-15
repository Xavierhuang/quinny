# Quinny

**An executable specification language.**

Describe *what* your software must do — its components and their concrete
acceptance criteria — in a small, reviewable `.qn` file. Quinny turns those
criteria into a runnable test suite and **verifies any implementation against
them**: code written by a human, by Claude Code, by Cursor — in Python or
JavaScript. Write the contract once; enforce it forever, in any language, in CI.

```
spec.qn ──► quinny verify ──► ✓/✗ per acceptance criterion, on ANY code, ANY language
   │                │
   │ reviewable     │ compiles your `test` criteria into a real test suite
   │ contract       │ (pytest / node:test), runs it, gates the build
```

A `.qn` file is **not code that runs** — it's a structured, version-controllable
statement of intent *and* the contract that decides whether an implementation
satisfies it.

## How it fits your dev cycle

Modern agents (Claude Code, Cursor) already write code well — fast, one-shot.
Quinny doesn't compete with that; it **holds the output to a contract you own.**

**Don't want to write the contract?** You don't have to. `quinny scaffold "build me
a store for selling trees"` scopes the part where correctness matters (the pricing,
cart, and inventory *logic* — not the UI, which `verify` can't gate anyway), drafts
the acceptance criteria, and stubs the module. You go straight to implement → verify.

```
write spec.qn  ──►  let any agent write/change the code  ──►  quinny verify  ──►  ✓ / ✗
   (once)              (its strength — fast, one-shot)          (your gate)
```

| Instead of… | With Quinny |
|---|---|
| Re-reading the diff to check requirements still hold | `quinny verify` checks them, per criterion |
| Hand-writing acceptance tests (the `mini_kv` contract → 147 lines) | generated from the spec you already wrote |
| Re-prompting an LLM to "review this against the spec" every change | emit the suite **once**, run it free forever |
| Re-specifying for each tool or model you try | one `.qn` gates them all, unchanged |

**In real terms** (all measured, not estimated):

- **~12 seconds** and **under a penny** to turn a spec into a ~140-line acceptance
  suite — the same suite you'd otherwise hand-write in ~30 minutes.
- **0.24 seconds** and **$0** to check *any* implementation against that committed
  suite — no AI in the loop, every time, forever.

**Say you try 10 implementations** before one sticks (you plus a couple of agents,
iterating). Generate the contract *once* (~12 s, <1¢), then verify all ten — about
**2.4 seconds total, $0**. Without it, you'd hand-write the tests once, or re-read
all ten diffs against the spec yourself. And it keeps paying off: every later
commit, refactor, or model swap is re-checked in a quarter-second, catching a broken
requirement before it ships. Your AI cost scales with **spec changes, not commits** —
50 pushes between spec edits still cost one ~12-second generation.

---

## Install

```bash
# One-liner — installs the Python-free binary on Apple Silicon, else falls back to pip:
curl -fsSL https://raw.githubusercontent.com/Xavierhuang/quinny/main/install.sh | sh

# Or straight from PyPI (needs Python 3.10+):
pip install quinny
```

The installer honors `QUINNY_METHOD=pip|binary`, `QUINNY_VERSION=vX.Y.Z`, and
`QUINNY_PREFIX=<dir>`. Prebuilt binaries are attached to each
[GitHub Release](https://github.com/Xavierhuang/quinny/releases). From source:
`git clone … && cd quinny && pip install -e .`. Requires Python 3.10+.

## Quickstart: verify an implementation against intent

Write `todo.qn` — note the concrete `test` lines, they're the contract:

```
project TodoService

component Store
    goal
        In-memory store mapping ids to todo items.

task AddTodo
    goal
        Add a todo item and return its integer id; ids never repeat.
    uses
        Store
    test
        add("milk") returns an int; adding again returns a different id.
    test
        A removed id is no longer listed.
```

Validate the spec itself (no LLM, no key needed):

```bash
quinny check todo.qn      # ✓ parses + graph is valid (missing deps, cycles)
```

Then verify any implementation directory against the contract:

```bash
quinny verify todo.qn ./my_impl/           # compiles `test` criteria, runs them
quinny verify todo.qn ./my_impl/ --emit contract_test.py   # save the suite…
quinny verify todo.qn ./my_impl/ --suite contract_test.py  # …then re-run it, no LLM
```

Output is a per-criterion PASS/FAIL table and a gate exit code. The
**emit → review → `--suite`** flow locks the generated suite into a committed file
so CI runs it deterministically, with no model in the loop — see
**[docs/ci.md](docs/ci.md)** for the ready-to-copy GitHub Action.

### How reliable is the gate?

**In plain terms: across ~40 implementations — some correct, some deliberately
broken — verify flagged every broken one and never once passed a bad one.** The
single time it disagreed with a human-written test suite, it was being *stricter*,
not letting a bug through. The measured detail, both benchmarks in [`benchmarks/`](benchmarks/):

**Synthetic** — implementations with known, exact defects (`verify_usability.py`):

| Metric | Result |
|---|---|
| False-PASS (green-lights a real defect) | **0 / 60** |
| False-FAIL (fails correct code) | **0 / 60** |
| Accuracy vs ground truth | **100%** |
| Consistency across runs | **100%** |

**Real-world** — 13 model-generated implementations across three domains (a data
structure, a formula engine, a 9-module interpreter), verify's gate vs an
*independent* hand-written held-out suite (`verify_realworld.py`):

| Metric | Result |
|---|---|
| Agreement with held-out ground truth | **12 / 13 = 92%** |
| Mean gate score on **good** impls | **89%** |
| Mean gate score on **broken** impls | **0%** |
| False-PASS (green-lit broken code) | **0 / 13** |

Across both, verify has **never once passed a broken implementation.** The only
disagreements were verify being *stricter* than the reference — the safe
direction for a gate.

**Determinism** (`verify_determinism.py`) — emit a suite once, then re-run it via
`--suite`: **60 re-runs, zero verdict drift** (correct impl 6/6 every run, broken
0/6 every run). A committed suite is a plain pytest file — no model, no flakiness,
safe to gate CI on.

**Cross-language** (`verify_crosslang.py`, *experimental*) — the `.qn` contract is
language-agnostic: `quinny verify --lang js` emits a Node `node:test` suite instead
of pytest. The same `mini_kv` contract gates a correct **JavaScript** impl at 6/6.
On the JS variant benchmark, verify kept its **0 false-PASS** safety property — it
never green-lit broken JS — but a *small* generation model (Haiku) was noisier on
JS than Python (63% accuracy, and every error a false-*alarm*, never a missed bug),
because JS test-gen (clock injection, `assert.throws`) is harder. The
emit→review→`--suite` flow is the fix — review the generated suite once, then it's
deterministic — and reliability rises with a stronger generation model.

Concrete `test` criteria **gate** the build; high-level `success` summaries are
shown as **advisory** (they're often unfalsifiable, so they never fail your build).

## The CLI

| Command | What it does | Needs an LLM? |
|---|---|---|
| `quinny scaffold "<english>"` | Scope the testable logic from a plain idea → draft a contract + a module stub | **yes** |
| `quinny check <file>` | Parse + validate the task graph (missing deps, cycles) | no |
| `quinny graph <file>` | Print the task graph | no |
| `quinny plan  <file>` | Show execution layers | no |
| `quinny verify <file> <impl/>` | Compile `test` criteria → run them against code → gate | **yes** (or `--suite`, no) |
| `quinny gen "<english>"` | Translate English → a `.qn` plan | **yes** |
| `quinny build <file>` | *(experimental)* generate code from a `.qn` | **yes** |

`quinny verify` flags: `--emit <path>` (save the suite), `--suite <path>` (re-run a
saved suite with no LLM), `--model <m>`.

## Credentials

`verify`/`gen`/`build` call an LLM via the Anthropic SDK: set `ANTHROPIC_API_KEY`,
or point at any Anthropic-compatible proxy with `ANTHROPIC_BASE_URL` +
`ANTHROPIC_AUTH_TOKEN`. `QUINNY_MODEL` sets the default model.
`check`/`graph`/`plan` and `verify --suite` need **no** credentials.

## The language

Ten keywords, indentation-sensitive, no loops or variables — those belong to the
target language:

```
project    task       component
goal       input      output
constraint depends    uses
test       success
```

Full reference: **[docs/LANGUAGE_SPEC.md](docs/LANGUAGE_SPEC.md)** ·
Writing plans with an LLM: **[docs/AI_PROMPT.md](docs/AI_PROMPT.md)** ·
Walkthrough: **[docs/getting-started.md](docs/getting-started.md)** ·
With Claude Code: **[docs/claude-code.md](docs/claude-code.md)**.

## A note on code generation (`quinny build`)

`quinny build` — decompose a `.qn` into a task graph and generate one file per
node — still ships, but it's **experimental**, and you should reach for it with
eyes open. In held-out benchmarks (`benchmarks/`), a plain one-shot prompt to a
single model consistently produced *better* code than Quinny's decompose-and-stitch
pipeline, at every project size — because modern models keep the whole problem
coherent, while per-node generation loses cross-module agreement. So: let a strong
agent write the code however it writes best, and use **`quinny verify`** to hold it
to your contract. That's where Quinny earns its keep.

## Status

Solid: the language + parser + graph validation, and **`quinny verify`** (the
acceptance-contract engine). Experimental: `gen`, `build`.

Roadmap: verification targets beyond pytest/Python (JS, Go, …); a packaged GitHub
Action for `quinny verify` (the pattern is in [docs/ci.md](docs/ci.md) today);
a JSON plan format for dependency-free tooling.

## Contributing

Issues and PRs welcome. Please keep the language small (10 keywords on purpose)
and add a test for any parser/graph/validator change.

## License

[Apache-2.0](LICENSE).
