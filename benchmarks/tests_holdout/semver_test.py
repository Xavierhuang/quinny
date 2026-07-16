"""Held-out suite for the `semver` task — never shown to the generator.

Edge-dense on purpose: numeric-not-lexical ordering, the full prerelease
precedence chain from the semver spec, build-metadata-ignored, and caret/tilde
range semantics (including the caret-pre-1.0 special case). These are exactly the
edges a strong model tends to miss on a single one-shot.
"""
import pytest

from semver import Version, satisfies


def test_parse_basic():
    v = Version("1.2.3")
    assert (v.major, v.minor, v.patch) == (1, 2, 3)


def test_parse_prerelease_and_build():
    v = Version("1.2.3-alpha.1+build.5")
    assert v.prerelease == "alpha.1"


def test_invalid_raises():
    for bad in ["1.2", "1.2.3.4", "a.b.c", "", "1.2.-3"]:
        with pytest.raises(ValueError):
            Version(bad)


def test_numeric_not_lexical():
    # the classic: 1.10.0 is NEWER than 1.2.0 (numeric, not string, compare)
    assert Version("1.2.0") < Version("1.10.0")
    assert Version("1.0.0") < Version("2.0.0")


def test_equality_and_ordering():
    assert Version("1.2.3") == Version("1.2.3")
    assert Version("1.2.4") > Version("1.2.3")


def test_prerelease_lower_than_release():
    assert Version("1.0.0-alpha") < Version("1.0.0")


def test_prerelease_precedence_chain():
    chain = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta",
             "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]
    versions = [Version(s) for s in chain]
    for a, b in zip(versions, versions[1:]):
        assert a < b, f"{a} should be < {b}"


def test_numeric_prerelease_identifiers():
    # numeric identifiers compare numerically: alpha.2 < alpha.11 (not lexical)
    assert Version("1.0.0-alpha.2") < Version("1.0.0-alpha.11")


def test_build_metadata_ignored_in_compare():
    assert Version("1.0.0+build.1") == Version("1.0.0+build.999")


def test_satisfies_exact():
    assert satisfies("1.2.3", "1.2.3") is True
    assert satisfies("1.2.4", "1.2.3") is False


def test_satisfies_gte():
    assert satisfies("1.2.4", ">=1.2.3") is True
    assert satisfies("1.2.2", ">=1.2.3") is False


def test_satisfies_caret_range():
    # ^1.2.3 := >=1.2.3 <2.0.0
    assert satisfies("1.9.9", "^1.2.3") is True
    assert satisfies("2.0.0", "^1.2.3") is False
    assert satisfies("1.2.2", "^1.2.3") is False


def test_satisfies_caret_pre_1_0():
    # ^0.2.3 := >=0.2.3 <0.3.0  (with 0 major, caret locks the MINOR)
    assert satisfies("0.2.9", "^0.2.3") is True
    assert satisfies("0.3.0", "^0.2.3") is False


def test_satisfies_tilde_range():
    # ~1.2.3 := >=1.2.3 <1.3.0
    assert satisfies("1.2.9", "~1.2.3") is True
    assert satisfies("1.3.0", "~1.2.3") is False
