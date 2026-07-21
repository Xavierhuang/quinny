Implement `parse_query_string(qs)` — parse an HTTP query string into a `dict` mapping decoded keys to a **list** of decoded values (so repeated keys are preserved).

## Rules

- Empty input → `{}`.
- Pairs are separated by `&`.
- Each pair splits on the first `=`. Key = substring before `=`, value = substring after.
  - A pair with no `=` (e.g. `"a"`) → key `"a"`, value `""`.
  - A pair with a trailing bare `=` (e.g. `"a="`) → key `"a"`, value `""`.
- Repeated keys accumulate in insertion order into a `list` under that key.
- Both keys and values are URL-decoded:
  - `%20` → space, `%3D` → `=`, etc.
  - `+` also decodes to a space (traditional form-encoded behavior).
- Non-string input → `TypeError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `parse_query_string(qs)`.
- Return type: `dict[str, list[str]]`.
- `urllib.parse` from the stdlib is fine.

## Reference cases

| input                | result                             |
|----------------------|------------------------------------|
| `""`                 | `{}`                               |
| `"a=1"`              | `{"a": ["1"]}`                     |
| `"a=1&b=2"`          | `{"a": ["1"], "b": ["2"]}`         |
| `"a=1&a=2"`          | `{"a": ["1", "2"]}`                |
| `"a"`                | `{"a": [""]}`                      |
| `"a="`               | `{"a": [""]}`                      |
| `"q=hello%20world"`  | `{"q": ["hello world"]}`           |
| `"q=hello+world"`    | `{"q": ["hello world"]}`           |
| `None`               | `TypeError`                        |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
