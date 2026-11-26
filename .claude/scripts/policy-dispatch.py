#!/usr/bin/env python
"""
PreToolUse policy dispatcher（P1-A：规则数据外移到 yaml）.

加载 .claude/rules/policies/{deny,ask-user,hints}.yaml，对 stdin payload
评估每条规则；命中即写 audit log + 输出到 stderr + 用对应 exit code 退出。

退出码 / 输出：
  0  = 通过（包括所有 hint 规则命中后）
  0  + stdout JSON permissionDecision=ask = 灰名单命中，交给 Claude Code 原生确认弹窗（ADR-0009）
  2  = 拦截（deny 命中，或 deny 规则加载失败 → fail-closed，ADR-0009 / D1-A）

失败要响：deny.yaml 读不出来（PyYAML 缺失 / 解析失败 / 文件缺失）时默认拦截；
ask-user / hints 读不出来时放行但在 stderr 提示。其余 dispatcher 自身异常兜底 exit 0 + 写 audit log。

Bypass：HARNESS_BYPASS=1 需在**启动 Claude Code 会话前**设置（hook 读的是自身进程环境），
放行黑+灰名单，但仍写 audit log。命令前缀 `HARNESS_BYPASS=1 <command>` 不生效（ADR-0009）。
Hint 去重：通过 .claude/.session.hints（per-session）。
"""

from __future__ import annotations

import datetime
import difflib
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


def changed_lines(tool_input: dict, file_path: str) -> str:
    """模拟这次 Edit / Write / MultiEdit，返回文件里会被删掉或新增的行（换行拼接）。

    只看 new_string 认不出"只换版本号数字"这类改动（G17）：改动文本里没有标签，
    要对照磁盘上的原文才知道碰的是哪一行。
    """
    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            before = f.read()
    except OSError:  # 新建文件
        before = ""
    if "content" in tool_input:  # Write
        after = str(tool_input.get("content") or "")
    else:  # Edit / MultiEdit（edits[] 按顺序应用）
        after = before
        for e in tool_input.get("edits") or [tool_input]:
            old, new = str(e.get("old_string") or ""), str(e.get("new_string") or "")
            after = after.replace(old, new) if e.get("replace_all") else after.replace(old, new, 1)
    # [2:] 去掉 ---/+++ 两行文件头；@@ 行不以 +/- 开头
    diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), n=0, lineterm=""))[2:]
    return "\n".join(line[1:] for line in diff if line[:1] in ("+", "-"))


def matches_when(
    when: dict, *, cmd: str, file_path: str, file_basename: str, new_content: str, tool_input: dict | None = None
) -> bool:
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

    # file_exists: 目标文件此刻是否已在磁盘上（true = 只管改已有文件；false = 只管新建）
    fexists = when.get("file_exists")
    if fexists is not None:
        if not file_path or os.path.exists(file_path) != bool(fexists):
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

    # changed_lines_imatches: case-insensitive ERE on the lines this edit adds or removes
    # （要读磁盘上的文件，放最后：前面的条件都过了才读）
    pat = when.get("changed_lines_imatches")
    if pat:
        if not file_path or not re.search(pat, changed_lines(tool_input or {}, file_path), re.IGNORECASE):
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
    "file_exists",
    "new_content_imatches",
    "new_content_present",
    "changed_lines_imatches",
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


PYYAML_FIX = "python -m pip install pyyaml（报 externally-managed-environment 时加 --user --break-system-packages）"

# deny 规则加载失败（fail-closed）时唯一放行的命令：装 PyYAML 本身，否则会话无法自救。
# 必须整行匹配，`pip install pyyaml && rm -rf /` 这类拼接不放行。
PYYAML_INSTALL_RE = re.compile(
    r"^\s*((python3?|py)\s+-m\s+)?(uv\s+)?pip3?\s+install\s+(--user\s+|-U\s+|--upgrade\s+|--break-system-packages\s+)*pyyaml\s*$",
    re.IGNORECASE,
)


def load_rules(filename: str) -> tuple[list[dict], str]:
    """返回 (rules, error)。error 非空 = 规则没读出来，调用方决定 fail-open 还是 fail-closed。"""
    path = POLICIES_DIR / filename
    if not path.exists():
        return [], f"{filename} not found at {path}"
    try:
        import yaml  # type: ignore
    except ImportError:
        msg = f"PyYAML missing — cannot load {filename}"
        audit_log("error", msg, tool="-", target=str(path))
        return [], msg
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        if not isinstance(data, list):
            msg = f"{filename} top-level must be list"
            audit_log("error", msg, tool="-", target=str(path))
            return [], msg
        rules = [r for r in data if isinstance(r, dict)]
        # schema 校验：runtime 不阻断（dispatcher 自身要兜底），但写 audit log 让 /doctor 看到
        for r in rules:
            for p in validate_rule(r, filename):
                audit_log("schema_error", p, tool="-", target=str(path))
        return rules, ""
    except Exception as e:
        msg = f"failed to parse {filename}: {e}"
        audit_log("error", msg, tool="-", target=str(path))
        return [], msg


def ask_decision(reason: str) -> str:
    """灰名单命中 → Claude Code 原生确认（PreToolUse hookSpecificOutput.permissionDecision=ask）。"""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": reason,
            }
        },
        ensure_ascii=False,
    )


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
    # NotebookEdit 用 notebook_path / new_source（F6）
    file_path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "").replace("\\", "/")
    file_basename = os.path.basename(file_path) if file_path else ""
    new_content = str(
        tool_input.get("new_string") or tool_input.get("content") or tool_input.get("new_source") or ""
    )
    # Claude Code 在 PreToolUse payload 注入当前权限模式：
    # default / acceptEdits / plan / auto / bypassPermissions（不同版本可能略有差异，原样落审计）
    permission_mode = str(payload.get("permission_mode") or "")

    target_for_log = file_path or cmd or ""

    # Bypass：放行所有规则但写审计
    if os.environ.get("HARNESS_BYPASS") == "1":
        audit_log("bypass", "HARNESS_BYPASS=1 in env", tool=tool_name, target=target_for_log, bypass=True, permission_mode=permission_mode)
        print("[pre-tool-use] ⚠️⚠️⚠️ BYPASS ACTIVE — 黑+灰名单全部放行，仅记录审计 ⚠️⚠️⚠️", file=sys.stderr)
        print("[pre-tool-use] 这不应是常态。本会话的提交会自动带 Harness-Bypass 尾注，CI 要求补 Bypass-Reviewed 理由才放行。", file=sys.stderr)
        # 用量阈值告警：过去 7 天 bypass 次数（含本次）≥ 阈值 → 红字提醒收敛
        used = count_bypass_in_window()
        if used >= BYPASS_WARN_THRESHOLD:
            print(
                f"\033[31m[pre-tool-use] ❗ bypass 已在过去 {BYPASS_WINDOW_DAYS} 天用了 {used} 次（阈值 {BYPASS_WARN_THRESHOLD}）。"
                f"这是机制性放行，不应成为日常 — 请回看规则是否需要放宽，或考虑改 policy。\033[0m",
                file=sys.stderr,
            )
        return 0

    eval_kwargs = dict(
        cmd=cmd, file_path=file_path, file_basename=file_basename, new_content=new_content, tool_input=tool_input
    )

    # 1) deny — 加载失败即 fail-closed（D1-A）
    deny_rules, deny_err = load_rules("deny.yaml")
    if deny_err:
        if tool_name == "Bash" and PYYAML_INSTALL_RE.match(cmd):
            audit_log("allow_fix", f"fail-closed exemption: {deny_err}", tool=tool_name, target=target_for_log, permission_mode=permission_mode)
            return 0
        audit_log("deny", f"fail-closed: {deny_err}", tool=tool_name, target=target_for_log, rule_id="fail-closed", permission_mode=permission_mode)
        print(f"[pre-tool-use] BLOCKED (fail-closed): 黑名单规则无法加载 — {deny_err}", file=sys.stderr)
        print(f"[pre-tool-use] 门禁失效时默认拦截。修复：在终端运行 `{PYYAML_FIX}`（hook 用的 python）", file=sys.stderr)
        print("[pre-tool-use] 或让 Claude 只执行这一条安装命令（唯一放行项）；然后重试。", file=sys.stderr)
        return 2
    for rule in deny_rules:
        if not tool_matches(rule.get("tool"), tool_name):
            continue
        if matches_when(rule.get("when") or {}, **eval_kwargs):
            reason = str(rule.get("reason") or "(no reason)")
            rule_id = str(rule.get("id") or "")
            audit_log("deny", reason, tool=tool_name, target=target_for_log, rule_id=rule_id, permission_mode=permission_mode)
            print(f"[pre-tool-use] BLOCKED: {reason}", file=sys.stderr)
            print("[pre-tool-use] 如确需执行，请用户在终端手动跑，或调整规则后重试", file=sys.stderr)
            return 2

    # 2) ask_user — 交给 Claude Code 原生确认弹窗（P0-3 / ADR-0009），用户同意即放行这一次
    ask_rules, ask_err = load_rules("ask-user.yaml")
    if ask_err:
        print(f"[pre-tool-use] ⚠️ 灰名单规则未加载（放行）：{ask_err}；修复：{PYYAML_FIX}", file=sys.stderr)
    for rule in ask_rules:
        if not tool_matches(rule.get("tool"), tool_name):
            continue
        if matches_when(rule.get("when") or {}, **eval_kwargs):
            reason = str(rule.get("reason") or "(no reason)")
            rule_id = str(rule.get("id") or "")
            audit_log("ask_user", reason, tool=tool_name, target=target_for_log, rule_id=rule_id, permission_mode=permission_mode)
            msg = f"⚠️ 待人工授权: {reason}（规则 {rule_id}）"
            # auto 模式下额外说明：分类器不可替代用户授权
            if permission_mode == "auto":
                msg += "；当前 permission_mode=auto，分类器不可替代用户授权"
            print(ask_decision(msg))
            return 0

    # 3) hints — 全部过一遍（多个 hint 可同时触发），不阻塞
    hint_rules, hint_err = load_rules("hints.yaml")
    if hint_err:
        print(f"[pre-tool-use] ⚠️ hints 未加载：{hint_err}", file=sys.stderr)
    for rule in hint_rules:
        if not tool_matches(rule.get("tool"), tool_name):
            continue
        if matches_when(rule.get("when") or {}, **eval_kwargs):
            reason = str(rule.get("reason") or "")
            if hint_already_fired(reason):
                continue
            print(f"💡 提示: {reason}", file=sys.stderr)
            remember_hint(reason)

    return 0


def observe_mcp() -> int:
    """G13：MCP 调用只记审计，不评估规则、不拦（由 mcp-observe.sh 以 --observe-mcp 调用）。"""
    try:
        payload = json.loads(sys.stdin.read())
        tool_input = payload.get("tool_input")
        target = json.dumps(tool_input, ensure_ascii=False, sort_keys=True) if tool_input else ""
        audit_log(
            "mcp_call", "observe only",
            tool=str(payload.get("tool_name") or ""), target=target,
            permission_mode=str(payload.get("permission_mode") or ""),
        )
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--observe-mcp":
        sys.exit(observe_mcp())
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
