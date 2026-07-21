"""Hand-authored placeholder suite for 033-insurance-premium."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
calc_premium = _impl.calc_premium


def _approx(a, b): return abs(a - b) < 0.005


def test_30_basic():
    assert _approx(calc_premium(30, "basic"), 100.0)


def test_30_standard():
    assert _approx(calc_premium(30, "standard"), 250.0)


def test_30_premium():
    assert _approx(calc_premium(30, "premium"), 500.0)


def test_24_basic_gets_1_5x():
    assert _approx(calc_premium(24, "basic"), 150.0)


def test_41_basic_gets_1_3x():
    assert _approx(calc_premium(41, "basic"), 130.0)


def test_60_basic_still_1_3x():
    assert _approx(calc_premium(60, "basic"), 130.0)


def test_61_basic_gets_1_8x():
    assert _approx(calc_premium(61, "basic"), 180.0)


def test_25_boundary_is_1_0x_not_1_5x():
    assert _approx(calc_premium(25, "basic"), 100.0)


def test_negative_age_raises_valueerror():
    with pytest.raises(ValueError):
        calc_premium(-1, "basic")


def test_non_int_age_raises_typeerror():
    with pytest.raises(TypeError):
        calc_premium(30.5, "basic")


def test_unknown_tier_raises_valueerror():
    with pytest.raises(ValueError):
        calc_premium(30, "platinum")
