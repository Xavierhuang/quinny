Implement a Python class `LRUCache` — a fixed-capacity, least-recently-used cache.

## API

- `LRUCache(capacity)` — constructor. `capacity` must be a positive `int` (booleans do **not** count as ints). Non-int → `TypeError`. Zero or negative → `ValueError`.
- `.size() -> int` — number of entries currently stored.
- `.get(key)` — return the stored value. Missing key → `KeyError`. **`get` renews recency** (accessing a key makes it the most-recently used).
- `.put(key, value)` — insert or update:
  - If `key` is already present: replace the value, renew recency, size does not grow.
  - If `key` is new and the cache is full (`size() == capacity`): evict the **least-recently-used** entry, then insert.
  - If `key` is new and the cache has room: just insert.

## Interface

- File: `impl.py`.
- Export exactly one public class: `LRUCache`.
- Stdlib only. `collections.OrderedDict` is the obvious choice.

## Reference cases

```python
c = LRUCache(3)
c.size()              # 0
c.put("a", 1)
c.get("a")            # 1
c.get("nope")         # KeyError

c = LRUCache(2)
c.put("a", 1)
c.put("b", 2)
c.put("c", 3)         # evicts "a"
c.get("a")            # KeyError
c.get("b")            # 2

c = LRUCache(2)
c.put("a", 1)
c.put("b", 2)
c.get("a")            # renew "a"
c.put("c", 3)         # evicts "b", not "a"
c.get("a")            # 1
c.get("b")            # KeyError

LRUCache(0)           # ValueError
LRUCache(-1)          # ValueError
LRUCache(1.5)         # TypeError
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
