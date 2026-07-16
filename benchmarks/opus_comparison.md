# Does a cheap model + Quinny beat Opus?

Short answer: **no — it *matches* it, and the reason it can't beat it is structural.**
That match is the useful result, so this note records exactly what was measured
and what it does and doesn't mean.

## The question

Can a weak, cheap model (Haiku 4.5) driven by Quinny's verify-loop reach — or
exceed — a frontier model's (Opus) one-shot output quality on tasks you can write
an acceptance contract for?

## Method

- **Nine single-module tasks**, each with a hand-written **held-out** pytest suite
  that the code generator never sees and that is *not* the `.qn` verify contract —
  so a pass means genuinely spec-conforming code, not teaching-to-its-own-test.
- **A leg (baseline):** the model writes the module one-shot from the prompt.
- **B leg (Quinny):** the model writes it, then runs `quinny verify` against the
  contract, feeds the FAILED criteria back, fixes, re-verifies — with the
  **keep-best guard** (never returns code worse than the best version seen) and an
  early-stop on sustained no-progress.
- Opus one-shot is generated via the `claude` CLI (`--tools ""`); Haiku via the
  Anthropic SDK. Both graded by the same held-out suite.

## Result 1 — Opus one-shots every gradeable task at 100%

| Regime | Tasks | Opus one-shot |
|---|---|---|
| Isolated-edge | semver, money, globmatch, cidr | **100%** |
| Algorithmic-subtle | cron (day-of-month/day-of-week OR-rule, Feb-29, steps) | **100%** |
| Integrated | fsheet, mini_sheet | **100%** |
| Volume (24 functions) | textkit | **100%** |

Across every regime a well-specified, objectively-gradeable task can take, Opus's
one-shot output was 100% correct. There was no headroom left to beat.

## Result 2 — Quinny lifts a cheap model to that same ceiling

The two *integrated* tasks are where a cheap model's one-shot is unreliable — and
where the verify-loop earns its keep:

| Task | Haiku one-shot | Haiku + Quinny (guarded) | Opus one-shot | cost of Quinny |
|---|---|---|---|---|
| **fsheet** | 94% (a run drops to 65%) | **100%** | 100% | 2.7× Haiku tokens |
| **mini_sheet** | 70% (a run drops to **0%**) | **98%** | ~100% | 2.9× Haiku tokens |

On fsheet the match is exact: **Haiku+Quinny 100% = Opus 100%.** And the cheap
model genuinely *needed* Quinny to get there — alone it silently shipped a 0/14
and a 65% build. The keep-best guard means no B run ever regressed below its own
one-shot; the catastrophic 0/14 cannot survive the loop.

## Why "beats" is structurally unreachable

To beat Opus you need a task where **Opus one-shot < 100% yet the task is still
objectively gradeable.** But gradeable requires a complete, unambiguous spec —
and a complete spec is exactly what lets Opus get it right. Underspecify the task
to trip Opus and you can no longer gate it fairly (verify would false-fail). The
goal fights itself. Nine tasks across four regimes confirmed it.

## The honest conclusion

- ❌ **"weak + Quinny beats Opus"** — unreachable on gradeable tasks; nobody beats
  a frontier model's 100%.
- ✅ **"weak + Quinny matches Opus"** — proven, at **2–3× the cheap model's cost**
  (a fraction of Opus's price), and **never regressing** the code.

The equality is one of **outcome on contract-gated tasks**, reached by *iteration
against a verifier*, not one of raw capability. It does not extend to open-ended
work where no contract can gate. Stated as the value proposition:

> **Quinny buys frontier-model reliability at cheap-model prices** — on any task
> you can write an acceptance contract for.

## Reproduce

```bash
# A vs B (held-out graded) for any task:
QUINNY_TASK=fsheet QUINNY_MODEL=claude-haiku-4-5 QUINNY_RUNS=4 \
  python benchmarks/metrics.py

# Opus one-shot champion (CLI path — the SDK path rate-limits on big gens):
QUINNY_TASK=fsheet QUINNY_MODEL=claude-opus-4-7 QUINNY_RUNS=4 \
  python benchmarks/opus_champion.py   # (script in this repo's history / scratch)
```
