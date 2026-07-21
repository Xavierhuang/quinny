Implement `top_k(items, k, key=None)` — return the `k` largest items from `items`, in descending order, preserving original order on ties.

## Rules

- `items` must be a `list` (of any comparable elements). Non-list → `TypeError`.
- `k` must be an `int` (booleans excluded). Non-int → `TypeError`. Negative → `ValueError`. `k == 0` → `[]`.
- If `k > len(items)`, return **all** items sorted descending (still stable on ties).
- Ties: preserve the **original insertion order** in the result — i.e. if two items compare equal by `key`, the one that appeared earlier in `items` comes first in the result.
- `key` is an optional callable applied to each item to derive the comparison value (identity if `None`).
- Return type: `list`. The returned list must contain the original items, not their key-values.

## Interface

- File: `impl.py`.
- Export exactly one public function: `top_k(items, k, key=None)`.
- Stdlib only.

## Reference cases

```python
top_k([], 3)                                            # []
top_k([1, 2, 3], 0)                                     # []
top_k([3, 1, 4, 1, 5, 9, 2, 6], 3)                      # [9, 6, 5]
top_k([1, 2, 3], 10)                                    # [3, 2, 1]

# Ties: first-occurrence order preserved.
top_k([(5,"a"), (3,"b"), (5,"c")], 2, key=lambda t: t[0])
# [(5, "a"), (5, "c")]

top_k([{"n":3}, {"n":1}, {"n":5}], 2, key=lambda d: d["n"])
# [{"n": 5}, {"n": 3}]

top_k([1,2,3], -1)                                       # ValueError
top_k([1,2,3], 1.5)                                      # TypeError
top_k("abc", 2)                                          # TypeError
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
