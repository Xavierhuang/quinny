Implement `weekend_count(start, end)` — count Saturdays and Sundays in the **inclusive** date range `[start, end]`.

## Rules

- Both `start` and `end` must be `datetime.date` (not `datetime`, not string). Others → `TypeError`.
- `end < start` → `ValueError`.
- The range is inclusive of both endpoints.
- "Weekend" = Saturday and Sunday (`date.weekday()` values 5 and 6).
- Return type: `int`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `weekend_count(start, end)`.
- Stdlib only.

## Reference cases

Using 2026-07-20 = Mon, 2026-07-24 = Fri, 2026-07-25 = Sat, 2026-07-26 = Sun, 2026-07-27 = next Mon:

| start        | end          | result |
|--------------|--------------|--------|
| 2026-07-20 Mon | 2026-07-24 Fri | 0    |
| 2026-07-20 Mon | 2026-07-26 Sun | 2    |
| 2026-07-25 Sat | 2026-07-25 Sat | 1    |
| 2026-07-26 Sun | 2026-07-26 Sun | 1    |
| 2026-07-25 Sat | 2026-07-27 Mon | 2    |
| 2026-07-20 Mon | 2026-07-27 Mon | 2    |
| 2026-07-20 Mon | 2026-08-03 Mon | 4    |
| 2026-07-22 Wed | 2026-07-22 Wed | 0    |
| 2026-07-24 Fri | 2026-07-20 Mon | ValueError |
| `"2026-07-20"` | 2026-07-20   | TypeError |
| 2026-07-20   | `"2026-07-21"` | TypeError |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
