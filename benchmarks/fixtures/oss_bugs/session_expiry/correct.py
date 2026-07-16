"""Correct: rejects expired + unknown + empty tokens."""
import uuid

TTL_SECONDS = 3600
_store: dict[str, float] = {}   # token -> expiry timestamp


def issue(user: str, now: float = 0.0) -> str:
    tok = uuid.uuid4().hex
    _store[tok] = now + TTL_SECONDS
    return tok


def validate(token: str, now: float) -> bool:
    if not token:
        return False
    expiry = _store.get(token)
    if expiry is None:
        return False
    return now < expiry
