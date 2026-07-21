def merge_intervals(intervals):
    if not isinstance(intervals, list):
        raise TypeError("intervals must be a list")
    for iv in intervals:
        if not (isinstance(iv, list) and len(iv) == 2):
            raise ValueError(f"each interval must be a two-element list, got {iv!r}")
        if iv[0] > iv[1]:
            raise ValueError(f"start must be <= end, got {iv!r}")
    out = []
    for start, end in sorted(intervals, key=lambda p: p[0]):
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out
