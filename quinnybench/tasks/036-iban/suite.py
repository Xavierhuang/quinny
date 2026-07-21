"""Hand-authored placeholder suite for 036-iban."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
is_valid_iban = _impl.is_valid_iban

# Canonical test IBANs from ISO documentation.
UK_IBAN = "GB82WEST12345698765432"     # 22 chars
DE_IBAN = "DE89370400440532013000"     # 22 chars


def test_valid_uk_iban_returns_true():
    assert is_valid_iban(UK_IBAN) is True


def test_valid_de_iban_returns_true():
    assert is_valid_iban(DE_IBAN) is True


def test_wrong_digit_breaks_checksum():
    # Flip a middle digit in the UK IBAN.
    bad = UK_IBAN[:10] + ("0" if UK_IBAN[10] != "0" else "1") + UK_IBAN[11:]
    assert is_valid_iban(bad) is False


def test_too_short_returns_false():
    assert is_valid_iban("GB82WEST1234569") is False        # 15 chars but wrong checksum
    assert is_valid_iban("GB82WEST123456") is False         # 14 chars → too short


def test_too_long_returns_false():
    assert is_valid_iban("A" * 35) is False


def test_lowercase_returns_false():
    assert is_valid_iban(UK_IBAN.lower()) is False


def test_whitespace_returns_false():
    assert is_valid_iban("GB82 WEST 1234 5698 7654 32") is False


def test_empty_string_returns_false():
    assert is_valid_iban("") is False


def test_non_string_raises_typeerror():
    with pytest.raises(TypeError):
        is_valid_iban(12345678901234)
