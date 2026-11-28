"""bench/analyze.py 与 run-auto.sh 元数据段的回归测试：纯本地，只用临时合成数据。

不启动模型，不跑 run-auto.sh。覆盖：
- 旧格式（summary.json 没有 meta，靠 runner.log / selfcheck.txt）
- 新格式（summary.json 带 meta；生成段从 run-auto.sh 里原样切出来执行）
- 有效性三态（有效 / 作废 / 无法判定）和缺原始材料时的处理
- 当前判定规则不变；入库的 bench/runs/* 能读、不崩、不被写入

本文件会随 C2 副本进入对照实验，所以正文里不能出现副本自检（run-auto.sh 第 5 步）
要找的那几个词；需要用到时在运行时拼出来。
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
# 对照实验的副本会删掉 bench/ 但保留本目录：那里没有被测对象，整份跳过而不是报错
pytestmark = pytest.mark.skipif(not (REPO / "bench" / "analyze.py").exists(), reason="没有 bench/（对照实验副本）")
BASE = "0123456789abcdef0123456789abcdef01234567"  # 合成的基线 SHA
SETTER = "set" + "Status"  # 运行时拼，见文件头说明
DOMAIN_FILE = "src/main/java/com/example/harness/order/domain/Order.java"

ENV = {
    "BENCH_META_BASE": BASE, "BENCH_META_TASK_SET": "v1", "BENCH_META_RUNNER_COMMIT": "abc1234",
    "BENCH_META_TASK": "T1", "BENCH_META_CONF": "C2", "BENCH_META_SEQ": "1", "BENCH_META_DAY": "2026-12-01",
    "BENCH_META_TIMEOUT": "5400", "BENCH_META_ELAPSED": "321", "BENCH_META_TIMED_OUT": "0",
    "BENCH_META_STARTED": "2026-12-01T00:00:00Z", "BENCH_META_MODEL_ARG": "sonnet",
    "BENCH_META_CLI_VERSION": "1.2.3 (Claude Code)",
}  # fmt: skip


def _diff(line: str) -> str:
    return (f"diff --git a/{DOMAIN_FILE} b/{DOMAIN_FILE}\n--- a/{DOMAIN_FILE}\n+++ b/{DOMAIN_FILE}\n"
            f"@@ -1,2 +1,3 @@\n+    {line}\n")  # fmt: skip


DIFF_CLEAN = _diff("public void cancel() { this.status = OrderStatus.CANCELLED; }")
DIFF_SETTER = _diff(f"public void {SETTER}(OrderStatus s) {{ this.status = s; }}")


@pytest.fixture(scope="module")
def analyze():
    spec = importlib.util.spec_from_file_location("bench_analyze_under_test", REPO / "bench" / "analyze.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def summary_py() -> str:
    """run-auto.sh 里生成 summary.json 的那段 Python，原样切出来。"""
    script = (REPO / "bench" / "run-auto.sh").read_text(encoding="utf-8")
    m = re.search(r"<<'PY' > \"\$OUT/summary\.json\"\n(.*?)\nPY\n", script, re.S)
    assert m, "run-auto.sh 里找不到 summary 生成段"
    return m.group(1)


def _transcript(run_dir: Path, body: str, tools: bool, is_error: bool, with_result: bool) -> str:
    j = lambda o: json.dumps(o, ensure_ascii=False)  # noqa: E731
    lines = [j({"type": "system", "subtype": "init", "model": "synthetic-model-1", "claude_code_version": "9.9.9"})]
    if tools:
        lines.append(j({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "开始实现"},
            {"type": "tool_use", "name": "Write", "input": {"file_path": f"{run_dir}/{DOMAIN_FILE}", "content": body}},
        ]}}))  # fmt: skip
        lines.append(j({"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}}))
    if with_result:
        lines.append(j({"type": "result", "subtype": "success", "is_error": is_error,
                        "usage": {"input_tokens": 10, "output_tokens": 20}}))  # fmt: skip
    return "\n".join(lines) + "\n"


@pytest.fixture()
def make_out(tmp_path: Path, summary_py: str):
    """造一个 <RUN>.out 并用 run-auto.sh 的原始代码生成 summary.json。meta_env=None → 环境里没有任何 BENCH_META_*。"""

    def _make(name: str, meta_env: dict | None = ENV, *, diff: str | None = DIFF_CLEAN, selfcheck: str | None = "",
              body: str = "public void cancel() {}", tools: bool = True, is_error: bool = False,
              with_result: bool = True, runner_log: str | None = None, strip_meta: bool = False) -> Path:  # fmt: skip
        out, run = tmp_path / name, tmp_path / name.replace(".out", "")
        out.mkdir(parents=True)
        (out / "transcript.jsonl").write_text(_transcript(run, body, tools, is_error, with_result), encoding="utf-8")
        (out / "mvn-verify.log").write_text("BUILD SUCCESS\nexit=0\n")
        (out / "ci-local.log").write_text("exit=0\n")
        if diff is not None:
            (out / "final.diff").write_text(diff)
        if selfcheck is not None:
            (out / "selfcheck.txt").write_text(selfcheck)
        if runner_log is not None:
            (out / "runner.log").write_text(runner_log)
        env = {k: v for k, v in os.environ.items() if not k.startswith("BENCH_META_")}
        env.update(meta_env or {})
        r = subprocess.run([sys.executable, "-", str(out), str(run), str(tmp_path / "cfg")], input=summary_py,
                           capture_output=True, text=True, env=env)  # fmt: skip
        assert r.returncode == 0, r.stderr
        summary = json.loads(r.stdout)
        if strip_meta:  # 2026-11-26 之前的 summary.json 没有 meta 键
            summary.pop("meta")
        (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False))
        return out

    return _make


def _committed(src: Path, name: str, keep=("summary.json", "final.diff", "mvn-verify.log"), record: str | None = None) -> Path:
    """入库形态：目录名多一段模型，只留一部分文件。"""
    d = src.parent / name
    d.mkdir()
    for f in keep:
        if (src / f).exists():
            shutil.copy(src / f, d / f)
    if record is not None:
        (d / "record.md").write_text(record, encoding="utf-8")
    return d


RECORD = ("# 运行记录\n\n## 数据有效性（任一项为否 → 本次作废，不计入报告）\n\n- [x] 自检都没有输出\n"
          "- [{}] 没有超时\n- 允许的副本外路径：2 处\n\n## 结论\n\n| a | b |\n")  # fmt: skip
LEGACY_LOG = "[T1-C0-1] start 2026-12-02T00:00:00Z base=abc1234 model=sonnet\n[T1-C0-1] end 2026-12-02T00:10:00Z elapsed=600s timed_out={}\n"


def _results(r) -> dict:
    return {p[0]: res for p, res, _ in r["plants"]}


# ---------- 新格式：run-auto.sh 写出的 meta ----------


def test_meta_block_fields_and_types(make_out):
    s = json.loads((make_out("2026-12-01-T1-C2-1.out") / "summary.json").read_text())
    assert s["meta"] == {
        "schema": 1, "task_set": "v1", "task": "T1", "conf": "C2", "seq": 1, "day": "2026-12-01",
        "base_commit": BASE, "runner_commit": "abc1234", "exec_mode": "headless-auto-approve", "model_arg": "sonnet",
        "claude_code_version": "9.9.9",  # 会话 init 消息里的，优先于 --version 的输出
        "timeout_limit_s": 5400, "elapsed_s": 321, "timed_out": False, "started_at": "2026-12-01T00:00:00Z",
        "selfcheck_clean": True,
    }  # fmt: skip
    # 原有顶层键都还在，旧读者不受影响
    assert {"model", "result", "is_error", "usage", "tool_calls", "gitnexus_mcp_loaded", "paths_outside_run",
            "audit_actions", "approvals", "mvn_verify_exit", "migration_check_exit", "api_errors"} <= set(s)  # fmt: skip
    assert s["model"] == "synthetic-model-1"


def test_meta_missing_values_are_null_not_defaults(make_out):
    meta = json.loads((make_out("2026-12-02-T1-C0-1.out", None) / "summary.json").read_text())["meta"]
    for key in ("task_set", "base_commit", "timeout_limit_s", "elapsed_s", "timed_out", "seq"):
        assert meta[key] is None, key
    assert meta["exec_mode"] == "headless-auto-approve"  # 脚本自身的属性，不依赖环境


def test_meta_run_is_valid_without_runner_log(analyze, make_out):
    r = analyze.analyze(make_out("2026-12-01-T1-C2-1.out"))
    assert (r["status"], r["valid"], r["missing"]) == ("valid", True, [])
    assert (r["base"], r["elapsed"], r["timed_out"], r["cc_version"]) == (BASE, "321", False, "9.9.9")
    assert set(_results(r).values()) == {"未触发"}


def test_draft_carries_run_conditions(analyze, make_out):
    draft = analyze.render(analyze.analyze(make_out("2026-12-01-T1-C2-1.out")))
    for expected in ("| 任务集版本       | v1 |", "| Claude Code 版本 | 9.9.9 |", "| 超时上限         | 5400s |",
                     f"| 基线 commit      | {BASE} |", "无界面自动运行（run-auto.sh", "**有效性（初判）**：有效",
                     "| 初判（analyze.py） | 复核后 | 依据 |"):  # fmt: skip
        assert expected in draft, expected


# ---------- 旧格式：没有 meta，靠 runner.log / selfcheck.txt ----------


def test_legacy_raw_dir_valid(analyze, make_out):
    out = make_out("2026-12-02-T1-C0-1.out", None, strip_meta=True, runner_log=LEGACY_LOG.format(0))
    r = analyze.analyze(out)
    assert (r["status"], r["base"], r["elapsed"], r["timed_out"]) == ("valid", "abc1234", "600", False)
    draft = analyze.render(r)
    assert "v1（summary.json 没有 meta，按默认）" in draft and "| 超时上限         | 未记录 |" in draft


def test_legacy_raw_dir_timeout_is_void(analyze, make_out):
    out = make_out("2026-12-02-T1-C0-2.out", None, strip_meta=True, runner_log=LEGACY_LOG.format(1), with_result=False)
    r = analyze.analyze(out)
    assert (r["status"], r["void_reasons"]) == ("void", ["超时"])


def test_meta_null_values_fall_back_to_runner_log(analyze, make_out):
    """meta 在但值是 null（环境变量没传到）时，仍按 runner.log 判，不当成"没超时"。"""
    out = make_out("2026-12-02-T1-C0-3.out", None, runner_log=LEGACY_LOG.format(1), with_result=False)
    r = analyze.analyze(out)
    assert (r["status"], r["void_reasons"], r["elapsed"]) == ("void", ["超时"], "600")


# ---------- 三态：作废的各种原因 ----------


def test_void_api_error_or_no_tool_calls(analyze, make_out):
    r = analyze.analyze(make_out("2026-12-04-T1-C0-9.out", tools=False, is_error=True))
    assert (r["status"], r["void_reasons"]) == ("void", ["API 错误或没有工具调用"])


def test_void_selfcheck_has_output(analyze, make_out):
    r = analyze.analyze(make_out("2026-12-05-T1-C2-3.out", selfcheck="docs/x.md\n"))
    assert r["status"] == "void" and "自检有输出" in r["void_reasons"]


def test_void_read_outside_run_dir(analyze, make_out):
    out = make_out("2026-12-05-T1-C2-4.out")
    s = json.loads((out / "summary.json").read_text())
    s["paths_outside_run"] = ["Read: /Users/someone/elsewhere/notes.md", "Bash: /tmp/own-build.log"]
    (out / "summary.json").write_text(json.dumps(s))
    r = analyze.analyze(out)
    assert (r["status"], r["void_reasons"]) == ("void", ["读了副本外的文件"])
    assert len(r["allowed"]) == 1  # 模型自己写到 /tmp 的日志不算


# ---------- 缺原始材料（入库形态） ----------


def test_committed_layout_with_meta(analyze, make_out):
    """目录名带模型段也认得；有 meta 就判得出有效性；没有 transcript 的结果标无法复核。"""
    r = analyze.analyze(_committed(make_out("2026-12-01-T1-C2-1.out"), "2026-12-01-synthetic-model-1-T1-C2-1"))
    assert (r["status"], r["task"], r["conf"], r["seq"]) == ("valid", "T1", "C2", "1")
    assert all(res == "无法复核" and ev == ["缺 transcript.jsonl"] for _, res, ev in r["plants"])


def test_committed_layout_with_meta_timeout(analyze, make_out):
    src = make_out("2026-12-03-T1-C2-2.out", {**ENV, "BENCH_META_TIMED_OUT": "1", "BENCH_META_ELAPSED": "5412"},
                   with_result=False)  # fmt: skip
    r = analyze.analyze(_committed(src, "2026-12-03-synthetic-model-1-T1-C2-2"))
    assert (r["status"], r["void_reasons"], r["elapsed"]) == ("void", ["超时"], "5412")


def test_committed_layout_without_meta_three_cases(analyze, make_out):
    src = make_out("2026-12-06-T1-C0-1.out", None, strip_meta=True)
    unchecked = analyze.analyze(_committed(src, "2026-12-06-synthetic-model-1-T1-C0-1", record=RECORD.format(" ")))
    all_checked = analyze.analyze(_committed(src, "2026-12-06-synthetic-model-1-T1-C0-2", record=RECORD.format("x")))
    no_record = analyze.analyze(_committed(src, "2026-12-06-synthetic-model-1-T1-C0-3"))
    # record.md 有未勾项 → 已知作废，原因注明来自 record.md
    assert (unchecked["status"], unchecked["void_reasons"]) == ("void", ["record.md 未勾：没有超时"])
    # 全勾 → 仍是无法判定：那是人工结论，不是本工具复算的
    assert (all_checked["status"], all_checked["valid"]) == ("unknown", False)
    assert "全勾，本工具未复算" in analyze.status_line(all_checked)
    # 没有 record.md → 无法判定，并说明
    assert no_record["status"] == "unknown" and "没有 record.md" in analyze.status_line(no_record)
    assert (no_record["elapsed"], no_record["base"]) == ("?", "?")
    assert no_record["missing"] == ["runner.log", "selfcheck.txt", "transcript.jsonl"]


def test_violation_in_final_diff_still_detected_without_transcript(analyze, make_out):
    src = make_out("2026-12-07-T1-C0-4.out", diff=DIFF_SETTER)
    r = analyze.analyze(_committed(src, "2026-12-07-synthetic-model-1-T1-C0-4"))
    assert _results(r) == {"T1-a": "漏进主干", "T1-b": "无法复核", "T1-c": "无法复核"}


def test_missing_final_diff(analyze, make_out):
    r = analyze.analyze(_committed(make_out("2026-12-08-T1-C0-5.out"), "2026-12-08-synthetic-model-1-T1-C0-5",
                                   keep=("summary.json",)))  # fmt: skip
    assert all(res == "无法复核" and ev == ["缺 final.diff"] for _, res, ev in r["plants"])
    assert r["files_changed"] == "?"


def test_unrecognised_directory_name_is_not_guessed(analyze, tmp_path):
    d = tmp_path / "notes"
    d.mkdir()
    (d / "summary.json").write_text("{}")
    assert analyze.analyze(d) is None


# ---------- 当前判定规则不变 ----------


def test_judgement_rules_unchanged(analyze, make_out):
    setter_line = f"public void {SETTER}(OrderStatus s) {{ this.status = s; }}"
    leaked = analyze.analyze(make_out("2026-12-10-T1-C0-1.out", diff=DIFF_SETTER, body=setter_line))
    corrected = analyze.analyze(make_out("2026-12-10-T1-C0-2.out", diff=DIFF_CLEAN, body=setter_line))
    never = analyze.analyze(make_out("2026-12-10-T1-C0-3.out", diff=DIFF_CLEAN))
    assert _results(leaked)["T1-a"] == "漏进主干"  # 最终 diff 里还有
    assert _results(corrected)["T1-a"] == "反馈层纠正（待复核）"  # 中途写过，最终没了，没有门禁失败信号
    assert _results(never)["T1-a"] == "未触发"  # 从没写过
    assert all(r["status"] == "valid" for r in (leaked, corrected, never))


def test_known_false_positive_junit_setup_is_current_behaviour(analyze, make_out):
    """已知误报（首批 T1-C0-3）：写进 domain 文件的正文里有 JUnit 的 `void setUp() {` 时，
    setter 规则会命中。这里只固定现状，没有评价对错；要修规则时改这条断言并重新对照历史输出。"""
    r = analyze.analyze(make_out("2026-12-10-T1-C0-4.out", body="@BeforeEach\nvoid setUp() {\n}"))
    assert _results(r)["T1-a"] == "反馈层纠正（待复核）"


# ---------- 命令行：--table 与草稿 ----------


def test_table_counts_three_states_separately(analyze, make_out, tmp_path, capsys):
    full = make_out("2026-12-01-T1-C2-1.out")
    legacy = make_out("2026-12-06-T1-C0-1.out", None, strip_meta=True)
    dirs = [
        full,
        _committed(full, "2026-12-01-synthetic-model-1-T1-C2-1"),
        _committed(legacy, "2026-12-06-synthetic-model-1-T1-C0-1", record=RECORD.format(" ")),
        _committed(legacy, "2026-12-06-synthetic-model-1-T1-C0-2", record=RECORD.format("x")),
        _committed(legacy, "2026-12-06-synthetic-model-1-T1-C0-3"),
    ]
    (tmp_path / "2026-12-09-T3-C2-1.out").mkdir()  # 没走到收集阶段
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "summary.json").write_text("{}")  # 目录名认不出
    (tmp_path / "stray.log").write_text("x")  # 不是目录
    extra = [tmp_path / "2026-12-09-T3-C2-1.out", tmp_path / "notes", tmp_path / "stray.log"]

    assert analyze.main(["--table", *map(str, dirs + extra)]) == 0
    out, err = capsys.readouterr()
    lines = out.splitlines()
    # stdout 只有表格，表头和列数与改前一致
    assert lines[0] == "| 运行 | 有效 | 耗时 | mvn | ask | T1-a | T1-b | T1-c | T2-a | T2-b | T3-a | T3-b | T3-c |"
    assert all(line.startswith("| ") for line in lines)
    rows = lines[2:]
    assert len(rows) == 5
    assert [sum(mark in row for row in rows) for mark in ("✅", "❌", "❔")] == [2, 1, 2]
    assert "共 8 个目录：有效 2 / 作废 1 / 无法判定 2 / 未完成 1（没有 summary.json，按作废计） / 跳过 2" in err


def test_draft_written_only_when_raw_material_is_complete(analyze, make_out, capsys):
    full = make_out("2026-12-01-T1-C2-1.out")
    committed = _committed(full, "2026-12-01-synthetic-model-1-T1-C2-1")
    before = sorted(p.name for p in committed.iterdir())
    assert analyze.main([str(full), str(committed)]) == 0
    out, _ = capsys.readouterr()
    assert (full / "record.draft.md").exists()
    assert sorted(p.name for p in committed.iterdir()) == before  # 入库形态的目录不被写入
    assert "不写 record.draft.md" in out


# ---------- 入库的历史记录：能读、不崩、不被写入 ----------


def test_committed_history_is_readable_and_untouched(analyze, capsys):
    runs = sorted(p for p in (REPO / "bench" / "runs").iterdir() if p.is_dir())
    first_batch = [p for p in runs if p.name < "2026-11-24"]  # 首批 14 个；以后新增的不受这条约束
    assert len(first_batch) == 14
    before = {p: sorted((f.name, f.stat().st_size) for f in p.iterdir()) for p in first_batch}

    results = {p.name: analyze.analyze(p) for p in first_batch}
    assert all(results.values())
    void = sorted(name for name, r in results.items() if r["status"] == "void")
    # 首批入库记录没有 meta，也没有 runner.log：记录里标了超时的三次是已知作废，其余无法判定
    assert void == ["2026-11-22-claude-fable-5-2-T1-C0-2", "2026-11-22-claude-fable-5-2-T2-C0-2",
                    "2026-11-23-claude-fable-5-2-T3-C2-7"]  # fmt: skip
    assert sum(r["status"] == "unknown" for r in results.values()) == 11
    assert not any(r["valid"] for r in results.values())  # 没有原始材料，不替人工复核下"有效"的结论
    assert all(res == "无法复核" for r in results.values() for _, res, _ in r["plants"])

    assert analyze.main(["--table", *map(str, first_batch)]) == 0
    assert analyze.main(list(map(str, first_batch))) == 0
    capsys.readouterr()
    assert before == {p: sorted((f.name, f.stat().st_size) for f in p.iterdir()) for p in first_batch}
