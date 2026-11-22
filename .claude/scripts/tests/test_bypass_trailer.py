"""bypass-trailer.py 端到端测试（backlog G6）。

在临时 git 仓库里装上 .githooks/prepare-commit-msg + 脚本，用伪造的 audit log 真实提交，
验证：尾注写入 / 不误报 / amend 界线 / --no-verify 跳不过 / --check 拒合与补理由放行。
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
UTC = datetime.timezone.utc


def _run(repo: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=repo, capture_output=True, text=True, env=env, check=True)


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch):
    r = tmp_path / "r"
    (r / ".claude" / "scripts").mkdir(parents=True)
    shutil.copy(REPO / ".claude/scripts/bypass-trailer.py", r / ".claude/scripts/bypass-trailer.py")
    shutil.copytree(REPO / ".githooks", r / ".githooks")
    _run(r, "git", "init", "-q", "-b", "main")
    _run(r, "git", "config", "user.email", "t@example.com")
    _run(r, "git", "config", "user.name", "t")
    _run(r, "git", "config", "core.hooksPath", ".githooks")
    monkeypatch.delenv("HARNESS_BYPASS", raising=False)
    monkeypatch.delenv("HARNESS_AUDIT_LOG_PATH", raising=False)
    return r


def _log(repo: Path, *entries: tuple[datetime.datetime, bool, str]) -> None:
    with open(repo / ".claude" / ".audit.log", "a", encoding="utf-8") as f:
        for ts, bypass, tool in entries:
            f.write(json.dumps({"ts": ts.isoformat(timespec="seconds"), "tool": tool, "bypass": bypass, "action": "bypass" if bypass else "allow"}) + "\n")


def _commit(repo: Path, name: str, *extra: str, env: dict | None = None) -> str:
    (repo / name).write_text(name)
    _run(repo, "git", "add", name)
    _run(repo, "git", "commit", "-q", "-m", f"add {name}", *extra, env=env)
    return _run(repo, "git", "log", "-1", "--format=%B").stdout


def _bp(repo: Path) -> str:
    """HEAD 上 git 认得的 Harness-Bypass 尾注值（CI 用同样方式读）。"""
    return _run(repo, "git", "log", "-1", "--format=%(trailers:key=Harness-Bypass,valueonly)").stdout.strip()


def _ago(seconds: int) -> datetime.datetime:
    return datetime.datetime.now(UTC) - datetime.timedelta(seconds=seconds)


def _check(repo: Path, rev_range: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, ".claude/scripts/bypass-trailer.py", "--check", rev_range],
        cwd=repo, capture_output=True, text=True,
    )


def test_no_bypass_no_trailer(repo):
    _log(repo, (_ago(5), False, "Bash"))
    assert "Harness-Bypass" not in _commit(repo, "a")


def test_bypass_entries_become_trailer(repo):
    _log(repo, (_ago(30), True, "Bash"), (_ago(20), True, "Bash"), (_ago(10), True, "Edit"))
    _commit(repo, "a", "-m", "Co-Authored-By: X <x@example.com>")
    assert _bp(repo).startswith("3 tool calls")
    assert _bp(repo).endswith("(Bash=2, Edit=1)")


def test_editor_template_trailer_is_recognized(repo):
    _log(repo, (_ago(5), True, "Bash"))
    (repo / "a").write_text("a")
    _run(repo, "git", "add", "a")
    # 模拟编辑器：在第 1 行写标题，其余原样保存
    editor = "sh -c 'printf \"%s\" \"feat: via editor\" | cat - \"$1\" > \"$1.new\" && mv \"$1.new\" \"$1\"' --"
    _run(repo, "git", "commit", "-q", env={**os.environ, "GIT_EDITOR": editor})
    assert _run(repo, "git", "log", "-1", "--format=%s").stdout.strip() == "feat: via editor"
    assert _bp(repo).startswith("1 tool calls")


def test_only_entries_after_previous_commit(repo):
    _log(repo, (_ago(120), True, "Bash"))
    assert "Harness-Bypass" in _commit(repo, "a")
    # 下一个提交：旧 bypass 已在上一个提交之前 → 不再报
    assert "Harness-Bypass" not in _commit(repo, "b")


def test_amend_keeps_trailer_and_review(repo):
    _commit(repo, "base")
    _log(repo, (datetime.datetime.now(UTC) + datetime.timedelta(seconds=1), True, "Write"))
    assert "Harness-Bypass: 1 tool calls" in _commit(repo, "a")
    # amend：界线退到 HEAD^，bypass 仍计入；补的理由保留，尾注不重复
    _run(repo, "git", "commit", "-q", "--amend", "--no-edit", "--trailer", "Bypass-Reviewed: 紧急修复，已复核 diff")
    msg = _run(repo, "git", "log", "-1", "--format=%B").stdout
    assert msg.count("Harness-Bypass:") == 1
    assert "Bypass-Reviewed: 紧急修复" in msg


def test_no_verify_cannot_skip(repo):
    _log(repo, (_ago(5), True, "Bash"))
    _commit(repo, "a", "--no-verify")
    assert _bp(repo).startswith("1 tool calls")


def test_env_active_session(repo):
    env = {**os.environ, "HARNESS_BYPASS": "1"}
    _commit(repo, "a", env=env)
    assert _bp(repo) == "committed with bypass env active"


def test_corrupt_log_does_not_block_commit(repo):
    (repo / ".claude" / ".audit.log").write_text("not json\n{\"bypass\": true}\n")
    assert "add a" in _commit(repo, "a")


def test_check_rejects_unreviewed_and_accepts_reviewed(repo):
    base = _commit(repo, "base") and _run(repo, "git", "rev-parse", "HEAD").stdout.strip()
    _log(repo, (datetime.datetime.now(UTC) + datetime.timedelta(seconds=1), True, "Bash"))
    _commit(repo, "a")
    r = _check(repo, f"{base}..HEAD")
    assert r.returncode == 1 and "::error::" in r.stdout

    _run(repo, "git", "commit", "-q", "--amend", "--no-edit", "--trailer", "Bypass-Reviewed: 已复核")
    r = _check(repo, f"{base}..HEAD")
    assert r.returncode == 0 and "::warning::" in r.stdout


def test_check_clean_range_passes(repo):
    base = _commit(repo, "base") and _run(repo, "git", "rev-parse", "HEAD").stdout.strip()
    _commit(repo, "a")
    assert _check(repo, f"{base}..HEAD").returncode == 0


def test_check_bad_range_fails_loud(repo):
    _commit(repo, "a")
    r = _check(repo, "nope..HEAD")
    assert r.returncode == 1 and "出错" in r.stdout
