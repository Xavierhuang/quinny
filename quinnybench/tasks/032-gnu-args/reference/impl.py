def parse_gnu_args(argv, value_options):
    if not isinstance(argv, list):
        raise TypeError("argv must be a list")
    if not isinstance(value_options, set):
        raise TypeError("value_options must be a set")

    flags = set()
    options = {}
    positional = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--":
            positional.extend(argv[i + 1:])
            break
        if tok.startswith("--"):
            body = tok[2:]
            if "=" in body:
                k, _, v = body.partition("=")
                options[k] = v
                i += 1
                continue
            name = body
            if name in value_options:
                if i + 1 >= len(argv):
                    raise ValueError(f"--{name} requires a value")
                options[name] = argv[i + 1]
                i += 2
            else:
                flags.add(name)
                i += 1
        elif tok.startswith("-") and len(tok) > 1:
            name = tok[1:]
            if name in value_options:
                if i + 1 >= len(argv):
                    raise ValueError(f"-{name} requires a value")
                options[name] = argv[i + 1]
                i += 2
            else:
                flags.add(name)
                i += 1
        else:
            positional.append(tok)
            i += 1
    return {"flags": flags, "options": options, "positional": positional}
