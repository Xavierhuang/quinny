Implement `get_config(argv, env, defaults)` — resolve each key in `defaults` using a **precedence chain**: `argv` beats `env` beats `defaults`.

## Rules

- `argv`: `list[str]`. Only `"--key=value"` tokens count as options; other tokens are ignored.
- `env`: `dict[str, str]`. Case matters — look up the **uppercased** version of the key with dashes converted to underscores. E.g. key `"log-level"` → env `"LOG_LEVEL"`.
- `defaults`: `dict[str, Any]`. Also the source of the **set of keys** to resolve — the output has exactly the keys in `defaults`.
- For each key in `defaults`, pick the first defined source in order: argv → env → defaults.
- Types must match: non-list `argv`, non-dict `env`, non-dict `defaults` all raise `TypeError`.

## Interface

- File: `impl.py`.
- Export exactly one public function: `get_config(argv, env, defaults)`.
- Return type: `dict`. Stdlib only.

## Reference cases

```python
get_config([], {}, {"host": "localhost"})
# {"host": "localhost"}

get_config(["--host=example.com"], {}, {"host": "localhost"})
# {"host": "example.com"}

get_config([], {"HOST": "example.com"}, {"host": "localhost"})
# {"host": "example.com"}

get_config(["--host=argv"], {"HOST": "env"}, {"host": "def"})
# {"host": "argv"}

get_config([], {}, {"host": "localhost", "port": "8080"})
# {"host": "localhost", "port": "8080"}

get_config([], {"LOG_LEVEL": "debug"}, {"log-level": "info"})
# {"log-level": "debug"}   (key normalised: dashes -> underscores, uppercased)

get_config("--host=x", {}, {"host": "y"})     # TypeError
get_config([], "nope", {"host": "y"})         # TypeError
get_config([], {}, "nope")                    # TypeError
```

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
