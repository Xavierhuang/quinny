"""Hand-authored placeholder suite for 037-pivot-table."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
pivot = _impl.pivot


def test_empty_rows_returns_empty_dict():
    assert pivot([], "r", "c", "v", "sum") == {}


def test_single_row():
    rows = [{"r": "A", "c": "X", "v": 5}]
    assert pivot(rows, "r", "c", "v", "sum") == {"A": {"X": 5}}


def test_multiple_rows_same_cell_sum():
    rows = [{"r": "A", "c": "X", "v": 5}, {"r": "A", "c": "X", "v": 3}]
    assert pivot(rows, "r", "c", "v", "sum") == {"A": {"X": 8}}


def test_count_ignores_value():
    rows = [{"r": "A", "c": "X", "v": 1000}, {"r": "A", "c": "X", "v": 999}]
    assert pivot(rows, "r", "c", "v", "count") == {"A": {"X": 2}}


def test_max_aggregation():
    rows = [{"r": "A", "c": "X", "v": 5}, {"r": "A", "c": "X", "v": 12}, {"r": "A", "c": "X", "v": 3}]
    assert pivot(rows, "r", "c", "v", "max") == {"A": {"X": 12}}


def test_min_aggregation():
    rows = [{"r": "A", "c": "X", "v": 5}, {"r": "A", "c": "X", "v": 12}, {"r": "A", "c": "X", "v": 3}]
    assert pivot(rows, "r", "c", "v", "min") == {"A": {"X": 3}}


def test_different_row_and_col_keys_split():
    rows = [
        {"r": "A", "c": "X", "v": 1},
        {"r": "A", "c": "Y", "v": 2},
        {"r": "B", "c": "X", "v": 3},
    ]
    assert pivot(rows, "r", "c", "v", "sum") == {
        "A": {"X": 1, "Y": 2},
        "B": {"X": 3},
    }


def test_row_missing_key_raises_keyerror():
    with pytest.raises(KeyError):
        pivot([{"r": "A", "c": "X"}], "r", "c", "v", "sum")


def test_non_list_raises_typeerror():
    with pytest.raises(TypeError):
        pivot({}, "r", "c", "v", "sum")


def test_unknown_agg_raises_valueerror():
    with pytest.raises(ValueError):
        pivot([{"r": "A", "c": "X", "v": 1}], "r", "c", "v", "median")
