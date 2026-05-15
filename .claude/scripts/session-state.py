#!/usr/bin/env python
"""
Session-state CLI helper（P1-C / roadmap M5-T6）.

维护 .claude/.session.state（JSON, gitignored），让 SessionStart hook 能
显示"上次会话未完事项"。Stop hook 不擦除这些字段，只更新 git 元数据。

主对话约定：在以下时机调用本脚本（详见 docs/loop-architecture.md §6）：
  - 接到新任务时        → set-task "<描述>"
  - 拆出步骤时          → add-step "<step>"  （可多次）
  - 完成一步时          → done-step "<step>"
  - 等用户授权时        → blocked "<原因>"   （清除：blocked --clear）
  - 任务全部完成时      → clear              （清空 task / steps / blocked）

CLI 失败永远不该让会话挂掉 → 异常静默吞掉，exit 0。
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

# Windows 控制台默认 cp936；中文 / emoji 走 utf-8
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

STATE_FILE = Path(".claude") / ".session.state"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _load() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _checkpoint(state: dict, action: str, detail: str = "") -> None:
    state["last_checkpoint"] = {
        "ts": _now(),
        "action": action,
        "detail": detail[:200],
    }


def cmd_set_task(args: argparse.Namespace) -> int:
    state = _load()
    state["current_task"] = args.task
    state.setdefault("pending_steps", [])
    state.setdefault("blocked_on", None)
    _checkpoint(state, "set-task", args.task)
    _save(state)
    print(f"task set: {args.task}")
    return 0


def cmd_add_step(args: argparse.Namespace) -> int:
    state = _load()
    steps = state.setdefault("pending_steps", [])
    if args.step not in steps:
        steps.append(args.step)
    _checkpoint(state, "add-step", args.step)
    _save(state)
    print(f"step added ({len(steps)} pending): {args.step}")
    return 0


def cmd_done_step(args: argparse.Namespace) -> int:
    state = _load()
    steps = state.setdefault("pending_steps", [])
    before = len(steps)
    steps[:] = [s for s in steps if s != args.step]
    _checkpoint(state, "done-step", args.step)
    _save(state)
    if len(steps) == before:
        print(f"step not found in pending: {args.step} (still {before} pending)")
    else:
        print(f"step done ({len(steps)} pending): {args.step}")
    return 0


def cmd_blocked(args: argparse.Namespace) -> int:
    state = _load()
    if args.clear:
        state["blocked_on"] = None
        _checkpoint(state, "blocked-clear")
        _save(state)
        print("blocked: cleared")
    else:
        state["blocked_on"] = args.reason
        _checkpoint(state, "blocked", args.reason or "")
        _save(state)
        print(f"blocked on: {args.reason}")
    return 0


def cmd_clear(_args: argparse.Namespace) -> int:
    state = _load()
    state["current_task"] = None
    state["pending_steps"] = []
    state["blocked_on"] = None
    _checkpoint(state, "clear")
    _save(state)
    print("session task / steps / blocked cleared")
    return 0


def cmd_show(_args: argparse.Namespace) -> int:
    state = _load()
    if not state:
        print("(empty)")
        return 0
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=".session.state helper (P1-C)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("set-task", help="set current task description")
    p.add_argument("task")
    p.set_defaults(func=cmd_set_task)

    p = sub.add_parser("add-step", help="append a pending step")
    p.add_argument("step")
    p.set_defaults(func=cmd_add_step)

    p = sub.add_parser("done-step", help="mark a step done (remove from pending)")
    p.add_argument("step")
    p.set_defaults(func=cmd_done_step)

    p = sub.add_parser("blocked", help="record blocking reason or clear")
    p.add_argument("reason", nargs="?", default="")
    p.add_argument("--clear", action="store_true", help="clear blocked_on")
    p.set_defaults(func=cmd_blocked)

    p = sub.add_parser("clear", help="clear current_task / pending_steps / blocked_on")
    p.set_defaults(func=cmd_clear)

    p = sub.add_parser("show", help="dump current state as JSON")
    p.set_defaults(func=cmd_show)

    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as e:
        print(f"[session-state] error (ignored): {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
