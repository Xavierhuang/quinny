Implement `charge(amount, day_of_month, days_in_month)` — a pro-rated subscription charge for a mid-month signup.

## Formula

```
charge = amount * (days_in_month - day_of_month + 1) / days_in_month
```

So a signup on day 1 of a 30-day month costs the full `amount`; a signup on day 30 of a 30-day month costs `amount / 30`.

## Rules

- `amount` must be a non-negative real number. Booleans do **not** count as numbers here. Non-numeric → `TypeError`. Negative → `ValueError`.
- `day_of_month` and `days_in_month` must be `int` (not `bool`). Non-int → `TypeError`.
- `days_in_month` must be one of `28, 29, 30, 31`. Otherwise → `ValueError`.
- `day_of_month` must satisfy `1 <= day_of_month <= days_in_month`. Otherwise → `ValueError`.
- Return type: `float`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `charge(amount, day_of_month, days_in_month)`.
- Stdlib only.

## Reference cases

| amount | day | days_in_month | charge         |
|--------|-----|---------------|----------------|
| 30     | 1   | 30            | 30.00          |
| 30     | 30  | 30            | 1.00           |
| 30     | 15  | 30            | 16.00          |
| 31     | 1   | 31            | 31.00          |
| 28     | 1   | 28            | 28.00          |
| 30     | 15  | 31            | ≈ 16.4516      |
| 0      | 15  | 30            | 0.00           |
| -1     | 1   | 30            | ValueError     |
| 30     | 0   | 30            | ValueError     |
| 30     | 31  | 30            | ValueError     |
| 30     | 1   | 27            | ValueError     |
| "30"   | 1   | 30            | TypeError      |
| 30     | 1.5 | 30            | TypeError      |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
