from urllib.parse import unquote_plus


def parse_query_string(qs):
    if not isinstance(qs, str):
        raise TypeError("qs must be a string")
    if qs == "":
        return {}
    out = {}
    for pair in qs.split("&"):
        k, sep, v = pair.partition("=")
        key = unquote_plus(k)
        val = unquote_plus(v) if sep else ""
        out.setdefault(key, []).append(val)
    return out
