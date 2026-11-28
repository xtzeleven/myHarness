"""bench 输出目录占用的回归测试：纯本地，只用临时目录和合成仓库。不启动模型，不做真实运行。

- claim-run-dirs.sh：成功、重复、任一目录已存在、并发只有一方成功，已有产物不被删改
- run-auto.sh：在临时合成仓库里跑脚本副本，claude 换成桩，所有子运行都停在目录占用这一步；
  验证单次冲突的退出码和 all 模式的失败传播，并确认桩没有被调用过
"""

from __future__ import annotations

import datetime
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
CLAIM = REPO / "bench" / "claim-run-dirs.sh"
# 对照实验的副本会删掉 bench/ 但保留本目录：那里没有被测对象，整份跳过而不是报错
pytestmark = pytest.mark.skipif(not CLAIM.exists(), reason="没有 bench/（对照实验副本）")


def _claim(run: Path, out: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(CLAIM), str(run), str(out)], capture_output=True, text=True, timeout=30)


def _tree(root: Path) -> list[tuple[str, str]]:
    """目录下所有条目及文件内容，用来断言"已有的东西原样保留"。"""
    return sorted((str(p.relative_to(root)), p.read_text() if p.is_file() else "<dir>") for p in root.rglob("*"))


# ---------- claim-run-dirs.sh ----------


def test_claim_creates_both_dirs_empty(tmp_path):
    run, out = tmp_path / "root" / "2026-12-01-T1-C0-1", tmp_path / "root" / "2026-12-01-T1-C0-1.out"
    r = _claim(run, out)  # 上级目录还不存在也能建（首次运行）
    assert r.returncode == 0, r.stderr
    assert run.is_dir() and out.is_dir()
    assert list(run.iterdir()) == [] and list(out.iterdir()) == []
    assert r.stderr == ""


def test_claim_twice_fails_and_keeps_first_result(tmp_path):
    run, out = tmp_path / "r", tmp_path / "r.out"
    assert _claim(run, out).returncode == 0
    (run / "src.txt").write_text("copy")
    (out / "summary.json").write_text('{"kept": true}')
    before = _tree(tmp_path)

    r = _claim(run, out)
    assert r.returncode == 1
    assert "已存在，不覆盖" in r.stderr and str(run) in r.stderr
    assert _tree(tmp_path) == before


def test_claim_fails_when_only_run_dir_exists(tmp_path):
    run, out = tmp_path / "r", tmp_path / "r.out"
    run.mkdir()
    (run / "leftover.txt").write_text("x")
    before = _tree(tmp_path)

    r = _claim(run, out)
    assert r.returncode == 1 and str(run) in r.stderr
    assert not out.exists()  # 没占到 RUN 就不去碰 OUT
    assert _tree(tmp_path) == before


def test_claim_fails_when_only_out_dir_exists_and_rolls_back_own_run_dir(tmp_path):
    run, out = tmp_path / "r", tmp_path / "r.out"
    out.mkdir()
    (out / "transcript.jsonl").write_text("earlier run")
    before = _tree(tmp_path)

    r = _claim(run, out)
    assert r.returncode == 1 and str(out) in r.stderr and "已存在，不覆盖" in r.stderr
    assert not run.exists()  # 本次刚建的空 RUN 用 rmdir 撤回，不留半个占用
    assert _tree(tmp_path) == before


def test_claim_does_not_remove_a_preexisting_empty_run_dir(tmp_path):
    """已存在的空目录不是本次建的：报冲突，但不删它。"""
    run, out = tmp_path / "r", tmp_path / "r.out"
    run.mkdir()
    r = _claim(run, out)
    assert r.returncode == 1
    assert run.is_dir() and not out.exists()


def test_claim_fails_when_target_is_a_file(tmp_path):
    run, out = tmp_path / "r", tmp_path / "r.out"
    out.write_text("not a directory")
    r = _claim(run, out)
    assert r.returncode == 1 and "已存在，不覆盖" in r.stderr
    assert out.read_text() == "not a directory" and not run.exists()


def test_claim_usage_error(tmp_path):
    r = subprocess.run(["bash", str(CLAIM), str(tmp_path / "only-one")], capture_output=True, text=True, timeout=30)
    assert r.returncode == 2 and "用法" in r.stderr
    assert list(tmp_path.iterdir()) == []


def test_claim_concurrent_only_one_wins(tmp_path):
    """同一对目录并发占用：每一轮恰好一个成功，其余报冲突，两个目录都在且是空的。"""
    for i in range(15):
        run, out = tmp_path / f"r{i}", tmp_path / f"r{i}.out"
        procs = [subprocess.Popen(["bash", str(CLAIM), str(run), str(out)], stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE, text=True) for _ in range(8)]  # fmt: skip
        results = [(p.wait(timeout=30), p.stderr.read()) for p in procs]
        for p in procs:
            p.stderr.close()
        codes = sorted(code for code, _ in results)
        assert codes == [0] + [1] * 7, f"round {i}: {codes}"
        assert all("已存在，不覆盖" in err for code, err in results if code == 1)
        assert run.is_dir() and out.is_dir()
        assert list(run.iterdir()) == [] and list(out.iterdir()) == []


# ---------- run-auto.sh：在合成仓库里跑脚本副本，claude 是桩 ----------


def _days() -> list[str]:
    today = datetime.date.today()
    return [today.isoformat(), (today + datetime.timedelta(days=1)).isoformat()]  # 跨零点时两天都占上


@pytest.fixture()
def sandbox(tmp_path: Path):
    """临时合成仓库 + 独立 HOME / 输出根目录 / 配置目录；CLAUDE_BIN 指向一个只留痕迹的桩。"""
    if not shutil.which("git"):
        pytest.skip("需要 git")
    src = tmp_path / "repo"
    (src / "bench").mkdir(parents=True)
    for name in ("run-auto.sh", "claim-run-dirs.sh"):
        shutil.copy(REPO / "bench" / name, src / "bench" / name)
    (src / "bench" / "README.md").write_text(
        "**当前版本：v1**（合成）\n\n- **T1**：`合成任务一`\n- **T2**：`合成任务二`\n- **T3**：`合成任务三`\n",
        encoding="utf-8",
    )
    home, cfg, root = tmp_path / "home", tmp_path / "cfg", tmp_path / "runs"
    home.mkdir()
    cfg.mkdir()
    (cfg / "settings.json").write_text("{}")  # 已存在 → 脚本不会去读真实的用户配置
    marker = tmp_path / "claude-was-called"
    stub = tmp_path / "fake-claude"
    stub.write_text(f"#!/bin/sh\necho called >> '{marker}'\nexit 1\n")
    stub.chmod(0o755)
    env = {
        "PATH": os.environ["PATH"], "HOME": str(home), "BENCH_ROOT": str(root), "BENCH_CLAUDE_CONFIG": str(cfg),
        "CLAUDE_BIN": str(stub), "BENCH_JOBS": "4", "BENCH_TIMEOUT": "5", "LC_ALL": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
    }  # fmt: skip
    git = ["git", "-C", str(src), "-c", "user.name=bench-test", "-c", "user.email=bench-test@localhost"]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True, env=env, capture_output=True)
    subprocess.run([*git, "add", "-A"], check=True, env=env, capture_output=True)
    subprocess.run([*git, "commit", "-q", "-m", "synthetic"], check=True, env=env, capture_output=True)

    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(src / "bench" / "run-auto.sh"), "HEAD", *args], env=env,
                              capture_output=True, text=True, timeout=120)  # fmt: skip

    return run, root, marker


def _occupy(root: Path, task: str, conf: str, seq: int, *, run_dir: bool = True, out_dir: bool = True) -> None:
    for day in _days():
        base = root / f"{day}-{task}-{conf}-{seq}"
        if run_dir:
            base.mkdir(parents=True)
            (base / "keep.txt").write_text(f"copy {task}-{conf}-{seq}")
        if out_dir:
            out = Path(str(base) + ".out")
            out.mkdir(parents=True)
            (out / "summary.json").write_text(f"result {task}-{conf}-{seq}")


def test_single_run_refuses_to_overwrite_existing_output(sandbox):
    run, root, marker = sandbox
    _occupy(root, "T1", "C0", 1, run_dir=False)  # 只有 .out 在（比如副本被手工清掉了）
    before = _tree(root)

    r = run("T1", "C0", "1")
    assert r.returncode == 1
    assert "已存在，不覆盖" in r.stderr
    assert _tree(root) == before  # 已有结果原样保留，也没留下新建的空副本目录
    assert not marker.exists()  # 没走到启动 claude 那一步


def test_single_run_with_unknown_task_does_not_claim_a_sequence_number(sandbox):
    run, root, marker = sandbox
    r = run("T9", "C0", "1")
    assert r.returncode == 1 and "找不到 T9 的提示词" in r.stderr
    assert not root.exists() or list(root.iterdir()) == []
    assert not marker.exists()


def test_all_mode_propagates_child_failures(sandbox):
    """12 个子运行的目录都已存在：每个都报冲突，all 整体以非零退出，已有结果一个不少。"""
    run, root, marker = sandbox
    for task in ("T1", "T2", "T3"):
        for conf in ("C0", "C2"):
            for seq in (1, 2):
                _occupy(root, task, conf, seq)
    before = _tree(root)

    r = run("all")
    assert r.returncode != 0  # 改前这里固定是 0
    assert r.stderr.count("已存在，不覆盖") == 12
    assert "FAILED: all 模式有子运行没跑起来或中止" in r.stderr
    assert _tree(root) == before
    assert not marker.exists()
