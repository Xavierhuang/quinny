"""Hand-authored placeholder suite for 028-phone-e164."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
is_valid_e164 = _impl.is_valid_e164


def test_common_us_11_digit():
    assert is_valid_e164("+15551234567") is True


def test_uk_12_digit():
    assert is_valid_e164("+441234567890") is True


def test_max_15_digit():
    assert is_valid_e164("+123456789012345") is True


def test_16_digit_rejected():
    assert is_valid_e164("+1234567890123456") is False


def test_missing_plus_rejected():
    assert is_valid_e164("15551234567") is False


def test_bare_plus_rejected():
    assert is_valid_e164("+") is False


def test_empty_string_rejected():
    assert is_valid_e164("") is False


def test_leading_zero_rejected():
    assert is_valid_e164("+0123456789") is False


def test_non_digits_rejected():
    assert is_valid_e164("+15551abc567") is False


def test_non_string_raises_typeerror():
    with pytest.raises(TypeError):
        is_valid_e164(15551234567)
