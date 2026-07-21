"""Hand-authored placeholder suite for 002-luhn-check.

Mirrors the .qn `test` criteria one-for-one. Phase 2 will regenerate this via
`quinny verify --emit` and diff against this version.
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
is_valid_luhn = _impl.is_valid_luhn


def test_valid_visa_returns_true():
    assert is_valid_luhn("4532015112830366") is True


def test_wrong_last_digit_returns_false():
    assert is_valid_luhn("4532015112830367") is False


def test_classical_luhn_test_string_returns_true():
    assert is_valid_luhn("79927398713") is True


def test_visa_with_spaces_returns_true():
    assert is_valid_luhn("4111 1111 1111 1111") is True


def test_visa_with_hyphens_returns_true():
    assert is_valid_luhn("4111-1111-1111-1111") is True


def test_empty_string_returns_false():
    assert is_valid_luhn("") is False


def test_alphabetic_returns_false():
    assert is_valid_luhn("abcd") is False


def test_single_digit_returns_false():
    assert is_valid_luhn("5") is False


def test_non_string_raises_typeerror():
    with pytest.raises(TypeError):
        is_valid_luhn(4532015112830366)


def test_none_raises_typeerror():
    with pytest.raises(TypeError):
        is_valid_luhn(None)
