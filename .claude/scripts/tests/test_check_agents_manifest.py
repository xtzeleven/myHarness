"""check-agents-manifest.py 纯逻辑单测。

聚焦解析与一致性判断：frontmatter 解析 / AGENTS.md 表抽名 / policy §2 抽行 / check()。
真源 .claude/agents.yaml 与实际文件的"活"校验由 CI job 跑脚本本体覆盖。
"""

from __future__ import annotations


# ---------- parse_frontmatter ----------


def test_parse_frontmatter_basic(check_agents_manifest):
    md = "---\nname: foo\nmodel: sonnet\ntools: Read, Grep\n---\n\n# body\n"
    fm = check_agents_manifest.parse_frontmatter(md)
    assert fm["name"] == "foo"
    assert fm["model"] == "sonnet"


def test_parse_frontmatter_strips_markdown_emphasis(check_agents_manifest):
    # frontmatter 里 model 有时写 **opus**
    md = "---\nname: ddd-architect\nmodel: **opus**\n---\n\nbody\n"
    fm = check_agents_manifest.parse_frontmatter(md)
    assert fm["model"] == "opus"


def test_parse_frontmatter_no_frontmatter(check_agents_manifest):
    assert check_agents_manifest.parse_frontmatter("# just a heading\n") == {}


# ---------- agents_md_table_names ----------


def test_agents_md_table_names_scopes_to_section(check_agents_manifest):
    md = (
        "## 路由速查\n\n"
        "| x | `not-an-agent` |\n\n"
        "## 自定义 Agents\n\n"
        "| Agent | 文件 | 触发 |\n"
        "| ----- | ---- | ---- |\n"
        "| `alpha` | [f](a.md) | ... |\n"
        "| `beta` | [f](b.md) | ... |\n\n"
        "## 下一节\n\n"
        "| `gamma` | should-not-count |\n"
    )
    names = check_agents_manifest.agents_md_table_names(md)
    assert names == ["alpha", "beta"]


def test_agents_md_table_names_missing_section(check_agents_manifest):
    assert check_agents_manifest.agents_md_table_names("# no section here\n") == []


# ---------- policy_md_rows ----------


def test_policy_md_rows_extracts_name_model(check_agents_manifest):
    md = (
        "## 1. 优先级\n\n"
        "| a | b |\n\n"
        "## 2. Agent 默认模型表\n\n"
        "| Agent | 默认模型 | 原因 | 升级 |\n"
        "| ----- | -------- | ---- | ---- |\n"
        "| `alpha` | sonnet | x | y |\n"
        "| `beta` | **opus** | x | y |\n\n"
        "## 3. 通用场景表\n"
    )
    rows = check_agents_manifest.policy_md_rows(md)
    assert rows == {"alpha": "sonnet", "beta": "opus"}


# ---------- has_model_comment ----------


def test_has_model_comment_detects_standard_form(check_agents_manifest):
    md = "---\nname: foo\nmodel: sonnet\n# model 选择：路径明确，sonnet 够用\n---\n\nbody\n"
    assert check_agents_manifest.has_model_comment(md) is True


def test_has_model_comment_missing(check_agents_manifest):
    md = "---\nname: foo\nmodel: sonnet\ntools: Read\n---\n\nbody\n"
    assert check_agents_manifest.has_model_comment(md) is False


def test_has_model_comment_only_scans_frontmatter(check_agents_manifest):
    # 正文里提到 model 的注释不算（必须在 frontmatter 块内）
    md = "---\nname: foo\nmodel: sonnet\n---\n\n<!-- model 选择在正文不算 -->\n"
    assert check_agents_manifest.has_model_comment(md) is False


# ---------- check() ----------


def test_load_manifest_rejects_missing_keys(check_agents_manifest, tmp_path):
    bad = tmp_path / "agents.yaml"
    bad.write_text("agents:\n  - name: foo\n", encoding="utf-8")
    try:
        check_agents_manifest.load_manifest(bad)
        assert False, "应因缺 model 抛错"
    except ValueError:
        pass


def test_check_current_repo_is_consistent(check_agents_manifest):
    # 真源与实际文件应始终一致（软警告不算 error）
    manifest = check_agents_manifest.load_manifest()
    errors, _warnings = check_agents_manifest.check(manifest)
    assert errors == [], f"仓库 agent 注册表不一致: {errors}"
