"""Hand-authored placeholder suite for 023-topo-sort."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
topo_sort = _impl.topo_sort


def test_empty_dict():
    assert topo_sort({}) == []


def test_single_node_no_deps():
    assert topo_sort({"a": []}) == ["a"]


def test_a_depends_on_b():
    assert topo_sort({"a": ["b"], "b": []}) == ["b", "a"]


def test_chain_a_b_c():
    assert topo_sort({"a": ["b"], "b": ["c"], "c": []}) == ["c", "b", "a"]


def test_diamond():
    # a -> b -> d, a -> c -> d. Alpha tie-break: b before c after d.
    assert topo_sort({"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}) == \
        ["d", "b", "c", "a"]


def test_implicit_leaf():
    # b is not a key; treat it as a leaf with no deps.
    assert topo_sort({"a": ["b"]}) == ["b", "a"]


def test_independent_nodes_sort_alphabetically():
    assert topo_sort({"b": [], "a": []}) == ["a", "b"]


def test_cycle_raises_valueerror():
    with pytest.raises(ValueError):
        topo_sort({"a": ["b"], "b": ["a"]})


def test_self_loop_raises_valueerror():
    with pytest.raises(ValueError):
        topo_sort({"a": ["a"]})


def test_non_dict_raises_typeerror():
    with pytest.raises(TypeError):
        topo_sort([("a", [])])
