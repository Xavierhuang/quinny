def _atom(term):
    """Parse a single comma-separated term into an iterable of minute ints.

    Grammar:  ('*' | N | N-M) ('/' K)?
    """
    step = 1
    if "/" in term:
        term, _, stepstr = term.partition("/")
        step = int(stepstr)
        if step <= 0:
            raise ValueError(f"step must be > 0: {stepstr!r}")
    if term == "*":
        lo, hi = 0, 59
    elif "-" in term:
        a, _, b = term.partition("-")
        lo, hi = int(a), int(b)
        if lo > hi:
            raise ValueError(f"reversed range {term!r}")
    else:
        v = int(term)
        lo, hi = v, v
    if not (0 <= lo <= 59 and 0 <= hi <= 59):
        raise ValueError(f"out of range: {term!r}")
    return range(lo, hi + 1, step)


def parse_cron_minute(field):
    if not isinstance(field, str):
        raise TypeError("field must be a string")
    seen = set()
    for term in field.split(","):
        for v in _atom(term):
            seen.add(v)
    return sorted(seen)
