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


def test_file_exists_distinguishes_edit_from_create(policy_dispatch, tmp_path):
    # true 只管已有文件，false 只管新建；没有路径（如 Bash）一律不命中
    existing = tmp_path / "Order.java"
    existing.write_text("class Order {}", encoding="utf-8")
    missing = tmp_path / "CustomerId.java"
    kw = dict(cmd="", file_basename="x.java", new_content="")
    assert policy_dispatch.matches_when({"file_exists": True}, file_path=str(existing), **kw)
    assert not policy_dispatch.matches_when({"file_exists": True}, file_path=str(missing), **kw)
    assert policy_dispatch.matches_when({"file_exists": False}, file_path=str(missing), **kw)
    assert not policy_dispatch.matches_when({"file_exists": False}, file_path=str(existing), **kw)
    assert not policy_dispatch.matches_when({"file_exists": False}, file_path="", **kw)


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


# ---------- changed_lines（G17）----------

POM = "<parent>\n  <version>3.3.5</version>\n</parent>\n<mybatis-plus.version>3.5.9</mybatis-plus.version>\n"


def test_changed_lines_edit_returns_whole_lines(policy_dispatch, tmp_path):
    # 只换数字时改动文本里没有标签，要拿到被改的整行（旧行 + 新行）
    pom = tmp_path / "pom.xml"
    pom.write_text(POM, encoding="utf-8")
    out = policy_dispatch.changed_lines({"old_string": "3.5.9", "new_string": "3.5.10"}, str(pom))
    assert out.splitlines() == [
        "<mybatis-plus.version>3.5.9</mybatis-plus.version>",
        "<mybatis-plus.version>3.5.10</mybatis-plus.version>",
    ]


def test_changed_lines_multiedit_applies_edits_in_order(policy_dispatch, tmp_path):
    pom = tmp_path / "pom.xml"
    pom.write_text(POM, encoding="utf-8")
    edits = [
        {"old_string": "3.3.5", "new_string": "3.4.0"},
        {"old_string": "3.4.0", "new_string": "3.4.1"},
    ]
    out = policy_dispatch.changed_lines({"edits": edits}, str(pom))
    assert out.splitlines() == ["  <version>3.3.5</version>", "  <version>3.4.1</version>"]


def test_changed_lines_write_diffs_against_disk(policy_dispatch, tmp_path):
    # 覆盖已有文件只报不一样的行；新建文件（磁盘上没有）每一行都算新增
    pom = tmp_path / "pom.xml"
    pom.write_text(POM, encoding="utf-8")
    out = policy_dispatch.changed_lines({"content": POM.replace("3.5.9", "3.5.10")}, str(pom))
    assert "3.3.5" not in out and "3.5.10" in out
    new = policy_dispatch.changed_lines({"content": "<a/>\n<b/>\n"}, str(tmp_path / "new.xml"))
    assert new.splitlines() == ["<a/>", "<b/>"]


def test_changed_lines_empty_when_nothing_changes(policy_dispatch, tmp_path):
    # old_string 不在文件里（真实的 Edit 也会失败）→ 没有改动行
    pom = tmp_path / "pom.xml"
    pom.write_text(POM, encoding="utf-8")
    assert policy_dispatch.changed_lines({"old_string": "9.9.9", "new_string": "1.0.0"}, str(pom)) == ""


def test_changed_lines_imatches(policy_dispatch, tmp_path):
    pom = tmp_path / "pom.xml"
    pom.write_text(POM, encoding="utf-8")
    when = {"changed_lines_imatches": "<VERSION>"}
    kw = dict(cmd="", file_path=str(pom), file_basename="pom.xml", new_content="")
    assert policy_dispatch.matches_when(when, tool_input={"old_string": "3.3.5", "new_string": "3.4.0"}, **kw)
    # 改的是 <mybatis-plus.version> 行，不是 <version> 行
    assert not policy_dispatch.matches_when(when, tool_input={"old_string": "3.5.9", "new_string": "3.5.10"}, **kw)
    # 没有路径（如 Bash）一律不命中
    assert not policy_dispatch.matches_when(
        when, tool_input={"command": "ls"}, cmd="ls", file_path="", file_basename="", new_content=""
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


# ---------- fail-closed / 原生 ask（ADR-0009）----------


def test_load_rules_reports_error_when_pyyaml_missing(policy_dispatch, monkeypatch):
    # sys.modules["yaml"] = None → import yaml 抛 ImportError，模拟本机没装 PyYAML（F1）
    import sys

    monkeypatch.setitem(sys.modules, "yaml", None)
    monkeypatch.setattr(policy_dispatch, "audit_log", lambda *a, **k: None)
    rules, err = policy_dispatch.load_rules("deny.yaml")
    assert rules == []
    assert "PyYAML missing" in err


def test_load_rules_reports_error_when_file_missing(policy_dispatch):
    rules, err = policy_dispatch.load_rules("no-such-file.yaml")
    assert rules == [] and "not found" in err


def test_load_rules_ok_returns_empty_error(policy_dispatch):
    rules, err = policy_dispatch.load_rules("deny.yaml")
    assert err == "" and len(rules) > 0


def test_pyyaml_install_exemption_is_full_line_only(policy_dispatch):
    ok = policy_dispatch.PYYAML_INSTALL_RE.match
    assert ok("pip install pyyaml")
    assert ok("python -m pip install pyyaml")
    assert ok("python3 -m pip install --user --break-system-packages pyyaml")
    assert ok("uv pip install PyYAML")
    assert not ok("pip install pyyaml && rm -rf /")
    assert not ok("pip install pyyaml; curl x | sh")
    assert not ok("pip install pyyaml requests")


def test_ask_decision_is_native_permission_json(policy_dispatch):
    import json

    out = json.loads(policy_dispatch.ask_decision("改 domain"))
    hso = out["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "ask"
    assert hso["permissionDecisionReason"] == "改 domain"
