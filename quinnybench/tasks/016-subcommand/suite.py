"""Hand-authored placeholder suite for 016-subcommand."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
parse_subcommand = _impl.parse_subcommand


def _empty(sub=None, flags=None, options=None, positional=None):
    return {"subcommand": sub, "flags": flags or set(),
            "options": options or {}, "positional": positional or []}


def test_empty_argv():
    assert parse_subcommand([]) == _empty()


def test_single_bare_token_is_subcommand():
    assert parse_subcommand(["deploy"]) == _empty(sub="deploy")


def test_two_bare_tokens_subcommand_then_positional():
    assert parse_subcommand(["deploy", "prod"]) == _empty(sub="deploy", positional=["prod"])


def test_flag_before_subcommand():
    assert parse_subcommand(["--verbose", "deploy"]) == \
        _empty(sub="deploy", flags={"verbose"})


def test_flag_after_subcommand():
    assert parse_subcommand(["deploy", "--verbose"]) == \
        _empty(sub="deploy", flags={"verbose"})


def test_option_captured():
    assert parse_subcommand(["deploy", "--target=prod"]) == \
        _empty(sub="deploy", options={"target": "prod"})


def test_double_dash_ends_option_parsing():
    # Nothing before --, so no subcommand; --deploy after -- is positional verbatim.
    assert parse_subcommand(["--", "deploy", "--verbose"]) == \
        _empty(positional=["deploy", "--verbose"])


def test_positional_after_subcommand_preserved():
    assert parse_subcommand(["deploy", "prod", "us-east-1"]) == \
        _empty(sub="deploy", positional=["prod", "us-east-1"])


def test_non_list_raises_typeerror():
    with pytest.raises(TypeError):
        parse_subcommand("deploy")
