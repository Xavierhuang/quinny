def parse_subcommand(argv):
    if not isinstance(argv, list):
        raise TypeError("argv must be a list of strings")
    subcommand = None
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
            else:
                flags.add(body)
        elif tok.startswith("-") and len(tok) > 1:
            flags.add(tok[1:])
        else:
            if subcommand is None:
                subcommand = tok
            else:
                positional.append(tok)
        i += 1
    return {"subcommand": subcommand, "flags": flags,
            "options": options, "positional": positional}
