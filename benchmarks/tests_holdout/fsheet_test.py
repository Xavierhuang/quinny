"""Held-out acceptance tests for the formula-spreadsheet task.

Never shown to the generator; not the verify contract. Grades real behavior.
Entrypoint: fsheet.py exposing class Sheet with set_cell(ref, text) / get_value(ref).
"""


def _s():
    from fsheet import Sheet
    return Sheet()


def test_numeric_literal_and_empty():
    s = _s()
    s.set_cell("A1", "5")
    assert s.get_value("A1") == 5
    assert s.get_value("Z9") == 0  # unset cell is 0


def test_basic_ref_and_add():
    s = _s()
    s.set_cell("A1", "5")
    s.set_cell("A2", "3")
    s.set_cell("A3", "=A1+A2")
    assert s.get_value("A3") == 8


def test_precedence():
    s = _s()
    s.set_cell("A1", "=2+3*4")
    assert s.get_value("A1") == 14


def test_parens_override_precedence():
    s = _s()
    s.set_cell("A1", "=(2+3)*4")
    assert s.get_value("A1") == 20


def test_unary_minus():
    s = _s()
    s.set_cell("A1", "10")
    s.set_cell("A2", "=-A1+3")
    assert s.get_value("A2") == -7


def test_division_float():
    s = _s()
    s.set_cell("A1", "=7/2")
    assert s.get_value("A1") == 3.5


def test_chained_dependencies():
    s = _s()
    s.set_cell("A1", "2")
    s.set_cell("A2", "=A1*3")
    s.set_cell("A3", "=A2+A1")
    assert s.get_value("A3") == 8


def test_recalc_after_change():
    s = _s()
    s.set_cell("A1", "2")
    s.set_cell("A2", "=A1*10")
    assert s.get_value("A2") == 20
    s.set_cell("A1", "5")
    assert s.get_value("A2") == 50  # must reflect the new dependency value


def test_sum_range_column():
    s = _s()
    s.set_cell("A1", "1")
    s.set_cell("A2", "2")
    s.set_cell("A3", "4")
    s.set_cell("A4", "=SUM(A1:A3)")
    assert s.get_value("A4") == 7


def test_sum_range_counts_empty_as_zero():
    s = _s()
    s.set_cell("A1", "10")
    s.set_cell("A3", "5")  # A2 left empty
    s.set_cell("B1", "=SUM(A1:A3)")
    assert s.get_value("B1") == 15


def test_rectangular_range():
    s = _s()
    for r, v in (("A1", 1), ("A2", 2), ("B1", 3), ("B2", 4)):
        s.set_cell(r, str(v))
    s.set_cell("C1", "=SUM(A1:B2)")
    assert s.get_value("C1") == 10


def test_min_max_avg():
    s = _s()
    s.set_cell("A1", "2")
    s.set_cell("A2", "8")
    s.set_cell("A3", "2")
    s.set_cell("B1", "=MIN(A1:A3)")
    s.set_cell("B2", "=MAX(A1:A3)")
    s.set_cell("B3", "=AVG(A1:A3)")
    assert s.get_value("B1") == 2
    assert s.get_value("B2") == 8
    assert s.get_value("B3") == 4


def test_div_by_zero_direct():
    s = _s()
    s.set_cell("A1", "=5/0")
    assert s.get_value("A1") == "#DIV/0!"


def test_div_by_zero_propagates():
    s = _s()
    s.set_cell("A1", "=1/0")
    s.set_cell("A2", "=A1+1")
    assert s.get_value("A2") == "#DIV/0!"


def test_self_cycle():
    s = _s()
    s.set_cell("A1", "=A1+1")
    assert s.get_value("A1") == "#CYCLE!"


def test_mutual_cycle():
    s = _s()
    s.set_cell("A1", "=B1+1")
    s.set_cell("B1", "=A1+1")
    assert s.get_value("A1") == "#CYCLE!"
    assert s.get_value("B1") == "#CYCLE!"


def test_no_false_cycle_diamond():
    s = _s()
    s.set_cell("A1", "1")
    s.set_cell("B1", "=A1+1")
    s.set_cell("C1", "=A1+2")
    s.set_cell("D1", "=B1+C1")  # references A1 via two paths — NOT a cycle
    assert s.get_value("D1") == 5
