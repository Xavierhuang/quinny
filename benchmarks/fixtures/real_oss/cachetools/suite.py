import pytest
from cache_api import make_lru, make_ttl, fake_timer, put, get, size, has


def test_c01():
    """With c=make_lru(4): put(c,"a",1); get(c,"a") returns 1."""
    c = make_lru(4)
    put(c, "a", 1)
    assert get(c, "a") == 1


def test_c02():
    """With c=make_lru(2): put(c,"a",1); put(c,"b",2); put(c,"c",3); size(c) equals 2."""
    c = make_lru(2)
    put(c, "a", 1)
    put(c, "b", 2)
    put(c, "c", 3)
    assert size(c) == 2


def test_c03():
    """With c=make_lru(2): put(c,"a",1); put(c,"b",2); get(c,"a"); put(c,"c",3); has(c,"a") is True and has(c,"b") is False."""
    c = make_lru(2)
    put(c, "a", 1)
    put(c, "b", 2)
    get(c, "a")
    put(c, "c", 3)
    assert has(c, "a") is True
    assert has(c, "b") is False


def test_c04():
    """With c=make_lru(4): get(c,"missing") raises KeyError."""
    c = make_lru(4)
    with pytest.raises(KeyError):
        get(c, "missing")


def test_c05():
    """With c=make_lru(4): put(c,"a",1); put(c,"a",2); size(c) equals 1."""
    c = make_lru(4)
    put(c, "a", 1)
    put(c, "a", 2)
    assert size(c) == 1


def test_c06():
    """With c=make_ttl(4, 10, fake_timer(start=0, step=0)): put(c,"a",1); get(c,"a") returns 1."""
    timer = fake_timer(start=0, step=0)
    c = make_ttl(4, 10, timer)
    put(c, "a", 1)
    assert get(c, "a") == 1


def test_c07():
    """With c=make_ttl(4, 10, fake_timer(start=0, step=100)): put(c,"a",1); get(c,"a") raises KeyError."""
    timer = fake_timer(start=0, step=100)
    c = make_ttl(4, 10, timer)
    put(c, "a", 1)
    with pytest.raises(KeyError):
        get(c, "a")


def test_c08():
    """With c=make_ttl(4, 10, fake_timer(start=0, step=5)): put(c,"a",1); get(c,"a") returns 1."""
    timer = fake_timer(start=0, step=5)
    c = make_ttl(4, 10, timer)
    put(c, "a", 1)
    assert get(c, "a") == 1
