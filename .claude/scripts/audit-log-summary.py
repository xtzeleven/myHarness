#!/usr/bin/env python
# coding: utf-8
"""
audit-log-summary.py — 摘要 .claude/.audit.log（PreToolUse hook 写入的 JSONL）

Usage:
  python .claude/scripts/audit-log-summary.py             # 全量摘要
  python .claude/scripts/audit-log-summary.py --tail 20   # 最近 20 条原始
  python .claude/scripts/audit-log-summary.py --bypass    # 仅 bypass 记录
  python .claude/scripts/audit-log-summary.py --since 24h # 最近 24 小时
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

LOG = Path(__file__).resolve().parent.parent.parent / ".claude" / ".audit.log"


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


def load_entries() -> list[dict]:
    if not LOG.exists():
        return []
    out = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def filter_entries(entries, since=None, only_bypass=False):
    out = entries
    if only_bypass:
        out = [e for e in out if e.get("bypass") or e.get("action") == "bypass"]
    if since:
        out = [
            e for e in out
            if (ts := datetime.fromisoformat(e["ts"].replace("Z", "+00:00")))
            and ts >= since
        ]
    return out


def summarize(entries):
    if not entries:
        print("(空) .claude/.audit.log 不存在或无记录")
        return

    by_action = Counter(e.get("action") for e in entries)
    by_tool = Counter(e.get("tool") for e in entries)
    by_reason = Counter(e.get("reason") for e in entries)
    bypass_count = sum(1 for e in entries if e.get("bypass"))

    print(f"=== 审计摘要 (共 {len(entries)} 条) ===")
    print(f"时间范围: {entries[0]['ts']} → {entries[-1]['ts']}")
    print(f"Bypass 触发: {bypass_count}{'  ⚠️ 注意' if bypass_count > 0 else ''}")
    print()
    print("按动作:")
    for k, v in by_action.most_common():
        print(f"  {k:<12}  {v}")
    print()
    print("按工具:")
    for k, v in by_tool.most_common(10):
        print(f"  {k:<12}  {v}")
    print()
    print("Top 10 原因:")
    for k, v in by_reason.most_common(10):
        reason = (k or "")[:80]
        print(f"  {v:>4}  {reason}")


def show_tail(entries, n):
    for e in entries[-n:]:
        print(json.dumps(e, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", type=int, help="显示最近 N 条原始记录")
    ap.add_argument("--bypass", action="store_true", help="仅 bypass 记录")
    ap.add_argument("--since", type=str, help="仅 N (h|d|m) 内 / ISO 时间戳之后")
    args = ap.parse_args()

    entries = load_entries()
    since = parse_since(args.since) if args.since else None
    entries = filter_entries(entries, since=since, only_bypass=args.bypass)

    if args.tail:
        show_tail(entries, args.tail)
    else:
        summarize(entries)


if __name__ == "__main__":
    main()
