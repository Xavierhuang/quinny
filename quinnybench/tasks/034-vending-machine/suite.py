"""Hand-authored placeholder suite for 034-vending-machine."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
VendingMachine = _impl.VendingMachine

PRODUCTS = {"cola": 150, "chips": 100, "candy": 75}


def test_fresh_balance_is_zero():
    assert VendingMachine(PRODUCTS).balance == 0


def test_insert_coin_adds_to_balance():
    m = VendingMachine(PRODUCTS); m.insert_coin(25)
    assert m.balance == 25


def test_multiple_coins_accumulate():
    m = VendingMachine(PRODUCTS)
    m.insert_coin(25); m.insert_coin(50); m.insert_coin(100)
    assert m.balance == 175


def test_select_exact_balance_returns_zero_change():
    m = VendingMachine(PRODUCTS); m.insert_coin(100)
    assert m.select("chips") == 0
    assert m.balance == 0


def test_select_returns_change():
    m = VendingMachine(PRODUCTS); m.insert_coin(200)
    assert m.select("chips") == 100


def test_balance_resets_after_dispense():
    m = VendingMachine(PRODUCTS); m.insert_coin(200); m.select("chips")
    assert m.balance == 0


def test_unknown_product_raises_keyerror():
    m = VendingMachine(PRODUCTS); m.insert_coin(200)
    with pytest.raises(KeyError):
        m.select("gum")


def test_insufficient_balance_raises_runtimeerror_and_preserves_balance():
    m = VendingMachine(PRODUCTS); m.insert_coin(50)
    with pytest.raises(RuntimeError):
        m.select("chips")
    assert m.balance == 50


def test_refund_returns_balance_and_resets():
    m = VendingMachine(PRODUCTS); m.insert_coin(75)
    assert m.refund() == 75
    assert m.balance == 0


def test_refund_on_empty_returns_zero():
    m = VendingMachine(PRODUCTS)
    assert m.refund() == 0


def test_non_int_coin_raises_typeerror():
    m = VendingMachine(PRODUCTS)
    with pytest.raises(TypeError):
        m.insert_coin(0.25)


def test_negative_coin_raises_valueerror():
    m = VendingMachine(PRODUCTS)
    with pytest.raises(ValueError):
        m.insert_coin(-25)
