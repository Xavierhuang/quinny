def parse_ini(text):
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    result = {}
    current = None   # section name; None until first section or first kv without section
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith((";", "#")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            result.setdefault(current, {})
            continue
        if "=" not in line:
            raise ValueError(f"expected key=value or [section], got: {raw!r}")
        key, _, value = line.partition("=")
        section = current if current is not None else ""
        result.setdefault(section, {})[key.strip()] = value.strip()
    return result
