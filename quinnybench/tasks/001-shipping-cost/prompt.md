Implement a Python function `shipping_cost(weight_kg)` that returns the cost in USD for shipping a package of the given weight.

## Rules

- Flat **$5.00** for any package **≤ 1 kg** (including 0 kg).
- Over 1 kg up to 10 kg inclusive: **$5.00 base + $1.50 per kg over 1 kg** (fractional kg pro-rated).
- Strictly over 10 kg: **$20.00 base + $2.00 per kg over 10 kg** (fractional kg pro-rated).
  Note: this creates a $1.50 discontinuity at 10 kg by design — the tier 2 ceiling is $18.50 but tier 3 starts at $20.00.
- **Negative** `weight_kg` must raise `ValueError`.
- **Non-numeric** `weight_kg` (e.g. a string) must raise `TypeError`.
- Return type: `float`.

## Interface

- Put the code in a single file named `impl.py`.
- Export exactly one public function: `shipping_cost(weight_kg)`.
- No CLI, no side effects, no imports outside the Python stdlib.

## Reference cases

| weight_kg | cost_usd |
|-----------|----------|
| 0         | 5.00     |
| 0.5       | 5.00     |
| 1.0       | 5.00     |
| 1.5       | 5.75     |
| 5.0       | 11.00    |
| 10.0      | 18.50    |
| 10.5      | 21.00    |
| 25.0      | 50.00    |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
