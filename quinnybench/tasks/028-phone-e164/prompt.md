Implement `is_valid_e164(s)` — validate a phone number against the [E.164](https://en.wikipedia.org/wiki/E.164) format.

## Rules

Return `True` iff `s` is a string of the form `+D…` where:
- Starts with a `+`.
- Followed by **1 to 15** digits.
- The **first digit after the `+` must not be `0`** (leading-zero country codes are invalid).
- No other characters (no spaces, hyphens, parens, etc.).

Non-string input → `TypeError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `is_valid_e164(s)`.
- Return type: `bool`. Stdlib only.

## Reference cases

| input                 | result       |
|-----------------------|--------------|
| `"+15551234567"`      | True         |
| `"+441234567890"`     | True         |
| `"+123456789012345"`  | True (15 digits — max)  |
| `"+1234567890123456"` | False (16 digits — too many) |
| `"15551234567"`       | False (no `+`) |
| `"+"`                 | False        |
| `""`                  | False        |
| `"+0123456789"`       | False (leading zero) |
| `"+15551abc567"`      | False (non-digits) |
| `15551234567` (int)   | TypeError    |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
