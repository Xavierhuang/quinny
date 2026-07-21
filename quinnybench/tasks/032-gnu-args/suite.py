"""Hand-authored placeholder suite for 032-gnu-args."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
parse_gnu_args = _impl.parse_gnu_args


def _e(flags=None, options=None, positional=None):
    return {"flags": flags or set(), "options": options or {}, "positional": positional or []}


def test_empty_argv():
    assert parse_gnu_args([], set()) == _e()


def test_long_flag():
    assert parse_gnu_args(["--verbose"], set()) == _e(flags={"verbose"})


def test_long_option_equals():
    assert parse_gnu_args(["--count=3"], set()) == _e(options={"count": "3"})


def test_long_option_needing_value():
    assert parse_gnu_args(["--count", "3"], {"count"}) == _e(options={"count": "3"})


def test_short_flag():
    assert parse_gnu_args(["-v"], set()) == _e(flags={"v"})


def test_short_option_needing_value():
    assert parse_gnu_args(["-o", "out.txt"], {"o"}) == _e(options={"o": "out.txt"})


def test_positional_passes_through():
    assert parse_gnu_args(["src.py"], set()) == _e(positional=["src.py"])


def test_bare_double_dash_ends_options():
    assert parse_gnu_args(["--", "-v", "--verbose"], set()) == \
        _e(positional=["-v", "--verbose"])


def test_missing_value_raises_valueerror():
    with pytest.raises(ValueError):
        parse_gnu_args(["--count"], {"count"})


def test_non_list_argv_raises_typeerror():
    with pytest.raises(TypeError):
        parse_gnu_args("-v", set())


def test_non_set_value_options_raises_typeerror():
    with pytest.raises(TypeError):
        parse_gnu_args([], ["count"])
