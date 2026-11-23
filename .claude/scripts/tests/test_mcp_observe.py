"""mcp-observe.sh（G13 / 规则清单 K4）：MCP 调用只记审计，任何情况都不拦。

真实跑 hook（bash → python dispatcher --observe-mcp），审计写到临时文件。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / ".claude" / "hooks" / "mcp-observe.sh"
BASH = shutil.which("bash") or "/bin/bash"


def _run(payload: str, tmp_path: Path, path_env: str | None = None):
    log = tmp_path / "audit.log"
    env = dict(os.environ, HARNESS_AUDIT_LOG_PATH=str(log))
    env.pop("HARNESS_BYPASS", None)
    if path_env is not None:
        env["PATH"] = path_env
    p = subprocess.run([BASH, str(HOOK)], input=payload, capture_output=True, text=True, env=env, cwd=tmp_path, timeout=20)
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
    return p, entries


def _payload(tool: str, tool_input) -> str:
    return json.dumps({"tool_name": tool, "tool_input": tool_input, "permission_mode": "default"})


def test_logs_call_and_allows(tmp_path):
    p, entries = _run(_payload("mcp__mysql-readonly__mysql_query", {"sql": "SELECT 1"}), tmp_path)
    assert p.returncode == 0
    assert p.stdout == ""  # 不输出 permissionDecision，不影响原生权限流程
    assert len(entries) == 1
    e = entries[0]
    assert (e["hook"], e["action"], e["tool"]) == ("PreToolUse", "mcp_call", "mcp__mysql-readonly__mysql_query")
    assert e["target"] == '{"sql": "SELECT 1"}'
    assert e["permission_mode"] == "default"


def test_does_not_evaluate_rules(tmp_path):
    # 内容即使命中黑名单写法也只记录：本 hook 不做门禁
    p, entries = _run(_payload("mcp__x__run", {"command": "rm -rf /"}), tmp_path)
    assert p.returncode == 0 and p.stdout == ""
    assert [e["action"] for e in entries] == ["mcp_call"]


def test_target_truncated(tmp_path):
    _, entries = _run(_payload("mcp__gitnexus__query", {"query": "x" * 500}), tmp_path)
    assert len(entries[0]["target"]) == 200


@pytest.mark.parametrize("payload", ["not json", "[]", ""])
def test_bad_payload_is_allowed(tmp_path, payload):
    p, entries = _run(payload, tmp_path)
    assert p.returncode == 0 and p.stdout == ""
    assert entries == []


def test_no_python_is_allowed(tmp_path):
    # 与 pre-tool-use.sh 的 fail-closed 相反：观测失效不能变成拦截
    p, entries = _run(_payload("mcp__x__y", {}), tmp_path, path_env=str(tmp_path / "empty-bin"))
    assert p.returncode == 0 and p.stdout == ""
    assert entries == []


def test_registered_in_settings():
    pre = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    by_cmd = {h["command"]: m["matcher"] for m in pre for h in m["hooks"]}
    mcp_matcher = by_cmd["bash .claude/hooks/mcp-observe.sh"]
    gate_matcher = by_cmd["bash .claude/hooks/pre-tool-use.sh"]
    for name in ("mcp__gitnexus__rename", "mcp__mysql-readonly__mysql_query"):
        assert re.fullmatch(mcp_matcher, name)
        assert not re.fullmatch(gate_matcher, name)  # MCP 不进门禁：缺 PyYAML 时 fail-closed 不该波及 MCP
    assert not re.fullmatch(mcp_matcher, "Bash")
