"""docs/rule-inventory.md 一致性校验（backlog G5 / improvement-plan P2 验收）。

- 覆盖：policies 规则 id、CI job、hook、agent、command、ArchUnit 规则都必须登记（写成 `名字`）
- 字段：每行成分含 ①–⑤、强制力含 机制/信号/文档、处置非空
- ①（能力补偿）② （编排补偿）行必须有退役条件（不能是空或 —）
新增规则忘了登记 → 本测试 fail。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
INVENTORY = REPO / "docs" / "rule-inventory.md"
HEADER = ["规则", "成分", "强制力", "处置", "退役条件"]

# bench 副本会删掉清单（防答案泄漏，见 bench/README.md）；真实仓库里由 CI structure-check
# 的 .github/required-files.txt 保证文件存在，所以这里跳过不会漏检
if not INVENTORY.exists():
    pytest.skip("docs/rule-inventory.md 不存在（bench 副本）", allow_module_level=True)


def _rows() -> list[list[str]]:
    rows, in_table = [], False
    for line in INVENTORY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells == HEADER:
            in_table = True
        elif in_table and not set("".join(cells)) <= set("-: "):
            rows.append(cells)
    return rows


ROWS = _rows()
TEXT = "\n".join(" | ".join(r) for r in ROWS)


def _policy_ids() -> list[str]:
    ids = []
    for f in sorted((REPO / ".claude/rules/policies").glob("*.yaml")):
        d = yaml.safe_load(f.read_text(encoding="utf-8"))
        rules = d.get("rules", []) if isinstance(d, dict) else d
        ids += [r["id"] for r in rules]
    return ids


def _ci_jobs() -> list[str]:
    jobs = []
    for f in ("lint.yml", "scheduled.yml"):
        jobs += list(yaml.safe_load((REPO / ".github/workflows" / f).read_text(encoding="utf-8"))["jobs"])
    return jobs


def _archunit_rules() -> list[str]:
    src = next(REPO.glob("src/test/java/**/DddRules.java")).read_text(encoding="utf-8")
    return re.findall(r"static final ArchRule ([A-Z_]+)", src)


EXPECTED = {
    "policy": _policy_ids(),
    "ci-job": _ci_jobs(),
    "hook": [p.name for p in (REPO / ".claude/hooks").glob("*.sh")] + [p.name for p in (REPO / ".githooks").iterdir()],
    "agent": [p.stem for p in (REPO / ".claude/agents").glob("*.md")],
    "command": ["/" + p.stem for p in (REPO / ".claude/commands").glob("*.md")],
    "archunit": _archunit_rules(),
}


def test_inventory_parsed():
    assert len(ROWS) > 50
    assert all(len(r) == 5 for r in ROWS), [r for r in ROWS if len(r) != 5]


@pytest.mark.parametrize("kind", sorted(EXPECTED))
def test_everything_is_registered(kind):
    assert EXPECTED[kind], f"没收集到任何 {kind}，收集逻辑可能失效"
    missing = [x for x in EXPECTED[kind] if f"`{x}`" not in TEXT]
    assert not missing, f"{kind} 未登记到 docs/rule-inventory.md：{missing}"


def test_fields_filled():
    bad = []
    for name, comp, force, action, retire in ROWS:
        if not re.search("[①②③④⑤]", comp) or not re.search("机制|信号|文档", force) or not action:
            bad.append(name)
    assert not bad, f"成分 / 强制力 / 处置 缺失：{bad}"


def test_compensation_rows_have_retirement_condition():
    bad = [r[0] for r in ROWS if re.search("[①②]", r[1]) and r[4] in ("", "—", "-")]
    assert not bad, f"①② 类规则缺退役条件：{bad}"
