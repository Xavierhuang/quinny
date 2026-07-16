"""Held-out suite for the `cidr` task — never shown to the generator.

`Network("a.b.c.d/n")` for IPv4: `contains(ip)`, `overlaps(other)`,
`num_addresses()`, `broadcast()`. Host-bit masking, /31 & /32, and overlap
symmetry are the edges a one-shot tends to miss.
"""
import pytest

from cidr import Network


def test_contains_basic():
    n = Network("10.0.0.0/8")
    assert n.contains("10.5.6.7") is True
    assert n.contains("11.0.0.0") is False


def test_host_bits_are_masked():
    # host bits in the network string are ignored — .130/24 means the .0/24 block
    n = Network("192.168.1.130/24")
    assert n.contains("192.168.1.1") is True
    assert n.contains("192.168.2.1") is False


def test_slash_32_single_host():
    n = Network("1.2.3.4/32")
    assert n.contains("1.2.3.4") is True
    assert n.contains("1.2.3.5") is False
    assert n.num_addresses() == 1


def test_slash_31_two_addresses():
    assert Network("1.2.3.4/31").num_addresses() == 2


def test_num_addresses():
    assert Network("192.168.1.0/24").num_addresses() == 256
    assert Network("10.0.0.0/8").num_addresses() == 16777216


def test_broadcast():
    assert Network("192.168.1.0/24").broadcast() == "192.168.1.255"
    assert Network("10.0.0.0/8").broadcast() == "10.255.255.255"


def test_overlaps_containment():
    assert Network("10.0.0.0/8").overlaps(Network("10.1.0.0/16")) is True
    assert Network("10.1.0.0/16").overlaps(Network("10.0.0.0/8")) is True  # symmetric


def test_overlaps_disjoint():
    assert Network("10.0.0.0/24").overlaps(Network("11.0.0.0/24")) is False


def test_invalid_raises():
    for bad in ["1.2.3.4/33", "999.0.0.0/8", "1.2.3/24", "1.2.3.4", "1.2.3.4/-1"]:
        with pytest.raises(ValueError):
            Network(bad)
