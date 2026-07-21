Implement `dedupe(items)` — return a new list with duplicates removed, keeping the **first** occurrence of each element.

## Rules

- `items` must be a `list`. Any other type → `TypeError`.
- Elements are compared by equality; equal elements after the first are dropped.
- Preserve the order of first appearances.
- Elements must be hashable. Unhashable elements (like nested lists) → `TypeError` (propagate the natural error from `set` operations).
- `1` (int) and `"1"` (str) are different values and MUST NOT collapse.

## Interface

- File: `impl.py`.
- Export exactly one public function: `dedupe(items)`.
- Return type: `list`. Stdlib only.

## Reference cases

```python
dedupe([])                          # []
dedupe([1, 2, 3])                   # [1, 2, 3]
dedupe([1, 1, 2, 3])                # [1, 2, 3]
dedupe([3, 1, 2, 1, 3])             # [3, 1, 2]
dedupe(["b", "a", "b", "c", "a"])   # ["b", "a", "c"]
dedupe([1, "1"])                    # [1, "1"]     (int and str differ)
dedupe("abc")                       # TypeError    (not a list)
dedupe([[1], [1]])                  # TypeError    (unhashable elements)
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
