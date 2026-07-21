"""Hand-authored placeholder suite for 038-format-duration."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
format_duration = _impl.format_duration


def test_zero_returns_0s():
    assert format_duration(0) == "0s"


def test_one_second():
    assert format_duration(1) == "1s"


def test_one_minute():
    assert format_duration(60) == "1m"


def test_one_hour():
    assert format_duration(3600) == "1h"


def test_one_day():
    assert format_duration(86400) == "1d"


def test_1h_1m_1s():
    assert format_duration(3661) == "1h 1m 1s"


def test_1d_no_hours():
    # 86461 = 1 day + 1 minute + 1 second → no "0h" gap.
    assert format_duration(86461) == "1d 1m 1s"


def test_1d_1h_1m_1s():
    assert format_duration(90061) == "1d 1h 1m 1s"


def test_59_seconds():
    assert format_duration(59) == "59s"


def test_59m_59s():
    assert format_duration(3599) == "59m 59s"


def test_negative_raises_valueerror():
    with pytest.raises(ValueError):
        format_duration(-1)


def test_non_int_raises_typeerror():
    with pytest.raises(TypeError):
        format_duration(1.5)
