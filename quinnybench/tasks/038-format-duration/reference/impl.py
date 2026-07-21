def format_duration(seconds):
    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise TypeError("seconds must be an int")
    if seconds < 0:
        raise ValueError("seconds must be non-negative")
    if seconds == 0:
        return "0s"
    parts = []
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        q, seconds = divmod(seconds, size)
        if q:
            parts.append(f"{q}{unit}")
    return " ".join(parts)
