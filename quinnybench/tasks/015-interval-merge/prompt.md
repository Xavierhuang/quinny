Implement `merge_intervals(intervals)` — merge overlapping and touching intervals into a sorted list of disjoint intervals.

## Rules

- `intervals` must be a `list` of `[start, end]` pairs (each a two-element `list`).
  - Non-list top level → `TypeError`.
  - Non-list or non-two-length inner → `ValueError`.
  - `start > end` → `ValueError`.
- Return a `list` of merged `[start, end]` pairs, **sorted by `start` ascending**.
- Overlapping intervals merge (e.g. `[1,4]` and `[2,5]` → `[1,5]`).
- **Touching** intervals (sharing an endpoint) also merge (`[1,4]` and `[4,5]` → `[1,5]`).
- Input may be unsorted; sort before merging.

## Interface

- File: `impl.py`.
- Export exactly one public function: `merge_intervals(intervals)`.
- Return type: `list[list[int|float]]`. Stdlib only.

## Reference cases

```python
merge_intervals([])                                      # []
merge_intervals([[1, 3]])                                # [[1, 3]]
merge_intervals([[1, 4], [2, 5]])                        # [[1, 5]]
merge_intervals([[1, 4], [4, 5]])                        # [[1, 5]]   (touching)
merge_intervals([[1, 3], [5, 8]])                        # [[1, 3], [5, 8]]
merge_intervals([[5, 10], [1, 3]])                       # [[1, 3], [5, 10]]  (sorted)
merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]])     # [[1, 6], [8, 10], [15, 18]]

merge_intervals("nope")           # TypeError
merge_intervals([[5, 3]])         # ValueError
merge_intervals([[1, 2, 3]])      # ValueError
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
