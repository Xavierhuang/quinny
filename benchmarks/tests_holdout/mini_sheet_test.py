"""Held-out acceptance suite for the `mini_sheet` task.

NEVER shown to the code generator. Imports the produced `mini_sheet.py` and
exercises the pinned public API from benchmarks/prompts/mini_sheet.txt.
"""
import pytest

from mini_sheet import Sheet, CycleError


# --- literals ------------------------------------------------------------

def test_numeric_literal():
    s = Sheet()
    s.set_cell("A1", "5")
    assert s.get_value("A1") == 5


def test_string_literal():
    s = Sheet()
    s.set_cell("A1", "hello")
    assert s.get_value("A1") == "hello"


def test_empty_cell_is_zero():
    s = Sheet()
    assert s.get_value("Z9") == 0


# --- arithmetic ----------------------------------------------------------

def test_formula_add_refs():
    s = Sheet()
    s.set_cell("A1", "2")
    s.set_cell("A2", "3")
    s.set_cell("A3", "=A1+A2")
    assert s.get_value("A3") == 5


def test_operator_precedence():
    s = Sheet()
    s.set_cell("A1", "=2+3*4")
    assert s.get_value("A1") == 14


def test_parentheses():
    s = Sheet()
    s.set_cell("A1", "=(2+3)*4")
    assert s.get_value("A1") == 20


def test_division():
    s = Sheet()
    s.set_cell("A1", "=6/2")
    assert s.get_value("A1") == 3


def test_division_by_zero_raises_valueerror():
    s = Sheet()
    s.set_cell("A1", "=1/0")
    with pytest.raises(ValueError):
        s.get_value("A1")


# --- dependencies + recalculation ---------------------------------------

def test_dependency_propagation():
    s = Sheet()
    s.set_cell("A1", "1")
    s.set_cell("A2", "=A1+1")
    s.set_cell("A3", "=A2+1")
    assert s.get_value("A3") == 3
    s.set_cell("A1", "10")          # must propagate through A2 -> A3
    assert s.get_value("A3") == 12


def test_ref_to_empty_is_zero():
    s = Sheet()
    s.set_cell("A1", "=B5+7")
    assert s.get_value("A1") == 7


# --- SUM range -----------------------------------------------------------

def test_sum_range():
    s = Sheet()
    s.set_cell("A1", "1")
    s.set_cell("A2", "2")
    s.set_cell("A3", "3")
    s.set_cell("B1", "=SUM(A1:A3)")
    assert s.get_value("B1") == 6


def test_sum_rectangular_range():
    s = Sheet()
    for ref in ("A1", "A2", "B1", "B2"):
        s.set_cell(ref, "2")
    s.set_cell("C1", "=SUM(A1:B2)")
    assert s.get_value("C1") == 8


# --- cycle detection -----------------------------------------------------

def test_self_cycle_raises():
    s = Sheet()
    with pytest.raises(CycleError):
        s.set_cell("A1", "=A1")


def test_mutual_cycle_raises_and_is_not_applied():
    s = Sheet()
    s.set_cell("A1", "=B1")         # B1 empty -> A1 == 0 so far
    with pytest.raises(CycleError):
        s.set_cell("B1", "=A1")     # would close the loop
    # The rejected write must not have taken effect.
    assert s.get_value("A1") == 0
