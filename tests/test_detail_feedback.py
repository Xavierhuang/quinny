"""The verify loop feeds back WHAT failed (expected-vs-got), not just THAT it
did — this is what breaks a re-guessing stall. Guards the pytest detail parser."""
from quinny.contract import _detail_pytest, CriterionResult

# A realistic pytest `-v --tb=short` failure section.
SAMPLE = """\
test_c01 PASSED
test_c05 FAILED
test_c08 FAILED

=================================== FAILURES ===================================
_________________________________ test_c05 _________________________________

    def test_c05():
        got = "#ERR!"
>       assert got == "#DIV/0!"
E       AssertionError: assert '#ERR!' == '#DIV/0!'
E         - #DIV/0!
E         + #ERR!

suite.py:44: AssertionError
_________________________________ test_c08 _________________________________

>       assert allocate(100, [1, 1, 1]) == [34, 33, 33]
E       AssertionError: assert [34, 34, 32] == [34, 33, 33]

suite.py:60: AssertionError
"""


def test_detail_extracts_expected_vs_got():
    d = _detail_pytest(SAMPLE)
    assert 5 in d and 8 in d
    assert "'#ERR!' == '#DIV/0!'" in d[5]
    assert "[34, 34, 32] == [34, 33, 33]" in d[8]


def test_no_detail_for_passing_run():
    assert _detail_pytest("test_c01 PASSED\ntest_c02 PASSED\n") == {}


def test_criterion_result_detail_defaults_empty():
    # Old call sites that don't pass detail still work.
    from quinny.contract import Criterion
    r = CriterionResult(Criterion(1, "N", "test", "x"), "PASS")
    assert r.detail == ""
