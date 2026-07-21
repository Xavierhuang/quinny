"""Hand-authored placeholder suite for 001-shipping-cost.

Phase 2 replaces this with a suite emitted by `quinny verify --emit`. The
hand-authored version mirrors the .qn `test` criteria one-for-one so runner
output is meaningful before the real emit.

Loads impl.py from the same directory this suite is placed in — Quinny's
verify path arranges that.
"""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
shipping_cost = _impl.shipping_cost


def test_weight_0_returns_5():
    assert abs(shipping_cost(0) - 5.00) < 0.005


def test_weight_half_kg_returns_5():
    assert abs(shipping_cost(0.5) - 5.00) < 0.005


def test_weight_1kg_returns_5():
    assert abs(shipping_cost(1.0) - 5.00) < 0.005


def test_weight_1_5kg_returns_5_75():
    assert abs(shipping_cost(1.5) - 5.75) < 0.005


def test_weight_5kg_returns_11():
    assert abs(shipping_cost(5.0) - 11.00) < 0.005


def test_weight_10kg_returns_18_50():
    assert abs(shipping_cost(10.0) - 18.50) < 0.005


def test_weight_10_5kg_returns_21():
    assert abs(shipping_cost(10.5) - 21.00) < 0.005


def test_weight_25kg_returns_50():
    assert abs(shipping_cost(25.0) - 50.00) < 0.005


def test_negative_weight_raises_valueerror():
    with pytest.raises(ValueError):
        shipping_cost(-1.0)


def test_non_numeric_raises_typeerror():
    with pytest.raises(TypeError):
        shipping_cost("heavy")
