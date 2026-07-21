def flatten_dict(source, sep="."):
    if not isinstance(source, dict):
        raise TypeError("source must be a dict")
    out = {}
    _walk(source, "", sep, out)
    return out


def _walk(node, prefix, sep, out):
    for k, v in node.items():
        key = f"{prefix}{sep}{k}" if prefix else str(k)
        if isinstance(v, dict):
            _walk(v, key, sep, out)
        else:
            out[key] = v
