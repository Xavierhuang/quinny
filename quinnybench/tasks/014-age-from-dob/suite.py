"""Hand-authored placeholder suite for 014-age-from-dob."""
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
age_as_of = _impl.age_as_of


def test_same_day_birth_is_zero():
    assert age_as_of(dt.date(2000, 6, 15), dt.date(2000, 6, 15)) == 0


def test_age_increments_on_birthday():
    assert age_as_of(dt.date(2000, 6, 15), dt.date(2026, 6, 15)) == 26


def test_day_before_birthday_is_pre_increment():
    assert age_as_of(dt.date(2000, 6, 15), dt.date(2026, 6, 14)) == 25


def test_full_year_prior_to_birthday():
    assert age_as_of(dt.date(2000, 1, 1), dt.date(2025, 12, 31)) == 25


def test_leap_dob_increments_on_march_1_in_non_leap_year():
    # 2026 is not a leap year — Feb 29 doesn't exist, so the birthday
    # is considered to happen on Mar 1.
    assert age_as_of(dt.date(2000, 2, 29), dt.date(2026, 3, 1)) == 26


def test_leap_dob_still_pre_increment_on_feb_28():
    assert age_as_of(dt.date(2000, 2, 29), dt.date(2026, 2, 28)) == 25


def test_future_dob_raises_valueerror():
    with pytest.raises(ValueError):
        age_as_of(dt.date(2030, 1, 1), dt.date(2026, 1, 1))


def test_non_date_dob_raises_typeerror():
    with pytest.raises(TypeError):
        age_as_of("2000-06-15", dt.date(2026, 6, 15))


def test_non_date_as_of_raises_typeerror():
    with pytest.raises(TypeError):
        age_as_of(dt.date(2000, 6, 15), "2026-06-15")
