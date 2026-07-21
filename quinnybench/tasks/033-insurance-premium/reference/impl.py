_BASE = {"basic": 100.0, "standard": 250.0, "premium": 500.0}


def _factor(age):
    if age < 25:  return 1.5
    if age <= 40: return 1.0
    if age <= 60: return 1.3
    return 1.8


def calc_premium(age, tier):
    if isinstance(age, bool) or not isinstance(age, int):
        raise TypeError("age must be an int")
    if age < 0:
        raise ValueError("age must be non-negative")
    if tier not in _BASE:
        raise ValueError(f"unknown tier: {tier!r}")
    return _BASE[tier] * _factor(age)
