Implement `is_valid_iban(s)` — validate an [IBAN](https://en.wikipedia.org/wiki/International_Bank_Account_Number) using the standard mod-97 check.

## Rules

Return `True` iff `s` is a `str` that:

1. Is between **15 and 34 characters** long.
2. Contains **only uppercase A–Z and digits 0–9** (no spaces, no lowercase, no punctuation).
3. Passes the mod-97 checksum:
   - Move the first 4 characters to the end.
   - Replace letters with numbers: `A=10, B=11, …, Z=35`.
   - Convert the resulting all-digit string to an integer.
   - Valid iff `n % 97 == 1`.

Non-string input → `TypeError`. Otherwise return `bool`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `is_valid_iban(s)`.
- Return type: `bool`. Stdlib only.

## Reference cases

| input                                    | result |
|------------------------------------------|--------|
| `"GB82WEST12345698765432"`               | True   |
| `"DE89370400440532013000"`               | True   |
| any of the above with one wrong digit    | False  |
| `"GB82WEST123456"` (14 chars)            | False  |
| a string of 35 chars                     | False  |
| `"gb82west12345698765432"` (lowercase)   | False  |
| `"GB82 WEST 1234 5698 7654 32"` (spaces) | False  |
| `""`                                     | False  |
| `12345678901234` (int)                   | TypeError |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
