"""Held-out suite for the `money` task — never shown to the generator.

`allocate(total, weights)` splits an integer amount proportionally with the
largest-remainder (Hamilton) method: the result must SUM EXACTLY to total, extra
units go to the largest fractional remainders, ties broken by lower index. The
sum-invariant + tie-breaking is a classic one-shot miss (naive rounding loses or
gains a cent).
"""
import pytest

from money import allocate


def test_even_split_exact():
    assert allocate(100, [1, 1, 1]) == [34, 33, 33]


def test_sum_invariant_always():
    for total, weights in [(100, [1, 1, 1]), (7, [1, 1, 1]), (101, [1, 1, 1]),
                           (10, [7, 3]), (55, [2, 3, 5]), (1, [1, 1, 1, 1])]:
        assert sum(allocate(total, weights)) == total


def test_exact_division():
    assert allocate(5, [1, 1, 1, 1, 1]) == [1, 1, 1, 1, 1]
    assert allocate(10, [7, 3]) == [7, 3]


def test_remainder_goes_to_largest_then_lowest_index():
    # 7/3: base 2,2,2 (sum 6), remainder 1, all fractions equal → lowest index
    assert allocate(7, [1, 1, 1]) == [3, 2, 2]
    # 101/3: base 33,33,33 (sum 99), remainder 2 → first two indices
    assert allocate(101, [1, 1, 1]) == [34, 34, 33]


def test_two_way_tie_to_lower_index():
    # 3 split 1:1 → 1.5 each, remainder 1 → lower index
    assert allocate(3, [1, 1]) == [2, 1]


def test_zero_weight_gets_nothing():
    assert allocate(100, [0, 1]) == [0, 100]


def test_zero_total():
    assert allocate(0, [1, 1]) == [0, 0]


def test_proportional():
    assert allocate(100, [1, 2, 1]) == [25, 50, 25]


def test_invalid_raises():
    for total, weights in [(100, []), (100, [0, 0]), (100, [-1, 1]), (-1, [1, 1])]:
        with pytest.raises(ValueError):
            allocate(total, weights)
