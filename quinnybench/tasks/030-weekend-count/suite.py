"""Hand-authored placeholder suite for 030-weekend-count."""
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
weekend_count = _impl.weekend_count

MON = dt.date(2026, 7, 20)   # Monday
TUE = dt.date(2026, 7, 21)
WED = dt.date(2026, 7, 22)
FRI = dt.date(2026, 7, 24)
SAT = dt.date(2026, 7, 25)
SUN = dt.date(2026, 7, 26)
NEXT_MON = dt.date(2026, 7, 27)
NEXT_NEXT_MON = dt.date(2026, 8, 3)


def test_mon_to_fri_returns_0():
    assert weekend_count(MON, FRI) == 0


def test_mon_to_sun_returns_2():
    assert weekend_count(MON, SUN) == 2


def test_saturday_alone():
    assert weekend_count(SAT, SAT) == 1


def test_sunday_alone():
    assert weekend_count(SUN, SUN) == 1


def test_sat_to_mon():
    assert weekend_count(SAT, NEXT_MON) == 2


def test_full_week_mon_to_mon():
    assert weekend_count(MON, NEXT_MON) == 2


def test_two_weeks():
    assert weekend_count(MON, NEXT_NEXT_MON) == 4


def test_same_wednesday_twice():
    assert weekend_count(WED, WED) == 0


def test_end_before_start_raises_valueerror():
    with pytest.raises(ValueError):
        weekend_count(FRI, MON)


def test_non_date_start_raises_typeerror():
    with pytest.raises(TypeError):
        weekend_count("2026-07-20", MON)


def test_non_date_end_raises_typeerror():
    with pytest.raises(TypeError):
        weekend_count(MON, "2026-07-21")
