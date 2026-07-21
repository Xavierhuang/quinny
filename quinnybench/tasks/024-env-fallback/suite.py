"""Hand-authored placeholder suite for 024-env-fallback."""
import importlib.util
import os
import sys

import pytest

_IMPL_DIR = os.environ.get("QUINNYBENCH_IMPL_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _IMPL_DIR)
_spec = importlib.util.spec_from_file_location("impl", os.path.join(_IMPL_DIR, "impl.py"))
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)
get_config = _impl.get_config


def test_no_sources_uses_defaults():
    assert get_config([], {}, {"host": "localhost"}) == {"host": "localhost"}


def test_argv_overrides_default():
    assert get_config(["--host=example.com"], {}, {"host": "localhost"}) == \
        {"host": "example.com"}


def test_env_overrides_default():
    assert get_config([], {"HOST": "example.com"}, {"host": "localhost"}) == \
        {"host": "example.com"}


def test_argv_wins_over_env():
    assert get_config(["--host=argv"], {"HOST": "env"}, {"host": "def"}) == \
        {"host": "argv"}


def test_multiple_defaulted_keys():
    assert get_config([], {}, {"host": "localhost", "port": "8080"}) == \
        {"host": "localhost", "port": "8080"}


def test_dashed_key_maps_to_underscored_env():
    assert get_config([], {"LOG_LEVEL": "debug"}, {"log-level": "info"}) == \
        {"log-level": "debug"}


def test_non_list_argv_raises_typeerror():
    with pytest.raises(TypeError):
        get_config("--host=x", {}, {"host": "y"})


def test_non_dict_env_raises_typeerror():
    with pytest.raises(TypeError):
        get_config([], "not-a-dict", {"host": "y"})


def test_non_dict_defaults_raises_typeerror():
    with pytest.raises(TypeError):
        get_config([], {}, "not-a-dict")
