from numbers import Real

# (upper_bound, rate) — the last row's upper is float('inf').
_BRACKETS = [
    (10000, 0.10),
    (40000, 0.12),
    (85000, 0.22),
    (165000, 0.24),
    (float("inf"), 0.32),
]


def calc_tax(income):
    if isinstance(income, bool) or not isinstance(income, Real):
        raise TypeError("income must be a real number")
    if income < 0:
        raise ValueError("income must be non-negative")
    total = 0.0
    prev = 0.0
    for upper, rate in _BRACKETS:
        if income <= upper:
            total += (income - prev) * rate
            return total
        total += (upper - prev) * rate
        prev = upper
    return total
