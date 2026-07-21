"""Hand-authored placeholder suite for 005-flatten-dict."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
flatten_dict = _impl.flatten_dict


def test_empty_dict_returns_empty():
    assert flatten_dict({}) == {}


def test_single_top_level_key():
    assert flatten_dict({"a": 1}) == {"a": 1}


def test_two_level_nesting():
    assert flatten_dict({"a": {"b": 1}}) == {"a.b": 1}


def test_three_level_nesting():
    assert flatten_dict({"a": {"b": {"c": 1}}}) == {"a.b.c": 1}


def test_non_dict_values_are_preserved():
    assert flatten_dict({"a": [1, 2, 3]}) == {"a": [1, 2, 3]}


def test_keys_containing_separator_are_preserved():
    assert flatten_dict({"a.b": 1}) == {"a.b": 1}


def test_empty_inner_dict_disappears():
    assert flatten_dict({"a": {}}) == {}


def test_custom_separator():
    assert flatten_dict({"a": {"b": 1}}, sep="/") == {"a/b": 1}


def test_non_dict_raises_typeerror():
    with pytest.raises(TypeError):
        flatten_dict("not a dict")


def test_none_raises_typeerror():
    with pytest.raises(TypeError):
        flatten_dict(None)
