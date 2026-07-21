"""Hand-authored placeholder suite for 017-proration."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
charge = _impl.charge


def _approx(a, b): return abs(a - b) < 0.005


def test_day_1_of_30_is_full():
    assert _approx(charge(30, 1, 30), 30.0)


def test_last_day_of_30_is_one_day():
    assert _approx(charge(30, 30, 30), 1.0)


def test_day_15_of_30():
    assert _approx(charge(30, 15, 30), 16.0)


def test_full_31_day_month():
    assert _approx(charge(31, 1, 31), 31.0)


def test_full_28_day_month():
    assert _approx(charge(28, 1, 28), 28.0)


def test_fractional_31_day_math():
    # amount=30, day=15, 31-day month → 30 * 17/31 = 16.451612...
    assert _approx(charge(30, 15, 31), 30 * 17 / 31)


def test_zero_amount_returns_zero():
    assert _approx(charge(0, 15, 30), 0.0)


def test_negative_amount_raises_valueerror():
    with pytest.raises(ValueError):
        charge(-1, 15, 30)


def test_day_below_1_raises_valueerror():
    with pytest.raises(ValueError):
        charge(30, 0, 30)


def test_day_above_days_in_month_raises_valueerror():
    with pytest.raises(ValueError):
        charge(30, 31, 30)


def test_bad_days_in_month_raises_valueerror():
    with pytest.raises(ValueError):
        charge(30, 1, 27)


def test_non_numeric_amount_raises_typeerror():
    with pytest.raises(TypeError):
        charge("30", 1, 30)


def test_non_int_day_raises_typeerror():
    with pytest.raises(TypeError):
        charge(30, 1.5, 30)
