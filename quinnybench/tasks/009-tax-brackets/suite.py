"""Hand-authored placeholder suite for 009-tax-brackets."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
calc_tax = _impl.calc_tax


def _approx(a, b): return abs(a - b) < 0.005


def test_zero_income_zero_tax():
    assert _approx(calc_tax(0), 0.0)


def test_10000_pays_1000():
    assert _approx(calc_tax(10000), 1000.0)


def test_40000_pays_4600():
    assert _approx(calc_tax(40000), 4600.0)


def test_100000_pays_18100():
    assert _approx(calc_tax(100000), 18100.0)


def test_165000_pays_33700():
    assert _approx(calc_tax(165000), 33700.0)


def test_200000_pays_44900():
    assert _approx(calc_tax(200000), 44900.0)


def test_bracket_boundary_overflow():
    # 10000.01 is $0.01 into the 12% bracket → 1000 + 0.12*0.01 ≈ 1000.0012.
    assert _approx(calc_tax(10000.01), 1000.0012)


def test_negative_income_raises_valueerror():
    with pytest.raises(ValueError):
        calc_tax(-1)


def test_non_numeric_raises_typeerror():
    with pytest.raises(TypeError):
        calc_tax("100000")
