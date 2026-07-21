"""Hand-authored placeholder suite for 013-group-by."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
group_by = _impl.group_by


def test_empty_list_returns_empty_dict():
    assert group_by([], "x") == {}


def test_single_row_forms_one_group():
    assert group_by([{"x": 1, "y": "a"}], "x") == {1: [{"x": 1, "y": "a"}]}


def test_two_rows_sharing_key_land_in_same_group():
    rows = [{"x": 1, "y": "a"}, {"x": 1, "y": "b"}]
    assert group_by(rows, "x") == {1: [{"x": 1, "y": "a"}, {"x": 1, "y": "b"}]}


def test_distinct_key_values_split_into_groups():
    rows = [{"x": 1, "y": "a"}, {"x": 2, "y": "b"}, {"x": 1, "y": "c"}]
    assert group_by(rows, "x") == {
        1: [{"x": 1, "y": "a"}, {"x": 1, "y": "c"}],
        2: [{"x": 2, "y": "b"}],
    }


def test_row_missing_key_raises_keyerror():
    with pytest.raises(KeyError):
        group_by([{"x": 1}, {"y": 2}], "x")


def test_non_list_rows_raises_typeerror():
    with pytest.raises(TypeError):
        group_by({"x": 1}, "x")


def test_non_string_key_raises_typeerror():
    with pytest.raises(TypeError):
        group_by([{"x": 1}], 123)
