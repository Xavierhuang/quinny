from numbers import Real


def charge(amount, day_of_month, days_in_month):
    if isinstance(amount, bool) or not isinstance(amount, Real):
        raise TypeError("amount must be numeric")
    if isinstance(day_of_month, bool) or not isinstance(day_of_month, int):
        raise TypeError("day_of_month must be int")
    if isinstance(days_in_month, bool) or not isinstance(days_in_month, int):
        raise TypeError("days_in_month must be int")
    if amount < 0:
        raise ValueError("amount must be non-negative")
    if days_in_month not in (28, 29, 30, 31):
        raise ValueError("days_in_month must be 28, 29, 30 or 31")
    if day_of_month < 1 or day_of_month > days_in_month:
        raise ValueError("day_of_month out of range")
    return amount * (days_in_month - day_of_month + 1) / days_in_month
