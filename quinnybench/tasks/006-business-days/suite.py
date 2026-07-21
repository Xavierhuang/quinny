"""Hand-authored placeholder suite for 006-business-days."""
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
add_business_days = _impl.add_business_days

# 2026-07-20 = Monday, 2026-07-24 = Friday, 2026-07-25 = Sat, 2026-07-26 = Sun,
# 2026-07-27 = Monday, 2026-07-28 = Tuesday, 2026-07-31 = Friday.
MON = dt.date(2026, 7, 20)
FRI = dt.date(2026, 7, 24)
SAT = dt.date(2026, 7, 25)
SUN = dt.date(2026, 7, 26)
NEXT_MON = dt.date(2026, 7, 27)
NEXT_TUE = dt.date(2026, 7, 28)
NEXT_FRI = dt.date(2026, 7, 31)
PREV_FRI = dt.date(2026, 7, 17)
PREV_WED = dt.date(2026, 7, 15)


def test_zero_returns_weekday_unchanged():
    assert add_business_days(MON, 0) == MON


def test_zero_returns_weekend_unchanged():
    assert add_business_days(SAT, 0) == SAT


def test_friday_plus_one_is_monday():
    assert add_business_days(FRI, 1) == NEXT_MON


def test_friday_plus_two_is_tuesday():
    assert add_business_days(FRI, 2) == NEXT_TUE


def test_friday_plus_five_is_next_friday():
    assert add_business_days(FRI, 5) == NEXT_FRI


def test_saturday_plus_one_is_monday():
    assert add_business_days(SAT, 1) == NEXT_MON


def test_sunday_plus_one_is_monday():
    assert add_business_days(SUN, 1) == NEXT_MON


def test_saturday_plus_two_is_tuesday():
    assert add_business_days(SAT, 2) == NEXT_TUE


def test_monday_minus_one_is_previous_friday():
    assert add_business_days(MON, -1) == PREV_FRI


def test_monday_minus_three_is_previous_wednesday():
    assert add_business_days(MON, -3) == PREV_WED


def test_non_date_raises_typeerror():
    with pytest.raises(TypeError):
        add_business_days("2026-07-20", 1)


def test_non_int_n_raises_typeerror():
    with pytest.raises(TypeError):
        add_business_days(MON, 1.5)
