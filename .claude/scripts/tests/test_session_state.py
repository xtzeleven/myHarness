"""session-state.py 状态机单测。

STATE_FILE 是相对路径 .claude/.session.state，测试用 monkeypatch 指向 tmp_path，
再直接调 cmd_* 函数（不走 argparse），验证任务/步骤/阻塞的读写与幂等。
"""

from __future__ import annotations

import argparse
import json


def _ns(**kw):
    return argparse.Namespace(**kw)


def _read_state(session_state):
    return json.loads(session_state.STATE_FILE.read_text(encoding="utf-8"))


def _redirect_state(session_state, monkeypatch, tmp_path):
    target = tmp_path / ".claude" / ".session.state"
    monkeypatch.setattr(session_state, "STATE_FILE", target)
    return target


def test_set_task_creates_state(session_state, monkeypatch, tmp_path):
    _redirect_state(session_state, monkeypatch, tmp_path)
    rc = session_state.cmd_set_task(_ns(task="做 A 功能"))
    assert rc == 0
    state = _read_state(session_state)
    assert state["current_task"] == "做 A 功能"
    assert state["pending_steps"] == []
    assert state["blocked_on"] is None
    assert state["last_checkpoint"]["action"] == "set-task"


def test_add_step_is_idempotent(session_state, monkeypatch, tmp_path):
    _redirect_state(session_state, monkeypatch, tmp_path)
    session_state.cmd_set_task(_ns(task="t"))
    session_state.cmd_add_step(_ns(step="step-1"))
    session_state.cmd_add_step(_ns(step="step-1"))  # 重复不应二次追加
    session_state.cmd_add_step(_ns(step="step-2"))
    state = _read_state(session_state)
    assert state["pending_steps"] == ["step-1", "step-2"]


def test_done_step_removes(session_state, monkeypatch, tmp_path):
    _redirect_state(session_state, monkeypatch, tmp_path)
    session_state.cmd_set_task(_ns(task="t"))
    session_state.cmd_add_step(_ns(step="a"))
    session_state.cmd_add_step(_ns(step="b"))
    session_state.cmd_done_step(_ns(step="a"))
    state = _read_state(session_state)
    assert state["pending_steps"] == ["b"]


def test_done_step_missing_is_noop(session_state, monkeypatch, tmp_path):
    _redirect_state(session_state, monkeypatch, tmp_path)
    session_state.cmd_set_task(_ns(task="t"))
    session_state.cmd_add_step(_ns(step="a"))
    rc = session_state.cmd_done_step(_ns(step="nonexistent"))
    assert rc == 0
    state = _read_state(session_state)
    assert state["pending_steps"] == ["a"]


def test_blocked_set_and_clear(session_state, monkeypatch, tmp_path):
    _redirect_state(session_state, monkeypatch, tmp_path)
    session_state.cmd_set_task(_ns(task="t"))
    session_state.cmd_blocked(_ns(reason="等用户授权", clear=False))
    assert _read_state(session_state)["blocked_on"] == "等用户授权"
    session_state.cmd_blocked(_ns(reason="", clear=True))
    assert _read_state(session_state)["blocked_on"] is None


def test_clear_resets_all(session_state, monkeypatch, tmp_path):
    _redirect_state(session_state, monkeypatch, tmp_path)
    session_state.cmd_set_task(_ns(task="t"))
    session_state.cmd_add_step(_ns(step="a"))
    session_state.cmd_blocked(_ns(reason="x", clear=False))
    session_state.cmd_clear(_ns())
    state = _read_state(session_state)
    assert state["current_task"] is None
    assert state["pending_steps"] == []
    assert state["blocked_on"] is None


def test_load_corrupt_file_returns_empty(session_state, monkeypatch, tmp_path):
    target = _redirect_state(session_state, monkeypatch, tmp_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{ not valid json", encoding="utf-8")
    # 损坏文件不应抛异常，_load 兜底返回 {}
    assert session_state._load() == {}


def test_show_empty_when_no_state(session_state, monkeypatch, tmp_path, capsys):
    _redirect_state(session_state, monkeypatch, tmp_path)
    rc = session_state.cmd_show(_ns())
    assert rc == 0
    assert "(empty)" in capsys.readouterr().out
