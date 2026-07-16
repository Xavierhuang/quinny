"""Held-out acceptance tests for the cron next-fire-time task.

Entrypoint: cron.py exposing class Cron with next_times(after_iso, n).
"""
import pytest


def _c(expr):
    from cron import Cron
    return Cron(expr)


def test_every_15_minutes():
    assert _c("*/15 * * * *").next_times("2024-01-01T00:07:00", 3) == [
        "2024-01-01T00:15:00", "2024-01-01T00:30:00", "2024-01-01T00:45:00"]


def test_daily_midnight():
    assert _c("0 0 * * *").next_times("2024-03-10T12:00:00", 2) == [
        "2024-03-11T00:00:00", "2024-03-12T00:00:00"]


def test_first_of_month():
    assert _c("0 0 1 * *").next_times("2024-01-15T00:00:00", 2) == [
        "2024-02-01T00:00:00", "2024-03-01T00:00:00"]


def test_dom_dow_or_rule():
    # "0 0 1 * 1" = midnight on (the 1st) OR (a Monday). Feb 1 2024 is a
    # Thursday (fires via DOM); Feb 5/12 are Mondays (fire via DOW).
    assert _c("0 0 1 * 1").next_times("2024-01-29T12:00:00", 3) == [
        "2024-02-01T00:00:00", "2024-02-05T00:00:00", "2024-02-12T00:00:00"]


def test_weekday_only_restricted():
    # dow restricted, dom is * -> only weekdays, no OR-rule.
    assert _c("0 9 * * 1-5").next_times("2024-03-08T12:00:00", 3) == [
        "2024-03-11T09:00:00", "2024-03-12T09:00:00", "2024-03-13T09:00:00"]


def test_step_within_range():
    assert _c("0 0-12/3 * * *").next_times("2024-01-01T00:30:00", 5) == [
        "2024-01-01T03:00:00", "2024-01-01T06:00:00", "2024-01-01T09:00:00",
        "2024-01-01T12:00:00", "2024-01-02T00:00:00"]


def test_list_of_hours():
    assert _c("30 8,12,17 * * *").next_times("2024-01-01T13:00:00", 3) == [
        "2024-01-01T17:30:00", "2024-01-02T08:30:00", "2024-01-02T12:30:00"]


def test_sunday_as_zero():
    assert _c("0 12 * * 0").next_times("2024-03-08T00:00:00", 2) == [
        "2024-03-10T12:00:00", "2024-03-17T12:00:00"]


def test_sunday_as_seven():
    assert _c("0 12 * * 7").next_times("2024-03-08T00:00:00", 1) == [
        "2024-03-10T12:00:00"]


def test_strictly_after():
    # after == a fire time -> that instant does NOT count; next one does.
    assert _c("0 0 * * *").next_times("2024-01-01T00:00:00", 1) == [
        "2024-01-02T00:00:00"]


def test_feb_29_skips_non_leap_years():
    # From Mar 2024, the next Feb 29 skips 2025/26/27 and lands on 2028.
    assert _c("0 0 29 2 *").next_times("2024-03-01T00:00:00", 1) == [
        "2028-02-29T00:00:00"]


def test_invalid_expression_raises():
    with pytest.raises(ValueError):
        _c("0 0 * *")  # only 4 fields
