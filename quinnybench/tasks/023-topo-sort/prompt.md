Implement `topo_sort(deps)` — a **deterministic** topological sort.

## Rules

- `deps` is a `dict` mapping a node to a list of the nodes it **depends on**. E.g. `{"a": ["b"]}` means `a` depends on `b`, so `b` must come before `a` in the output.
- Return a `list` of nodes in dependency order (dependencies first).
- A node that only appears as a **dependency** (not as a key) is treated as having no deps of its own.
- **Deterministic tie-break**: when multiple nodes are ready (all deps resolved), pick them in alphabetical order. Use a min-heap of ready nodes.
- A cycle (including a self-loop like `{"a": ["a"]}`) → `ValueError`.
- Non-dict input → `TypeError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `topo_sort(deps)`.
- Return type: `list`. Stdlib only (`heapq` is fine).

## Reference cases

```python
topo_sort({})                                          # []
topo_sort({"a": []})                                   # ["a"]
topo_sort({"a": ["b"], "b": []})                       # ["b", "a"]
topo_sort({"a": ["b"], "b": ["c"], "c": []})           # ["c", "b", "a"]

# Diamond — a → b → d, a → c → d. Alphabetical tie-break:
topo_sort({"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []})
# ["d", "b", "c", "a"]

# Implicit leaf: b is not a key, treated as no-deps.
topo_sort({"a": ["b"]})                                # ["b", "a"]

topo_sort({"b": [], "a": []})                          # ["a", "b"]   (alphabetical)

topo_sort({"a": ["b"], "b": ["a"]})                    # ValueError   (cycle)
topo_sort({"a": ["a"]})                                # ValueError   (self-loop)
topo_sort([("a", [])])                                 # TypeError    (not a dict)
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
