Implement `parse_subcommand(argv)` — a git-style command-line parser that separates the **first non-dash token** as the subcommand and buckets the rest into flags, options, and positional args.

## Grammar

- `--name` (no `=`) → boolean **flag** `name`.
- `--name=value` → **option** `name → value`.
- `-x` → boolean **flag** `x`.
- Bare `--` ends option parsing; everything after is positional, verbatim.
- Any other token is a **candidate positional**. The **first** candidate positional (before `--`) becomes the `subcommand`; every subsequent candidate positional joins the `positional` list.

## Return

```python
{
  "subcommand": str | None,
  "flags":      set[str],
  "options":    dict[str, str],
  "positional": list[str],
}
```

If no candidate positional appears before `--`, `subcommand` is `None`.

## Errors

- `argv` must be a `list`. Any other type → `TypeError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `parse_subcommand(argv)`.
- Stdlib only.

## Reference cases

```python
parse_subcommand([])
# {subcommand: None, flags: set(), options: {}, positional: []}

parse_subcommand(["deploy"])
# {subcommand: "deploy", ...}

parse_subcommand(["deploy", "prod"])
# {subcommand: "deploy", positional: ["prod"]}

parse_subcommand(["--verbose", "deploy"])
# {subcommand: "deploy", flags: {"verbose"}}

parse_subcommand(["deploy", "--verbose"])
# {subcommand: "deploy", flags: {"verbose"}}

parse_subcommand(["deploy", "--target=prod"])
# {subcommand: "deploy", options: {"target": "prod"}}

parse_subcommand(["--", "deploy", "--verbose"])
# {subcommand: None, positional: ["deploy", "--verbose"]}

parse_subcommand(["deploy", "prod", "us-east-1"])
# {subcommand: "deploy", positional: ["prod", "us-east-1"]}

parse_subcommand("deploy")          # TypeError (not a list)
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
