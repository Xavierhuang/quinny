"""Hand-authored placeholder suite for 018-elevator."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
Elevator = _impl.Elevator


def test_fresh_state():
    e = Elevator(5)
    assert e.current_floor == 1
    assert e.direction == "IDLE"
    assert e.pending == 0


def test_request_sets_up_direction():
    e = Elevator(5); e.request(3)
    assert e.direction == "UP"
    assert e.pending == 1


def test_tick_advances_one_floor_up():
    e = Elevator(5); e.request(3); e.tick()
    assert e.current_floor == 2


def test_reaching_target_pops_it():
    e = Elevator(5); e.request(3)
    e.tick(); e.tick()
    assert e.current_floor == 3
    assert e.pending == 0


def test_no_pending_becomes_idle():
    e = Elevator(5); e.request(3)
    e.tick(); e.tick()
    assert e.direction == "IDLE"


def test_duplicate_requests_do_not_stack():
    e = Elevator(5); e.request(3); e.request(3)
    assert e.pending == 1


def test_fifo_serves_first_request_first():
    e = Elevator(5); e.request(5); e.request(2)
    for _ in range(4):
        e.tick()
    assert e.current_floor == 5
    assert e.pending == 1


def test_fifo_continues_to_second_request():
    e = Elevator(5); e.request(5); e.request(2)
    for _ in range(7):
        e.tick()
    assert e.current_floor == 2
    assert e.pending == 0


def test_request_zero_raises_valueerror():
    with pytest.raises(ValueError):
        Elevator(5).request(0)


def test_request_above_max_raises_valueerror():
    with pytest.raises(ValueError):
        Elevator(5).request(6)


def test_single_floor_elevator_raises_valueerror():
    with pytest.raises(ValueError):
        Elevator(1)


def test_non_int_floors_raises_typeerror():
    with pytest.raises(TypeError):
        Elevator("5")
