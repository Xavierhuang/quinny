"""Correct: pick best single code, reject unknown."""

_CODES = {"SAVE10": 0.10, "SAVE20": 0.20, "SAVE5": 0.05}


def apply_codes(total: float, codes: list[str]) -> float:
    if not codes:
        return total
    best = 0.0
    for c in codes:
        if c not in _CODES:
            raise ValueError(f"unknown code: {c}")
        if _CODES[c] > best:
            best = _CODES[c]
    return total * (1 - best)
