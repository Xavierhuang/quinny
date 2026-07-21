"""Hand-authored placeholder suite for 019-csv-row."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
parse_csv_row = _impl.parse_csv_row


def test_empty_string_yields_single_empty_field():
    assert parse_csv_row("") == [""]


def test_single_unquoted_field():
    assert parse_csv_row("hello") == ["hello"]


def test_three_comma_separated_fields():
    assert parse_csv_row("a,b,c") == ["a", "b", "c"]


def test_empty_middle_field():
    assert parse_csv_row("a,,c") == ["a", "", "c"]


def test_trailing_empty_field():
    assert parse_csv_row("a,b,") == ["a", "b", ""]


def test_quoted_field_with_comma():
    assert parse_csv_row('"a,b",c') == ["a,b", "c"]


def test_doubled_quote_decodes_to_single_quote():
    assert parse_csv_row('"say ""hi"""') == ['say "hi"']


def test_unclosed_quote_raises_valueerror():
    with pytest.raises(ValueError):
        parse_csv_row('"unclosed')


def test_junk_after_closing_quote_raises_valueerror():
    with pytest.raises(ValueError):
        parse_csv_row('"a"b')


def test_non_string_raises_typeerror():
    with pytest.raises(TypeError):
        parse_csv_row(123)
