def dedupe(items):
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    seen = set()
    out = []
    for x in items:
        # hash() raises TypeError on unhashable; propagate that.
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out
