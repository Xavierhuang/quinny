Implement a `TokenBucket` class — a rate limiter driven by an **external clock** (so tests are deterministic without `time.sleep`).

## API

- `TokenBucket(capacity, refill_per_sec)`:
  - `capacity` — `int > 0`; the max tokens the bucket can hold. Non-int → `TypeError`. `<= 0` → `ValueError`.
  - `refill_per_sec` — non-negative `float` (or int); tokens added per second. Non-numeric → `TypeError`. Negative → `ValueError`.
  - Bucket starts **full** (`tokens == capacity`).
- `.tokens` — current token count as `int` (floor of the internal float). Read-only.
- `.try_take(now, n=1) -> bool`:
  - `now` is the caller's current time in seconds (float or int). It only ever moves forward.
  - Before deciding, **refill** the bucket based on elapsed time since the previous call: `tokens += (now - last) * refill_per_sec`, capped at `capacity`.
  - If `tokens >= n`, deduct `n` and return `True`.
  - Otherwise return `False` **without** deducting.

## Interface

- File: `impl.py`.
- Export exactly one public class: `TokenBucket`.
- Stdlib only.

## Reference cases

```python
b = TokenBucket(5, 1.0)
b.tokens                                   # 5

b.try_take(0.0, 1)                         # True; tokens == 4
b.try_take(0.0, 4)                         # True; tokens == 0 (from 4)
b.try_take(0.0, 5)                         # False; tokens stays

# Refill: 1 second later at rate 1/sec → 1 more token.
b2 = TokenBucket(5, 1.0); b2.try_take(0.0, 5)   # empty
b2.try_take(1.0, 1)                        # True; tokens == 0

# Refill is capped at capacity even after a long wait.
b3 = TokenBucket(5, 1.0); b3.try_take(0.0, 5)   # empty
b3.try_take(100.0, 5)                      # True (not 100 tokens; capped at 5)

TokenBucket(0, 1.0)                        # ValueError
TokenBucket(5, -1.0)                       # ValueError
TokenBucket(1.5, 1.0)                      # TypeError
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
