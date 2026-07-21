import datetime as dt


def _is_date(x):
    return isinstance(x, dt.date) and not isinstance(x, dt.datetime)


def weekend_count(start, end):
    if not _is_date(start):
        raise TypeError("start must be a datetime.date")
    if not _is_date(end):
        raise TypeError("end must be a datetime.date")
    if end < start:
        raise ValueError("end must be >= start")
    total_days = (end - start).days + 1
    full_weeks, leftover = divmod(total_days, 7)
    count = full_weeks * 2
    # Iterate leftover days from start.weekday()
    for i in range(leftover):
        wd = (start.weekday() + full_weeks * 7 + i) % 7
        if wd >= 5:
            count += 1
    return count
