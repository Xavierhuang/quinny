# Quinny

**An executable specification language.**

Created by **[LingCode Baby](https://lingcode.dev/baby.html)** — a macOS IDE
that embeds Quinny as its built-in verify loop.

Describe *what* your software must do — its components and their concrete
acceptance criteria — in a small, reviewable `.qn` file. Quinny turns those
criteria into a runnable test suite and **verifies any implementation against
them** — code written by a human or by any AI coding assistant, in Python,
JavaScript, or Swift. Write the contract once; enforce it forever, in any language, in CI.

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

**In plain terms: across ~85 implementations — some correct, some deliberately
broken, some shaped like real CVEs — verify flagged every broken one and never
once passed a bad one.** The few times it disagreed with a human-written suite,
it was being *stricter*, not letting a bug through. The measured detail, five
benchmarks in [`benchmarks/`](benchmarks/):

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

**Determinism** (`verify_determinism.py`) — emit a suite once, then re-run it via
`--suite`: **60 re-runs, zero verdict drift** (correct impl 6/6 every run, broken
0/6 every run). A committed suite is a plain pytest file — no model, no flakiness,
safe to gate CI on.

**OSS-bug shapes** (`verify_oss_bugs.py`) — 5 fixtures modeled on real-world
CVE-shaped patterns (negative-quantity checkout, coupon stacking, zip-slip
path traversal, session-token expiry ignored, rate-limit off-by-one):

| Metric | Result |
|---|---|
| False-PASS (green-lit a buggy impl) | **0 / 5** |
| Defect criteria caught across buggy impls | **12 / 20** |
| False-FAIL on correct impls | 2 / 20 criteria (cried wolf, safe direction) |

**Scale** (`verify_scale.py`) — sweep from 10 → 1000 acceptance criteria per
spec. This is the harshest coherence test: does the emit stay honest as
the spec grows? Two models tested; the ceiling is model-specific:

*Haiku 4.5*

| N criteria | emit time | suite lines | passed / N | coverage | verdict |
|---:|---:|---:|---:|---:|---|
| 10   | 12.3s | 73  | 10/10   | 100%    | coherent |
| 25   | 13.2s | 158 | 25/25   | 100%    | coherent |
| 50   | 24.1s | 316 | 50/50   | 100%    | coherent |
| 100  | 45.8s | 623 | 100/100 | 100%    | coherent |
| 250  | 28.3s | 663 | 102/250 | **41%** | **degrading** |
| 500  | 58.3s | 366 | 0/500   | **0%**  | **collapsed** |
| 1000 | 55.7s | 157 | 0/1000  | **0%**  | **collapsed** |

*Kimi K2* (via LingCode proxy, `kimi-k2.7`)

| N criteria | emit time | suite lines | passed / N | coverage | verdict |
|---:|---:|---:|---:|---:|---|
| 250  | 79.0s | 23 | 250/250   | 100% | coherent |
| 500  | 32.4s | 22 | 500/500   | 100% | coherent |
| 1000 | 65.7s | 18 | 1000/1000 | 100% | coherent |

**What Kimi did differently**: rather than emit 1000 separate test
functions (which would hit any model's output ceiling), Kimi wrote a
20-line metaprogrammed loop that dynamically generates one test per
criterion via `globals()`. Pytest discovers all 1000 tests individually
and runs them — real coverage, not a shortcut. **Caveat**: this works
because these criteria share a homogeneous shape (`set_kN(v)` /
`get_kN() == v`); on heterogeneous specs (OSS-bug, subtle, real-OSS)
metaprogramming would not apply and per-criterion emit would return.

**Honest limit named**: on Haiku 4.5 the emit stays coherent through ~100
criteria and collapses past 250 (output-token ceiling — see `suite lines`
shrinking from 623 → 157 as N grows). This is a false-*FAIL* cliff, not
a false-PASS one; missing tests fail-by-default, so the safety property
still holds. Kimi K2 pushes this ceiling out significantly on
homogeneous specs. The committed suite path (`--suite`, no model) has no
such limit and re-runs flat at ~0.3s regardless of N.

*Future work*: rerun the 250 / 500 / 1000 sweep on Sonnet 4.6 and Opus
4.7 (the initial attempt hit subscription-tier rate limits). Also run
Kimi against the OSS-bug and subtle harnesses to see if its structural
advantage carries over to heterogeneous criteria.

**Subtle-bug classes** (`verify_subtle.py`) — 6 defect variants each targeting
one criterion: off-by-one at capacity, silent NaN in aggregation, unicode
NFC/NFD confusion, wrong exception type, TTL integer overflow, TTL=0 semantics.
The kind of bug humans reliably miss in review:

| Metric | Result |
|---|---|
| False-PASS (missed a subtle defect) | **0 / 6** |
| Surgical FAIL (exact criterion the defect targets) | 6 / 6 |
| False-FAIL on correct impl | 0 |

After one emit, the committed suite (`benchmarks/fixtures/subtle/suite.py`)
runs offline forever — the pattern you'd use in CI.

**Real-OSS** (`verify_real_oss.py`) — the strongest single data point in the
suite: verify pointed at [`cachetools`](https://github.com/tkem/cachetools)
(~2k stars, 15+ years old, *not* authored by us). A thin wrapper exposes
`LRUCache` and `TTLCache`; the .qn spec targets 8 documented API guarantees.
Then a targeted mutation is injected (LRU-recency bypass on reads):

| Variant | Verdict | Ground truth |
|---|---|---|
| pristine cachetools (shipping code) | 8/8 PASS | ✅ 0 cried-wolf on real library |
| mutated (LRU-recency defect) | 7/8 PASS, C3 fails | ✅ surgical: exactly the injected bug |

Neither failure mode fired: the gate did not cry wolf on real shipping code,
and it identified the exact criterion the mutation targeted with zero
collateral. This is the answer to *"of course the gate catches bugs you
wrote"* — the library, the wrapper wiring, and the test scaffolding all
work end-to-end on code we did not author.

**Add your own library.** The harness auto-discovers every subdirectory
under `benchmarks/fixtures/real_oss/` with a `manifest.py` — five files
and no code changes to add a new one. Full recipe in
[`benchmarks/fixtures/real_oss/README.md`](benchmarks/fixtures/real_oss/README.md).
Every library that lands there is one more independent data point for
the gate's honesty on code the Quinny author didn't touch.

**Format equivalence: DSL vs JSON** (`verify_formats.py`) — same
acceptance criteria expressed once in `.qn` DSL and once in `.json`.
Both formats extract to the same 6 criteria and produce identical
verify verdicts against the same committed suite. Conclusion: **the
DSL is a matter of taste, not capability** — teams that prefer JSON
can use it and lose nothing. (Bug fix landed in the same commit:
`ast_to_json` was silently dropping repeated `test` blocks, so this
claim was actually broken in main until this benchmark surfaced it.)

**Across all six benchmarks: 0 false-PASS on ~90 implementations** spanning
synthetic defects, real model-generated code, CVE-shaped bug patterns,
subtle-defect classes, and a real published library. The handful of
disagreements are verify being *stricter* than the reference — the safe
direction for a gate. That reliability is what makes the write→verify→fix
loop below actually work.

**Cross-language** (*experimental*) — the `.qn` contract is language-agnostic; only
the emitted suite differs. `--lang python` → pytest, `--lang js` → Node's `node:test`,
`--lang swift` → a test compiled alongside the code with `swiftc`. The same contract
that gates Python gates a correct **JavaScript** impl (6/6) and a **Swift** one (a
correct cart 4/4, a broken cart 2/4 — catching exactly the two planted defects).
Verify kept its **0 false-PASS** safety property in every language. Caveat: a *small*
generation model is noisier on non-Python targets (on the JS variant benchmark,
Haiku was 63% accurate — every error a false-*alarm*, never a missed bug), because
their test-gen is harder. The emit→review→`--suite` flow is the fix (review the
generated suite once, then it's deterministic), and reliability rises with a stronger
model. Adding a language (Go, Rust, …) is one entry in the `LANGS` registry.

Concrete `test` criteria **gate** the build; high-level `success` summaries are
shown as **advisory** (they're often unfalsifiable, so they never fail your build).

### Does it actually improve the code an agent produces?

The tables above show verify *catches* broken code. This measures the **outcome**:
give the same model the loop it enables — write → verify → fix the failures →
repeat — and grade the result with an *independent* held-out suite. Full method +
reproduce steps in [`benchmarks/VERIFY_LOOP_RESULTS.md`](benchmarks/VERIFY_LOOP_RESULTS.md).

| Model | one-shot (no Quinny) | verify-loop (Quinny) |
|---|---|---|
| **Haiku** | 50% — swings 11/0/9 across runs | **100%** |
| **Kimi (k2.7)** | 67% — swings 14/0/14 across runs | **100%** |

**~1.4–2.4× the tokens and time → correctness ~50–67% → 100%, for both models.**

The honest read: it doesn't make a model *smarter* — it makes it **reliable.**
One-shot, both models sometimes nail it (14/14) and sometimes ship silent garbage
(0/14); the loop turns those unseen mistakes into an objective fix signal and lands
at correct every time. You pay ~2× to never ship the broken half — worth it for
checkout math, not for a landing page. On a run the model already gets right, the
loop adds no correctness (zero fix rounds) — it's insurance, not overhead you always
pay. (Opus pending — rate-limited during testing; the mechanism is model-independent.)

**Honest limit — the loop can hit the `MAX_FIX` ceiling and deliver
un-converged code.** Retested on `fsheet` (a formula spreadsheet engine,
17 held-out tests) with Haiku:

| Run | held-out | notes |
|---|---:|---|
| A one-shot run 0 | 13/17 | ranges + parens buggy |
| A one-shot run 1 | 17/17 | perfect |
| B verify-loop run 0 | **10/17** | 3 fix rounds — verify still flagged 3 failures at exit |

Autopsy: verify's 6 criteria correctly flagged the initial range +
precedence bugs. Haiku's fix rounds fixed those — but under pressure to
make failures go away also added a defensive
`except Exception: return "#DIV/0!"` catch-all in the expression parser.
Any subsequent parser hiccup now silently returns `#DIV/0!` instead of
the real value, breaking `test_basic_ref_and_add`, unary minus, cycle
detection, and recalc-after-change. Running verify against the final B
code correctly reports 3 gating FAILs — the contract *did* catch the
regression. The loop just ran out of fix rounds (`MAX_FIX=3` in
`verify_loop.py`) and returned the still-broken code, which then landed
at 10/17 on held-out.

Two lessons:

1. **Trust the verify verdict at exit, not just the fix-round count.**
   The loop should refuse to declare success — or fall back to the
   pre-loop code — if verify still reports gating failures after
   `MAX_FIX` rounds. `verify_loop.py` currently just exits and returns
   whatever the last fix round produced. That's a fixable bug.
2. **Haiku's fix pattern under pressure is to silently swallow errors.**
   A blanket `except Exception: return SENTINEL` is a well-known
   antipattern; a pre-verify lint step could flag it and stop the fix
   round from being accepted at all.

*Follow-up experiment.* We then doubled the contract to 11 criteria
(added unary minus, MIN/MAX/AVG, rectangular ranges, diamond-not-cycle,
recalc-explicitly) and raised `MAX_FIX` to 5, then re-ran:

| Run | held-out | notes |
|---|---:|---|
| A one-shot run 0 | 17/17 | perfect |
| A one-shot run 1 | 15/17 | small swing (2 tests off) |
| B verify-loop run 0 | 13/17 | 2 fix rounds — verify PASSED |
| B verify-loop run 1 | 14/17 | 2 fix rounds — verify PASSED |

Summary: **A mean 94% → B mean 79%** at **5.2× tokens, 3.5× time**. Both
B runs converged (verify said PASS after 2 rounds) — so this isn't a
`MAX_FIX` exhaustion. The 11-criterion contract still under-specifies;
Haiku found rewrites that satisfy all 11 while regressing behaviors
still not covered.

**The refined thesis, honest version:**

- **Loop helps** when one-shot is *unreliable* — swings between 100% and
  catastrophic 0% (mini_sheet on both Haiku and Kimi). The loop closes
  the catastrophic tail; net correctness goes from ~50% mean → 100%.
- **Loop hurts** when one-shot is *already mostly-right* (fsheet + Haiku
  at 94% one-shot). Fix rounds' rewrites introduce more bugs than they
  solve, and the contract can't discipline behaviors it doesn't test.
  The loop can regress net correctness by ~15 percentage points *while
  believing it succeeded*.

Use the loop where one-shot is genuinely risky (unfamiliar logic,
sometimes-broken outputs, high cost of a silent bug). Skip it — or
just use it as a passive check without letting fix rounds mutate the
code — where the base model is already reliable on the task.

**Follow-up fix (landed on `main`).** Two changes to close the fsheet
regression: (1) a diff-aware `fix()` prompt that demands the smallest
possible change and explicitly forbids broad-except panic patterns; (2)
an AST-level lint that rejects any fix round whose new code has a
narrow `except` and a broad `except Exception` returning the same
sentinel (the exact shape that regressed 7 held-out tests). Same task,
same model, both fixes active:

| Configuration | A mean | B mean | Δ |
|---|---:|---:|---:|
| Original (6-crit contract, `MAX_FIX=3`) | 88% | 59% | **-29pp** |
| + Extended contract (11 crit, `MAX_FIX=5`) | 94% | 79% | **-15pp** |
| + Diff-aware prompt + panic lint | 76% | **94%** | **+18pp** |

The two fixes flipped fsheet Haiku from a -29pp regression into a
+18pp win. The lint fired zero times this run — the prompt alone was
enough to stop the antipattern being emitted. The lint stays as
defense in depth. B still isn't a clean 100% (one run landed at
15/17), so the loop remains "insurance," not a magic upgrade — but
it's now insurance that pays out net-positive.

## The CLI

| Command | What it does | Needs an LLM? |
|---|---|---|
| `quinny scaffold "<english>"` | Scope the testable logic from a plain idea → draft a contract + a module stub | **yes** |
| `quinny import <spec.md>` | Turn a [GitHub Spec Kit](https://github.com/github/spec-kit) `spec.md` into a `.qn` contract (stories → components, Given/When/Then → gating tests) | no |
| `quinny check <file>` | Parse + validate the task graph (missing deps, cycles) | no |
| `quinny graph <file>` | Print the task graph | no |
| `quinny plan  <file>` | Show execution layers | no |
| `quinny verify <file> <impl/>` | Compile `test` criteria → run them against code → gate (`--lang python`/`js`/`swift`) | **yes** (or `--suite`, no) |
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
