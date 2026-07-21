Implement `is_valid_email(s)` — a practical (not full-RFC-5322) email validator.

## Rules

Return `True` iff `s` is a string of the form `<local>@<domain>` where:

**Local part:**
- Non-empty.
- Only characters `A-Z`, `a-z`, `0-9`, `.`, `_`, `%`, `+`, `-`.
- Must NOT start or end with `.`.
- Must NOT contain consecutive `.`.

**Domain:**
- Non-empty.
- Contains at least one `.` (i.e. at least two labels).
- Each **label** (dot-separated component) is 1+ chars from `A-Z`, `a-z`, `0-9`, `-`; the label must NOT start or end with `-`.
- The **TLD** (last label) is at least 2 alphabetic characters (no digits, no hyphens).

Everything else returns `False`. Non-string input → `TypeError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `is_valid_email(s)`.
- Return type: `bool`. Stdlib only.

## Reference cases

| input                    | result       |
|--------------------------|--------------|
| `"a@b.co"`               | True         |
| `"test.user@example.com"`| True         |
| `"foo+bar@example.com"`  | True         |
| `"foo@example.co.uk"`    | True         |
| `".foo@bar.com"`         | False        |
| `"foo.@bar.com"`         | False        |
| `"foo..bar@baz.com"`     | False        |
| `"foo@bar"`              | False        |
| `"foo@-bar.com"`         | False        |
| `"foo@bar-.com"`         | False        |
| `""`                     | False        |
| `"@bar.com"`             | False        |
| `"foo@"`                 | False        |
| `None`                   | TypeError    |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
