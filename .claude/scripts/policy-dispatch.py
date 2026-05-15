#!/usr/bin/env python
"""
PreToolUse policy dispatcher（P1-A：规则数据外移到 yaml）.

加载 .claude/rules/policies/{deny,ask-user,hints}.yaml，对 stdin payload
评估每条规则；命中即写 audit log + 输出到 stderr + 用对应 exit code 退出。

退出码：
  0  = 通过（包括所有 hint 规则命中后）
  2  = 拦截（deny 或 ask_user 命中）

dispatcher 自身异常永远不应阻断会话 → 兜底 exit 0 + 异常写 audit log。

Bypass：HARNESS_BYPASS=1 时放行黑+灰名单，但仍写 audit log。
Hint 去重：通过 .claude/.session.hints（per-session）。
"""

from __future__ import annotations

import datetime
import fnmatch
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable

# Windows 控制台默认 cp936；stderr/stdout 中文 / emoji 走 utf-8
if sys.platform.startswith("win"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(".")  # 相对仓库根（settings.json 注册的 hook 由 Claude Code 在 cwd 执行）
# audit / hints 走 cwd 相对，与原 hook 保持一致；测试在 tempdir 跑可天然隔离
AUDIT_LOG = ROOT / ".claude" / ".audit.log"
HINTS_FILE = ROOT / ".claude" / ".session.hints"
# policies 走脚本相对，让测试能复用项目的 yaml 而不必复制到 tempdir
POLICIES_DIR = Path(__file__).resolve().parent.parent / "rules" / "policies"


# ---------- audit log ----------

def audit_log(action: str, reason: str, *, tool: str, target: str, bypass: bool = False, rule_id: str = "") -> None:
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "hook": "PreToolUse",
            "tool": tool,
            "target": target[:200],
            "action": action,
            "reason": reason,
            "rule_id": rule_id,
            "bypass": bypass,
        }
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ---------- hint dedup ----------

def hint_already_fired(msg: str) -> bool:
    if not HINTS_FILE.exists():
        return False
    try:
        with open(HINTS_FILE, encoding="utf-8") as f:
            for line in f:
                if line.rstrip("\n") == msg:
                    return True
    except Exception:
        return False
    return False


def remember_hint(msg: str) -> None:
    try:
        HINTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HINTS_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


# ---------- predicate evaluators ----------

def _as_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    return list(v)


def matches_when(when: dict, *, cmd: str, file_path: str, file_basename: str, new_content: str) -> bool:
    """All conditions AND. Missing condition => True."""
    if not isinstance(when, dict):
        return False

    # cmd_contains_any: substring OR
    needles = _as_list(when.get("cmd_contains_any"))
    if needles:
        if not cmd or not any(n in cmd for n in needles):
            return False

    # cmd_matches: ERE
    pat = when.get("cmd_matches")
    if pat:
        if not cmd or not re.search(pat, cmd):
            return False

    # cmd_imatches: ERE case-insensitive
    pat = when.get("cmd_imatches")
    if pat:
        if not cmd or not re.search(pat, cmd, re.IGNORECASE):
            return False

    # file_basename_in: exact OR
    bases = _as_list(when.get("file_basename_in"))
    if bases:
        if file_basename not in bases:
            return False

    # file_basename_glob: glob OR (e.g. "*.key", ".env.*")
    globs = _as_list(when.get("file_basename_glob"))
    if globs:
        if not file_basename or not any(fnmatch.fnmatchcase(file_basename, g) for g in globs):
            return False

    # file_basename_not_in: 白名单豁免（must NOT be in this list）
    excludes = _as_list(when.get("file_basename_not_in"))
    if excludes and file_basename in excludes:
        return False

    # file_basename_matches: ERE
    pat = when.get("file_basename_matches")
    if pat:
        if not file_basename or not re.search(pat, file_basename):
            return False

    # file_path_matches: ERE
    pat = when.get("file_path_matches")
    if pat:
        if not file_path or not re.search(pat, file_path):
            return False

    # new_content_imatches: case-insensitive ERE on edit content
    pat = when.get("new_content_imatches")
    if pat:
        if not new_content or not re.search(pat, new_content, re.IGNORECASE):
            return False

    # new_content_present: special — trigger when content empty
    npresent = when.get("new_content_present")
    if npresent is False:
        if new_content:
            return False
    elif npresent is True:
        if not new_content:
            return False

    return True


def tool_matches(rule_tool: Any, actual_tool: str) -> bool:
    if not rule_tool or not actual_tool:
        return False
    if isinstance(rule_tool, str):
        return rule_tool == actual_tool
    return actual_tool in rule_tool


# ---------- rule loading ----------

def load_rules(filename: str) -> list[dict]:
    path = POLICIES_DIR / filename
    if not path.exists():
        return []
    try:
        import yaml  # type: ignore
    except ImportError:
        audit_log("error", f"PyYAML missing — cannot load {filename}", tool="-", target=str(path))
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        if not isinstance(data, list):
            audit_log("error", f"{filename} top-level must be list", tool="-", target=str(path))
            return []
        return [r for r in data if isinstance(r, dict)]
    except Exception as e:
        audit_log("error", f"failed to parse {filename}: {e}", tool="-", target=str(path))
        return []


# ---------- main ----------

def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception:
        # 非法 payload — 不阻断会话
        return 0

    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    cmd = str(tool_input.get("command") or "")
    file_path = str(tool_input.get("file_path") or "")
    file_basename = os.path.basename(file_path) if file_path else ""
    new_content = str(tool_input.get("new_string") or tool_input.get("content") or "")

    target_for_log = file_path or cmd or ""

    # Bypass：放行所有规则但写审计
    if os.environ.get("HARNESS_BYPASS") == "1":
        audit_log("bypass", "HARNESS_BYPASS=1 in env", tool=tool_name, target=target_for_log, bypass=True)
        print("[pre-tool-use] ⚠️⚠️⚠️ BYPASS ACTIVE — 黑+灰名单全部放行，仅记录审计 ⚠️⚠️⚠️", file=sys.stderr)
        print("[pre-tool-use] 这不应是常态。CI 检测到 commit message 含 'BYPASS:' 会拒合。", file=sys.stderr)
        return 0

    eval_kwargs = dict(cmd=cmd, file_path=file_path, file_basename=file_basename, new_content=new_content)

    # 1) deny
    for rule in load_rules("deny.yaml"):
        if not tool_matches(rule.get("tool"), tool_name):
            continue
        if matches_when(rule.get("when") or {}, **eval_kwargs):
            reason = str(rule.get("reason") or "(no reason)")
            rule_id = str(rule.get("id") or "")
            audit_log("deny", reason, tool=tool_name, target=target_for_log, rule_id=rule_id)
            print(f"[pre-tool-use] BLOCKED: {reason}", file=sys.stderr)
            print("[pre-tool-use] 如确需执行，请用户在终端手动跑，或调整规则后重试", file=sys.stderr)
            return 2

    # 2) ask_user
    for rule in load_rules("ask-user.yaml"):
        if not tool_matches(rule.get("tool"), tool_name):
            continue
        if matches_when(rule.get("when") or {}, **eval_kwargs):
            reason = str(rule.get("reason") or "(no reason)")
            rule_id = str(rule.get("id") or "")
            audit_log("ask_user", reason, tool=tool_name, target=target_for_log, rule_id=rule_id)
            print(f"[pre-tool-use] ⚠️ 待人工授权: {reason}", file=sys.stderr)
            print("[pre-tool-use] 主 Claude：请向用户描述将执行的动作并等待明确授权后再重试，不可绕过。", file=sys.stderr)
            return 2

    # 3) hints — 全部过一遍（多个 hint 可同时触发），不阻塞
    for rule in load_rules("hints.yaml"):
        if not tool_matches(rule.get("tool"), tool_name):
            continue
        if matches_when(rule.get("when") or {}, **eval_kwargs):
            reason = str(rule.get("reason") or "")
            if hint_already_fired(reason):
                continue
            print(f"💡 提示: {reason}", file=sys.stderr)
            remember_hint(reason)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        # 兜底：dispatcher 不应阻断会话
        audit_log("error", f"dispatcher uncaught: {e}", tool="-", target="")
        sys.exit(0)
