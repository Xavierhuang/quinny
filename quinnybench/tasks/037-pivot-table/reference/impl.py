_AGG_FNS = {
    "sum":   lambda a, v: v if a is None else a + v,
    "count": lambda a, v: 1 if a is None else a + 1,
    "max":   lambda a, v: v if a is None else max(a, v),
    "min":   lambda a, v: v if a is None else min(a, v),
}


def pivot(rows, row_key, col_key, value_key, agg="sum"):
    if not isinstance(rows, list):
        raise TypeError("rows must be a list")
    if agg not in _AGG_FNS:
        raise ValueError(f"unknown agg: {agg!r}")
    fn = _AGG_FNS[agg]
    out = {}
    for r in rows:
        rk = r[row_key]      # KeyError propagates
        ck = r[col_key]
        v = r[value_key]
        out.setdefault(rk, {})
        prev = out[rk].get(ck)
        out[rk][ck] = fn(prev, v)
    return out
