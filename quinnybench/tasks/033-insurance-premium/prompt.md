Implement `calc_premium(age, tier)` — annual insurance premium as `tier base rate × age factor`.

## Rates

| tier       | base rate |
|------------|-----------|
| `basic`    | 100       |
| `standard` | 250       |
| `premium`  | 500       |

## Age factor

| age band                   | factor |
|----------------------------|--------|
| `age < 25`                 | 1.5×   |
| `25 <= age <= 40`          | 1.0×   |
| `41 <= age <= 60`          | 1.3×   |
| `age >= 61`                | 1.8×   |

## Errors

- Non-int `age` (booleans excluded) → `TypeError`.
- Negative `age` → `ValueError`.
- Unknown `tier` (anything not in `{"basic","standard","premium"}`) → `ValueError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `calc_premium(age, tier)`.
- Return type: `float`. Stdlib only.

## Reference cases

| age | tier       | premium |
|-----|------------|---------|
| 30  | basic      | 100     |
| 30  | standard   | 250     |
| 30  | premium    | 500     |
| 24  | basic      | 150 (1.5×) |
| 41  | basic      | 130 (1.3×) |
| 60  | basic      | 130     |
| 61  | basic      | 180 (1.8×) |
| 25  | basic      | 100 (boundary: 1.0×, not 1.5×) |
| -1  | basic      | ValueError |
| 30.5| basic      | TypeError |
| 30  | platinum   | ValueError |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
