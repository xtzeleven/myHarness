"""policy-dispatch.py 纯逻辑单测。

聚焦门禁匹配核心：matches_when（谓词 AND 语义）/ tool_matches / validate_rule。
不测 audit log 写入与 main() I/O（那些走 bash smoke test test_pre_tool_use.sh）。
"""

from __future__ import annotations


# ---------- matches_when ----------


def test_missing_condition_matches_everything(policy_dispatch):
    # 空 when：所有条件缺失 => True
    assert policy_dispatch.matches_when(
        {}, cmd="anything", file_path="a/b.py", file_basename="b.py", new_content="x"
    )


def test_when_not_dict_is_false(policy_dispatch):
    assert not policy_dispatch.matches_when(
        None, cmd="x", file_path="", file_basename="", new_content=""
    )


def test_cmd_contains_any_or_semantics(policy_dispatch):
    when = {"cmd_contains_any": ["rm -rf", "chmod 777"]}
    assert policy_dispatch.matches_when(
        when, cmd="sudo chmod 777 /etc", file_path="", file_basename="", new_content=""
    )
    assert not policy_dispatch.matches_when(
        when, cmd="ls -la", file_path="", file_basename="", new_content=""
    )


def test_cmd_matches_is_case_sensitive(policy_dispatch):
    when = {"cmd_matches": "DROP TABLE"}
    assert policy_dispatch.matches_when(
        when, cmd="DROP TABLE users", file_path="", file_basename="", new_content=""
    )
    # 小写不命中大小写敏感正则
    assert not policy_dispatch.matches_when(
        when, cmd="drop table users", file_path="", file_basename="", new_content=""
    )


def test_cmd_imatches_is_case_insensitive(policy_dispatch):
    when = {"cmd_imatches": "drop table"}
    assert policy_dispatch.matches_when(
        when, cmd="DROP TABLE users", file_path="", file_basename="", new_content=""
    )


def test_conditions_are_anded(policy_dispatch):
    # 两个条件都要满足
    when = {"cmd_contains_any": ["git push"], "cmd_matches": "--force"}
    assert policy_dispatch.matches_when(
        when, cmd="git push --force origin main", file_path="", file_basename="", new_content=""
    )
    # 只满足一个 => False
    assert not policy_dispatch.matches_when(
        when, cmd="git push origin main", file_path="", file_basename="", new_content=""
    )


def test_file_basename_in_exact(policy_dispatch):
    when = {"file_basename_in": [".env", "id_rsa"]}
    assert policy_dispatch.matches_when(
        when, cmd="", file_path="proj/.env", file_basename=".env", new_content=""
    )
    assert not policy_dispatch.matches_when(
        when, cmd="", file_path="proj/.envrc", file_basename=".envrc", new_content=""
    )


def test_file_basename_glob(policy_dispatch):
    when = {"file_basename_glob": ["*.key", "*.pem"]}
    assert policy_dispatch.matches_when(
        when, cmd="", file_path="a/server.key", file_basename="server.key", new_content=""
    )
    assert not policy_dispatch.matches_when(
        when, cmd="", file_path="a/server.txt", file_basename="server.txt", new_content=""
    )


def test_file_basename_not_in_exemption(policy_dispatch):
    # not_in 是白名单豁免：命中列表 => False
    when = {"file_basename_not_in": ["settings.local.json"]}
    assert not policy_dispatch.matches_when(
        when,
        cmd="",
        file_path=".claude/settings.local.json",
        file_basename="settings.local.json",
        new_content="",
    )
    # 不在豁免列表 => 该条件不阻断
    assert policy_dispatch.matches_when(
        when,
        cmd="",
        file_path=".claude/settings.json",
        file_basename="settings.json",
        new_content="",
    )


def test_file_path_matches(policy_dispatch):
    when = {"file_path_matches": r"src/main/java/.*/domain/"}
    assert policy_dispatch.matches_when(
        when,
        cmd="",
        file_path="src/main/java/com/example/harness/domain/order/Order.java",
        file_basename="Order.java",
        new_content="",
    )
    assert not policy_dispatch.matches_when(
        when,
        cmd="",
        file_path="src/main/java/com/example/harness/application/order/X.java",
        file_basename="X.java",
        new_content="",
    )


def test_new_content_present_false_triggers_on_empty(policy_dispatch):
    # new_content_present: false —— 仅当内容为空触发（整文件改写场景）
    when = {"new_content_present": False}
    assert policy_dispatch.matches_when(
        when, cmd="", file_path="pom.xml", file_basename="pom.xml", new_content=""
    )
    assert not policy_dispatch.matches_when(
        when, cmd="", file_path="pom.xml", file_basename="pom.xml", new_content="<dep>"
    )


def test_new_content_imatches(policy_dispatch):
    when = {"new_content_imatches": "spring-boot"}
    assert policy_dispatch.matches_when(
        when,
        cmd="",
        file_path="pom.xml",
        file_basename="pom.xml",
        new_content="<artifactId>SPRING-BOOT-starter</artifactId>",
    )


# ---------- tool_matches ----------


def test_tool_matches_string(policy_dispatch):
    assert policy_dispatch.tool_matches("Bash", "Bash")
    assert not policy_dispatch.tool_matches("Bash", "Edit")


def test_tool_matches_list(policy_dispatch):
    assert policy_dispatch.tool_matches(["Edit", "Write", "MultiEdit"], "Write")
    assert not policy_dispatch.tool_matches(["Edit", "Write"], "Bash")


def test_tool_matches_empty_is_false(policy_dispatch):
    assert not policy_dispatch.tool_matches("", "Bash")
    assert not policy_dispatch.tool_matches("Bash", "")


# ---------- validate_rule ----------


def test_valid_rule_has_no_problems(policy_dispatch):
    rule = {
        "id": "sample",
        "tool": "Bash",
        "when": {"cmd_contains_any": ["rm -rf /"]},
        "reason": "危险删除",
    }
    assert policy_dispatch.validate_rule(rule, "deny.yaml") == []


def test_missing_required_fields_flagged(policy_dispatch):
    problems = policy_dispatch.validate_rule({"when": {}}, "deny.yaml")
    joined = " ".join(problems)
    assert "missing 'id'" in joined
    assert "missing 'tool'" in joined
    assert "missing 'reason'" in joined


def test_unknown_top_level_key_flagged(policy_dispatch):
    rule = {
        "id": "x",
        "tool": "Bash",
        "when": {},
        "reason": "r",
        "typo_field": 1,
    }
    problems = policy_dispatch.validate_rule(rule, "deny.yaml")
    assert any("unknown top-level keys" in p for p in problems)


def test_unknown_when_key_flagged(policy_dispatch):
    # cmd_contain_any 少个 s，是最容易 silent-skip 的坑
    rule = {
        "id": "x",
        "tool": "Bash",
        "when": {"cmd_contain_any": ["rm"]},
        "reason": "r",
    }
    problems = policy_dispatch.validate_rule(rule, "deny.yaml")
    assert any("unknown 'when' keys" in p for p in problems)


def test_when_must_be_mapping(policy_dispatch):
    rule = {"id": "x", "tool": "Bash", "when": ["not", "a", "dict"], "reason": "r"}
    problems = policy_dispatch.validate_rule(rule, "deny.yaml")
    assert any("must be a mapping" in p for p in problems)
