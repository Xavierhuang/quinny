Implement `render_help(program, options)` — render a `--help` style block for a CLI, with aligned option columns.

## Option spec

Each option is a dict:
```python
{"short": str | None, "long": str, "value": str | None, "help": str}
```

## Format

```
Usage: <program> [OPTIONS]
                           ← blank line
Options:
  -x, --long VALUE  help text
      --long-only VALUE  help text
```

- Left column starts with 2 spaces, then either `-x, ` (6 chars total) when `short` is set, or 4 blanks (also 6 chars total: the `-x, ` slot padded).
- Followed by `--<long>` and, if `value` is set, `<space><VALUE>`.
- The gutter between left column and `help` is `"  "` (exactly two spaces), applied after **padding every left column to the widest one**. So all help texts align in one vertical column.
- Trailing newline after each rendered line, including the last.

## Empty case

If `options` is `[]`, still emit:
```
Usage: <program> [OPTIONS]

Options:
```
(with a trailing newline after `Options:`.)

## Errors

- Non-string `program` → `TypeError`.
- Non-list `options` → `TypeError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `render_help(program, options)`.
- Return type: `str`. Stdlib only.

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
