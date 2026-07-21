from collections import deque


def window_max(nums, k):
    if not isinstance(nums, list):
        raise TypeError("nums must be a list")
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("k must be an int")
    n = len(nums)
    if k < 1 or k > n:
        raise ValueError("k must satisfy 1 <= k <= len(nums)")

    out = []
    # Monotonic deque of indices: front is always index of window's max.
    dq = deque()
    for i, x in enumerate(nums):
        while dq and dq[0] <= i - k:
            dq.popleft()
        while dq and nums[dq[-1]] <= x:
            dq.pop()
        dq.append(i)
        if i >= k - 1:
            out.append(nums[dq[0]])
    return out
