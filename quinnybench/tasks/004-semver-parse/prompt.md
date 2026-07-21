Implement a Python function `parse_semver(version)` that parses a [Semantic Versioning 2.0](https://semver.org/) string into a dict.

## Return shape

```python
{"major": int, "minor": int, "patch": int, "prerelease": str | None, "buildmetadata": str | None}
```

## Grammar (semver 2.0)

- `MAJOR.MINOR.PATCH` are non-negative integers.
- **Leading zeros** are forbidden (`"0"` is fine, `"01"` is not).
- Optional `-PRERELEASE` after `PATCH`. PRERELEASE is one or more dot-separated identifiers; each identifier is `[0-9A-Za-z-]+`; a numeric-only identifier may not have leading zeros.
- Optional `+BUILDMETADATA` at the very end. BUILDMETADATA is one or more dot-separated identifiers, each `[0-9A-Za-z-]+`. Numeric identifiers may have leading zeros here.
- The full string must be `MAJOR.MINOR.PATCH[-PRERELEASE][+BUILDMETADATA]` with nothing extra.

## Errors

- Non-string input → `TypeError`.
- Empty string, malformed, missing components, extra trailing content, or grammar violation → `ValueError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `parse_semver(version)`.
- Stdlib only (regex is fine).

## Reference cases

| version              | result                                                                              |
|----------------------|-------------------------------------------------------------------------------------|
| `"1.0.0"`            | `{major:1, minor:0, patch:0, prerelease:None, buildmetadata:None}`                  |
| `"1.2.3"`            | `{major:1, minor:2, patch:3, prerelease:None, buildmetadata:None}`                  |
| `"1.2.3-alpha"`      | `{..., prerelease:"alpha", buildmetadata:None}`                                     |
| `"1.2.3-alpha.1"`    | `{..., prerelease:"alpha.1", buildmetadata:None}`                                   |
| `"1.2.3+build.5"`    | `{..., prerelease:None, buildmetadata:"build.5"}`                                   |
| `"1.2.3-rc.1+meta"`  | `{..., prerelease:"rc.1", buildmetadata:"meta"}`                                    |
| `"01.2.3"`           | `ValueError` (leading zero)                                                          |
| `"1.2"`              | `ValueError` (missing patch)                                                         |
| `"1.2.3."`           | `ValueError` (trailing dot)                                                          |
| `""`                 | `ValueError`                                                                         |
| `123` (int)          | `TypeError`                                                                          |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
