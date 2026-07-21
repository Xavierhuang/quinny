Implement an `Order` class whose `status` moves through this state machine:

```
PENDING ── pay ──▶ PAID ── ship ──▶ SHIPPED ── deliver ──▶ DELIVERED
   │                │
   └── cancel ──▶ CANCELLED ◀── cancel ── PAID
```

## API

- `Order()` — constructor. No positional arguments. Any positional argument → `TypeError`. Starts in `"PENDING"`.
- `.status` — the current state, one of `"PENDING"`, `"PAID"`, `"SHIPPED"`, `"DELIVERED"`, `"CANCELLED"`.
- `.pay()`, `.ship()`, `.deliver()`, `.cancel()` — attempt the transition.
- Any transition **not** listed above raises `RuntimeError`.

## Allowed transitions (only these)

| from      | method    | to         |
|-----------|-----------|------------|
| PENDING   | pay       | PAID       |
| PENDING   | cancel    | CANCELLED  |
| PAID      | ship      | SHIPPED    |
| PAID      | cancel    | CANCELLED  |
| SHIPPED   | deliver   | DELIVERED  |

Everything else → `RuntimeError`. Specifically: `DELIVERED` and `CANCELLED` are terminal — no method call succeeds from them.

## Interface

- File: `impl.py`.
- Export exactly one public class: `Order`.
- Stdlib only.

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
