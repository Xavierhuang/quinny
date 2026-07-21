Implement `validate_password(password)` — a policy checker that returns the list of rule ids the password **fails**, in a fixed order. Empty list means the password satisfies every rule.

## Rules (in the required order)

1. `"min_length"` — at least 8 characters.
2. `"has_upper"` — at least one A–Z character.
3. `"has_lower"` — at least one a–z character.
4. `"has_digit"` — at least one 0–9 character.
5. `"has_special"` — at least one character from the set `!@#$%^&*()-_+=`.

The result **must preserve this order**: e.g. if a password fails `min_length` and `has_digit`, return `["min_length", "has_digit"]`, not the reverse.

## Errors

- Non-string input → `TypeError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `validate_password(password)`.
- Return type: `list[str]`. Stdlib only.

## Reference cases

| password         | result                                                        |
|------------------|---------------------------------------------------------------|
| `"Str0ng!Pass"`  | `[]`                                                          |
| `""`             | `["min_length","has_upper","has_lower","has_digit","has_special"]` |
| `"Ab1!Cd"`       | `["min_length"]`                                              |
| `"password1!"`   | `["has_upper"]`                                               |
| `"PASSWORD1!"`   | `["has_lower"]`                                               |
| `"Password!"`    | `["has_digit"]`                                               |
| `"Password1"`    | `["has_special"]`                                             |
| `"weak"`         | `["min_length","has_upper","has_digit","has_special"]`        |
| `12345678` (int) | `TypeError`                                                   |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
