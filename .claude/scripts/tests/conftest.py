"""pytest 共享夹具：加载带连字符文件名的脚本模块。

.claude/scripts/ 下脚本名带连字符（policy-dispatch.py），无法用普通 import，
统一走 importlib.util.spec_from_file_location 加载，作为夹具暴露给测试。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent


def _load_module(filename: str, mod_name: str):
    path = SCRIPTS_DIR / filename
    spec = importlib.util.spec_from_file_location(mod_name, path)
    assert spec and spec.loader, f"cannot build spec for {path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def policy_dispatch():
    return _load_module("policy-dispatch.py", "policy_dispatch_under_test")


@pytest.fixture(scope="session")
def session_state():
    return _load_module("session-state.py", "session_state_under_test")
