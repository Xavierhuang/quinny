"""Hand-authored placeholder suite for 027-ini-parse."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
parse_ini = _impl.parse_ini


def test_empty_string_returns_empty_dict():
    assert parse_ini("") == {}


def test_single_section_one_kv():
    assert parse_ini("[a]\nk=v") == {"a": {"k": "v"}}


def test_multiple_sections_and_keys():
    text = "[a]\nk=v\nl=w\n[b]\nm=x"
    assert parse_ini(text) == {"a": {"k": "v", "l": "w"}, "b": {"m": "x"}}


def test_whitespace_around_key_and_value_stripped():
    assert parse_ini("[a]\n  k  =  v  ") == {"a": {"k": "v"}}


def test_semicolon_comments_ignored():
    text = "; this is a comment\n[a]\nk=v"
    assert parse_ini(text) == {"a": {"k": "v"}}


def test_hash_comments_ignored():
    text = "# also a comment\n[a]\nk=v"
    assert parse_ini(text) == {"a": {"k": "v"}}


def test_blank_lines_ignored():
    text = "\n\n[a]\n\nk=v\n\n"
    assert parse_ini(text) == {"a": {"k": "v"}}


def test_duplicate_key_last_wins():
    assert parse_ini("[a]\nk=v1\nk=v2") == {"a": {"k": "v2"}}


def test_keys_before_section_go_to_empty_section():
    assert parse_ini("k=v\n[a]\nl=w") == {"": {"k": "v"}, "a": {"l": "w"}}


def test_line_without_equals_raises_valueerror():
    with pytest.raises(ValueError):
        parse_ini("[a]\nno_equals_here")


def test_non_string_raises_typeerror():
    with pytest.raises(TypeError):
        parse_ini(None)
