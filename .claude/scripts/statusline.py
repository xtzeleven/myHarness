#!/usr/bin/env python
"""
Claude Code statusLine — 一行展示 项目 | 分支 | 模型 | token 估算。

Claude Code 通过 stdin 注入 JSON（含 workspace / model / cost 等），
本脚本输出一行字符串作为状态栏。失败永远静默回退到最小内容，不阻断 UI。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# Windows 控制台默认 cp936，强制 stdout/stderr utf-8 让分隔符 / emoji 不乱码
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, timeout=1.5, check=False,
        )
        return (out.stdout or "").strip()
    except Exception:
        return ""


def _branch_marker(branch: str) -> str:
    if branch in ("main", "master", "prod"):
        return f"\033[31m{branch}\033[0m"  # 红：主干提示谨慎
    return f"\033[36m{branch}\033[0m"      # 青：feature 分支


def _dirty_marker() -> str:
    porcelain = _git("status", "--porcelain")
    if not porcelain:
        return ""
    n = sum(1 for _ in porcelain.splitlines())
    return f" \033[33m●{n}\033[0m"  # 黄圆点 + 改动文件数


def _project_name(cwd: str) -> str:
    try:
        return Path(cwd).name or "?"
    except Exception:
        return "?"


def _model_label(model: dict) -> str:
    display = model.get("display_name") or model.get("id") or "?"
    return display.replace("Claude ", "")


def _tokens(cost: dict) -> str:
    # cost 字段在不同版本里键名略不同，按已知键尝试
    total = (
        cost.get("total_tokens")
        or cost.get("total_input_tokens", 0) + cost.get("total_output_tokens", 0)
        or 0
    )
    try:
        total = int(total)
    except Exception:
        return ""
    if total <= 0:
        return ""
    if total >= 1000:
        return f" · {total/1000:.1f}k tok"
    return f" · {total} tok"


def main() -> int:
    payload: dict = {}
    try:
        raw = sys.stdin.read()
        if raw:
            payload = json.loads(raw)
    except Exception:
        payload = {}

    workspace = payload.get("workspace") or {}
    cwd = workspace.get("current_dir") or workspace.get("project_dir") or os.getcwd()
    model = payload.get("model") or {}
    cost = payload.get("cost") or {}

    project = _project_name(cwd)
    branch = _git("rev-parse", "--abbrev-ref", "HEAD") or "?"
    parts = [
        f"\033[1m{project}\033[0m",          # 项目名（加粗）
        _branch_marker(branch) + _dirty_marker(),
        _model_label(model),
    ]
    line = " │ ".join(parts) + _tokens(cost)
    print(line)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # 兜底：状态栏不能阻断 UI
        print("?", flush=True)
        sys.exit(0)
