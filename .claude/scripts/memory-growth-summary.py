#!/usr/bin/env python
"""
memory-growth-summary.py — 扫 Claude Code 项目 memory 目录，统计条目数与新增速率。

输出（一次性快照 → 后续可重复跑做趋势对比）:
  - 各类型条目数（decision_* / pitfall_* / pref_* / session_* / ref_*）
  - 最近 7 / 30 天新增（按文件 mtime）
  - 体积统计（总字节数 / 平均字节数）
  - 索引漂移检查：MEMORY.md 引用 vs 实际文件

用法：
  python .claude/scripts/memory-growth-summary.py
  python .claude/scripts/memory-growth-summary.py --memory-dir /path/to/memory
  python .claude/scripts/memory-growth-summary.py --json   # 机器可读

Memory 路径由 Claude Code 客户端按用户与项目派生。本脚本不固化绝对路径，
按下面顺序尝试，第一个存在的目录胜出：
  1. --memory-dir 参数
  2. CLAUDE_MEMORY_DIR 环境变量
  3. ~/.claude/projects/<encoded-cwd>/memory   (Windows / *nix 通用)
  4. session-start.sh 同款 fallback (PWD / USERNAME 派生)

失败时返回非 0 + 友好提示，不抛栈。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 已知类型前缀（与 docs/memory-conventions.md 一致）
KNOWN_PREFIXES = ("decision_", "pitfall_", "pref_", "session_", "ref_")


def encode_cwd_to_claude_project_id(cwd: Path) -> str:
    """Claude Code 派生规则（实测）：冒号与分隔符 / \\ 各自独立替换为 `-`（不折叠）。
    例：D:\\myGithub\\myHarness → D--myGithub-myHarness  (D + : + \\ → 三段)
    """
    s = str(cwd)
    s = re.sub(r"[:\\/]", "-", s)
    return s


def candidate_memory_dirs(cli_dir: str | None) -> list[Path]:
    out: list[Path] = []
    if cli_dir:
        out.append(Path(cli_dir).expanduser())
    env_dir = os.environ.get("CLAUDE_MEMORY_DIR")
    if env_dir:
        out.append(Path(env_dir).expanduser())
    cwd = Path(os.getcwd()).resolve()
    encoded = encode_cwd_to_claude_project_id(cwd)
    home = Path.home()
    out.append(home / ".claude" / "projects" / encoded / "memory")
    # session-start.sh 同款 fallback
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "rw135"
    out.append(Path(f"/c/Users/{user}/.claude/projects/{encoded}/memory"))
    out.append(Path(f"C:/Users/{user}/.claude/projects/{encoded}/memory"))
    # 去重保序
    seen = set()
    uniq = []
    for p in out:
        key = str(p)
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


def resolve_memory_dir(cli_dir: str | None) -> Path | None:
    for p in candidate_memory_dirs(cli_dir):
        if p.is_dir():
            return p
    return None


def classify(filename: str) -> str:
    for pref in KNOWN_PREFIXES:
        if filename.startswith(pref):
            return pref.rstrip("_")
    return "other"


def file_mtime_utc(p: Path) -> datetime:
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)


def scan_memory(mdir: Path) -> dict:
    files = [p for p in mdir.iterdir() if p.is_file() and p.suffix == ".md" and p.name != "MEMORY.md"]
    now = datetime.now(timezone.utc)
    by_type: Counter[str] = Counter()
    new_7d: Counter[str] = Counter()
    new_30d: Counter[str] = Counter()
    total_bytes = 0
    per_file_bytes: list[int] = []
    for f in files:
        t = classify(f.name)
        by_type[t] += 1
        size = f.stat().st_size
        total_bytes += size
        per_file_bytes.append(size)
        mt = file_mtime_utc(f)
        if now - mt <= timedelta(days=7):
            new_7d[t] += 1
        if now - mt <= timedelta(days=30):
            new_30d[t] += 1

    # 索引漂移：MEMORY.md 行 `- [name](file.md)` 与目录实际文件比对
    # 仅认"无路径分隔 + 文件名以已知前缀开头"的 link 为 memory 引用
    index_listed: set[str] = set()
    index_path = mdir / "MEMORY.md"
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            m = re.search(r"\[(.*?)\]\(([^)]+\.md)\)", line)
            if m:
                href = m.group(2)
                if "/" in href or "\\" in href:
                    continue
                basename = Path(href).name
                if not basename.startswith(KNOWN_PREFIXES):
                    continue
                index_listed.add(basename)
    actual = {f.name for f in files}
    listed_missing_file = sorted(index_listed - actual)
    file_unlisted = sorted(actual - index_listed)

    return {
        "dir": str(mdir),
        "total_files": len(files),
        "by_type": dict(by_type),
        "new_7d": dict(new_7d),
        "new_30d": dict(new_30d),
        "bytes_total": total_bytes,
        "bytes_avg": int(total_bytes / len(files)) if files else 0,
        "bytes_max": max(per_file_bytes) if per_file_bytes else 0,
        "index_drift": {
            "listed_but_no_file": listed_missing_file,
            "file_but_not_listed": file_unlisted,
        },
    }


def print_text(report: dict) -> None:
    print(f"=== Memory 增长摘要 ===")
    print(f"目录: {report['dir']}")
    print(f"总条目: {report['total_files']} (不含 MEMORY.md)")
    print()
    print("按类型:")
    for k in sorted(report["by_type"], key=lambda x: (-report["by_type"][x], x)):
        v = report["by_type"][k]
        n7 = report["new_7d"].get(k, 0)
        n30 = report["new_30d"].get(k, 0)
        line = f"  {k:<10}  {v:>3}  (近7天 +{n7}, 近30天 +{n30})"
        print(line)
    print()
    print(f"总字节: {report['bytes_total']:,}    平均: {report['bytes_avg']:,}    最大单文件: {report['bytes_max']:,}")

    drift = report["index_drift"]
    if drift["listed_but_no_file"] or drift["file_but_not_listed"]:
        print()
        print("⚠️ MEMORY.md 索引漂移:")
        for n in drift["listed_but_no_file"]:
            print(f"  - 索引列了但文件不存在: {n}")
        for n in drift["file_but_not_listed"]:
            print(f"  - 文件存在但索引未列: {n}")
    else:
        print()
        print("✅ MEMORY.md 索引与目录文件一致")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--memory-dir", help="显式指定 memory 目录")
    ap.add_argument("--json", action="store_true", help="输出 JSON（机器可读）")
    args = ap.parse_args()

    mdir = resolve_memory_dir(args.memory_dir)
    if mdir is None:
        print("memory 目录未找到。尝试过的位置：", file=sys.stderr)
        for p in candidate_memory_dirs(args.memory_dir):
            print(f"  - {p}", file=sys.stderr)
        print("可用 --memory-dir 或 CLAUDE_MEMORY_DIR 指定。", file=sys.stderr)
        return 1

    report = scan_memory(mdir)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
