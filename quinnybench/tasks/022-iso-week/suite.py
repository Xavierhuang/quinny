"""Hand-authored placeholder suite for 022-iso-week."""
import datetime as dt
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
iso_week = _impl.iso_week


def test_monday_2024_01_01():
    assert iso_week(dt.date(2024, 1, 1)) == (2024, 1, 1)


def test_sunday_2024_01_07():
    assert iso_week(dt.date(2024, 1, 7)) == (2024, 1, 7)


def test_monday_2024_01_08():
    assert iso_week(dt.date(2024, 1, 8)) == (2024, 2, 1)


def test_sunday_2023_01_01_is_iso_2022_week_52():
    assert iso_week(dt.date(2023, 1, 1)) == (2022, 52, 7)


def test_tuesday_2024_12_31_is_iso_2025_week_1():
    assert iso_week(dt.date(2024, 12, 31)) == (2025, 1, 2)


def test_thursday_2020_12_31_is_week_53():
    assert iso_week(dt.date(2020, 12, 31)) == (2020, 53, 4)


def test_non_date_raises_typeerror():
    with pytest.raises(TypeError):
        iso_week("2024-01-01")
