Implement a Python function `is_valid_luhn(card_number)` that returns `True` when the given card-number string passes the Luhn checksum, and `False` otherwise.

## Rules

- Input is a **string**. Non-string inputs (int, None, list, etc.) must raise `TypeError`.
- **Ignore** spaces and hyphens inside the string before validating (`"4111 1111 1111 1111"` and `"4111-1111-1111-1111"` are treated as `"4111111111111111"`).
- After stripping, if the string is **empty**, **shorter than 2 characters**, or contains **any non-digit character**, return `False`.
- Otherwise apply the standard Luhn algorithm and return `True` iff the checksum is 0 mod 10.

## Standard Luhn algorithm

1. Starting from the **rightmost** digit, walk left.
2. Double every **second** digit (the one immediately left of the rightmost, then two-left, etc.).
3. If a doubled digit is > 9, subtract 9 (equivalent to summing its own digits).
4. Sum all the digits.
5. Number is valid iff `sum % 10 == 0`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `is_valid_luhn(card_number)`.
- No CLI, no side effects, stdlib only.

## Reference cases

| card_number                | result |
|----------------------------|--------|
| `"4532015112830366"`       | True   |
| `"4532015112830367"`       | False  |
| `"79927398713"`            | True   |
| `"4111 1111 1111 1111"`    | True   |
| `"4111-1111-1111-1111"`    | True   |
| `""`                       | False  |
| `"abcd"`                   | False  |
| `"5"`                      | False  |
| `4532015112830366` (int)   | TypeError |
| `None`                     | TypeError |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
