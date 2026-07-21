"""Hand-authored placeholder suite for 011-order-lifecycle."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
Order = _impl.Order


def test_new_order_is_pending():
    assert Order().status == "PENDING"


def test_pay_moves_to_paid():
    o = Order(); o.pay()
    assert o.status == "PAID"


def test_pay_then_ship_reaches_shipped():
    o = Order(); o.pay(); o.ship()
    assert o.status == "SHIPPED"


def test_pay_then_ship_then_deliver_reaches_delivered():
    o = Order(); o.pay(); o.ship(); o.deliver()
    assert o.status == "DELIVERED"


def test_cancel_from_pending_moves_to_cancelled():
    o = Order(); o.cancel()
    assert o.status == "CANCELLED"


def test_pay_then_cancel_moves_to_cancelled():
    o = Order(); o.pay(); o.cancel()
    assert o.status == "CANCELLED"


def test_ship_from_pending_raises_runtimeerror():
    with pytest.raises(RuntimeError):
        Order().ship()


def test_deliver_from_pending_raises_runtimeerror():
    with pytest.raises(RuntimeError):
        Order().deliver()


def test_deliver_from_paid_raises_runtimeerror():
    o = Order(); o.pay()
    with pytest.raises(RuntimeError):
        o.deliver()


def test_pay_after_paid_raises_runtimeerror():
    o = Order(); o.pay()
    with pytest.raises(RuntimeError):
        o.pay()


def test_pay_after_cancelled_raises_runtimeerror():
    o = Order(); o.cancel()
    with pytest.raises(RuntimeError):
        o.pay()


def test_constructor_with_arg_raises_typeerror():
    with pytest.raises(TypeError):
        Order("PAID")
