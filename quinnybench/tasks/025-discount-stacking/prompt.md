Implement `apply_discounts(subtotal, discounts)` — apply discount rules to a subtotal.

## Discount shape

Each discount is a dict:
```python
{"type": "percent" | "flat", "value": <number>, "stackable": <bool>}
```

- `percent` value is a percentage (e.g. `10` means 10% off).
- `flat` value is subtracted directly.

## Application rules

1. **Non-stackables:** if any non-stackable discounts are present, apply **only the ONE that gives the biggest savings** (silently drop the others). Compute savings against the current subtotal at the moment of selection.
2. **Stackables:** after the (single) non-stackable, apply **every** stackable, in the order given. Percents compound multiplicatively; flats subtract.
3. **Clamp**: the final total is `max(0.0, total)` — never negative.

## Errors

- Non-numeric `subtotal` (booleans excluded) → `TypeError`.
- Negative `subtotal` → `ValueError`.
- Non-list `discounts` → `TypeError`.
- Any discount with an unknown `type` → `ValueError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `apply_discounts(subtotal, discounts)`.
- Return type: `float`. Stdlib only.

## Reference cases

Using `P(v, s)` for percent, `F(v, s)` for flat, `s=True` stackable:

| subtotal | discounts                          | result |
|----------|------------------------------------|--------|
| 100      | `[]`                               | 100    |
| 100      | `[P(10, True)]`                    | 90     |
| 100      | `[F(15, True)]`                    | 85     |
| 100      | `[P(10, True), P(20, True)]`       | 72     |
| 100      | `[F(15, True), F(20, True)]`       | 65     |
| 100      | `[P(10, False), F(20, False)]`     | 80     |
| 100      | `[P(20, False), P(10, True)]`      | 72     |
| 100      | `[F(150, True)]`                   | 0      |
| 0        | `[P(50, True)]`                    | 0      |
| -1       | `[]`                               | ValueError |
| 100      | `[{"type":"bogus", …}]`            | ValueError |
| 100      | `P(10, True)` (not list)           | TypeError |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
