Implement `parse_csv_row(row)` — parse a single RFC 4180 CSV row into a list of field strings.

## Rules

- Fields are separated by `,`.
- A field may be **quoted** with `"…"`. A quoted field can contain commas (they're part of the field, not separators).
- Inside a quoted field, a doubled `""` decodes to a single `"` (RFC 4180 escape).
- A quoted field must **start at the beginning of a field** and be followed immediately by `,` or end-of-row. Junk between the closing `"` and the next `,` (e.g. `"a"b`) → `ValueError`.
- Unclosed quote (no matching `"`) → `ValueError`.
- Empty string → single empty field: `[""]`.
- A trailing `,` produces a trailing empty field.
- Non-string input → `TypeError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `parse_csv_row(row)`.
- Return type: `list[str]`. Stdlib only.

## Reference cases

| input               | result              |
|---------------------|---------------------|
| `""`                | `[""]`              |
| `"hello"`           | `["hello"]`         |
| `"a,b,c"`           | `["a", "b", "c"]`   |
| `"a,,c"`            | `["a", "", "c"]`    |
| `"a,b,"`            | `["a", "b", ""]`    |
| `'"a,b",c'`         | `["a,b", "c"]`      |
| `'"say ""hi"""'`    | `['say "hi"']`      |
| `'"unclosed'`       | `ValueError`        |
| `'"a"b'`            | `ValueError`        |
| `123`               | `TypeError`         |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
