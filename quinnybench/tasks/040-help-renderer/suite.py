"""Hand-authored placeholder suite for 040-help-renderer."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
render_help = _impl.render_help


def test_single_long_only_flag():
    out = render_help("mytool", [
        {"short": None, "long": "verbose", "value": None, "help": "chatty mode"},
    ])
    assert out == (
        "Usage: mytool [OPTIONS]\n"
        "\n"
        "Options:\n"
        "      --verbose  chatty mode\n"
    )


def test_short_and_long_flag_pair():
    out = render_help("mytool", [
        {"short": "v", "long": "verbose", "value": None, "help": "chatty mode"},
    ])
    assert out == (
        "Usage: mytool [OPTIONS]\n"
        "\n"
        "Options:\n"
        "  -v, --verbose  chatty mode\n"
    )


def test_long_option_with_value():
    out = render_help("mytool", [
        {"short": None, "long": "count", "value": "N", "help": "how many"},
    ])
    assert out == (
        "Usage: mytool [OPTIONS]\n"
        "\n"
        "Options:\n"
        "      --count N  how many\n"
    )


def test_short_long_with_value():
    out = render_help("mytool", [
        {"short": "o", "long": "output", "value": "FILE", "help": "write to FILE"},
    ])
    assert out == (
        "Usage: mytool [OPTIONS]\n"
        "\n"
        "Options:\n"
        "  -o, --output FILE  write to FILE\n"
    )


def test_multiple_options_aligned_to_widest():
    out = render_help("mytool", [
        {"short": "v", "long": "verbose",     "value": None,   "help": "chatty"},
        {"short": "o", "long": "output-file", "value": "PATH", "help": "output path"},
    ])
    assert out == (
        "Usage: mytool [OPTIONS]\n"
        "\n"
        "Options:\n"
        "  -v, --verbose           chatty\n"
        "  -o, --output-file PATH  output path\n"
    )


def test_empty_options_still_prints_header():
    out = render_help("mytool", [])
    assert out == (
        "Usage: mytool [OPTIONS]\n"
        "\n"
        "Options:\n"
    )


def test_non_string_program_raises_typeerror():
    with pytest.raises(TypeError):
        render_help(123, [])


def test_non_list_options_raises_typeerror():
    with pytest.raises(TypeError):
        render_help("mytool", {})
