"""Hand-authored placeholder suite for 021-dedupe."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
dedupe = _impl.dedupe


def test_empty_list_returns_empty_list():
    assert dedupe([]) == []


def test_all_unique_unchanged():
    assert dedupe([1, 2, 3]) == [1, 2, 3]


def test_adjacent_duplicates_collapse():
    assert dedupe([1, 1, 2, 3]) == [1, 2, 3]


def test_non_adjacent_duplicates_first_kept():
    assert dedupe([3, 1, 2, 1, 3]) == [3, 1, 2]


def test_order_of_first_occurrences_preserved():
    assert dedupe(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]


def test_int_and_str_with_same_repr_stay_distinct():
    # 1 and "1" are different objects; they should NOT collapse.
    assert dedupe([1, "1"]) == [1, "1"]


def test_non_list_raises_typeerror():
    with pytest.raises(TypeError):
        dedupe("abc")


def test_unhashable_elements_raise_typeerror():
    with pytest.raises(TypeError):
        dedupe([[1], [1]])
