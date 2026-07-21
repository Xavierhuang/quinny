Implement `group_by(rows, key)` — group a list of dict rows into buckets keyed by the value at a given field.

## Rules

- `rows` must be a `list` (of dicts). Any other type → `TypeError`.
- `key` must be a `str`. Any other type → `TypeError`.
- For each row, look up `row[key]` and append the row to `result[row[key]]`.
- If a row is missing `key` → `KeyError` (propagate the natural dict lookup error).
- **Preserve the input order** within each group.
- Group-key values can be any hashable type (int, str, tuple, …).

## Interface

- File: `impl.py`.
- Export exactly one public function: `group_by(rows, key)`.
- Return type: `dict[Any, list[dict]]`. Stdlib only.

## Reference cases

```python
group_by([], "x")
# {}

group_by([{"x": 1, "y": "a"}], "x")
# {1: [{"x": 1, "y": "a"}]}

group_by([{"x": 1, "y": "a"}, {"x": 1, "y": "b"}], "x")
# {1: [{"x": 1, "y": "a"}, {"x": 1, "y": "b"}]}

group_by([{"x": 1, "y": "a"}, {"x": 2, "y": "b"}, {"x": 1, "y": "c"}], "x")
# {1: [{"x": 1, "y": "a"}, {"x": 1, "y": "c"}], 2: [{"x": 2, "y": "b"}]}

group_by([{"x": 1}, {"y": 2}], "x")     # KeyError
group_by({"x": 1}, "x")                 # TypeError (rows not a list)
group_by([{"x": 1}], 123)               # TypeError (key not a string)
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
