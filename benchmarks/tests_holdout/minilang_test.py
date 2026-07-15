"""Held-out acceptance suite for the `minilang` scale task.

NEVER shown to the generator. A small expression-language interpreter with a
single pinned entry point: `evaluate(source: str)` in `minilang.py`. This is a
genuinely multi-module task (lexer, parser, AST, environment, evaluator,
builtins) — the regime where decomposition could plausibly help a weak model.
"""
import pytest

from minilang import evaluate


# --- literals & arithmetic ----------------------------------------------

def test_int_literal():
    assert evaluate("42") == 42

def test_arithmetic_precedence():
    assert evaluate("2 + 3 * 4") == 14

def test_parentheses():
    assert evaluate("(2 + 3) * 4") == 20

def test_float_division():
    assert evaluate("7 / 2") == 3.5

def test_modulo():
    assert evaluate("7 % 3") == 1

def test_unary_minus():
    assert evaluate("-5 + 2") == -3


# --- strings & booleans -------------------------------------------------

def test_string_concat():
    assert evaluate('"a" + "b"') == "ab"

def test_comparison():
    assert evaluate("3 <= 3") is True
    assert evaluate("2 > 5") is False

def test_boolean_and_or_not():
    assert evaluate("1 == 1 and 2 == 3") is False
    assert evaluate("1 == 1 or 2 == 3") is True
    assert evaluate("not (1 == 2)") is True


# --- let bindings -------------------------------------------------------

def test_let_binding():
    assert evaluate("let x = 5; x * 2") == 10

def test_multiple_lets():
    assert evaluate("let x = 5; let y = x + 1; y * y") == 36


# --- if expression ------------------------------------------------------

def test_if_expression():
    assert evaluate("if 2 > 1 then 10 else 20") == 10
    assert evaluate("if 2 < 1 then 10 else 20") == 20


# --- functions & closures ----------------------------------------------

def test_function_call():
    assert evaluate("let add = fn(a, b) => a + b; add(3, 4)") == 7

def test_closure_captures_env():
    assert evaluate("let x = 10; let g = fn(n) => n + x; g(5)") == 15

def test_higher_order():
    assert evaluate(
        "let twice = fn(f, v) => f(f(v)); let inc = fn(n) => n + 1; twice(inc, 10)"
    ) == 12


# --- builtins -----------------------------------------------------------

def test_builtin_len_and_abs():
    assert evaluate('len("hello")') == 5
    assert evaluate("abs(0 - 7)") == 7


# --- errors -------------------------------------------------------------

def test_undefined_variable_raises():
    with pytest.raises(NameError):
        evaluate("nope")

def test_division_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        evaluate("1 / 0")
