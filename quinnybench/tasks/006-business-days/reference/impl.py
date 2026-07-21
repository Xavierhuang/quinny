import datetime as dt


def add_business_days(start_date, n):
    if not isinstance(start_date, dt.date) or isinstance(start_date, dt.datetime):
        # Accept date but not datetime (datetime is a subclass of date); the
        # spec is about calendar dates.
        raise TypeError("start_date must be a datetime.date (not datetime)")
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an int")
    if n == 0:
        return start_date
    step = 1 if n > 0 else -1
    remaining = abs(n)
    cur = start_date
    while remaining > 0:
        cur += dt.timedelta(days=step)
        # Skip weekends: 5=Sat, 6=Sun
        while cur.weekday() >= 5:
            cur += dt.timedelta(days=step)
        remaining -= 1
    return cur
