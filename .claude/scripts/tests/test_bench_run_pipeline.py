"""run-auto.sh 占到目录之后的流程回归测试：纯本地，临时合成仓库 + 本地桩。

不调用真实模型，不跑真实的构建：claude、mvnw、CI 脚本都是合成仓库里的桩。覆盖：
- 成功路径：导出副本、按配置裁剪、自检、收集、summary.json、开始 / 结束记录
- 自检中止、API 错误、超时、会话中途退出、脚本被信号中断、脚本被强杀
- 记录一次写入不覆盖（并发、目标已存在、目录不可写）
- all 模式：子脚本执行状态与样本有效性分开报
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
BENCH = REPO / "bench"
REC = BENCH / "attempt-record.py"
# 对照实验的副本会删掉 bench/ 但保留本目录：那里没有被测对象，整份跳过而不是报错
pytestmark = pytest.mark.skipif(not REC.exists(), reason="没有 bench/（对照实验副本）")

LEAK_WORD = "AFTER" + "_COMMIT"  # 副本自检要找的词之一，运行时拼

STUB_CLAUDE = r"""#!/usr/bin/env python3
import json, os, sys, time
if "--version" in sys.argv:
    print("9.9.9 (stub)"); sys.exit(0)
name = os.path.basename(os.getcwd())[11:]  # 去掉 YYYY-MM-DD-
mode = json.loads(os.environ.get("BENCH_STUB_MODES", "{}")).get(name, os.environ.get("BENCH_STUB_MODE", "ok"))
with open(os.environ["BENCH_STUB_LOG"], "a") as f:
    f.write(name + " " + mode + "\n")
if os.environ.get("BENCH_STUB_PROMPTS"):
    with open(os.environ["BENCH_STUB_PROMPTS"], "a") as f:
        f.write(sys.argv[sys.argv.index("-p") + 1] + "\n")
def emit(o):
    print(json.dumps(o), flush=True)
emit({"type": "system", "subtype": "init", "model": "stub-model-1", "claude_code_version": "9.9.9"})
if mode == "api-error":
    emit({"type": "result", "subtype": "success", "is_error": True, "usage": {}}); sys.exit(0)
os.makedirs("notes", exist_ok=True)
open("notes/added-by-stub.txt", "w").write("hello\n")
emit({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Write",
      "input": {"file_path": os.getcwd() + "/notes/added-by-stub.txt", "content": "hello\n"}}]}})
emit({"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}})
if mode == "crash":
    sys.exit(3)
if mode == "hang":
    time.sleep(30)
emit({"type": "result", "subtype": "success", "is_error": False, "usage": {"input_tokens": 1, "output_tokens": 2}})
"""


def _today() -> str:
    return datetime.date.today().isoformat()


class Sandbox:
    def __init__(self, tmp: Path, leak: bool = False):
        self.tmp, self.src, self.root = tmp, tmp / "repo", tmp / "runs"
        self.stub_log = tmp / "stub-calls.log"
        s = self.src
        (s / "bench").mkdir(parents=True)
        for name in ("run-auto.sh", "claim-run-dirs.sh", "attempt-record.py"):
            shutil.copy(BENCH / name, s / "bench" / name)
        (s / "bench" / "README.md").write_text(
            "**当前版本：v9**（合成）\n\n- **T1**：`合成任务一`\n- **T2**：`合成任务二`\n- **T3**：`合成任务三`\n", encoding="utf-8")  # fmt: skip
        for rel, text in {
            ".mcp.json": '{"mcpServers":{}}\n', "CLAUDE.md": "# 根说明\n", ".claude/settings.json": "{}\n",
            "docs/improvement-plan.md": "会被删掉\n", "docs/keep.md": "保留\n", "CHANGELOG.md": "会被删掉\n",
            "src/main/java/com/example/harness/domain/CLAUDE.md": "# 分层说明\n",
            "src/main/java/com/example/harness/domain/Order.java": "class Order {}\n",
            "mvnw": "#!/bin/sh\necho 'BUILD SUCCESS (stub)'\nexit 0\n",
            ".github/scripts/check-migration-immutability.sh": "#!/bin/sh\necho ok\nexit 0\n",
        }.items():  # fmt: skip
            p = s / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        (s / "mvnw").chmod(0o755)
        if leak:
            (s / "docs" / "notes.md").write_text(f"这里写着 {LEAK_WORD}\n", encoding="utf-8")
        home, cfg = tmp / "home", tmp / "cfg"
        home.mkdir()
        cfg.mkdir()
        (cfg / "settings.json").write_text("{}")  # 已存在 → 脚本不读真实的用户配置
        stub = tmp / "fake-claude"
        stub.write_text(STUB_CLAUDE)
        stub.chmod(0o755)
        self.env = {
            "PATH": os.environ["PATH"], "HOME": str(home), "BENCH_ROOT": str(self.root), "BENCH_CLAUDE_CONFIG": str(cfg),
            "CLAUDE_BIN": str(stub), "BENCH_STUB_LOG": str(self.stub_log), "BENCH_JOBS": "4", "BENCH_TIMEOUT": "20",
            "BENCH_POLL": "1", "LC_ALL": "C.UTF-8", "GIT_CONFIG_NOSYSTEM": "1",
        }  # fmt: skip
        git = ["git", "-C", str(s), "-c", "user.name=t", "-c", "user.email=t@localhost"]
        # gc.auto / maintenance.auto：不让提交之后的后台维护进程和测试里的并发 git 操作抢锁
        for args in (["init", "-q", "-b", "main"], ["config", "gc.auto", "0"], ["config", "maintenance.auto", "false"],
                     ["add", "-A"], ["commit", "-q", "-m", "synthetic"]):  # fmt: skip
            subprocess.run([*git, *args], check=True, env=self.env, capture_output=True)
        self.head = subprocess.run([*git, "rev-parse", "HEAD"], check=True, env=self.env, capture_output=True, text=True).stdout.strip()

    def cmd(self, *args: str, base: str = "HEAD") -> list[str]:
        return ["bash", str(self.src / "bench" / "run-auto.sh"), base, *args]

    def run(self, *args: str, base: str = "HEAD", **env: str) -> subprocess.CompletedProcess:
        return subprocess.run(self.cmd(*args, base=base), env={**self.env, **env}, capture_output=True, text=True, timeout=180)

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.src), *args], check=True, env=self.env, capture_output=True, text=True).stdout.strip()

    def dirs(self, task: str, conf: str, seq: int) -> tuple[Path, Path]:
        base = self.root / f"{_today()}-{task}-{conf}-{seq}"
        return base, Path(str(base) + ".out")

    def calls(self) -> list[str]:
        return self.stub_log.read_text().split("\n")[:-1] if self.stub_log.exists() else []


@pytest.fixture()
def sandbox(tmp_path: Path) -> Sandbox:
    if not shutil.which("git"):
        pytest.skip("需要 git")
    return Sandbox(tmp_path)


@pytest.fixture(scope="module")
def analyze():
    spec = importlib.util.spec_from_file_location("bench_analyze_pipeline_under_test", BENCH / "analyze.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


# ---------- 成功路径 ----------


def test_success_c2_export_selfcheck_collect_and_records(sandbox, analyze):
    r = sandbox.run("T1", "C2", "1", BENCH_TIMEOUT="20")
    run, out = sandbox.dirs("T1", "C2", 1)
    assert r.returncode == 0, r.stderr
    # 导出 + 裁剪：答案文件删掉，Harness 留着，只有一个提交
    assert not (run / "bench").exists() and not (run / "docs/improvement-plan.md").exists() and not (run / "CHANGELOG.md").exists()
    assert (run / "CLAUDE.md").exists() and (run / ".claude/settings.json").exists() and (run / "docs/keep.md").exists()
    log = subprocess.run(["git", "-C", str(run), "rev-list", "--count", "HEAD"], capture_output=True, text=True, env=sandbox.env)
    assert log.stdout.strip() == "1"
    # 自检 + 收集
    assert (out / "selfcheck.txt").read_text() == ""
    assert "exit=0" in (out / "mvn-verify.log").read_text() and "exit=0" in (out / "ci-local.log").read_text()
    assert "notes/added-by-stub.txt" in (out / "final.diff").read_text()
    # 开始记录：占到目录时就知道的条件
    start = _json(out / "attempt-start.json")
    assert {k: start[k] for k in ("schema", "task", "conf", "seq", "task_set", "base_arg", "base_commit", "exec_mode",
                                  "model_arg", "timeout_limit_s", "batch_id", "run_dir", "out_dir")} == {
        "schema": 1, "task": "T1", "conf": "C2", "seq": "1", "task_set": "v9", "base_arg": "HEAD",
        "base_commit": sandbox.head, "exec_mode": "headless-auto-approve", "model_arg": "sonnet",
        "timeout_limit_s": 20, "batch_id": None, "run_dir": str(run), "out_dir": str(out)}  # fmt: skip
    # 结束记录：脚本跑完，停在最后一步
    end = _json(out / "attempt-end.json")
    assert (end["script_status"], end["stage"], end["exit_code"], end["signal"], end["timed_out"], end["model_exit"]) == (
        "completed", "done", 0, None, False, 0)  # fmt: skip
    # summary.json 与 analyze.py：原口径下是有效样本
    meta = _json(out / "summary.json")["meta"]
    assert (meta["base_commit"], meta["task_set"], meta["timeout_limit_s"], meta["timed_out"], meta["claude_code_version"]) == (
        sandbox.head, "v9", 20, False, "9.9.9")  # fmt: skip
    res = analyze.analyze(out)
    assert (res["status"], res["missing"]) == ("valid", [])
    assert sandbox.calls() == ["T1-C2-1 ok"]


def test_success_c0_strips_harness(sandbox):
    r = sandbox.run("T2", "C0", "1")
    run, out = sandbox.dirs("T2", "C0", 1)
    assert r.returncode == 0, r.stderr
    assert not (run / "CLAUDE.md").exists() and not (run / ".claude").exists()
    assert not (run / "src/main/java/com/example/harness/domain/CLAUDE.md").exists()
    assert (run / "src/main/java/com/example/harness/domain/Order.java").exists() and (run / ".github").exists()
    assert _json(out / "attempt-end.json")["script_status"] == "completed"


# ---------- 各种不成功 ----------


def test_selfcheck_abort_stops_before_model(tmp_path):
    sb = Sandbox(tmp_path, leak=True)
    r = sb.run("T1", "C2", "1")
    _, out = sb.dirs("T1", "C2", 1)
    end = _json(out / "attempt-end.json")
    assert r.returncode == 1
    assert (end["script_status"], end["stage"], end["exit_code"]) == ("failed", "selfcheck", 1)
    assert (out / "selfcheck.txt").read_text().strip() == "docs/notes.md"
    assert not (out / "summary.json").exists() and not (out / "transcript.jsonl").exists()
    assert sb.calls() == []  # 没有启动会话


def test_api_error_script_completes_but_sample_is_void(sandbox, analyze):
    r = sandbox.run("T1", "C0", "1", BENCH_STUB_MODE="api-error")
    _, out = sandbox.dirs("T1", "C0", 1)
    end = _json(out / "attempt-end.json")
    assert r.returncode == 0  # 脚本本身跑完了
    assert (end["script_status"], end["stage"], end["timed_out"]) == ("completed", "done", False)
    res = analyze.analyze(out)  # 样本按原口径作废
    assert (res["status"], res["void_reasons"]) == ("void", ["API 错误或没有工具调用"])


def test_timeout_script_completes_but_sample_is_void(sandbox, analyze):
    r = sandbox.run("T3", "C2", "1", BENCH_STUB_MODE="hang", BENCH_TIMEOUT="1")
    _, out = sandbox.dirs("T3", "C2", 1)
    end = _json(out / "attempt-end.json")
    assert r.returncode == 0
    assert (end["script_status"], end["stage"], end["timed_out"]) == ("completed", "done", True)
    assert end["model_exit"] != 0  # 会话进程是被终止的
    meta = _json(out / "summary.json")["meta"]
    assert (meta["timeout_limit_s"], meta["timed_out"]) == (1, True)
    res = analyze.analyze(out)
    assert (res["status"], res["void_reasons"]) == ("void", ["超时"])
    assert "timed_out=1" in (out / "runner.log").read_text()  # 旧格式的日志行还在


def test_session_exits_midway_is_recorded(sandbox):
    """会话进程自己中途退出（非零、没有 result 消息）：退出码记进结束记录，收集照常做完。"""
    r = sandbox.run("T1", "C2", "2", BENCH_STUB_MODE="crash")
    _, out = sandbox.dirs("T1", "C2", 2)
    end = _json(out / "attempt-end.json")
    assert r.returncode == 0
    assert (end["script_status"], end["stage"], end["model_exit"], end["timed_out"]) == ("completed", "done", 3, False)
    assert _json(out / "summary.json")["result"] is None  # 没有 result 消息


def _wait_for(path: Path, timeout: float = 30) -> None:
    deadline = time.time() + timeout
    while not path.exists():
        assert time.time() < deadline, f"等不到 {path}"
        time.sleep(0.05)


def test_runner_interrupted_by_signal_leaves_end_record(sandbox, analyze, capsys):
    proc = subprocess.Popen(sandbox.cmd("T2", "C2", "1"), env={**sandbox.env, "BENCH_STUB_MODE": "hang"},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # fmt: skip
    _, out = sandbox.dirs("T2", "C2", 1)
    _wait_for(out / "transcript.jsonl")
    proc.send_signal(signal.SIGTERM)
    assert proc.wait(timeout=30) == 143
    end = _json(out / "attempt-end.json")
    assert (end["script_status"], end["stage"], end["exit_code"], end["signal"]) == ("interrupted", "model", 143, "TERM")
    assert not (out / "summary.json").exists()
    # analyze.py 照旧把没有 summary.json 的目录算"未完成"
    assert analyze.main(["--table", str(out)]) == 0
    assert "未完成 1" in capsys.readouterr().err


def test_runner_killed_leaves_start_record_only(sandbox):
    """脚本被强杀、来不及收尾：没有结束记录，但开始记录里的基线 / 配置 / 上限还在。"""
    proc = subprocess.Popen(sandbox.cmd("T2", "C0", "2"), env={**sandbox.env, "BENCH_STUB_MODE": "hang", "BENCH_TIMEOUT": "77"},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)  # fmt: skip
    _, out = sandbox.dirs("T2", "C0", 2)
    _wait_for(out / "transcript.jsonl")
    os.killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=30)
    assert not (out / "attempt-end.json").exists() and not (out / "summary.json").exists()
    start = _json(out / "attempt-start.json")
    assert (start["task"], start["conf"], start["base_commit"], start["timeout_limit_s"]) == ("T2", "C0", sandbox.head, 77)


def test_start_record_failure_aborts_before_export(sandbox):
    r = sandbox.run("T1", "C0", "2", BENCH_TIMEOUT="abc")  # 上限不是数字 → 开始记录写不出来
    run, out = sandbox.dirs("T1", "C0", 2)
    end = _json(out / "attempt-end.json")
    assert r.returncode == 1
    assert (end["script_status"], end["stage"]) == ("failed", "start-record")
    assert not (out / "attempt-start.json").exists() and list(run.iterdir()) == []
    assert sandbox.calls() == []


# ---------- 记录一次写入、不覆盖 ----------


def _write(dest: Path, *pairs: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(REC), "write", str(dest), *pairs], capture_output=True, text=True, timeout=30)


def test_record_write_once_keeps_earlier_content(tmp_path):
    dest = tmp_path / "attempt-end.json"
    assert _write(dest, "schema:=1", "who=first", "n:=5", "empty=", "flag:=true").returncode == 0
    assert _json(dest) == {"schema": 1, "who": "first", "n": 5, "empty": None, "flag": True}
    r = _write(dest, "who=second")
    assert r.returncode == 3 and "已存在，不覆盖" in r.stderr
    assert _json(dest)["who"] == "first"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["attempt-end.json"]  # 不留临时文件


def test_record_concurrent_writers_only_one_wins(tmp_path):
    for i in range(10):
        dest = tmp_path / f"r{i}.json"
        procs = [subprocess.Popen([sys.executable, str(REC), "write", str(dest), f"who=w{j}", "pad=" + "x" * 4000],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for j in range(6)]  # fmt: skip
        codes = sorted(p.wait(timeout=30) for p in procs)
        assert codes == [0] + [3] * 5, f"round {i}: {codes}"
        rec = _json(dest)  # 内容是某一个写入者的完整记录，不是拼出来的
        assert rec["who"] in {f"w{j}" for j in range(6)} and rec["pad"] == "x" * 4000
    assert sorted(p.name for p in tmp_path.iterdir()) == [f"r{i}.json" for i in range(10)]


def test_record_write_failure_creates_nothing(tmp_path):
    assert _write(tmp_path / "missing-dir" / "a.json", "x=1").returncode == 1
    r = _write(tmp_path / "bad.json", "n:=not-json")
    assert r.returncode == 2 and not (tmp_path / "bad.json").exists()
    if os.geteuid() != 0:
        ro = tmp_path / "ro"
        ro.mkdir()
        (ro / "earlier.json").write_text("earlier")
        ro.chmod(0o555)
        try:
            assert _write(ro / "a.json", "x=1").returncode == 1
            assert sorted(p.name for p in ro.iterdir()) == ["earlier.json"] and (ro / "earlier.json").read_text() == "earlier"
        finally:
            ro.chmod(0o755)


def test_existing_batch_record_is_not_overwritten_and_run_reports_failure(sandbox):
    batch = sandbox.tmp / "batch-x"
    batch.mkdir()
    (batch / "T1-C2-1.json").write_text("earlier record")
    r = sandbox.run("T1", "C2", "1", BENCH_BATCH_DIR=str(batch))
    _, out = sandbox.dirs("T1", "C2", 1)
    assert r.returncode == 1  # 记录写不进去：不把这次当成功
    assert (batch / "T1-C2-1.json").read_text() == "earlier record"
    assert _json(out / "attempt-end.json")["script_status"] == "completed"  # 自己目录里的记录照写


# ---------- all 模式：脚本状态与样本有效性分开 ----------


def test_all_mode_reports_script_status_separately_from_sample_validity(sandbox, analyze, capsys):
    occupied_run, occupied_out = sandbox.dirs("T3", "C0", 2)
    occupied_out.mkdir(parents=True)
    (occupied_out / "summary.json").write_text("earlier result")  # 已有结果 → 这个子运行占不到目录
    modes = json.dumps({"T1-C0-1": "api-error", "T2-C2-1": "hang"})
    r = sandbox.run("all", BENCH_STUB_MODES=modes, BENCH_TIMEOUT="3")
    assert r.returncode != 0
    assert (occupied_out / "summary.json").read_text() == "earlier result" and not occupied_run.exists()

    batches = list((sandbox.root / ".batches").iterdir())
    assert len(batches) == 1
    b = _json(batches[0] / "batch.json")
    assert b["script_status_counts"] == {"completed": 11, "failed": 1, "interrupted": 0, "no-end-record": 0}
    by = {c["name"]: c for c in b["children"]}
    assert (by["T3-C0-2"]["script_status"], by["T3-C0-2"]["stage"], by["T3-C0-2"].get("out_dir")) == ("failed", "claim", None)
    # 脚本跑完 ≠ 样本有效：这两个子脚本都"跑完"了
    assert by["T1-C0-1"]["script_status"] == by["T2-C2-1"]["script_status"] == "completed"
    assert by["T2-C2-1"]["timed_out"] is True and by["T1-C0-1"]["timed_out"] is False
    assert "跑完 11 / 失败 1 / 被信号中断 0 / 没有结束记录 0" in r.stdout and "样本有效性不在这里判" in r.stdout
    assert len((batches[0] / "plan.txt").read_text().splitlines()) == 12

    # 样本有效性仍由 analyze.py 按原口径判：11 个跑完的里 9 个有效、2 个作废
    outs = sorted(c["out_dir"] for c in b["children"] if c.get("out_dir"))
    status = {Path(o).name[11:-4]: analyze.analyze(Path(o))["status"] for o in outs}
    assert sorted(k for k, v in status.items() if v == "void") == ["T1-C0-1", "T2-C2-1"]
    assert sum(v == "valid" for v in status.values()) == 9
    assert all(_json(Path(o) / "attempt-start.json")["batch_id"] == batches[0].name for o in outs)
    capsys.readouterr()


# ---------- 基线只解析一次：运行途中引用被移动 ----------

MOVE_REF_WRAPPER = r"""#!/bin/sh
# 测试用：在"读完提示词之后、导出副本之前"给合成仓库加一个提交（HEAD 移动），然后照常占用目录。
# 用自己的临时 index 和 commit-tree / update-ref 造提交，不碰仓库共用的 index：all 模式下别的子脚本
# 同时在读这个仓库，CI 上出现过 git add 拿不到 index.lock 的情况。
d=$(cd "$(dirname "$0")/.." && pwd)
if mkdir "$d/.ref-moved" 2>/dev/null; then
  (
    GIT_INDEX_FILE="$d/.git/ref-move.index"; export GIT_INDEX_FILE
    git -C "$d" read-tree HEAD &&
      readme=$(git -C "$d" show HEAD:bench/README.md | sed 's/v9/v10/; s/合成任务/换过的任务/' | git -C "$d" hash-object -w --stdin) &&
      late=$(echo late | git -C "$d" hash-object -w --stdin) &&
      git -C "$d" update-index --add --cacheinfo "100644,$readme,bench/README.md" \
        --cacheinfo "100644,$late,added-after-start.txt" &&
      tree=$(git -C "$d" write-tree) &&
      new=$(git -C "$d" -c user.name=t -c user.email=t@localhost commit-tree "$tree" -p HEAD -m "moved after start") &&
      git -C "$d" update-ref HEAD "$new"
  ) || exit 97
fi
exec bash "$d/bench/claim-run-dirs.real.sh" "$@"
"""


def _move_ref_during_run(sb: Sandbox) -> Path:
    bench = sb.src / "bench"
    (bench / "claim-run-dirs.sh").rename(bench / "claim-run-dirs.real.sh")
    (bench / "claim-run-dirs.sh").write_text(MOVE_REF_WRAPPER, encoding="utf-8")
    prompts = sb.tmp / "prompts.log"
    sb.env["BENCH_STUB_PROMPTS"] = str(prompts)
    return prompts


def test_base_is_pinned_once_when_ref_moves_before_export(sandbox):
    prompts = _move_ref_during_run(sandbox)
    r = sandbox.run("T1", "C2", "1")
    run, out = sandbox.dirs("T1", "C2", 1)
    assert r.returncode == 0, r.stderr
    assert sandbox.git("rev-parse", "HEAD") != sandbox.head  # 引用确实在途中被移动了
    # 提示词、任务集版本、导出的副本、两份记录都来自开跑时解析出的那个提交
    assert not (run / "added-after-start.txt").exists()
    assert prompts.read_text(encoding="utf-8") == "合成任务一\n"
    start, meta = _json(out / "attempt-start.json"), _json(out / "summary.json")["meta"]
    assert (start["base_arg"], start["base_commit"], start["task_set"]) == ("HEAD", sandbox.head, "v9")
    assert (meta["base_commit"], meta["task_set"]) == (sandbox.head, "v9")
    assert f"base={sandbox.head} " in (out / "runner.log").read_text()


def test_all_mode_pins_base_once_in_parent(sandbox):
    """all 模式：第一个子脚本移动了 HEAD，其余 11 个仍用父脚本固定的那个提交。"""
    prompts = _move_ref_during_run(sandbox)
    r = sandbox.run("all")
    assert r.returncode == 0, r.stderr
    assert sandbox.git("rev-parse", "HEAD") != sandbox.head
    batch = next((sandbox.root / ".batches").iterdir())
    plan = (batch / "plan.txt").read_text().splitlines()
    assert len(plan) == 12 and all(line.startswith(sandbox.head + " ") for line in plan)
    outs = sorted(p for p in sandbox.root.iterdir() if p.name.endswith(".out"))
    assert len(outs) == 12
    for out in outs:
        start, meta = _json(out / "attempt-start.json"), _json(out / "summary.json")["meta"]
        assert (start["base_arg"], start["base_commit"], start["task_set"]) == ("HEAD", sandbox.head, "v9"), out.name
        assert (meta["base_commit"], meta["task_set"]) == (sandbox.head, "v9"), out.name
        assert not (Path(str(out)[:-4]) / "added-after-start.txt").exists(), out.name
    assert sorted(set(prompts.read_text(encoding="utf-8").split("\n")[:-1])) == ["合成任务一", "合成任务三", "合成任务二"]


def test_unresolvable_base_exits_clearly_and_claims_nothing(sandbox):
    r = sandbox.run("T1", "C0", "1", base="no-such-ref")
    assert r.returncode == 1
    assert "基线解析不出 commit" in r.stderr and "'no-such-ref'" in r.stderr  # 原输入留在报错里
    assert not sandbox.root.exists() or list(sandbox.root.iterdir()) == []
    r = sandbox.run("all", base="no-such-ref")
    assert r.returncode == 1 and "'no-such-ref'" in r.stderr
    assert not sandbox.root.exists() or list(sandbox.root.iterdir()) == []  # 连批次目录都不建
    assert sandbox.calls() == []


# ---------- 收集出错要传播 ----------

FAKE_GIT = r"""#!/bin/sh
# 测试用：只在"会话已经跑过的副本"里让指定的 git 子命令失败，其余原样交给真正的 git
if [ -f "$PWD.out/transcript.jsonl" ]; then
  case "$BENCH_FAKE_GIT_FAIL $*" in
    "diff diff --cached "*) echo "diff --git a/half b/half"; exit 42 ;;
    "add add -A") exit 43 ;;
  esac
fi
exec "$BENCH_REAL_GIT" "$@"
"""


@pytest.mark.parametrize(("fail", "logged"), [("diff", "git diff exit=42"), ("add", "git add exit=43")])
def test_collect_failure_is_propagated_and_leaves_no_usable_result(sandbox, analyze, capsys, fail, logged):
    fake_bin = sandbox.tmp / "fake-bin"
    fake_bin.mkdir()
    (fake_bin / "git").write_text(FAKE_GIT)
    (fake_bin / "git").chmod(0o755)
    r = sandbox.run("T1", "C2", "1", PATH=f"{fake_bin}:{sandbox.env['PATH']}", BENCH_REAL_GIT=shutil.which("git"),
                    BENCH_FAKE_GIT_FAIL=fail)  # fmt: skip
    _, out = sandbox.dirs("T1", "C2", 1)
    end = _json(out / "attempt-end.json")
    assert r.returncode == 1
    assert (end["script_status"], end["stage"], end["exit_code"], end["timed_out"]) == ("failed", "collect", 1, False)
    # 不留半截的 diff，也不发布 summary.json：这次尝试不会被分析成有效样本
    assert not (out / "final.diff").exists() and not (out / "final.diff.partial").exists()
    assert not (out / "summary.json").exists()
    assert "ABORT: 收集失败" in (out / "runner.log").read_text() and logged in (out / "runner.log").read_text()
    assert (out / "mvn-verify.log").exists()  # 出错之前收集到的照常保留
    assert analyze.main(["--table", str(out)]) == 0
    assert "有效 0" in (err := capsys.readouterr().err) and "未完成 1" in err
