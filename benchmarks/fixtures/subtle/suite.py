import pytest
import math
import unicodedata
from subtle_kv import make_store, set, get, exists, sum_values, len_store


def test_c01():
    """With capacity=3: set a=1, b=2, c=3, d=4 — exists(a) is False, len is 3."""
    store = make_store(capacity=3)
    set(store, "a", 1)
    set(store, "b", 2)
    set(store, "c", 3)
    set(store, "d", 4)
    assert exists(store, "a") is False
    assert len_store(store) == 3


def test_c02():
    """sum_values() over {"a": 1.0, "b": float("nan"), "c": 2.0} returns NaN, not 3.0."""
    store = make_store(capacity=10)
    set(store, "a", 1.0)
    set(store, "b", float("nan"))
    set(store, "c", 2.0)
    result = sum_values(store)
    assert math.isnan(result)


def test_c03():
    """set("café", 1); get("café") returns 1 (NFC/NFD normalize equal)."""
    store = make_store(capacity=10)
    key_nfc = "café"  # NFC form
    key_nfd = unicodedata.normalize("NFD", "café")  # NFD form
    set(store, key_nfc, 1)
    retrieved = get(store, key_nfd)
    assert retrieved == 1


def test_c04():
    """get("nonexistent") raises KeyError, not a bare Exception."""
    store = make_store(capacity=10)
    with pytest.raises(KeyError):
        get(store, "nonexistent")


def test_c05():
    """set("k", 1, ttl=10**18) then exists("k") is True (no overflow to expired)."""
    store = make_store(capacity=10)
    set(store, "k", 1, ttl=10**18)
    assert exists(store, "k") is True


def test_c06():
    """set("k", 1, ttl=0) then exists("k") is False (ttl=0 means expired now)."""
    store = make_store(capacity=10)
    set(store, "k", 1, ttl=0)
    assert exists(store, "k") is False
