Implement `flatten_dict(source, sep=".")` that flattens a nested Python `dict` into a flat dict of dotted-path keys.

## Rules

- `source` must be a `dict`. Any other input (list, str, None, …) raises `TypeError`.
- Nested dicts recurse. Non-dict values (int, str, list, tuple, custom objects) are kept **as-is**; lists are NOT recursed into.
- An empty **inner** dict contributes no keys — it disappears from the output.
- Keys that themselves contain the separator are left verbatim (no attempt to disambiguate).
- `sep` may be any single- or multi-character string.

## Interface

- File: `impl.py`.
- Export exactly one public function: `flatten_dict(source, sep=".")`.
- Stdlib only.

## Reference cases

| input                                       | sep | output                              |
|---------------------------------------------|-----|-------------------------------------|
| `{}`                                        | `.` | `{}`                                |
| `{"a": 1}`                                  | `.` | `{"a": 1}`                          |
| `{"a": {"b": 1}}`                           | `.` | `{"a.b": 1}`                        |
| `{"a": {"b": {"c": 1}}}`                    | `.` | `{"a.b.c": 1}`                      |
| `{"a": [1, 2, 3]}`                          | `.` | `{"a": [1, 2, 3]}`                  |
| `{"a.b": 1}`                                | `.` | `{"a.b": 1}`                        |
| `{"a": {}}`                                 | `.` | `{}`                                |
| `{"a": {"b": 1}}`                           | `/` | `{"a/b": 1}`                        |
| `"not a dict"`                              | —   | `TypeError`                         |
| `None`                                      | —   | `TypeError`                         |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
