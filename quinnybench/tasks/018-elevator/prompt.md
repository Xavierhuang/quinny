Implement an `Elevator` class that serves floor requests in FIFO order, one floor per tick.

## API

- `Elevator(num_floors)` — `num_floors` must be `int >= 2` (booleans do not count). Non-int → `TypeError`. `< 2` → `ValueError`. Starts at floor 1.
- `.current_floor` — current integer floor.
- `.direction` — one of `"UP"`, `"DOWN"`, `"IDLE"`, **computed** from the next queued target:
  - No pending → `"IDLE"`.
  - Head of queue is above `current_floor` → `"UP"`.
  - Head is below → `"DOWN"`.
  - Head equals current floor → `"IDLE"` (about to be popped on next tick).
- `.pending` — number of queued requests.
- `.request(floor)` — enqueue a floor request. Non-int → `TypeError`. Out of range (`< 1` or `> num_floors`) → `ValueError`. Duplicate requests (floor already in queue) are silently ignored.
- `.tick()` — advance one step: move one floor toward the head of the queue; when the elevator reaches the head, pop it. If the queue is empty, do nothing.

## FIFO semantics (important)

Requests are served in the order they were made — even if a later request is closer. Example: from floor 1 in a 5-floor building, `request(5); request(2)` then 4 ticks reaches floor 5 (pending drops to 1); 3 more ticks reaches floor 2 (pending 0).

## Interface

- File: `impl.py`.
- Export exactly one public class: `Elevator`.
- Stdlib only.

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
