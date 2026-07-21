Implement `format_duration(seconds)` — format a non-negative integer number of seconds into a compact human string like `"1d 2h 3m 4s"`.

## Rules

- Components are `d` (days = 86400s), `h` (hours = 3600s), `m` (minutes = 60s), `s` (seconds). Always in that order.
- Skip zero components. E.g. `86461s = 1 day + 1 minute + 1 second` → `"1d 1m 1s"` (no `"0h"` in the middle).
- The one special case: `0` seconds → `"0s"` (must return something non-empty).
- Components are joined by a single space.

## Errors

- Non-int input (booleans excluded) → `TypeError`.
- Negative input → `ValueError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `format_duration(seconds)`.
- Return type: `str`. Stdlib only.

## Reference cases

| seconds | result           |
|---------|------------------|
| 0       | `"0s"`           |
| 1       | `"1s"`           |
| 60      | `"1m"`           |
| 3600    | `"1h"`           |
| 86400   | `"1d"`           |
| 3661    | `"1h 1m 1s"`     |
| 86461   | `"1d 1m 1s"`     |
| 90061   | `"1d 1h 1m 1s"`  |
| 59      | `"59s"`          |
| 3599    | `"59m 59s"`      |
| -1      | ValueError       |
| 1.5     | TypeError        |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
