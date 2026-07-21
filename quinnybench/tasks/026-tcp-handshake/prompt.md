Implement a `TCPConnection` class modelling the client-side TCP handshake.

## States and transitions (only these)

```
CLOSED ── open() ──▶ SYN_SENT ── syn_ack() ──▶ ESTABLISHED ── close() ──▶ CLOSED
```

- `TCPConnection()` — constructor. No positional args (any arg → `TypeError`). Starts in `"CLOSED"`.
- `.state` — current state string.
- `.open()` — `CLOSED → SYN_SENT`.
- `.syn_ack()` — `SYN_SENT → ESTABLISHED` (models receiving SYN-ACK from the server and sending the final ACK).
- `.close()` — `ESTABLISHED → CLOSED`.
- Any transition not listed above raises `RuntimeError`.

## Interface

- File: `impl.py`.
- Export exactly one public class: `TCPConnection`.
- Stdlib only.

Respond with **only** the contents of `impl.py`, in a single fenced Python code block. No explanation.
