"""Hand-authored placeholder suite for 003-traffic-light."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
TrafficLight = _impl.TrafficLight


def test_fresh_light_is_red():
    assert TrafficLight().current() == "RED"


def test_one_tick_yields_green():
    t = TrafficLight()
    t.tick()
    assert t.current() == "GREEN"


def test_two_ticks_yield_yellow():
    t = TrafficLight()
    t.tick(); t.tick()
    assert t.current() == "YELLOW"


def test_three_ticks_return_to_red():
    t = TrafficLight()
    t.tick(); t.tick(); t.tick()
    assert t.current() == "RED"


def test_seven_ticks_yield_green():
    t = TrafficLight()
    for _ in range(7):
        t.tick()
    assert t.current() == "GREEN"


def test_reset_from_yellow_returns_to_red():
    t = TrafficLight()
    t.tick(); t.tick()
    assert t.current() == "YELLOW"
    t.reset()
    assert t.current() == "RED"


def test_reset_from_red_stays_red():
    t = TrafficLight()
    t.reset()
    assert t.current() == "RED"


def test_constructor_with_arg_raises_typeerror():
    with pytest.raises(TypeError):
        TrafficLight("RED")
