"""Same wrapper as pristine_wrapper.py, with one narrowly-targeted defect.

Bug: LRU-order-on-read is broken. `get` bypasses the cache's __getitem__
(which normally updates recency) and pokes at the underlying dict. As a
result, the "most-recently-used" bookkeeping doesn't advance on reads,
so the wrong entry gets evicted under pressure.

Every other criterion in the spec is unaffected. If the gate is
surgically-honest, we should see exactly one FAIL — the LRU-order test —
and everything else PASS.
"""
from __future__ import annotations

from cachetools import LRUCache, TTLCache


def make_lru(maxsize):
    return LRUCache(maxsize=maxsize)


def make_ttl(maxsize, ttl, time_fn):
    return TTLCache(maxsize=maxsize, ttl=ttl, timer=time_fn)


def fake_timer(start: float = 0.0, step: float = 0.0):
    state = {"t": float(start)}

    def _tick() -> float:
        val = state["t"]
        state["t"] += step
        return val

    return _tick


def put(c, k, v):
    c[k] = v


def get(c, k):
    # DEFECT: for LRUCache, bypass the recency update by hitting the
    # underlying dict directly. TTLCache still goes through normal access
    # (so expiration semantics remain intact — the bug is surgical).
    if isinstance(c, LRUCache) and not isinstance(c, TTLCache):
        return dict.__getitem__(c, k)
    return c[k]


def size(c):
    return len(c)


def has(c, k):
    return k in c
