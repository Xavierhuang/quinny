import datetime as dt


def _is_date(x):
    return isinstance(x, dt.date) and not isinstance(x, dt.datetime)


def age_as_of(dob, as_of):
    if not _is_date(dob):
        raise TypeError("dob must be a datetime.date (not datetime)")
    if not _is_date(as_of):
        raise TypeError("as_of must be a datetime.date (not datetime)")
    if dob > as_of:
        raise ValueError("dob is after as_of")
    # Use strict tuple comparison — for Feb 29 dob, this makes the birthday
    # "occur" on Mar 1 in non-leap years (since (3,1) > (2,29) but (2,28) is not).
    return as_of.year - dob.year - ((as_of.month, as_of.day) < (dob.month, dob.day))
