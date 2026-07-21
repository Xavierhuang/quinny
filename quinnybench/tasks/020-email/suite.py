"""Hand-authored placeholder suite for 020-email."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
is_valid_email = _impl.is_valid_email


def test_simple_valid():
    assert is_valid_email("a@b.co") is True


def test_dotted_local_part():
    assert is_valid_email("test.user@example.com") is True


def test_plus_tag():
    assert is_valid_email("foo+bar@example.com") is True


def test_multi_label_tld():
    assert is_valid_email("foo@example.co.uk") is True


def test_leading_dot_local_rejected():
    assert is_valid_email(".foo@bar.com") is False


def test_trailing_dot_local_rejected():
    assert is_valid_email("foo.@bar.com") is False


def test_consecutive_dots_local_rejected():
    assert is_valid_email("foo..bar@baz.com") is False


def test_domain_without_dot_rejected():
    assert is_valid_email("foo@bar") is False


def test_leading_hyphen_label_rejected():
    assert is_valid_email("foo@-bar.com") is False


def test_trailing_hyphen_label_rejected():
    assert is_valid_email("foo@bar-.com") is False


def test_empty_string_rejected():
    assert is_valid_email("") is False


def test_empty_local_rejected():
    assert is_valid_email("@bar.com") is False


def test_empty_domain_rejected():
    assert is_valid_email("foo@") is False


def test_non_string_raises_typeerror():
    with pytest.raises(TypeError):
        is_valid_email(None)
