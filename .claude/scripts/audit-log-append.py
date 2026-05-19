#!/usr/bin/env python
# coding: utf-8
"""audit-log-append.py — 通用 audit log 追加工具

把一行 JSONL 写入 .claude/.audit.log，供 slash 命令 / 一次性脚本统一打点。
worktree-aware：子 worktree 内自动写主仓库 .audit.log（与 policy-dispatch.py 行为一致）。

Usage:
  # 直接 CLI 参数
  python .claude/scripts/audit-log-append.py \
    --hook PracticesAudit \
    --action scored \
    --target "15-dim-audit" \
    --reason "/audit-practices run" \
    --extra layer1=L1 \
    --extra scores='{"1":"✅","9":"⚠️","12":"N/A"}'

  # 整段 JSON 从 stdin 读
  echo '{"hook":"PracticesAudit","action":"scored","scores":{...}}' \
    | python .claude/scripts/audit-log-append.py --stdin

extras 的 VALUE 若以 `{` / `[` 开头会按 JSON 解析，否则当字符串。
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_audit_log_path() -> Path:
    """与 policy-dispatch.py / audit-log-summary.py 同款解析。"""
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
                main_repo = common_path.resolve().parent
                return main_repo / ".claude" / ".audit.log"
    except Exception:
        pass
    return ROOT / ".claude" / ".audit.log"


def _parse_extra(kv: str) -> tuple[str, object]:
    if "=" not in kv:
        raise ValueError(f"extra 缺 '=': {kv}")
    k, v = kv.split("=", 1)
    k = k.strip()
    v = v.strip()
    if v.startswith(("{", "[")):
        try:
            return k, json.loads(v)
        except json.JSONDecodeError as e:
            raise ValueError(f"extra {k} 值看起来是 JSON 但解析失败: {e}") from e
    return k, v


def main() -> int:
    ap = argparse.ArgumentParser(description="追加一行 JSONL 到 .claude/.audit.log")
    ap.add_argument("--hook", help="hook 名（如 PracticesAudit）")
    ap.add_argument("--action", help="action（如 scored / baseline）")
    ap.add_argument("--target", default="", help="目标标识")
    ap.add_argument("--tool", default="cli", help="工具名（默认 cli）")
    ap.add_argument("--reason", default="", help="原因 / 调用方")
    ap.add_argument("--bypass", action="store_true", help="标记 bypass=true")
    ap.add_argument("--extra", action="append", default=[],
                    help="额外字段 KEY=VALUE，VALUE 以 {/[ 开头按 JSON 解析；可多次")
    ap.add_argument("--stdin", action="store_true", help="从 stdin 读整段 JSON 作为 entry")
    args = ap.parse_args()

    if args.stdin:
        try:
            entry = json.load(sys.stdin)
            if not isinstance(entry, dict):
                print("stdin JSON 必须是 object", file=sys.stderr)
                return 2
        except json.JSONDecodeError as e:
            print(f"stdin JSON 解析失败：{e}", file=sys.stderr)
            return 2
    else:
        if not args.hook or not args.action:
            print("非 --stdin 模式下必须给 --hook 和 --action", file=sys.stderr)
            return 2
        entry = {
            "hook": args.hook,
            "tool": args.tool,
            "target": args.target[:200],
            "action": args.action,
            "reason": args.reason,
            "bypass": bool(args.bypass),
        }
        for kv in args.extra:
            try:
                k, v = _parse_extra(kv)
            except ValueError as e:
                print(f"[warn] {e}", file=sys.stderr)
                return 2
            entry[k] = v

    # 统一补 ts
    entry.setdefault(
        "ts",
        datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    )

    log_path = _resolve_audit_log_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[warn] 写 audit.log 失败：{e}", file=sys.stderr)
        return 1

    print(f"写入 {log_path}: hook={entry.get('hook')} action={entry.get('action')}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
