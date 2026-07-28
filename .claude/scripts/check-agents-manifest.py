#!/usr/bin/env python
# coding: utf-8
"""
check-agents-manifest.py — agent 注册表三向一致校验

单一真源：.claude/agents.yaml
派生方（本脚本校验其与真源一致，消除手工同步漂移）：
  1. .claude/agents/<name>.md          每个 agent 文件必须存在
                                        frontmatter 的 name/model 与 yaml 一致
                                        含 <!-- harness:agent-output --> schema 标记
  2. AGENTS.md「自定义 Agents」表        行集 == yaml agent 集（不多不少）
  3. docs/policy-model-selection.md §2   交叉校验（软警告，不阻塞）：
                                        yaml 里每个 agent 应在 §2 表出现且模型一致

退出码：
  0  全部一致（软警告不影响退出码）
  1  发现硬性不一致（CI 应据此 fail）

Usage:
  python .claude/scripts/check-agents-manifest.py            # 校验并打印报告
  python .claude/scripts/check-agents-manifest.py --quiet    # 仅在失败时输出
  python .claude/scripts/check-agents-manifest.py --list     # 打印 yaml 里的 agent 名（换行分隔，供 shell 消费）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent.parent
MANIFEST = REPO / ".claude" / "agents.yaml"
AGENTS_DIR = REPO / ".claude" / "agents"
AGENTS_MD = REPO / "AGENTS.md"
POLICY_MD = REPO / "docs" / "policy-model-selection.md"

SCHEMA_MARKER = "harness:agent-output"


def load_manifest(path: Path = MANIFEST) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    agents = data.get("agents") or []
    if not isinstance(agents, list):
        raise ValueError("agents.yaml: 'agents' 必须是列表")
    for a in agents:
        if not isinstance(a, dict) or "name" not in a or "model" not in a:
            raise ValueError(f"agents.yaml: 每条须含 name + model，问题条目: {a!r}")
    return agents


def parse_frontmatter(md_text: str) -> dict:
    """提取 --- ... --- 之间的 YAML frontmatter。仅取 name/model 简单键值。"""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", md_text, re.DOTALL)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([a-zA-Z_]+):\s*(.+?)\s*$", line)
        if km:
            key, val = km.group(1), km.group(2)
            # 去掉 markdown 强调星号（frontmatter 里 model 有时写 **opus**）
            val = val.strip().strip("*").strip().strip('"').strip("'")
            out[key] = val
    return out


def agents_md_table_names(md_text: str) -> list[str]:
    """从 AGENTS.md「自定义 Agents」章的表格里抽取每行首列 backtick 包裹的 agent 名。

    只扫「## 自定义 Agents」到下一个「## 」之间，避免误抓路由表 / 反馈环表里的名字。
    """
    lines = md_text.splitlines()
    start = end = None
    for i, ln in enumerate(lines):
        if re.match(r"^##\s+自定义 Agents", ln):
            start = i
            continue
        if start is not None and re.match(r"^##\s+", ln) and i > start:
            end = i
            break
    if start is None:
        return []
    section = lines[start : end if end is not None else len(lines)]

    names: list[str] = []
    for ln in section:
        # 表体行形如：| `name` | [file](...) | ... |
        cells = [c.strip() for c in ln.split("|")]
        if len(cells) < 3:
            continue
        m = re.match(r"^`([a-z][a-z0-9-]*)`$", cells[1])
        if m:
            names.append(m.group(1))
    return names


def policy_md_rows(md_text: str) -> dict[str, str]:
    """从 policy-model-selection.md §2 表抽 {agent_name: model}。软校验用。"""
    lines = md_text.splitlines()
    start = end = None
    for i, ln in enumerate(lines):
        if re.match(r"^##\s+2\.", ln):
            start = i
            continue
        if start is not None and re.match(r"^##\s+", ln) and i > start:
            end = i
            break
    if start is None:
        return {}
    section = lines[start : end if end is not None else len(lines)]

    rows: dict[str, str] = {}
    for ln in section:
        cells = [c.strip() for c in ln.split("|")]
        if len(cells) < 4:
            continue
        nm = re.match(r"^`([a-z][a-z0-9-]*)`$", cells[1])
        if not nm:
            continue
        model = cells[2].strip().strip("*").strip()
        rows[nm.group(1)] = model
    return rows


def check(manifest: list[dict]) -> tuple[list[str], list[str]]:
    """返回 (errors, warnings)。errors 非空 → 退出码 1。"""
    errors: list[str] = []
    warnings: list[str] = []

    manifest_names = [a["name"] for a in manifest]
    manifest_models = {a["name"]: a["model"] for a in manifest}

    # 重复名
    dupes = {n for n in manifest_names if manifest_names.count(n) > 1}
    if dupes:
        errors.append(f"agents.yaml 有重复 name: {sorted(dupes)}")

    # 1. 每个 agent 的 .md 文件存在 + frontmatter name/model 一致 + schema 标记
    for a in manifest:
        name = a["name"]
        md_path = AGENTS_DIR / f"{name}.md"
        if not md_path.exists():
            errors.append(f"缺 agent 文件: .claude/agents/{name}.md（agents.yaml 声明了但文件不存在）")
            continue
        text = md_path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm.get("name") != name:
            errors.append(f"{name}.md frontmatter name={fm.get('name')!r} 与文件名/yaml 不一致")
        if fm.get("model") != a["model"]:
            errors.append(
                f"{name}.md frontmatter model={fm.get('model')!r} 与 agents.yaml model={a['model']!r} 不一致"
            )
        if SCHEMA_MARKER not in text:
            errors.append(f"{name}.md 缺 <!-- {SCHEMA_MARKER} --> schema 示例标记")

    # 2. 目录里多出来的 .md（yaml 没登记）
    disk_names = {p.stem for p in AGENTS_DIR.glob("*.md")}
    orphan = disk_names - set(manifest_names)
    if orphan:
        errors.append(f".claude/agents/ 有未在 agents.yaml 登记的文件: {sorted(orphan)}")

    # 3. AGENTS.md 表行集 == yaml
    if AGENTS_MD.exists():
        md_names = set(agents_md_table_names(AGENTS_MD.read_text(encoding="utf-8")))
        missing_in_md = set(manifest_names) - md_names
        extra_in_md = md_names - set(manifest_names)
        if missing_in_md:
            errors.append(f"AGENTS.md「自定义 Agents」表缺行: {sorted(missing_in_md)}")
        if extra_in_md:
            errors.append(f"AGENTS.md「自定义 Agents」表多出（yaml 未登记）: {sorted(extra_in_md)}")
    else:
        errors.append("AGENTS.md 不存在")

    # 4. 软校验：policy-model-selection §2
    if POLICY_MD.exists():
        policy = policy_md_rows(POLICY_MD.read_text(encoding="utf-8"))
        for name, model in manifest_models.items():
            if name not in policy:
                warnings.append(f"policy-model-selection §2 表缺 agent: {name}（建议补一行说明为什么用 {model}）")
            elif policy[name] != model:
                warnings.append(
                    f"policy-model-selection §2 中 {name} 模型={policy[name]!r} 与 agents.yaml={model!r} 不符"
                )
    else:
        warnings.append("docs/policy-model-selection.md 不存在，跳过 §2 交叉校验")

    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true", help="仅在失败时输出")
    ap.add_argument("--list", action="store_true", help="打印 yaml 里的 agent 名（换行分隔）后退出")
    args = ap.parse_args()

    manifest = load_manifest()

    if args.list:
        for a in manifest:
            print(a["name"])
        return 0

    errors, warnings = check(manifest)

    if errors:
        print(f"❌ agent 注册表不一致（{len(errors)} 项）：")
        for e in errors:
            print(f"  - {e}")
    elif not args.quiet:
        print(f"✅ agent 注册表三向一致（{len(manifest)} 个 agent：yaml ↔ .md 文件 ↔ AGENTS.md 表）")

    if warnings and not args.quiet:
        print(f"\n⚠️  软警告（{len(warnings)} 项，不阻塞 CI）：")
        for w in warnings:
            print(f"  - {w}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
