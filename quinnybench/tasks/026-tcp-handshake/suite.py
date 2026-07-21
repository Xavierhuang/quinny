"""Hand-authored placeholder suite for 026-tcp-handshake."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
TCPConnection = _impl.TCPConnection


def test_fresh_is_closed():
    assert TCPConnection().state == "CLOSED"


def test_open_moves_to_syn_sent():
    c = TCPConnection(); c.open()
    assert c.state == "SYN_SENT"


def test_syn_ack_moves_to_established():
    c = TCPConnection(); c.open(); c.syn_ack()
    assert c.state == "ESTABLISHED"


def test_close_from_established_moves_to_closed():
    c = TCPConnection(); c.open(); c.syn_ack(); c.close()
    assert c.state == "CLOSED"


def test_full_cycle_returns_to_closed():
    c = TCPConnection(); c.open(); c.syn_ack(); c.close()
    assert c.state == "CLOSED"


def test_syn_ack_from_closed_raises():
    with pytest.raises(RuntimeError):
        TCPConnection().syn_ack()


def test_close_from_closed_raises():
    with pytest.raises(RuntimeError):
        TCPConnection().close()


def test_open_from_syn_sent_raises():
    c = TCPConnection(); c.open()
    with pytest.raises(RuntimeError):
        c.open()


def test_open_from_established_raises():
    c = TCPConnection(); c.open(); c.syn_ack()
    with pytest.raises(RuntimeError):
        c.open()


def test_close_from_syn_sent_raises():
    c = TCPConnection(); c.open()
    with pytest.raises(RuntimeError):
        c.close()


def test_constructor_with_arg_raises_typeerror():
    with pytest.raises(TypeError):
        TCPConnection("CLOSED")
