#!/usr/bin/env python
# coding: utf-8
"""
audit-context-cost.py — 估算每会话上下文注入成本

分类：
  AUTO   每会话自动注入（CLAUDE.md / MEMORY.md 索引 / SessionStart 输出估算）
  RULES  按需注入（.claude/rules/ 下规则）
  AGENTS sub-agent 内部上下文（只在 spawn 时计入）
  DOCS   按需 Read 的文档

Tokenizer：
  优先用 tiktoken cl100k_base（粗略接近 Claude），不在则 fallback 字符数 / 4。

Usage:
  python .claude/scripts/audit-context-cost.py            # 全部
  python .claude/scripts/audit-context-cost.py --auto     # 仅自动注入
  python .claude/scripts/audit-context-cost.py --top 10   # Top 10
  python .claude/scripts/audit-context-cost.py --json     # 机器可读
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Windows console 编码兼容
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ===== Tokenizer =====
def get_token_counter():
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return ("tiktoken-cl100k_base", lambda s: len(enc.encode(s)))
    except Exception:
        # 字符数 / 4 是英文近似；中文每字符 1-2 token，但 / 4 仍是常用粗估
        return ("char/4 approx", lambda s: max(1, len(s) // 4))

# ===== 文件分类 =====
# 项目根优先级：(1) CLAUDE_PROJECT_DIR env (Claude Code 注入用户项目根)
#               (2) cwd (从用户项目调用时)
#               (3) 脚本所在 plugin 的父父父目录 (standalone fallback)
def _resolve_project_root() -> Path:
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir and Path(env_dir).is_dir():
        return Path(env_dir).resolve()
    cwd = Path.cwd()
    # 简单启发式：cwd 看起来是项目根（含 .git 或 CLAUDE.md 或 README.md）就用它
    if any((cwd / m).exists() for m in (".git", "CLAUDE.md", "README.md", "pyproject.toml", "package.json", "pom.xml")):
        return cwd.resolve()
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = _resolve_project_root()

def files_in(globs: list[str]) -> list[Path]:
    out = []
    for g in globs:
        for p in PROJECT_ROOT.glob(g):
            if p.is_file():
                out.append(p)
    return sorted(set(out))

CATEGORIES = {
    # 每会话注入：根 CLAUDE.md（标准）+ MEMORY 索引（在 ~/.claude 不在仓库，单独估算）
    "AUTO_root_claude": ["CLAUDE.md"],
    # 按需 - rules
    "RULES": [".claude/rules/*.md"],
    # 按需 - agent（仅 spawn 时计入；列出供单独审）
    "AGENTS": [".claude/agents/*.md"],
    # 按需 - command（被调用时计入）
    "COMMANDS": [".claude/commands/*.md"],
    # 按需 - docs
    "DOCS": ["docs/*.md", "docs/adr/*.md"],
    # 索引类（每会话自动；MEMORY.md 不在 git，单独处理）
    "AUTO_agents_index": ["AGENTS.md"],
    "AUTO_readme": ["README.md"],
    "AUTO_changelog": ["CHANGELOG.md"],
}

AUTO_INJECT = {"AUTO_root_claude"}  # 真正每次自动全量注入的
AUTO_HINTED = {"AUTO_agents_index", "AUTO_readme", "AUTO_changelog"}  # 主对话可能 prefetch；不一定每次

# ===== 主流程 =====
def audit():
    name, count = get_token_counter()
    rows = []
    for cat, globs in CATEGORIES.items():
        for p in files_in(globs):
            try:
                content = p.read_text(encoding="utf-8")
            except Exception as e:
                rows.append({"category": cat, "path": str(p.relative_to(PROJECT_ROOT)),
                             "tokens": 0, "lines": 0, "error": str(e)})
                continue
            rows.append({
                "category": cat,
                "path": str(p.relative_to(PROJECT_ROOT)),
                "tokens": count(content),
                "lines": content.count("\n") + 1,
            })

    # 加 MEMORY.md 索引（在 ~/.claude/projects/<encoded-cwd>/memory/）
    # 不硬编码项目名，按 basename 匹配
    project_base = PROJECT_ROOT.name
    home_claude = Path.home() / ".claude" / "projects"
    if home_claude.is_dir():
        for candidate in home_claude.glob(f"*{project_base}*/memory/MEMORY.md"):
            if candidate.exists():
                try:
                    content = candidate.read_text(encoding="utf-8")
                    rows.append({
                        "category": "AUTO_memory_index",
                        "path": str(candidate),
                        "tokens": count(content),
                        "lines": content.count("\n") + 1,
                    })
                    break
                except Exception:
                    pass
    return name, rows

def fmt_table(rows, top=None):
    rows = sorted(rows, key=lambda r: -r["tokens"])
    if top:
        rows = rows[:top]
    cat_w = max(len(r["category"]) for r in rows) if rows else 12
    path_w = min(60, max(len(r["path"]) for r in rows) if rows else 30)
    print(f"  {'CATEGORY':<{cat_w}}  {'PATH':<{path_w}}  {'TOKENS':>8}  {'LINES':>6}")
    print(f"  {'-' * cat_w}  {'-' * path_w}  {'-' * 8}  {'-' * 6}")
    for r in rows:
        path = r["path"]
        if len(path) > path_w:
            path = "..." + path[-(path_w - 3):]
        print(f"  {r['category']:<{cat_w}}  {path:<{path_w}}  {r['tokens']:>8}  {r['lines']:>6}")

def summarize(rows):
    auto = sum(r["tokens"] for r in rows if r["category"] in AUTO_INJECT or r["category"] == "AUTO_memory_index")
    auto_hinted = sum(r["tokens"] for r in rows if r["category"] in AUTO_HINTED)
    rules = sum(r["tokens"] for r in rows if r["category"] == "RULES")
    agents = sum(r["tokens"] for r in rows if r["category"] == "AGENTS")
    commands = sum(r["tokens"] for r in rows if r["category"] == "COMMANDS")
    docs = sum(r["tokens"] for r in rows if r["category"] == "DOCS")
    return {
        "auto_inject": auto,
        "auto_inject_hinted": auto_hinted,
        "on_demand_rules": rules,
        "on_demand_agents_total": agents,
        "on_demand_commands_total": commands,
        "on_demand_docs_total": docs,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true", help="仅显示自动注入")
    ap.add_argument("--top", type=int, default=None, help="只显示 Top N")
    ap.add_argument("--json", action="store_true", help="JSON 机器可读")
    args = ap.parse_args()

    tokenizer, rows = audit()

    if args.auto:
        rows = [r for r in rows if r["category"] in (AUTO_INJECT | {"AUTO_memory_index"})]

    summary = summarize(rows)

    if args.json:
        print(json.dumps({
            "tokenizer": tokenizer,
            "files": rows,
            "summary": summary,
        }, ensure_ascii=False, indent=2))
        return

    print(f"Tokenizer: {tokenizer}")
    print()
    print("=== 文件级 ===")
    fmt_table(rows, top=args.top)
    print()
    print("=== 汇总（tokens） ===")
    print(f"  自动注入（每会话付费）         {summary['auto_inject']:>8}")
    print(f"  常被 prefetch（README 等）     {summary['auto_inject_hinted']:>8}")
    print(f"  Rules（按需 Read）             {summary['on_demand_rules']:>8}")
    print(f"  Agents 总和（仅 spawn 时计入） {summary['on_demand_agents_total']:>8}")
    print(f"  Commands 总和（调用时计入）    {summary['on_demand_commands_total']:>8}")
    print(f"  Docs 总和（按需 Read）         {summary['on_demand_docs_total']:>8}")
    print()
    print("=== 预算检查 ===")
    target = 8000
    actual = summary["auto_inject"]
    pct = actual / target * 100 if target else 0
    status = "✅" if actual <= target else "⚠️"
    print(f"  自动注入预算 ≤ 8K：实际 {actual} / 目标 {target}  {status} ({pct:.0f}%)")
    print()
    if actual > target:
        print("=== 减重建议 ===")
        # 找 AUTO_root_claude 中最大的章节（按 ## 分隔）粗估
        claude = next((r for r in rows if r["path"] == "CLAUDE.md"), None)
        if claude and claude["tokens"] > 4000:
            print(f"  - CLAUDE.md ({claude['tokens']} tokens) 偏大；")
            print(f"    建议拆出 §11（memory）、§9（人工决策清单）到引用文档")
        memidx = next((r for r in rows if r["category"] == "AUTO_memory_index"), None)
        if memidx and memidx["tokens"] > 1000:
            print(f"  - MEMORY.md 索引 ({memidx['tokens']} tokens) 超 1K；")
            print(f"    检查每行 ≤ 150 字符；按主题分组而非平铺")

if __name__ == "__main__":
    main()
