def get_config(argv, env, defaults):
    if not isinstance(argv, list):
        raise TypeError("argv must be a list")
    if not isinstance(env, dict):
        raise TypeError("env must be a dict")
    if not isinstance(defaults, dict):
        raise TypeError("defaults must be a dict")

    # Parse argv into --key=value options; later value wins.
    argv_opts = {}
    for tok in argv:
        if isinstance(tok, str) and tok.startswith("--") and "=" in tok:
            k, _, v = tok[2:].partition("=")
            argv_opts[k] = v

    out = {}
    for key, default in defaults.items():
        if key in argv_opts:
            out[key] = argv_opts[key]
            continue
        env_name = key.upper().replace("-", "_")
        if env_name in env:
            out[key] = env[env_name]
            continue
        out[key] = default
    return out
