from numbers import Real


class TokenBucket:
    def __init__(self, capacity, refill_per_sec):
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be an int")
        if isinstance(refill_per_sec, bool) or not isinstance(refill_per_sec, Real):
            raise TypeError("refill_per_sec must be numeric")
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if refill_per_sec < 0:
            raise ValueError("refill_per_sec must be >= 0")
        self._cap = capacity
        self._rate = float(refill_per_sec)
        self._tokens = float(capacity)
        self._last = None   # set on first try_take

    @property
    def tokens(self):
        # int for exact-comparison assertions in the suite.
        return int(self._tokens)

    def try_take(self, now, n=1):
        if self._last is None:
            self._last = now
        else:
            elapsed = max(0.0, now - self._last)
            self._tokens = min(float(self._cap), self._tokens + elapsed * self._rate)
            self._last = now
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False
