"""Hand-authored placeholder suite for 012-query-string."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
parse_query_string = _impl.parse_query_string


def test_empty_string():
    assert parse_query_string("") == {}


def test_single_pair():
    assert parse_query_string("a=1") == {"a": ["1"]}


def test_two_pairs():
    assert parse_query_string("a=1&b=2") == {"a": ["1"], "b": ["2"]}


def test_repeated_key_preserves_order():
    assert parse_query_string("a=1&a=2") == {"a": ["1", "2"]}


def test_key_without_equals():
    assert parse_query_string("a") == {"a": [""]}


def test_key_with_bare_equals():
    assert parse_query_string("a=") == {"a": [""]}


def test_percent_encoded_value():
    assert parse_query_string("q=hello%20world") == {"q": ["hello world"]}


def test_plus_decodes_to_space():
    assert parse_query_string("q=hello+world") == {"q": ["hello world"]}


def test_non_string_raises_typeerror():
    with pytest.raises(TypeError):
        parse_query_string(None)
