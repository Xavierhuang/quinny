"""Held-out acceptance suite for the `mini_kv` task.

NEVER shown to the code generator — this is the hidden black-box grader. It
imports whatever the project produced at `mini_kv.py` and exercises the pinned
public API described in benchmarks/prompts/mini_kv.txt.
"""
import pytest

from mini_kv import MiniKV


class Clock:
    """Controllable monotonic clock injected as MiniKV(time_fn=...)."""
    def __init__(self, t=0.0):
        self.t = float(t)

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


# --- basics --------------------------------------------------------------

def test_set_get_roundtrip():
    kv = MiniKV(capacity=10)
    kv.set("a", 1)
    assert kv.get("a") == 1


def test_overwrite_updates_value():
    kv = MiniKV(capacity=10)
    kv.set("a", 1)
    kv.set("a", 2)
    assert kv.get("a") == 2


def test_get_missing_raises_keyerror():
    kv = MiniKV(capacity=10)
    with pytest.raises(KeyError):
        kv.get("nope")


def test_delete_returns_bool():
    kv = MiniKV(capacity=10)
    kv.set("a", 1)
    assert kv.delete("a") is True
    assert kv.delete("a") is False


def test_exists_and_len():
    kv = MiniKV(capacity=10)
    assert kv.exists("a") is False
    kv.set("a", 1)
    kv.set("b", 2)
    assert kv.exists("a") is True
    assert len(kv) == 2


# --- LRU eviction --------------------------------------------------------

def test_lru_evicts_least_recently_used():
    kv = MiniKV(capacity=2)
    kv.set("a", 1)
    kv.set("b", 2)
    kv.set("c", 3)          # over capacity -> evict "a" (LRU)
    with pytest.raises(KeyError):
        kv.get("a")
    assert kv.get("b") == 2
    assert kv.get("c") == 3


def test_get_refreshes_recency():
    kv = MiniKV(capacity=2)
    kv.set("a", 1)
    kv.set("b", 2)
    kv.get("a")             # "a" now most-recently used
    kv.set("c", 3)          # evict "b" instead of "a"
    assert kv.get("a") == 1
    with pytest.raises(KeyError):
        kv.get("b")


# --- TTL expiry ----------------------------------------------------------

def test_ttl_expires_after_deadline():
    clk = Clock()
    kv = MiniKV(capacity=10, time_fn=clk)
    kv.set("k", "v", ttl=10)
    clk.advance(5)
    assert kv.get("k") == "v"      # still alive
    clk.advance(6)                 # t=11 > 10
    with pytest.raises(KeyError):
        kv.get("k")


def test_expired_entry_drops_from_len():
    clk = Clock()
    kv = MiniKV(capacity=10, time_fn=clk)
    kv.set("k", "v", ttl=1)
    kv.set("perm", "p")            # no ttl -> never expires
    clk.advance(2)
    assert kv.exists("k") is False
    assert kv.exists("perm") is True
    assert len(kv) == 1


# --- transactions --------------------------------------------------------

def test_transaction_commit_persists():
    kv = MiniKV(capacity=10)
    kv.begin()
    kv.set("x", 1)
    kv.commit()
    assert kv.get("x") == 1


def test_transaction_rollback_discards_writes():
    kv = MiniKV(capacity=10)
    kv.set("x", 1)
    kv.begin()
    kv.set("x", 2)
    kv.set("y", 9)
    kv.rollback()
    assert kv.get("x") == 1
    assert kv.exists("y") is False


def test_transaction_rollback_restores_deletes():
    kv = MiniKV(capacity=10)
    kv.set("y", 1)
    kv.begin()
    kv.delete("y")
    kv.rollback()
    assert kv.get("y") == 1


def test_nested_begin_and_stray_commit_error():
    kv = MiniKV(capacity=10)
    with pytest.raises((RuntimeError, ValueError)):
        kv.commit()                # no active transaction
    kv.begin()
    with pytest.raises((RuntimeError, ValueError)):
        kv.begin()                 # nested not allowed
