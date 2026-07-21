Implement `pivot(rows, row_key, col_key, value_key, agg="sum")` — pivot a list of dict rows into a nested dict `{row_val: {col_val: aggregated_value}}`.

## Rules

- For each row, look up `row_key`, `col_key`, `value_key` (all dict-style; missing key → `KeyError`, propagate).
- Aggregate cells that share the same `(row_val, col_val)` using `agg`:
  - `"sum"` — running sum of values.
  - `"count"` — number of contributing rows (ignores value; each row counts once).
  - `"max"` — maximum value.
  - `"min"` — minimum value.
- `agg` defaults to `"sum"`.

## Errors

- Non-list `rows` → `TypeError`.
- Unknown `agg` → `ValueError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `pivot(rows, row_key, col_key, value_key, agg="sum")`.
- Return type: `dict[Any, dict[Any, Any]]`. Stdlib only.

## Reference cases

```python
pivot([], "r", "c", "v", "sum")                                # {}

pivot([{"r":"A","c":"X","v":5}], "r","c","v","sum")            # {"A": {"X": 5}}

pivot([{"r":"A","c":"X","v":5}, {"r":"A","c":"X","v":3}],
      "r","c","v","sum")                                        # {"A": {"X": 8}}

pivot([{"r":"A","c":"X","v":1000}, {"r":"A","c":"X","v":999}],
      "r","c","v","count")                                      # {"A": {"X": 2}}

pivot([{"r":"A","c":"X","v":5}, {"r":"A","c":"X","v":12}, {"r":"A","c":"X","v":3}],
      "r","c","v","max")                                        # {"A": {"X": 12}}

pivot([{"r":"A","c":"X","v":5}, {"r":"A","c":"X","v":12}, {"r":"A","c":"X","v":3}],
      "r","c","v","min")                                        # {"A": {"X": 3}}

pivot([{"r":"A","c":"X","v":1}, {"r":"A","c":"Y","v":2}, {"r":"B","c":"X","v":3}],
      "r","c","v","sum")                                        # {"A": {"X":1,"Y":2}, "B": {"X":3}}

pivot([{"r":"A","c":"X"}], "r","c","v","sum")                  # KeyError (missing "v")
pivot({}, "r","c","v","sum")                                    # TypeError
pivot([{"r":"A","c":"X","v":1}], "r","c","v","median")         # ValueError
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
