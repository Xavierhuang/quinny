Implement `iso_week(d)` — return the ISO 8601 week date tuple `(year, week, weekday)` for a given `datetime.date`.

## Rules

- `d` must be a `datetime.date` (not `datetime.datetime`, not string). Others → `TypeError`.
- Return a **tuple of three ints**: `(iso_year, iso_week, iso_weekday)` where:
  - `iso_weekday` uses **1 = Monday, …, 7 = Sunday**.
  - `iso_year` may differ from `d.year` around January 1 (per ISO 8601 rules): e.g. Sunday 2023-01-01 belongs to ISO year 2022 week 52; Tuesday 2024-12-31 belongs to ISO year 2025 week 1.
  - Some years have 53 ISO weeks (e.g. 2020).

## Interface

- File: `impl.py`.
- Export exactly one public function: `iso_week(d)`.
- Return type: `tuple[int, int, int]`. Stdlib only — `date.isocalendar()` does the heavy lifting.

## Reference cases

| date (weekday)             | result          |
|----------------------------|-----------------|
| 2024-01-01 (Mon)           | (2024, 1, 1)    |
| 2024-01-07 (Sun)           | (2024, 1, 7)    |
| 2024-01-08 (Mon)           | (2024, 2, 1)    |
| 2023-01-01 (Sun)           | (2022, 52, 7)   |
| 2024-12-31 (Tue)           | (2025, 1, 2)    |
| 2020-12-31 (Thu)           | (2020, 53, 4)   |
| `"2024-01-01"` (str)       | `TypeError`     |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
