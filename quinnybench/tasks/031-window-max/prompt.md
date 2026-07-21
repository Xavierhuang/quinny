Implement `window_max(nums, k)` — return a list containing the maximum of every contiguous window of size `k` in `nums`.

## Rules

- Output length is `len(nums) - k + 1`.
- `nums` must be a `list`. Non-list → `TypeError`.
- `k` must be an `int` (booleans excluded). Non-int → `TypeError`.
- `k` must satisfy `1 <= k <= len(nums)`. Otherwise → `ValueError` (empty `nums` with any `k` → `ValueError`).

An O(n) implementation using a monotonic deque is preferred, but any correct implementation passes.

## Interface

- File: `impl.py`.
- Export exactly one public function: `window_max(nums, k)`.
- Return type: `list`. Stdlib only (`collections.deque` is fine).

## Reference cases

```python
window_max([1, 3, -1, -3, 5, 3, 6, 7], 3)   # [3, 3, 5, 5, 6, 7]
window_max([1, 2, 3, 4], 1)                 # [1, 2, 3, 4]
window_max([1, 5, 3, 2], 4)                 # [5]
window_max([42], 1)                          # [42]
window_max([7, 7, 7, 7], 2)                  # [7, 7, 7]
window_max([1, 2, 3], 0)                     # ValueError
window_max([1, 2, 3], 4)                     # ValueError
window_max([], 1)                            # ValueError
window_max("abc", 1)                         # TypeError
window_max([1, 2, 3], 1.0)                   # TypeError
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
