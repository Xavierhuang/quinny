# Does the verify loop make a model produce better code?

The other benchmarks show `quinny verify` *catches* broken code. This one asks
the outcome question: if you embed the verify loop in an agent's workflow, does
the agent ship **more-correct** code than one-shot?

## Method

Same model, two conditions, on `mini_sheet` (a formula engine):

- **A — one-shot (no Quinny):** write the module from the prompt. Stop.
- **B — verify-loop (Quinny):** write it → `quinny verify` against a contract →
  feed the FAILED criteria back → fix → re-verify, up to a few rounds.

Both graded by an **independent hand-written held-out suite** (`tests_holdout/
mini_sheet_test.py`) — never shown to the model, and NOT the verify contract — so
a gain means genuinely more spec-conforming code, not teaching-to-its-own-test.
Every model call (generation, fixes, AND verify's own test generation) is metered,
so the token cost is the true total. Harness: `verify_loop.py`, `metrics.py`.

## Results (2 runs each, held-out graded)

| Model | Condition | Tokens (in+out) | Time | Correctness |
|---|---|---|---|---|
| **Haiku** | one-shot | 5,218 | 38s | **50%** — swung 11, 0, 9 across runs |
| **Haiku** | verify-loop | 7,175 | 42s | **100%** |
| **Kimi (k2.7)** | one-shot | 16,446 | 293s | **50%** — swung 14, 0 |
| **Kimi (k2.7)** | verify-loop | 39,341 | 708s | **100%** |

**Cost of the loop: ~1.4–2.4× tokens, ~1.1–2.4× time. Correctness 50% → 100% for both.**

## What it means

- **Neither model is weak** — one-shot, *both* sometimes produce a perfect 14/14.
- **Both are unreliable** — the same prompt also produces **0/14** (silent total
  failure). That swing is the real risk: sometimes the logic is right, sometimes
  it's quietly broken.
- **The loop makes them reliable** — 100% every run. The clearest case: a Kimi
  one-shot that would have shipped broken took **2 fix rounds → 14/14**.

So the loop does **not** make a model smarter — it makes it **reliable**, by turning
the model's unseen mistakes into an objective fix signal. The price is ~2× tokens
and time. Worth it exactly where a wrong answer is expensive (checkout math), not
for a landing page. And on runs the model already gets right, the loop adds no
correctness (Kimi B-run with 0 fix rounds) — it's insurance against the broken half.

## Reproduce

```bash
# Haiku (via a Claude subscription / OAuth):
ANTHROPIC_AUTH_TOKEN=<oauth> QUINNY_OAUTH=1 QUINNY_MODEL=claude-haiku-4-5 \
  python benchmarks/metrics.py

# Kimi (via an Anthropic-compatible proxy):
ANTHROPIC_AUTH_TOKEN=<token> ANTHROPIC_BASE_URL=<proxy> QUINNY_MODEL=kimi-k2.7 \
  python benchmarks/metrics.py
```

## Harness notes (so the numbers are trustworthy)

- **Kimi emits `thinking` blocks.** The Anthropic SDK's high-level streaming
  accumulator crashes on them (`content.thinking += None`), which silently yielded
  *empty* generations (a false 0%). Fix: low-level streaming (`create(stream=True)`)
  collecting only `text_delta` events.
- **Budget.** Kimi spends much of its token budget thinking; at 8k it exhausted the
  budget before emitting code. `max_tokens=16000` gives room for thinking + code.
- These were harness bugs, not model failures — worth stating because an early,
  buggy run reported Kimi at 0% and it was wrong.
