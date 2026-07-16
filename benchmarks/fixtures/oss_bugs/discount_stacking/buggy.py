"""Buggy: multiplies discounts (real coupon-stacking exploit shape)."""

_CODES = {"SAVE10": 0.10, "SAVE20": 0.20, "SAVE5": 0.05}


def apply_codes(total: float, codes: list[str]) -> float:
    if not codes:
        return total
    for c in codes:
        if c not in _CODES:
            raise ValueError(f"unknown code: {c}")
        total = total * (1 - _CODES[c])   # stacks — this is the bug
    return total
