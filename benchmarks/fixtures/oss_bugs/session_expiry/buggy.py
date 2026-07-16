"""Buggy: `token in store` ignores the expiry. Classic session-timeout leak."""
import uuid

TTL_SECONDS = 3600
_store: dict[str, float] = {}


def issue(user: str, now: float = 0.0) -> str:
    tok = uuid.uuid4().hex
    _store[tok] = now + TTL_SECONDS
    return tok


def validate(token: str, now: float) -> bool:
    # Bug: forgot to compare against expiry, and empty string not filtered.
    return token in _store
