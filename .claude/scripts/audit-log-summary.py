#!/usr/bin/env python
# coding: utf-8
"""
audit-log-summary.py — 摘要 .claude/.audit.log（JSONL）

支持来源：
  PreToolUse hook    — deny / ask_user / bypass / hint
  PostToolUse hook   — executed
  SubagentStop hook  — sub-agent 完成时的 status/degraded_from/escalate_to

Usage:
  python .claude/scripts/audit-log-summary.py                     # 全量摘要
  python .claude/scripts/audit-log-summary.py --tail 20           # 最近 20 条原始
  python .claude/scripts/audit-log-summary.py --bypass            # 仅 bypass 记录
  python .claude/scripts/audit-log-summary.py --since 24h         # 最近 24 小时
  python .claude/scripts/audit-log-summary.py --by-hook           # 按 hook 类型聚合
  python .claude/scripts/audit-log-summary.py --by-tool           # 按 tool 聚合
  python .claude/scripts/audit-log-summary.py --by-action         # 按 action 聚合
  python .claude/scripts/audit-log-summary.py --by-agent          # 按 sub-agent 聚合
  python .claude/scripts/audit-log-summary.py --by-ext            # 按文件后缀聚合（PostToolUse）
  python .claude/scripts/audit-log-summary.py --by-day            # 按日期聚合
  python .claude/scripts/audit-log-summary.py --by-permission-mode # 按权限模式聚合（auto/plan/默认...）
  python .claude/scripts/audit-log-summary.py --hook SubagentStop # 过滤 hook 类型
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def _resolve_audit_log_path() -> Path:
    """Worktree-aware：与 policy-dispatch.py 保持一致的解析逻辑。

    优先级：env var HARNESS_AUDIT_LOG_PATH > 子 worktree 内主仓库 > 脚本所在仓库根。
    """
    import os
    import subprocess

    env_p = os.environ.get("HARNESS_AUDIT_LOG_PATH")
    if env_p:
        return Path(env_p).expanduser()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        common = (out.stdout or "").strip()
        if common:
            common_path = Path(common)
            if common_path.is_absolute():
                main_repo = common_path.resolve().parent
                return main_repo / ".claude" / ".audit.log"
    except Exception:
        pass
    # 主 worktree / 非 git：用脚本所在仓库根（保持原行为）
    return Path(__file__).resolve().parent.parent.parent / ".claude" / ".audit.log"


LOG = _resolve_audit_log_path()


def parse_since(s: str) -> datetime | None:
    if not s:
        return None
    s = s.strip().lower()
    now = datetime.now(timezone.utc)
    try:
        if s.endswith("h"):
            return now - timedelta(hours=int(s[:-1]))
        if s.endswith("d"):
            return now - timedelta(days=int(s[:-1]))
        if s.endswith("m"):
            return now - timedelta(minutes=int(s[:-1]))
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def load_entries(log_path: Path | None = None) -> list[dict]:
    p = log_path or LOG
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def filter_entries(entries, since=None, only_bypass=False, only_hook=None):
    out = entries
    if only_bypass:
        out = [e for e in out if e.get("bypass") or e.get("action") == "bypass"]
    if only_hook:
        out = [e for e in out if e.get("hook") == only_hook]
    if since:
        kept = []
        for e in out:
            ts_raw = e.get("ts", "")
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                if ts >= since:
                    kept.append(e)
            except Exception:
                continue
        out = kept
    return out


def _ext_of(target: str) -> str:
    if not target or "." not in target:
        return "(none)"
    ext = target.rsplit(".", 1)[-1]
    # 去掉非字母数字字符（防止 target 含换行 / 控制符干扰）
    import re
    ext = re.split(r"[^A-Za-z0-9]", ext)[0]
    return "." + ext if ext else "(none)"


def _day_of(ts_raw: str) -> str:
    try:
        return ts_raw[:10]  # YYYY-MM-DD
    except Exception:
        return "(unknown)"


def summarize_default(entries):
    if not entries:
        print("(空) .claude/.audit.log 不存在或无记录")
        return

    by_hook = Counter((e.get("hook") or "").strip() for e in entries)
    by_action = Counter((e.get("action") or "").strip() for e in entries)
    by_tool = Counter((e.get("tool") or "").strip() for e in entries if e.get("tool"))
    bypass_count = sum(1 for e in entries if e.get("bypass"))
    by_reason = Counter((e.get("reason") or "").strip() for e in entries if e.get("reason"))

    print(f"=== 审计摘要 (共 {len(entries)} 条) ===")
    print(f"时间范围: {entries[0]['ts']} → {entries[-1]['ts']}")
    print(f"Bypass 触发: {bypass_count}{'  ⚠️ 注意' if bypass_count > 0 else ''}")
    print()
    print("按 Hook:")
    for k, v in by_hook.most_common():
        print(f"  {(k or '?'):<14}  {v}")
    print()
    print("按 Action:")
    for k, v in by_action.most_common():
        print(f"  {(k or '?'):<14}  {v}")
    print()
    print("按 Tool（top 10）:")
    for k, v in by_tool.most_common(10):
        print(f"  {(k or '?'):<14}  {v}")
    print()
    print("Top 10 Reason:")
    for k, v in by_reason.most_common(10):
        reason = (k or "")[:80]
        print(f"  {v:>4}  {reason}")


def by_field(entries, field_extractor, title, top=20):
    """通用按字段聚合输出。"""
    counter = Counter()
    for e in entries:
        v = field_extractor(e)
        if v is None or v == "":
            continue
        # strip 包括 \r / 尾空格，避免 Windows 写入的"Write "与"Write"被分开计数
        if isinstance(v, str):
            v = v.strip()
        if not v:
            continue
        counter[v] += 1

    print(f"=== {title} (共 {len(entries)} 条, {sum(counter.values())} 已分类) ===")
    if not counter:
        print("  (无数据)")
        return
    for k, v in counter.most_common(top):
        print(f"  {v:>4}  {k}")


def show_tail(entries, n):
    for e in entries[-n:]:
        print(json.dumps(e, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tail", type=int, help="显示最近 N 条原始记录")
    ap.add_argument("--bypass", action="store_true", help="仅 bypass 记录")
    ap.add_argument("--since", type=str, help="仅 N (h|d|m) 内 / ISO 时间戳之后")
    ap.add_argument("--hook", type=str, help="过滤 hook 类型（PreToolUse/PostToolUse/SubagentStop）")
    ap.add_argument("--by-hook", action="store_true", help="按 hook 类型聚合")
    ap.add_argument("--by-tool", action="store_true", help="按 tool 聚合")
    ap.add_argument("--by-action", action="store_true", help="按 action 聚合")
    ap.add_argument("--by-agent", action="store_true", help="按 sub-agent 聚合（SubagentStop）")
    ap.add_argument("--by-ext", action="store_true", help="按文件后缀聚合（PostToolUse）")
    ap.add_argument("--by-day", action="store_true", help="按日期聚合")
    ap.add_argument("--by-permission-mode", action="store_true", help="按 permission_mode 聚合（default/acceptEdits/plan/auto/bypassPermissions）")
    ap.add_argument("--log-path", type=str, help="覆盖 audit log 路径（默认 worktree-aware 自动解析）")
    args = ap.parse_args()

    log_path = Path(args.log_path).expanduser() if args.log_path else LOG
    entries = load_entries(log_path)
    since = parse_since(args.since) if args.since else None
    entries = filter_entries(entries, since=since, only_bypass=args.bypass, only_hook=args.hook)

    if args.tail:
        show_tail(entries, args.tail)
        return

    # 聚合视角（可组合，分节输出）
    any_aggregate = any([args.by_hook, args.by_tool, args.by_action,
                          args.by_agent, args.by_ext, args.by_day,
                          args.by_permission_mode])

    if args.by_hook:
        by_field(entries, lambda e: e.get("hook"), "按 Hook")
        print()
    if args.by_tool:
        by_field(entries, lambda e: e.get("tool"), "按 Tool")
        print()
    if args.by_action:
        by_field(entries, lambda e: e.get("action"), "按 Action")
        print()
    if args.by_agent:
        # 只看 SubagentStop（其他 hook 无 agent 字段）
        subs = [e for e in entries if e.get("hook") == "SubagentStop"]
        by_field(subs, lambda e: e.get("agent"), "按 Sub-agent（SubagentStop）")
        print()
    if args.by_ext:
        # 只看 PostToolUse（PreToolUse 的 target 是 command 而非 file_path）
        posts = [e for e in entries if e.get("hook") == "PostToolUse"]
        by_field(posts, lambda e: _ext_of(e.get("target", "")), "按文件后缀（PostToolUse）")
        print()
    if args.by_day:
        by_field(entries, lambda e: _day_of(e.get("ts", "")), "按日期")
        print()
    if args.by_permission_mode:
        # 老记录无此字段 → 归类为 (legacy)，帮助识别字段引入前后切换点
        by_field(entries, lambda e: e.get("permission_mode") or "(legacy)", "按 Permission Mode")
        print()

    if not any_aggregate:
        summarize_default(entries)


if __name__ == "__main__":
    main()
