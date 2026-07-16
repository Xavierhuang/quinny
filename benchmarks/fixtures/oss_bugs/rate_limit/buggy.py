"""Buggy: `<=` instead of `<`, and shared bucket across keys.
Two real bug classes in one — matches the "quick rate limit" seen in
many hackathon projects and one memorable pre-Redis Django middleware."""


class Limiter:
    def __init__(self, limit: int, window: float):
        self.limit = limit
        self.window = window
        self._start = None
        self._count = 0

    def allow(self, key: str = "_", now: float | None = None) -> bool:
        import time
        t = time.monotonic() if now is None else now
        if self._start is None or t - self._start >= self.window:
            self._start, self._count = t, 0
        if self._count > self.limit:      # off-by-one: allows N+1
            return False
        self._count += 1
        return True                        # also ignores `key`
