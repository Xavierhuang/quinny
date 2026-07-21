Implement `calc_tax(income)` — total tax owed under this fixed progressive-bracket schedule.

## Brackets

| From      | To (inclusive) | Rate |
|-----------|----------------|------|
| 0         | 10 000         | 10%  |
| 10 000    | 40 000         | 12%  |
| 40 000    | 85 000         | 22%  |
| 85 000    | 165 000        | 24%  |
| 165 000   | ∞              | 32%  |

Only income **within each bracket** is taxed at that bracket's rate ("marginal" / progressive). Cross a bracket boundary and only the overflow is taxed at the new rate.

## Errors

- Negative `income` → `ValueError`.
- Non-numeric input (str, None, list, `bool`) → `TypeError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `calc_tax(income)`.
- Return type: `float`. Stdlib only.

## Reference cases

| income     | tax        |
|------------|------------|
| 0          | 0.00       |
| 10 000     | 1 000.00   |
| 10 000.01  | ≈ 1 000.0012 (one cent into 12% bracket) |
| 40 000     | 4 600.00   |
| 100 000    | 18 100.00  |
| 165 000    | 33 700.00  |
| 200 000    | 44 900.00  |
| -1         | ValueError |
| "100000"   | TypeError  |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
