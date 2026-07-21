Implement `parse_ini(text)` — parse an INI-format string into a nested dict `{section: {key: value}}`.

## Rules

- `text` must be a `str`. Other types → `TypeError`.
- Lines are separated by `\n`.
- A section header is `[section_name]` (whole line, after stripping whitespace).
- A key/value line is `key = value`. Whitespace around key and value is stripped.
- Comment lines start with `;` or `#`. Ignored.
- Blank lines (after stripping) are ignored.
- Duplicate keys within the same section: later value wins.
- Keys before any section header belong to section `""` (empty-string key in the top-level dict).
- A non-blank, non-comment, non-header line without an `=` → `ValueError`.
- All values are `str` — no type coercion.

## Interface

- File: `impl.py`.
- Export exactly one public function: `parse_ini(text)`.
- Return type: `dict[str, dict[str, str]]`. Stdlib only.

## Reference cases

```python
parse_ini("")                              # {}
parse_ini("[a]\nk=v")                      # {"a": {"k": "v"}}
parse_ini("[a]\nk=v\nl=w\n[b]\nm=x")       # {"a": {"k":"v","l":"w"}, "b": {"m":"x"}}
parse_ini("[a]\n  k  =  v  ")              # {"a": {"k": "v"}}
parse_ini("; comment\n[a]\nk=v")           # {"a": {"k": "v"}}
parse_ini("# comment\n[a]\nk=v")           # {"a": {"k": "v"}}
parse_ini("\n\n[a]\n\nk=v\n\n")            # {"a": {"k": "v"}}
parse_ini("[a]\nk=v1\nk=v2")               # {"a": {"k": "v2"}}
parse_ini("k=v\n[a]\nl=w")                 # {"": {"k": "v"}, "a": {"l": "w"}}
parse_ini("[a]\nno_equals_here")           # ValueError
parse_ini(None)                            # TypeError
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
