"""Hand-authored placeholder suite for 004-semver-parse."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
parse_semver = _impl.parse_semver


def test_1_0_0():
    assert parse_semver("1.0.0") == {
        "major": 1, "minor": 0, "patch": 0,
        "prerelease": None, "buildmetadata": None,
    }


def test_1_2_3():
    assert parse_semver("1.2.3") == {
        "major": 1, "minor": 2, "patch": 3,
        "prerelease": None, "buildmetadata": None,
    }


def test_prerelease_alpha():
    r = parse_semver("1.2.3-alpha")
    assert r["prerelease"] == "alpha"
    assert r["buildmetadata"] is None


def test_prerelease_alpha_1():
    r = parse_semver("1.2.3-alpha.1")
    assert r["prerelease"] == "alpha.1"


def test_buildmetadata_build_5():
    r = parse_semver("1.2.3+build.5")
    assert r["buildmetadata"] == "build.5"
    assert r["prerelease"] is None


def test_prerelease_and_buildmetadata():
    r = parse_semver("1.2.3-rc.1+meta")
    assert r["prerelease"] == "rc.1"
    assert r["buildmetadata"] == "meta"


def test_leading_zero_raises_valueerror():
    with pytest.raises(ValueError):
        parse_semver("01.2.3")


def test_missing_patch_raises_valueerror():
    with pytest.raises(ValueError):
        parse_semver("1.2")


def test_trailing_dot_after_patch_raises_valueerror():
    with pytest.raises(ValueError):
        parse_semver("1.2.3.")


def test_empty_string_raises_valueerror():
    with pytest.raises(ValueError):
        parse_semver("")


def test_non_string_raises_typeerror():
    with pytest.raises(TypeError):
        parse_semver(123)
