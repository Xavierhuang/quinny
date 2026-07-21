def top_k(items, k, key=None):
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("k must be an int")
    if k < 0:
        raise ValueError("k must be non-negative")
    if k == 0:
        return []
    keyfn = key if key is not None else (lambda x: x)
    # Sort by (-key, index) so descending key, ties break on original order.
    # Python's sort is stable; sorting by negated key alone already respects
    # original order on ties, but explicit index keeps it robust for non-numeric
    # keys where negation isn't defined.
    indexed = list(enumerate(items))
    indexed.sort(key=lambda p: (_neg(keyfn(p[1])), p[0]))
    return [x for _, x in indexed[:k]]


class _Negatable:
    """Wrapper enabling __lt__ on any orderable value by inverting comparison."""
    __slots__ = ("v",)
    def __init__(self, v): self.v = v
    def __lt__(self, other): return other.v < self.v


def _neg(v):
    return _Negatable(v)
