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
HINTS_FILE = ROOT / ".claude" / ".session.hints"
# policies 走脚本相对，让测试能复用项目的 yaml 而不必复制到 tempdir
POLICIES_DIR = Path(__file__).resolve().parent.parent / "rules" / "policies"


def _resolve_audit_log_path() -> Path:
    """Worktree-aware audit log 路径解析。

    优先级：
      1. env var HARNESS_AUDIT_LOG_PATH（用户显式覆盖）
      2. 子 worktree 内 → 写主仓库的 .claude/.audit.log（让多 worktree 共享一份）
      3. 主 worktree / 非 git 仓库 → cwd 相对 .claude/.audit.log（保持原行为）

    判断依据：`git rev-parse --git-common-dir` 在子 worktree 内返回绝对路径
    （指向主仓库的 .git/），在主 worktree 内返回相对 ".git"。
    """
    env_p = os.environ.get("HARNESS_AUDIT_LOG_PATH")
    if env_p:
        return Path(env_p).expanduser()
    try:
        import subprocess
        out = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        common = (out.stdout or "").strip()
        if common:
            common_path = Path(common)
            if common_path.is_absolute():
                # 子 worktree：common 指向主仓库 .git/
                main_repo = common_path.resolve().parent
                return main_repo / ".claude" / ".audit.log"
    except Exception:
        pass
    # 默认：cwd 相对（主 worktree 或非 git；保持与历史行为一致）
    return ROOT / ".claude" / ".audit.log"


AUDIT_LOG = _resolve_audit_log_path()


# ---------- audit log ----------

def audit_log(action: str, reason: str, *, tool: str, target: str, bypass: bool = False, rule_id: str = "", permission_mode: str = "") -> None:
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
            "permission_mode": permission_mode,
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


# ---------- bypass usage threshold ----------

BYPASS_WARN_THRESHOLD = int(os.environ.get("HARNESS_BYPASS_WARN_AT", "3"))
BYPASS_WINDOW_DAYS = 7


def count_bypass_in_window() -> int:
    """统计过去 N 天 .audit.log 中 bypass=true 的次数（含本次之前）。"""
    if not AUDIT_LOG.exists():
        return 0
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=BYPASS_WINDOW_DAYS)
    n = 0
    try:
        with open(AUDIT_LOG, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if not rec.get("bypass"):
                    continue
                ts = rec.get("ts") or ""
                try:
                    when = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    continue
                if when >= cutoff:
                    n += 1
    except Exception:
        return n
    return n


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

# 顶层规则合法字段；多余字段记 audit log 但不阻断（dispatcher 不阻断 policy）
RULE_TOP_KEYS = {"id", "tool", "when", "reason"}

# when.* 合法谓词；写错（如 cmd_contain_any）会让规则 silent skip，必须告警
WHEN_KEYS = {
    "cmd_contains_any",
    "cmd_matches",
    "cmd_imatches",
    "file_basename_in",
    "file_basename_glob",
    "file_basename_not_in",
    "file_basename_matches",
    "file_path_matches",
    "new_content_imatches",
    "new_content_present",
}


def validate_rule(rule: dict, source: str) -> list[str]:
    """返回该规则的 schema 问题列表（空表示 OK）。"""
    problems: list[str] = []
    rid = str(rule.get("id") or "<no-id>")

    # 必填
    if not rule.get("id"):
        problems.append(f"{source} rule missing 'id'")
    if not rule.get("tool"):
        problems.append(f"{source}[{rid}] missing 'tool'")
    if not rule.get("reason"):
        problems.append(f"{source}[{rid}] missing 'reason'")

    # 顶层未知键
    unknown_top = set(rule.keys()) - RULE_TOP_KEYS
    if unknown_top:
        problems.append(f"{source}[{rid}] unknown top-level keys: {sorted(unknown_top)}")

    # when 校验
    when = rule.get("when")
    if when is None:
        problems.append(f"{source}[{rid}] missing 'when' block")
    elif not isinstance(when, dict):
        problems.append(f"{source}[{rid}] 'when' must be a mapping, got {type(when).__name__}")
    else:
        unknown_when = set(when.keys()) - WHEN_KEYS
        if unknown_when:
            problems.append(
                f"{source}[{rid}] unknown 'when' keys (typo?): {sorted(unknown_when)}; "
                f"allowed: {sorted(WHEN_KEYS)}"
            )

    return problems


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
        rules = [r for r in data if isinstance(r, dict)]
        # schema 校验：runtime 不阻断（dispatcher 自身要兜底），但写 audit log 让 /doctor 看到
        for r in rules:
            for p in validate_rule(r, filename):
                audit_log("schema_error", p, tool="-", target=str(path))
        return rules
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
    # D9 修复：Windows 上 Claude Code 传入的 file_path 是反斜杠 D:\a\b\c.java，
    # 而所有 yaml 规则的 file_path_matches / file_path_glob 用正斜杠正则。
    # normalize 一律转正斜杠，让 8 条 file_path_matches 规则跨平台生效。
    # basename 在 normalized path 上仍正确（os.path.basename("D:/a/b/c.java") == "c.java"）。
    # target_for_log 同步用 normalized：跨平台 audit log 一致。
    file_path = str(tool_input.get("file_path") or "").replace("\\", "/")
    file_basename = os.path.basename(file_path) if file_path else ""
    new_content = str(tool_input.get("new_string") or tool_input.get("content") or "")
    # Claude Code 在 PreToolUse payload 注入当前权限模式：
    # default / acceptEdits / plan / auto / bypassPermissions（不同版本可能略有差异，原样落审计）
    permission_mode = str(payload.get("permission_mode") or "")

    target_for_log = file_path or cmd or ""

    # Bypass：放行所有规则但写审计
    if os.environ.get("HARNESS_BYPASS") == "1":
        audit_log("bypass", "HARNESS_BYPASS=1 in env", tool=tool_name, target=target_for_log, bypass=True, permission_mode=permission_mode)
        print("[pre-tool-use] ⚠️⚠️⚠️ BYPASS ACTIVE — 黑+灰名单全部放行，仅记录审计 ⚠️⚠️⚠️", file=sys.stderr)
        print("[pre-tool-use] 这不应是常态。CI 检测到 commit message 含 'BYPASS:' 会拒合。", file=sys.stderr)
        # 用量阈值告警：过去 7 天 bypass 次数（含本次）≥ 阈值 → 红字提醒收敛
        used = count_bypass_in_window()
        if used >= BYPASS_WARN_THRESHOLD:
            print(
                f"\033[31m[pre-tool-use] ❗ bypass 已在过去 {BYPASS_WINDOW_DAYS} 天用了 {used} 次（阈值 {BYPASS_WARN_THRESHOLD}）。"
                f"这是机制性放行，不应成为日常 — 请回看规则是否需要放宽，或考虑改 policy。\033[0m",
                file=sys.stderr,
            )
        return 0

    eval_kwargs = dict(cmd=cmd, file_path=file_path, file_basename=file_basename, new_content=new_content)

    # 1) deny
    for rule in load_rules("deny.yaml"):
        if not tool_matches(rule.get("tool"), tool_name):
            continue
        if matches_when(rule.get("when") or {}, **eval_kwargs):
            reason = str(rule.get("reason") or "(no reason)")
            rule_id = str(rule.get("id") or "")
            audit_log("deny", reason, tool=tool_name, target=target_for_log, rule_id=rule_id, permission_mode=permission_mode)
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
            audit_log("ask_user", reason, tool=tool_name, target=target_for_log, rule_id=rule_id, permission_mode=permission_mode)
            print(f"[pre-tool-use] ⚠️ 待人工授权: {reason}", file=sys.stderr)
            print("[pre-tool-use] 主 Claude：请向用户描述将执行的动作并等待明确授权后再重试，不可绕过。", file=sys.stderr)
            # auto 模式下灰名单触发额外提醒（auto 的分类器可能想自动放行）
            if permission_mode == "auto":
                print("[pre-tool-use] ↑ 当前 permission_mode=auto，分类器**不可**替代用户授权。", file=sys.stderr)
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
    # 显式 validate 模式：CI / 本地手测用，不读 stdin payload，只校验 yaml schema
    if len(sys.argv) > 1 and sys.argv[1] == "--validate":
        try:
            import yaml  # noqa: F401
        except ImportError:
            print("[policy-validate] PyYAML missing — install pyyaml first", file=sys.stderr)
            sys.exit(2)
        all_problems: list[str] = []
        for fname in ("deny.yaml", "ask-user.yaml", "hints.yaml"):
            path = POLICIES_DIR / fname
            if not path.exists():
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or []
            except Exception as e:
                all_problems.append(f"{fname}: yaml parse error: {e}")
                continue
            if not isinstance(data, list):
                all_problems.append(f"{fname}: top-level must be list, got {type(data).__name__}")
                continue
            seen_ids: set[str] = set()
            for r in data:
                if not isinstance(r, dict):
                    all_problems.append(f"{fname}: rule entry must be mapping")
                    continue
                rid = str(r.get("id") or "")
                if rid:
                    if rid in seen_ids:
                        all_problems.append(f"{fname}[{rid}] duplicate id")
                    seen_ids.add(rid)
                all_problems.extend(validate_rule(r, fname))
        if all_problems:
            print(f"[policy-validate] {len(all_problems)} problem(s):", file=sys.stderr)
            for p in all_problems:
                print(f"  - {p}", file=sys.stderr)
            sys.exit(1)
        print("[policy-validate] all rules pass schema check", file=sys.stderr)
        sys.exit(0)

    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        # 兜底：dispatcher 不应阻断会话
        audit_log("error", f"dispatcher uncaught: {e}", tool="-", target="")
        sys.exit(0)
