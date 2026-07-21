Implement a Python class `TrafficLight` that cycles through three states: `RED → GREEN → YELLOW → RED → …`.

## API

- `TrafficLight()` — constructor takes **no arguments** (calling with any positional argument must raise `TypeError`). Fresh instance starts in `RED`.
- `.current() -> str` — returns the current state, one of the exact strings `"RED"`, `"GREEN"`, `"YELLOW"`.
- `.tick()` — advance one state along the cycle. From `"RED"` → `"GREEN"`, from `"GREEN"` → `"YELLOW"`, from `"YELLOW"` → `"RED"`.
- `.reset()` — return to `"RED"` regardless of current state.

## Interface

- File: `impl.py`.
- Export exactly one public class: `TrafficLight`.
- No imports outside the Python stdlib. No CLI, no side effects at import time.

## Reference cases

| sequence                              | result       |
|---------------------------------------|--------------|
| `t = TrafficLight(); t.current()`     | `"RED"`      |
| `t.tick(); t.current()`               | `"GREEN"`    |
| `t.tick(); t.tick(); t.current()`     | `"YELLOW"`   |
| `t.tick() × 3; t.current()`           | `"RED"`      |
| `t.tick() × 7; t.current()`           | `"GREEN"`    |
| reset from any state → `t.current()`  | `"RED"`      |
| `TrafficLight("RED")`                 | `TypeError`  |

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
