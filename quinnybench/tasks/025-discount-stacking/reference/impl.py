from numbers import Real


def _savings(d, base):
    if d["type"] == "percent":
        return base * d["value"] / 100.0
    if d["type"] == "flat":
        return d["value"]
    raise ValueError(f"unknown discount type: {d['type']!r}")


def _apply(d, base):
    if d["type"] == "percent":
        return base * (1 - d["value"] / 100.0)
    if d["type"] == "flat":
        return base - d["value"]
    raise ValueError(f"unknown discount type: {d['type']!r}")


def apply_discounts(subtotal, discounts):
    if isinstance(subtotal, bool) or not isinstance(subtotal, Real):
        raise TypeError("subtotal must be numeric")
    if subtotal < 0:
        raise ValueError("subtotal must be non-negative")
    if not isinstance(discounts, list):
        raise TypeError("discounts must be a list")

    non_stack = [d for d in discounts if not d["stackable"]]
    stack     = [d for d in discounts if d["stackable"]]

    total = float(subtotal)
    # Validate types early so unknown-type errors surface even if that discount
    # would ultimately be skipped by the non-stackable selection.
    for d in discounts:
        _savings(d, total)

    if non_stack:
        best = max(non_stack, key=lambda d: _savings(d, total))
        total = _apply(best, total)
    for d in stack:
        total = _apply(d, total)
    return max(0.0, total)
