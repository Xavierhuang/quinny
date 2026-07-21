Implement `parse_gnu_args(argv, value_options)` — a GNU-style CLI parser that knows which options TAKE VALUES.

## Grammar

- `argv`: list of string tokens.
- `value_options`: **set** of option names (short OR long, no leading dashes) that expect a value.

Token handling:
- `--name=VALUE` → option `name → VALUE`, always (regardless of `value_options`).
- `--name` where `name` **is in** `value_options` → consume the **next token** as the value: option `name → argv[i+1]`. Missing next token → `ValueError`.
- `--name` where `name` **is not in** `value_options` → boolean flag `name`.
- `-x` where `x` **is in** `value_options` → consume next token: option `x → argv[i+1]`. Missing → `ValueError`.
- `-x` where `x` **is not in** `value_options` → boolean flag `x`.
- Bare `--` (two dashes, nothing after) ends option parsing; everything after is positional, verbatim.
- Anything else is a positional argument.

## Errors

- Non-list `argv` → `TypeError`.
- Non-set `value_options` → `TypeError` (a list is NOT accepted — must be a real `set`).
- Value option with no following token → `ValueError`.

## Return

```python
{"flags": set[str], "options": dict[str, str], "positional": list[str]}
```

## Interface

- File: `impl.py`.
- Export exactly one public function: `parse_gnu_args(argv, value_options)`.
- Stdlib only.

## Reference cases

```python
parse_gnu_args([], set())
# {flags: set(), options: {}, positional: []}

parse_gnu_args(["--verbose"], set())
# {flags: {"verbose"}, ...}

parse_gnu_args(["--count=3"], set())
# {options: {"count": "3"}, ...}

parse_gnu_args(["--count", "3"], {"count"})
# {options: {"count": "3"}, ...}

parse_gnu_args(["-v"], set())
# {flags: {"v"}, ...}

parse_gnu_args(["-o", "out.txt"], {"o"})
# {options: {"o": "out.txt"}, ...}

parse_gnu_args(["src.py"], set())
# {positional: ["src.py"], ...}

parse_gnu_args(["--", "-v", "--verbose"], set())
# {positional: ["-v", "--verbose"], ...}

parse_gnu_args(["--count"], {"count"})    # ValueError (no value)
parse_gnu_args("-v", set())               # TypeError (argv not list)
parse_gnu_args([], ["count"])             # TypeError (value_options must be a set)
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
