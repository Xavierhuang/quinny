"""Hand-authored placeholder suite for 008-parse-args."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
parse_args = _impl.parse_args


def test_empty_argv():
    assert parse_args([]) == {"flags": set(), "options": {}, "positional": []}


def test_single_positional():
    assert parse_args(["src.py"]) == {
        "flags": set(), "options": {}, "positional": ["src.py"],
    }


def test_long_flag():
    assert parse_args(["--verbose"]) == {
        "flags": {"verbose"}, "options": {}, "positional": [],
    }


def test_short_flag():
    assert parse_args(["-v"]) == {
        "flags": {"v"}, "options": {}, "positional": [],
    }


def test_long_option_equals_value():
    assert parse_args(["--count=3"]) == {
        "flags": set(), "options": {"count": "3"}, "positional": [],
    }


def test_mixed_tokens():
    assert parse_args(["--count=3", "--verbose", "-o", "src.py"]) == {
        "flags": {"verbose", "o"},
        "options": {"count": "3"},
        "positional": ["src.py"],
    }


def test_double_dash_ends_options():
    assert parse_args(["--", "-v", "--verbose"]) == {
        "flags": set(),
        "options": {},
        "positional": ["-v", "--verbose"],
    }


def test_positional_before_double_dash_preserved():
    assert parse_args(["file.py", "--", "-v"]) == {
        "flags": set(),
        "options": {},
        "positional": ["file.py", "-v"],
    }


def test_later_option_overrides_earlier():
    assert parse_args(["--k=v1", "--k=v2"]) == {
        "flags": set(),
        "options": {"k": "v2"},
        "positional": [],
    }


def test_non_list_raises_typeerror():
    with pytest.raises(TypeError):
        parse_args("--verbose")
