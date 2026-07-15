# Quinny

**An intent language that doubles as an executable acceptance contract.**

You describe *what* should be built — goals, inputs/outputs, dependencies,
constraints, and concrete acceptance `test`s — in a small, reviewable `.qn` file.
Quinny turns those acceptance criteria into a runnable test suite and **verifies
any implementation against them** — code written by a human, by Claude Code, by
Cursor, by anything.

```
intent.qn  ──►  quinny verify  ──►  ✓/✗ per acceptance criterion, on ANY code
   │                    │
   │ reviewable,        │ compiles your `test` criteria into a pytest suite,
   │ diffable spec      │ runs it against the implementation, gates the build
```

A `.qn` file is **not code that runs** — it's a structured, version-controllable
description of intent *and* the contract that decides whether an implementation
satisfies it. Write "done" once; enforce it forever, in CI.

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

Measured on implementations with known, exact defects (`benchmarks/verify_usability.py`):

| Metric | Result |
|---|---|
| False-PASS (green-lights a real defect) | **0 / 60** |
| False-FAIL (fails correct code) | **0 / 60** |
| Accuracy vs ground truth | **100%** |
| Consistency across runs | **100%** |

Concrete `test` criteria **gate** the build; high-level `success` summaries are
shown as **advisory** (they're often unfalsifiable, so they never fail your build).

## The CLI

| Command | What it does | Needs an LLM? |
|---|---|---|
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
