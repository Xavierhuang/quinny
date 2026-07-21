def _left(opt):
    """Render the left column: '  -x, --long VALUE' with short-slot padding."""
    short = opt.get("short")
    long = opt["long"]
    value = opt.get("value")
    prefix = f"  -{short}, " if short else "      "   # 4-char pad where "-x, " would go
    core = f"--{long}"
    if value:
        core = f"{core} {value}"
    return prefix + core


def render_help(program, options):
    if not isinstance(program, str):
        raise TypeError("program must be a string")
    if not isinstance(options, list):
        raise TypeError("options must be a list")
    lines = [f"Usage: {program} [OPTIONS]", "", "Options:"]
    if not options:
        return "\n".join(lines) + "\n"
    left_cols = [_left(o) for o in options]
    width = max(len(s) for s in left_cols)
    for l, o in zip(left_cols, options):
        lines.append(f"{l.ljust(width)}  {o['help']}")
    return "\n".join(lines) + "\n"
