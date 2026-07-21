Implement `parse_args(argv)` — a minimal command-line argument parser that splits a token list into flags, options, and positional args.

## Grammar

- `--name` (a token that starts with `--` and has no `=`) → boolean **flag** named `name`.
- `--name=value` (a `--` token containing `=`) → **option** `name → value` (value is the substring after the first `=`).
- `-x` (single dash + one or more chars, no `=`) → boolean **flag** named `x` (the char(s) after the dash).
- A bare `--` token (exactly two dashes, nothing after) ends option parsing; **everything after it** is treated as positional, verbatim (including tokens that start with `-`).
- Anything else is a **positional** argument, kept in order.

If a later `--name=v2` follows an earlier `--name=v1`, the later value wins.

## Return

```python
{"flags": set[str], "options": dict[str, str], "positional": list[str]}
```

## Errors

- `argv` must be a `list`. Any other type (`str`, tuple, None, …) raises `TypeError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `parse_args(argv)`.
- Stdlib only.

## Reference cases

```python
parse_args([])
# {"flags": set(), "options": {}, "positional": []}

parse_args(["src.py"])
# {"flags": set(), "options": {}, "positional": ["src.py"]}

parse_args(["--verbose"])
# {"flags": {"verbose"}, "options": {}, "positional": []}

parse_args(["-v"])
# {"flags": {"v"}, "options": {}, "positional": []}

parse_args(["--count=3"])
# {"flags": set(), "options": {"count": "3"}, "positional": []}

parse_args(["--count=3", "--verbose", "-o", "src.py"])
# {"flags": {"verbose", "o"}, "options": {"count": "3"}, "positional": ["src.py"]}

parse_args(["--", "-v", "--verbose"])
# {"flags": set(), "options": {}, "positional": ["-v", "--verbose"]}

parse_args(["file.py", "--", "-v"])
# {"flags": set(), "options": {}, "positional": ["file.py", "-v"]}

parse_args(["--k=v1", "--k=v2"])
# {"flags": set(), "options": {"k": "v2"}, "positional": []}

parse_args("--verbose")     # TypeError (string, not list)
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
