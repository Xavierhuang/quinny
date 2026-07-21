"""Hand-authored placeholder suite for 031-window-max."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
window_max = _impl.window_max


def test_classic_leetcode_example():
    assert window_max([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]


def test_k_1_returns_copy():
    assert window_max([1, 2, 3, 4], 1) == [1, 2, 3, 4]


def test_k_equal_len_returns_single_max():
    assert window_max([1, 5, 3, 2], 4) == [5]


def test_single_element_k_1():
    assert window_max([42], 1) == [42]


def test_all_equal():
    assert window_max([7, 7, 7, 7], 2) == [7, 7, 7]


def test_k_zero_raises_valueerror():
    with pytest.raises(ValueError):
        window_max([1, 2, 3], 0)


def test_k_greater_than_len_raises_valueerror():
    with pytest.raises(ValueError):
        window_max([1, 2, 3], 4)


def test_empty_nums_raises_valueerror():
    with pytest.raises(ValueError):
        window_max([], 1)


def test_non_list_raises_typeerror():
    with pytest.raises(TypeError):
        window_max("abc", 1)


def test_non_int_k_raises_typeerror():
    with pytest.raises(TypeError):
        window_max([1, 2, 3], 1.0)
