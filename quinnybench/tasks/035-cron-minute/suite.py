"""Hand-authored placeholder suite for 035-cron-minute."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
parse_cron_minute = _impl.parse_cron_minute


def test_asterisk_expands_all():
    assert parse_cron_minute("*") == list(range(60))


def test_single_number():
    assert parse_cron_minute("5") == [5]


def test_range():
    assert parse_cron_minute("10-14") == [10, 11, 12, 13, 14]


def test_step_over_asterisk():
    assert parse_cron_minute("*/15") == [0, 15, 30, 45]


def test_step_over_range():
    assert parse_cron_minute("5-15/5") == [5, 10, 15]


def test_comma_list():
    assert parse_cron_minute("0,15,30") == [0, 15, 30]


def test_comma_list_merges_and_dedupes():
    assert parse_cron_minute("0,5,0-10") == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_result_is_sorted():
    assert parse_cron_minute("30,10,20") == [10, 20, 30]


def test_out_of_range_raises_valueerror():
    with pytest.raises(ValueError):
        parse_cron_minute("60")


def test_malformed_raises_valueerror():
    with pytest.raises(ValueError):
        parse_cron_minute("abc")


def test_non_string_raises_typeerror():
    with pytest.raises(TypeError):
        parse_cron_minute(5)
