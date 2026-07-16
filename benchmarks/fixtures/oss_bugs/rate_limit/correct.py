"""Correct: strict `< limit` with per-key window reset."""


class Limiter:
    def __init__(self, limit: int, window: float):
        self.limit = limit
        self.window = window
        self._buckets: dict[str, tuple[float, int]] = {}   # key -> (window_start, count)

    def allow(self, key: str = "_", now: float | None = None) -> bool:
        import time
        t = time.monotonic() if now is None else now
        start, count = self._buckets.get(key, (t, 0))
        if t - start >= self.window:
            start, count = t, 0
        if count >= self.limit:      # strict — the fix
            self._buckets[key] = (start, count)
            return False
        self._buckets[key] = (start, count + 1)
        return True
