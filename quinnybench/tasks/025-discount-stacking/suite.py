"""Hand-authored placeholder suite for 025-discount-stacking."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
apply_discounts = _impl.apply_discounts


def _approx(a, b): return abs(a - b) < 0.005


def _p(v, stackable=True): return {"type": "percent", "value": v, "stackable": stackable}
def _f(v, stackable=True): return {"type": "flat",    "value": v, "stackable": stackable}


def test_no_discounts_unchanged():
    assert _approx(apply_discounts(100, []), 100.0)


def test_single_stackable_percent():
    assert _approx(apply_discounts(100, [_p(10)]), 90.0)


def test_single_stackable_flat():
    assert _approx(apply_discounts(100, [_f(15)]), 85.0)


def test_two_stackable_percents_multiply():
    assert _approx(apply_discounts(100, [_p(10), _p(20)]), 72.0)


def test_two_stackable_flats_sum():
    assert _approx(apply_discounts(100, [_f(15), _f(20)]), 65.0)


def test_non_stackable_best_wins():
    # 10% non-stack saves $10; $20 flat non-stack saves $20 → apply the flat.
    assert _approx(apply_discounts(100, [_p(10, False), _f(20, False)]), 80.0)


def test_non_stackable_applies_before_stackables():
    # 20% non-stack → 80; then 10% stack → 72.
    assert _approx(apply_discounts(100, [_p(20, False), _p(10)]), 72.0)


def test_over_discount_clamps_to_zero():
    assert _approx(apply_discounts(100, [_f(150)]), 0.0)


def test_zero_subtotal():
    assert _approx(apply_discounts(0, [_p(50)]), 0.0)


def test_negative_subtotal_raises_valueerror():
    with pytest.raises(ValueError):
        apply_discounts(-1, [])


def test_unknown_discount_type_raises_valueerror():
    with pytest.raises(ValueError):
        apply_discounts(100, [{"type": "bogus", "value": 1, "stackable": True}])


def test_non_list_discounts_raises_typeerror():
    with pytest.raises(TypeError):
        apply_discounts(100, _p(10))
