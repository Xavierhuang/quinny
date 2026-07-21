def group_by(rows, key):
    if not isinstance(rows, list):
        raise TypeError("rows must be a list")
    if not isinstance(key, str):
        raise TypeError("key must be a string")
    out = {}
    for row in rows:
        v = row[key]   # KeyError propagates naturally
        out.setdefault(v, []).append(row)
    return out
