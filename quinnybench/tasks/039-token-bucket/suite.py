"""Hand-authored placeholder suite for 039-token-bucket."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
TokenBucket = _impl.TokenBucket


def test_fresh_bucket_is_full():
    b = TokenBucket(5, 1.0)
    assert b.tokens == 5


def test_take_one_succeeds_and_deducts():
    b = TokenBucket(5, 1.0)
    assert b.try_take(0.0, 1) is True
    assert b.tokens == 4


def test_take_more_than_available_returns_false_and_no_deduct():
    b = TokenBucket(5, 1.0)
    b.try_take(0.0, 4)
    assert b.tokens == 1
    assert b.try_take(0.0, 5) is False
    assert b.tokens == 1


def test_second_take_at_same_time_fails_after_emptying():
    b = TokenBucket(1, 1.0)
    assert b.try_take(0.0, 1) is True
    assert b.try_take(0.0, 1) is False


def test_refill_after_one_second():
    b = TokenBucket(5, 1.0)
    b.try_take(0.0, 5)              # empty
    assert b.try_take(1.0, 1) is True   # refilled 1 token, take it
    assert b.tokens == 0


def test_refill_capped_at_capacity():
    b = TokenBucket(5, 1.0)
    b.try_take(0.0, 5)              # empty
    # 100 seconds later — should be capped at capacity, not 100 tokens.
    assert b.try_take(100.0, 5) is True
    assert b.tokens == 0


def test_zero_capacity_raises_valueerror():
    with pytest.raises(ValueError):
        TokenBucket(0, 1.0)


def test_negative_refill_raises_valueerror():
    with pytest.raises(ValueError):
        TokenBucket(5, -1.0)


def test_non_int_capacity_raises_typeerror():
    with pytest.raises(TypeError):
        TokenBucket(1.5, 1.0)
