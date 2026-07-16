"""Held-out suite for the `globmatch` task — never shown to the generator.

`matches(pattern, text)` is a whole-string glob: `*` any run (incl. empty), `?`
exactly one char, `[...]` char class with ranges and `[!..]`/`[^..]` negation,
and `\\` escapes the next metachar. Negation classes, escaped metachars, and the
whole-string anchoring are the edges a one-shot tends to miss.
"""
import pytest

from globmatch import matches


def test_star_runs():
    assert matches("a*c", "abbbc") is True
    assert matches("a*c", "ac") is True          # * matches empty
    assert matches("a*c", "ab") is False


def test_question_single():
    assert matches("a?c", "abc") is True
    assert matches("a?c", "ac") is False          # ? needs exactly one


def test_char_class_range():
    assert matches("[a-c]x", "bx") is True
    assert matches("[a-c]x", "dx") is False


def test_negated_class():
    assert matches("[!a-c]x", "dx") is True
    assert matches("[!a-c]x", "bx") is False
    assert matches("[^0-9]", "a") is True         # ^ negation form too


def test_escaped_metachars():
    assert matches(r"a\*b", "a*b") is True         # literal star
    assert matches(r"a\*b", "axb") is False
    assert matches(r"a\?b", "a?b") is True


def test_whole_string_anchored():
    assert matches("abc", "abcd") is False
    assert matches("abc", "abc") is True


def test_star_edges():
    assert matches("*", "") is True
    assert matches("*", "anything") is True
    assert matches("*.txt", "file.txt") is True
    assert matches("*.txt", "file.md") is False


def test_question_then_star():
    assert matches("?*", "a") is True              # ? = a, * = empty
    assert matches("?*", "") is False


def test_multiple_stars():
    assert matches("a*b*c", "axxbyyc") is True
    assert matches("a*b*c", "axxc") is False
