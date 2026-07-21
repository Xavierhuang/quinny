"""Hand-authored placeholder suite for 015-interval-merge."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
merge_intervals = _impl.merge_intervals


def test_empty_input():
    assert merge_intervals([]) == []


def test_single_interval_unchanged():
    assert merge_intervals([[1, 3]]) == [[1, 3]]


def test_two_overlapping_merge():
    assert merge_intervals([[1, 4], [2, 5]]) == [[1, 5]]


def test_two_touching_merge():
    assert merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]


def test_gap_yields_two_intervals():
    assert merge_intervals([[1, 3], [5, 8]]) == [[1, 3], [5, 8]]


def test_unsorted_input_is_sorted_before_merging():
    assert merge_intervals([[5, 10], [1, 3]]) == [[1, 3], [5, 10]]


def test_canonical_leetcode_example():
    assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == \
        [[1, 6], [8, 10], [15, 18]]


def test_non_list_raises_typeerror():
    with pytest.raises(TypeError):
        merge_intervals("nope")


def test_start_gt_end_raises_valueerror():
    with pytest.raises(ValueError):
        merge_intervals([[5, 3]])


def test_non_pair_sublist_raises_valueerror():
    with pytest.raises(ValueError):
        merge_intervals([[1, 2, 3]])
