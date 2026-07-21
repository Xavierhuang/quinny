"""Hand-authored placeholder suite for 029-top-k."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
top_k = _impl.top_k


def test_empty_list_returns_empty():
    assert top_k([], 3) == []


def test_k_zero_returns_empty():
    assert top_k([1, 2, 3], 0) == []


def test_classic_case():
    assert top_k([3, 1, 4, 1, 5, 9, 2, 6], 3) == [9, 6, 5]


def test_k_greater_than_length_returns_all_sorted_desc():
    assert top_k([1, 2, 3], 10) == [3, 2, 1]


def test_ties_preserve_first_occurrence_order():
    # Two 5s: the first-seen one comes first in the result.
    tagged = [(5, "a"), (3, "b"), (5, "c")]
    result = top_k(tagged, 2, key=lambda t: t[0])
    assert result == [(5, "a"), (5, "c")]


def test_custom_key_function():
    items = [{"n": 3}, {"n": 1}, {"n": 5}]
    assert top_k(items, 2, key=lambda d: d["n"]) == [{"n": 5}, {"n": 3}]


def test_negative_k_raises_valueerror():
    with pytest.raises(ValueError):
        top_k([1, 2, 3], -1)


def test_non_int_k_raises_typeerror():
    with pytest.raises(TypeError):
        top_k([1, 2, 3], 1.5)


def test_non_list_items_raises_typeerror():
    with pytest.raises(TypeError):
        top_k("abc", 2)
