"""Thin wrapper over the pip-installed cachetools library.

The .qn spec talks about functions like make_lru / put / get / has / size,
so we expose a flat module-level API that delegates to cachetools.LRUCache
and cachetools.TTLCache. Nothing is reimplemented — this is a pass-through.

If the gate is honest, verifying this wrapper against the spec should
yield all-PASS (the library is correct; the wrapper is trivial).
"""
from __future__ import annotations

from cachetools import LRUCache, TTLCache


def make_lru(maxsize):
    return LRUCache(maxsize=maxsize)


def make_ttl(maxsize, ttl, time_fn):
    return TTLCache(maxsize=maxsize, ttl=ttl, timer=time_fn)


def fake_timer(start: float = 0.0, step: float = 0.0):
    """Return a callable(): each call returns start, then start+step, ..."""
    state = {"t": float(start)}

    def _tick() -> float:
        val = state["t"]
        state["t"] += step
        return val

    return _tick


def put(c, k, v):
    c[k] = v


def get(c, k):
    return c[k]


def size(c):
    return len(c)


def has(c, k):
    return k in c
