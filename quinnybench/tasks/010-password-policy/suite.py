"""Hand-authored placeholder suite for 010-password-policy."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
validate_password = _impl.validate_password


def test_strong_password_returns_empty():
    assert validate_password("Str0ng!Pass") == []


def test_empty_string_fails_every_rule():
    assert validate_password("") == [
        "min_length", "has_upper", "has_lower", "has_digit", "has_special"
    ]


def test_short_but_full_char_types_fails_min_length_only():
    # "Ab1!Cd" is 6 chars — under 8. Has upper, lower, digit, special.
    assert validate_password("Ab1!Cd") == ["min_length"]


def test_missing_upper():
    assert validate_password("password1!") == ["has_upper"]


def test_missing_lower():
    assert validate_password("PASSWORD1!") == ["has_lower"]


def test_missing_digit():
    assert validate_password("Password!") == ["has_digit"]


def test_missing_special():
    assert validate_password("Password1") == ["has_special"]


def test_weak_four_char_fails_four_rules():
    assert validate_password("weak") == [
        "min_length", "has_upper", "has_digit", "has_special"
    ]


def test_non_string_raises_typeerror():
    with pytest.raises(TypeError):
        validate_password(12345678)
