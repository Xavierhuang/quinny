import datetime as dt


def iso_week(d):
    if not isinstance(d, dt.date) or isinstance(d, dt.datetime):
        raise TypeError("d must be a datetime.date (not datetime)")
    iso = d.isocalendar()
    # date.isocalendar() returns a named tuple in modern Python; unpack safely.
    return (int(iso[0]), int(iso[1]), int(iso[2]))
