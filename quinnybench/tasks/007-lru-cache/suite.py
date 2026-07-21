"""Hand-authored placeholder suite for 007-lru-cache."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
LRUCache = _impl.LRUCache


def test_new_cache_has_size_zero():
    assert LRUCache(3).size() == 0


def test_put_and_size():
    c = LRUCache(3)
    c.put("a", 1)
    c.put("b", 2)
    assert c.size() == 2


def test_get_returns_value():
    c = LRUCache(3)
    c.put("a", 1)
    assert c.get("a") == 1


def test_get_missing_raises_keyerror():
    c = LRUCache(3)
    with pytest.raises(KeyError):
        c.get("nope")


def test_put_existing_key_replaces_value():
    c = LRUCache(3)
    c.put("a", 1)
    c.put("a", 2)
    assert c.get("a") == 2


def test_put_existing_key_does_not_grow():
    c = LRUCache(3)
    c.put("a", 1)
    c.put("a", 2)
    assert c.size() == 1


def test_eviction_when_over_capacity():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)              # evicts "a" (LRU)
    with pytest.raises(KeyError):
        c.get("a")
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_get_renews_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")                 # renew "a" — now "b" is LRU
    c.put("c", 3)              # should evict "b", not "a"
    assert c.get("a") == 1
    with pytest.raises(KeyError):
        c.get("b")


def test_capacity_zero_raises_valueerror():
    with pytest.raises(ValueError):
        LRUCache(0)


def test_negative_capacity_raises_valueerror():
    with pytest.raises(ValueError):
        LRUCache(-1)


def test_non_int_capacity_raises_typeerror():
    with pytest.raises(TypeError):
        LRUCache(1.5)
