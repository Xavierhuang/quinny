Implement `age_as_of(dob, as_of)` — integer age in years from a date of birth as of a reference date.

## Rules

- Both `dob` and `as_of` must be `datetime.date` (not `datetime.datetime` and not strings). Others → `TypeError`.
- `dob > as_of` → `ValueError` (a future date of birth is nonsense).
- Return **completed years** as an `int`. The birthday must have *occurred* — a birthday on the same month/day of `as_of` counts as occurred (age increments that day).
- **Leap-year rule**: a Feb 29 date of birth is considered to have its "birthday" on **Mar 1** in non-leap years (i.e. the birthday hasn't yet happened until the calendar is past February).

## Interface

- File: `impl.py`.
- Export exactly one public function: `age_as_of(dob, as_of)`.
- Return type: `int`. Stdlib only.

## Reference cases

| dob         | as_of       | age                                       |
|-------------|-------------|-------------------------------------------|
| 2000-06-15  | 2000-06-15  | 0                                         |
| 2000-06-15  | 2026-06-15  | 26 (birthday today)                       |
| 2000-06-15  | 2026-06-14  | 25 (birthday tomorrow)                    |
| 2000-01-01  | 2025-12-31  | 25                                        |
| 2000-02-29  | 2026-03-01  | 26 (non-leap year — Feb 29 birthday counts as Mar 1) |
| 2000-02-29  | 2026-02-28  | 25 (birthday not yet occurred in non-leap year) |
| 2030-01-01  | 2026-01-01  | `ValueError` (dob after as_of)            |
| `"2000-06-15"` (str) | 2026-06-15 | `TypeError`                       |
| 2000-06-15  | `"2026-06-15"` (str) | `TypeError`                       |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
