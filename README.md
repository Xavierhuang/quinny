# Quinny

**A task-oriented intent language for AI coding agents.**

Quinny sits *above* Python, Swift, TypeScript, Rust, etc. You describe **what**
should be built — goals, inputs/outputs, dependencies, constraints, and how to
verify it — and Quinny compiles that into a validated **task graph**, then drives
an LLM to generate, verify, and assemble the actual code.

```
English  →  Quinny (.qn)  →  Task Graph  →  Plan  →  Generated code (Python, …)
             │                  │            │          │
             │ 10 keywords      │ DAG +      │ layers    │ per-node LLM gen
             │ indentation      │ validation │           │ + verify + repair
```

A `.qn` file is **not code that runs** — it is a structured, human-readable,
version-controllable description of intent. `quinny check` catches missing
components and broken dependencies *at plan time* (cheap), before a single line
of code is generated.

---

## Install

```bash
# One-liner — installs the Python-free binary on Apple Silicon, else falls back to pip:
curl -fsSL https://raw.githubusercontent.com/weijiahuang/quinny/main/install.sh | sh

# Or straight from PyPI (needs Python 3.10+):
pip install quinny
```

The installer honors `QUINNY_METHOD=pip|binary`, `QUINNY_VERSION=vX.Y.Z`, and
`QUINNY_PREFIX=<dir>`. Prebuilt binaries are attached to each
[GitHub Release](https://github.com/weijiahuang/quinny/releases).

From source:

```bash
git clone https://github.com/weijiahuang/quinny
cd quinny
pip install -e .
```

Requires Python 3.10+.

## Quickstart

Write `hello.qn`:

```
project SimpleLogin

task Login
    goal
        Authenticate a user with email and password.
    input
        email
        password
    output
        jwt_token
    constraint
        Under 200ms latency.
    test
        Invalid password is rejected.
    success
        Valid credentials produce a token.
```

Validate and inspect the plan (no LLM, no key needed):

```bash
quinny check hello.qn      # ✓ parses + graph is valid
quinny plan  hello.qn      # execution layers
quinny graph hello.qn      # the task graph
```

Generate code (needs credentials — see below):

```bash
quinny build hello.qn --full-verify --assemble -o out/
# → out/login.py, out/shared_types.py, out/main.py, requirements.txt, README.md
```

## The CLI

| Command | What it does | Needs an LLM? |
|---|---|---|
| `quinny parse <file>`  | Parse a `.qn` to its AST | no |
| `quinny check <file>`  | Parse + validate the task graph (missing deps, cycles) | no |
| `quinny graph <file>`  | Print the task graph | no |
| `quinny plan  <file>`  | Show execution layers (what can run in parallel) | no |
| `quinny gen "<english>"` | Translate English → a `.qn` plan | **yes** |
| `quinny build <file>`  | Generate code from a `.qn` (per-node gen → verify → repair → assemble) | **yes** |

`quinny build` flags: `--target python`, `-o <dir>`, `--full-verify`, `--assemble`,
`--model <m>` (and per-stage `--types-model` / `--node-model` / `--repair-model` /
`--assemble-model`), `--max-repair N`, `--only <node>`.

## Credentials

`gen` and `build` call an LLM. Quinny uses the Anthropic Python SDK, so it reads
standard environment variables:

- **Anthropic API key:** `export ANTHROPIC_API_KEY=sk-...`
- **Any Anthropic-compatible proxy** (bring-your-own gateway): set
  `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` (Bearer). `QUINNY_MODEL` sets the
  default model. Everything before `gen`/`build` (`parse`/`check`/`graph`/`plan`)
  needs **no** credentials.

## The language

Ten keywords, indentation-sensitive, no loops or variables — those belong to the
target language the agent emits:

```
project    task       component
goal       input      output
constraint depends    uses
test       success
```

Full reference: **[docs/LANGUAGE_SPEC.md](docs/LANGUAGE_SPEC.md)**.
Writing plans with an LLM: **[docs/AI_PROMPT.md](docs/AI_PROMPT.md)**.
First-time walkthrough: **[docs/getting-started.md](docs/getting-started.md)**.

## When to use Quinny (honest scope)

Quinny is **v0.1 / alpha**, and it is not free — a `build` makes many sequential
LLM calls, so it costs **more** tokens and time than a single "just write it"
prompt. It earns that cost only on **genuinely complex, multi-component projects**
where a one-shot attempt would miss a piece, leave a dependency dangling, or drift
between files — the kind of failure that's expensive to debug afterward.

- **Reach for Quinny:** larger systems with several interdependent components,
  cross-file contracts, and non-trivial ordering; when you want the plan reviewed
  before code is written; when you want each file verified as it's generated.
- **Don't bother:** simple scripts, one-file utilities, single features, quick
  edits, refactors, bug fixes — a plain prompt is faster, cheaper, and just as
  reliable.

The `.qn` plan is the durable artifact: readable, editable, diffable, reusable.

## Status

Implemented: parser, task-graph builder + validator, planner, code generator,
verify/repair loop, `main.py` assembly, CLI. See
[CHANGELOG.md](CHANGELOG.md).

Roadmap: a JSON/schema plan format (for dependency-free tooling), parallel node
execution, and code-gen targets beyond Python.

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[Apache-2.0](LICENSE).
