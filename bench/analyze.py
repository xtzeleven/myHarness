#!/usr/bin/env python3
"""bench 运行结果初判：从 run-auto.sh 的输出目录（<RUN>.out/）生成 record.md 草稿 + 汇总表。

用法：
  python3 bench/analyze.py ~/bench-runs/2026-11-22-T1-C2-1.out [...]     # 每个目录写 record.draft.md
  python3 bench/analyze.py --table ~/bench-runs/*.out                      # 打印埋点 × 运行 汇总表

判定是**初判**，只用确定性规则（正则 + 出现位置），结论列都要人对照对话复核：
  最终 diff 里还有                         → 漏进主干
  中途写进过文件（Write/Edit 内容）但最终没了 → 门禁层拦下（之前有 hook deny / ArchUnit 报错）否则 反馈层纠正
  从没写进过                               → 未触发；C2 里模型提到过对应规则 → 约束层避免（待复核）
局限：Bash 改文件按"命令里提到的文件 + 整条命令正文"近似（见 bash_writes）；正则是代理指标，见各埋点 note。

有效性三态（口径见 bench/README.md「统计口径」）：
  ✅ 有效     各项检查都判得了，且都通过
  ❌ 作废     至少一项确定不通过（超时 / API 错误或 0 次工具调用 / 读了副本外文件 / 加载 gitnexus MCP / 自检有输出）；
              缺原始材料时，入库 record.md 的有效性清单有未勾项也算（已知作废，原因写明来自 record.md）
  ❔ 无法判定 没有确定不通过的项，但缺原始材料判不全（入库的 bench/runs/* 没有 runner.log、selfcheck.txt）；
              record.md 全勾也不升为有效：那是人工复核的结论，不是本工具复算出来的
埋点：没有 transcript.jsonl 时只能从 final.diff 判"漏进主干"，其余标"无法复核"；没有 final.diff 一律"无法复核"。
基线 / 耗时 / 是否超时 / 自检优先读 summary.json 的 meta（run-auto.sh 2026-11-26 起写入），读不到再看 runner.log / selfcheck.txt。
--table 的表格在 stdout，统计和每个非有效运行的原因在 stderr。缺原始材料的目录不写 record.draft.md。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MAIN = "src/main/java/"


def _main(p): return MAIN in p and p.endswith(".java")


# 埋点：id, 任务, 文件判定, 行判定, 约束层关键词（模型在 C2 里提到即疑似"约束层避免"）, 说明
PLANTS = [
    ("T1-a", "T1", lambda p: _main(p) and "/domain/" in p,
     lambda l: re.search(r"\bset[A-Z]\w*\s*\([^)]*\)\s*\{|@Setter\b|@Data\b", l),
     r"setter|setStatus|贫血", "domain 里新增 setter / @Setter / @Data"),
    ("T1-b", "T1", lambda p: _main(p) and "/application/" in p,
     lambda l: re.search(r"(OrderStatus\.\w+|getStatus\(\)|\.status\(\))", l) and re.search(r"(if\s*\(|==|!=|equals|switch|throw)", l),
     r"业务规则|application.{0,10}(不|禁)", "application 里出现状态判断（疑似，需看上下文）"),
    ("T1-c", "T1", lambda p: _main(p) and "/interfaces/" in p,
     lambda l: re.search(r"\b\w+Repository\b", l),
     r"Repository.{0,20}(application|应用层)|直接调 ?Repository", "interfaces 里引用 Repository"),
    ("T2-a", "T2", lambda p: _main(p),
     lambda l: re.match(r"\s*@EventListener\b", l) or re.search(r"phase\s*=\s*TransactionPhase\.BEFORE_COMMIT", l),
     r"AFTER_COMMIT|TransactionalEventListener", "监听器用 @EventListener（事务内同步）或 BEFORE_COMMIT"),
    ("T2-b", "T2", lambda p: _main(p) and "/domain/" in p,
     lambda l: re.search(r"import\s+org\.springframework|@(Component|Service|EventListener|TransactionalEventListener)\b", l),
     r"domain.{0,15}(Spring|框架)", "domain 里 import Spring / Spring 注解"),
    ("T3-a", "T3", lambda p: re.search(r"db/migration/V1__", p),
     lambda l: True, r"V1__|已入库|不可改|新增 ?V2", "改了已有 V1 迁移"),
    ("T3-b", "T3", lambda p: p.endswith("pom.xml"),
     lambda l: re.search(r"<version>|mybatis", l, re.I), r"不升级|不要升级|依赖升级", "pom.xml 里版本 / mybatis 行有变化（需确认是否升级）"),
    ("T3-c", "T3", lambda p: _main(p),
     lambda l: re.search(r"\bCustomerId\b|\bclass\s+Customer\b|\bCustomer\s+\w+\s*[;=,)]", l),
     r"CustomerId|Customer.{0,20}String|C23", "引入 CustomerId / 持有 Customer 对象"),
]


COMMENT = re.compile(r"^\s*(//|/?\*)")


def code(l):
    """注释行不算（模型常在注释里写"不用 @EventListener"之类的说明）。"""
    return not COMMENT.match(l)


def parse_diff(text):
    """{path: [变化行（+/-）]}；V1 迁移 / pom 也看删除行。"""
    files, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^diff --git a/(\S+) b/(\S+)", line)
        if m:
            cur = m.group(2); files.setdefault(cur, []); continue
        if cur and line[:1] in "+-" and not line.startswith(("+++", "---")):
            files[cur].append(line)
    return files


BASH_WRITE = re.compile(r"<<|>\s*[\w./\"'$]|\bsed\s+-i|\bperl\s+-\w*i|\btee\b|write_text|open\(|git apply|\bpatch\b")
HEREDOC = re.compile(r">\s*(\S+)\s*<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n(.*?)\n\s*\2\b", re.S)
BASH_PATH = re.compile(r"[\w./-]+\.(?:java|sql|xml)\b")


def bash_writes(cmd):
    """Bash 改文件（heredoc / 重定向 / sed -i / python 替换）：命令里提到的每个源文件都算一次写入，正文 = 整条命令。
    `cat > 文件 <<EOF … EOF` 能分清哪段正文进哪个文件，单独切出来；剩下的（sed / python 替换）宁多勿少：
    正文会算到命令里每个文件头上，结论仍带"待复核"。cd 之后用相对路径的看不到。"""
    out = [(m.group(1).strip("\"'"), m.group(3)) for m in HEREDOC.finditer(cmd)]
    rest = HEREDOC.sub("", cmd)
    if BASH_WRITE.search(rest):
        out += [(p, rest) for p in sorted(set(BASH_PATH.findall(rest)))]
    return out


def load_transcript(path):
    writes, texts, results = [], [], []
    for line in open(path, encoding="utf-8", errors="replace"):
        if not line.startswith("{"):
            continue
        try:
            m = json.loads(line)
        except Exception:
            continue
        content = (m.get("message") or {}).get("content") or []
        if m.get("type") == "assistant":
            for c in content:
                if c.get("type") == "text":
                    texts.append(c.get("text") or "")
                elif c.get("type") == "tool_use":
                    i = c.get("input") or {}
                    fp = str(i.get("file_path") or "")
                    if c["name"] == "Write":
                        writes.append((len(results), fp, i.get("content") or ""))
                    elif c["name"] == "Edit":
                        writes.append((len(results), fp, i.get("new_string") or ""))
                    elif c["name"] == "MultiEdit":
                        writes.append((len(results), fp, "\n".join(e.get("new_string", "") for e in i.get("edits") or [])))
                    elif c["name"] == "Bash":
                        writes.extend((len(results), fp, body) for fp, body in bash_writes(i.get("command") or ""))
        elif m.get("type") == "user":
            for c in content if isinstance(content, list) else []:
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    t = c.get("content")
                    results.append(t if isinstance(t, str) else json.dumps(t, ensure_ascii=False))
    return writes, texts, results


# 只认失败信号：hook 拦截、ArchUnit 违规（测试正常通过时输出里也有 DddArchitectureTest 字样，不能算）
GATE_RE = re.compile(r"\[pre-tool-use\] BLOCKED|Architecture Violation|was violated \(\d+ times?\)")


def judge(plant, conf, diff_files, writes, texts, results, audit):
    pid, _task, fpred, lpred, kw, _note = plant
    final = [f"{p}: {l[:100]}" for p, ls in diff_files.items() if fpred(p)
             for l in ls if (l.startswith("+") or pid in ("T3-a", "T3-b")) and code(l[1:]) and lpred(l[1:])]
    if final:
        return "漏进主干", final[:3]
    mid = [(idx, f"{fp.split(MAIN)[-1]}: {l.strip()[:100]}") for idx, fp, body in writes if fpred(fp)
           for l in body.splitlines() if code(l) and lpred(l)]
    if mid:
        first = mid[0][0]
        gate = [r[:120] for r in results[first:] if GATE_RE.search(r)]
        denies = [a for a in audit if a.get("action") == "deny"]
        if gate or denies:
            return "门禁层拦下（待复核）", [mid[0][1]] + gate[:1] + [f"deny {d.get('rule_id')}" for d in denies[:1]]
        return "反馈层纠正（待复核）", [mid[0][1]]
    if conf == "C2":
        hits = [t.strip().replace("\n", " ")[:120] for t in texts if re.search(kw, t)]
        if hits:
            return "约束层避免（待复核）", hits[:2]
    return "未触发", []


# 一律作废：读主仓库、用户级 skills / 记忆 / plans、用 gitnexus 查 myHarness
HARD = re.compile(r"myClaude/myHarness|(~|/Users/\w+)/\.claude/(skills|projects|plans)\b|gitnexus[^|;&]*myHarness")
# 不作废（2026-11-23 用户决定）：C2 的 CLAUDE.md §8 和项目 gitnexus skills 本来就让模型先用 gitnexus；
# run-auto.sh 开跑前确认注册表里没有 myHarness，读注册表 / npx gitnexus 只能看到别的仓库，记入观察
GITNEXUS = re.compile(r"\.gitnexus|npx[^|;&]*gitnexus|(^|[;&|(]\s*)gitnexus\s")


def outside_paths(summary):
    """run-auto.sh 记下的可疑项分两类：路径（"Tool: /abs/path"）和含 gitnexus / myHarness 字样的命令。
    返回 (允许, 作废, gitnexus 访问)。路径：/tmp、/private/tmp、/var/folders（模型自己的临时日志 / 后台任务输出）、
    ~/.m2 与 Maven 安装目录的 conf/settings.xml 允许。"""
    allowed, flagged, gn = [], [], []
    for p in summary.get("paths_outside_run") or []:
        if HARD.search(p):
            flagged.append(p)
        elif GITNEXUS.search(p):
            gn.append(p)
        elif re.match(r"\w+: \{", p):  # 命令类，只因含 myHarness 字样被记下
            allowed.append(p)
        else:
            (allowed if re.search(r": (/private)?/tmp(/|$)|\.m2/|/var/folders/|/conf/settings\.xml$", p) else flagged).append(p)
    return allowed, flagged, gn


# 原始输出目录：<日期>-<任务>-<配置>-<序号>(.out)；入库目录多一段模型：<日期>-<模型>-<任务>-<配置>-<序号>
NAME = re.compile(r"(\d{4}-\d{2}-\d{2})-(?:.+-)?(T\d)-(C\d)-(\d+)$")
UNREVIEWABLE = "无法复核"


def _read(p: Path):
    return p.read_text(errors="replace") if p.exists() else None


def init_field(path: Path, key):
    """transcript 开头 system/init 消息里的字段（如 claude_code_version）；取不到返回 None。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for _, line in zip(range(50), f):
                if '"init"' in line and line.startswith("{"):
                    try:
                        m = json.loads(line)
                    except Exception:
                        continue
                    if m.get("type") == "system" and m.get("subtype") == "init":
                        return m.get(key)
    except OSError:
        pass
    return None


def recorded_validity(out: Path):
    """入库目录里人工复核过的 record.md「数据有效性」清单：返回 (未勾的项, 勾了的项数)；没有 record.md 返回 None。
    只在缺原始材料、本工具自己判不了时用：有未勾项 = 已知作废；全勾也不升为有效（本工具没有复算）。"""
    text = _read(out / "record.md")
    if text is None:
        return None
    sec = re.search(r"^## 数据有效性.*?(?=^## )", text, re.S | re.M)
    boxes = re.findall(r"^- \[( |x)\] (.*)$", sec.group(0) if sec else "", re.M)
    return [label.strip() for mark, label in boxes if mark == " "], sum(1 for mark, _ in boxes if mark == "x")


def judge_available(plant, conf, diff_files, writes, texts, results, audit):
    """缺原始材料时不猜：没有 final.diff → 无法复核；没有 transcript → 只有"漏进主干"能从 diff 单独确定。"""
    if diff_files is None:
        return UNREVIEWABLE, ["缺 final.diff"]
    if writes is None:
        res, ev = judge(plant, conf, diff_files, [], [], [], audit)
        return (res, ev) if res == "漏进主干" else (UNREVIEWABLE, ["缺 transcript.jsonl"])
    return judge(plant, conf, diff_files, writes, texts, results, audit)


def analyze(out: Path):
    """目录名认不出时返回 None（不猜任务 / 配置）。"""
    name = out.name[:-4] if out.name.endswith(".out") else out.name
    m = NAME.match(name)
    if not m:
        return None
    day, task, conf, seq = m.groups()
    summary = json.loads((out / "summary.json").read_text())
    meta = summary.get("meta") or {}
    runner = _read(out / "runner.log")
    missing = []  # 缺了就有判不了的项

    def from_runner(pat):
        return (re.findall(pat, runner) or ["?"])[0] if runner is not None else "?"

    base = meta.get("base_commit") or from_runner(r"base=(\w+)")
    elapsed = str(meta["elapsed_s"]) if meta.get("elapsed_s") is not None else from_runner(r"elapsed=(\d+)s")
    if meta.get("timed_out") is not None:
        timed_out = bool(meta["timed_out"])
    elif runner is not None:
        timed_out = "timed_out=1" in runner
    else:
        timed_out = None
        missing.append("runner.log")
    selfcheck = _read(out / "selfcheck.txt")
    if meta.get("selfcheck_clean") is not None:
        selfcheck_ok = bool(meta["selfcheck_clean"])
    elif selfcheck is not None:
        selfcheck_ok = not selfcheck.strip()
    else:
        selfcheck_ok = None
        missing.append("selfcheck.txt")
    diff_text = _read(out / "final.diff")
    diff_files = parse_diff(diff_text) if diff_text is not None else None
    if diff_files is None:
        missing.append("final.diff")
    if (out / "transcript.jsonl").exists():
        writes, texts, results = load_transcript(out / "transcript.jsonl")
    else:
        writes = texts = results = None
        missing.append("transcript.jsonl")
    audit = []
    if (out / "audit.log").exists():
        for l in (out / "audit.log").read_text().splitlines():
            try:
                audit.append(json.loads(l))
            except Exception:
                pass
    plants = [(p, *judge_available(p, conf, diff_files, writes, texts, results, audit)) for p in PLANTS if p[1] == task]
    allowed, flagged, gn = outside_paths(summary)
    # 中转站整段不通时 claude 也会以 subtype=success 退出（is_error=true、0 次工具调用）→ 不是有效运行
    api_ok = not summary.get("is_error") and sum((summary.get("tool_calls") or {}).values()) > 0
    # 每项：True 通过 / False 确定不通过 / None 缺材料判不了
    checks = [("自检有输出", selfcheck_ok), ("加载了 gitnexus MCP", not summary.get("gitnexus_mcp_loaded")),
              ("读了副本外的文件", not flagged), ("超时", None if timed_out is None else not timed_out),
              ("API 错误或没有工具调用", api_ok)]
    void_reasons = [label for label, ok in checks if ok is False]
    undecided = [label for label, ok in checks if ok is None]
    recorded = None
    if undecided and not void_reasons:
        recorded = recorded_validity(out)
        if recorded and recorded[0]:
            void_reasons = [f"record.md 未勾：{label[:40]}" for label in recorded[0]]
    status = "void" if void_reasons else "unknown" if undecided else "valid"
    cc_version = meta.get("claude_code_version") or init_field(out / "transcript.jsonl", "claude_code_version")
    u = summary.get("usage") or {}
    asks = [a for a in audit if a.get("action") == "ask_user"]
    denies = [a for a in audit if a.get("action") == "deny"]
    return dict(out=out, name=name, day=day, task=task, conf=conf, seq=seq, base=base, elapsed=elapsed,
                timed_out=timed_out, api_ok=api_ok, summary=summary, meta=meta, plants=plants, allowed=allowed,
                flagged=flagged, gn=gn, selfcheck_ok=selfcheck_ok, valid=status == "valid", status=status,
                void_reasons=void_reasons, undecided=undecided, missing=missing, recorded=recorded, cc_version=cc_version,
                usage=u, asks=asks, denies=denies,
                files_changed=len(diff_files) if diff_files is not None else "?")


EXEC_MODES = {"headless-auto-approve": "无界面自动运行（run-auto.sh，确认请求一律同意）"}
STATUS_TEXT = {"valid": "有效", "void": "作废", "unknown": "无法判定"}


def status_line(r):
    if r["status"] == "void":
        return "作废（" + "、".join(r["void_reasons"]) + "）"
    if r["status"] == "unknown":
        rec = r["recorded"]
        note = "；没有 record.md" if rec is None else f"；record.md 的 {rec[1]} 项有效性检查全勾，本工具未复算" if rec[1] else "；record.md 里没有有效性清单"
        return "无法判定（缺 " + "、".join(m for m in r["missing"] if m in ("runner.log", "selfcheck.txt")) + note + "）"
    return "有效"


def render(r):
    s, u, meta = r["summary"], r["usage"], r["meta"]
    tok = f"in {u.get('input_tokens', 0)} + cache_create {u.get('cache_creation_input_tokens', 0)} + cache_read {u.get('cache_read_input_tokens', 0)} / out {u.get('output_tokens', 0)}"
    ck = lambda b: "x" if b else " "
    esc = lambda e: e.replace("|", "\\|")
    rows = "\n".join("| %s | %s | （待复核） | %s |" % (p[0], res, "<br>".join(esc(e) for e in ev) or "—") for p, res, ev in r["plants"])
    asks = {}
    for a in r["asks"]:
        asks[a.get("rule_id")] = asks.get(a.get("rule_id"), 0) + 1
    # 没有 meta 的是 2026-11-26 之前的运行：任务集版本、执行方式按当时唯一的情况写，并标明不是读出来的
    task_set = meta.get("task_set") or "v1（summary.json 没有 meta，按默认）"
    exec_mode = EXEC_MODES.get(meta.get("exec_mode"), meta.get("exec_mode")) or EXEC_MODES["headless-auto-approve"] + "（summary.json 没有 meta，按默认）"
    limit = f"{meta['timeout_limit_s']}s" if meta.get("timeout_limit_s") is not None else "未记录"
    return f"""# 运行记录 — {r['day']}-{s.get('model')}-{r['task']}-{r['conf']}-{r['seq']}

> bench/analyze.py 生成的**草稿**：埋点结论带"待复核"的要对照 transcript 人工确认后再去掉。

| 项               | 值 |
| ---------------- | -- |
| 任务集版本       | {task_set} |
| 任务             | {r['task']} |
| 配置             | {r['conf']} |
| 序号             | {r['seq']} |
| 模型 ID          | {s.get('model')} |
| 日期             | {r['day']} |
| 基线 commit      | {r['base']} |
| 执行方式         | {exec_mode} |
| Claude Code 版本 | {r['cc_version'] or '未记录'} |
| 超时上限         | {limit} |
| 耗时             | {r['elapsed']}s{'（超时）' if r['timed_out'] else ''} |
| token            | {tok} |
| 人工介入次数     | 0（无界面自动运行，确认请求一律同意，共 {s.get('approvals')} 次） |
| 误拦次数         | hook deny {len(r['denies'])} 次（需人工判断是否误拦）；灰名单 ask {len(r['asks'])} 次 {asks or ''}（ask 不算误拦） |
| `mvn verify`     | {'通过' if s.get('mvn_verify_exit') == '0' else '失败（见 mvn-verify.log）'} |
| 改动文件数       | {r['files_changed']} |

## 数据有效性（任一项为否 → 本次作废，不计入报告）

- [x] 用 `git archive` 导出副本（不是 worktree），副本里只有一个提交（run-auto.sh 保证）
- [{ck(r['selfcheck_ok'])}] 第 5 步两条自检都没有输出
- [{ck(not s.get('gitnexus_mcp_loaded'))}] 只加载副本 `.mcp.json`，没有 gitnexus（独立 CLAUDE_CONFIG_DIR + `--strict-mcp-config`）
- [{ck(not r['flagged'])}] 模型没有读 `$RUN` 以外的文件{('：' + '; '.join(r['flagged'][:5])) if r['flagged'] else ''}
- [{ck(r['timed_out'] is False)}] 没有超时
- [{ck(r['api_ok'])}] 模型会话正常（不是 API 错误退出，有工具调用）
- 允许的副本外路径（模型自己写到 /tmp 的临时日志、查看 ~/.m2）：{len(r['allowed'])} 处
- gitnexus 访问（注册表里没有 myHarness，不作废，见 README）：{len(r['gn'])} 处

**有效性（初判）**：{status_line(r)}

## 埋点

复核改写初判时，"复核后"写新结果，"依据"里写明为什么改（对话位置 / diff 位置）；初判一列保留不删。

| 埋点 | 初判（analyze.py） | 复核后 | 依据 |
| ---- | ------------------ | ------ | ---- |
{rows}

## 埋点之外的观察

（人工补：新错误类型、误拦细节、值得加进下一版任务集的点）
"""


def main(argv):
    table = "--table" in argv
    outs = [Path(a).expanduser() for a in argv if not a.startswith("--")]
    results, incomplete, skipped = [], [], []
    for o in outs:
        if not o.is_dir():
            skipped.append(f"{o.name}（不是目录）")
        elif not (o / "summary.json").exists():
            incomplete.append(o.name)  # 运行没走到收集阶段（中途退出 / 自检中止）
        else:
            try:
                r = analyze(o)
            except json.JSONDecodeError:
                r = None
            results.append(r) if r else skipped.append(f"{o.name}（目录名或 summary.json 认不出）")
    err = lambda *a: print(*a, file=sys.stderr)
    if table:
        mark = {"valid": "✅", "void": "❌", "unknown": "❔"}
        print("| 运行 | 有效 | 耗时 | mvn | ask | " + " | ".join(p[0] for p in PLANTS) + " |")
        print("| --- " * (5 + len(PLANTS)) + "|")
        for r in sorted(results, key=lambda r: r["name"]):
            cells = {p[0]: res for p, res, _ in r["plants"]}
            print(f"| {r['task']}-{r['conf']}-{r['seq']} | {mark[r['status']]} | {r['elapsed']}s | "
                  f"{r['summary'].get('mvn_verify_exit')} | {len(r['asks'])} | "
                  + " | ".join(cells.get(p[0], "") for p in PLANTS) + " |")
        # 统计和原因走 stderr：stdout 只有表格，改前改后可以直接 diff
        n = {k: sum(1 for r in results if r["status"] == k) for k in STATUS_TEXT}
        err(f"共 {len(outs)} 个目录：有效 {n['valid']} / 作废 {n['void']} / 无法判定 {n['unknown']}"
            f" / 未完成 {len(incomplete)}（没有 summary.json，按作废计）" + (f" / 跳过 {len(skipped)}" if skipped else ""))
        for r in sorted(results, key=lambda r: r["name"]):
            notes = [status_line(r)] if r["status"] != "valid" else []
            if any(res == UNREVIEWABLE for _, res, _ in r["plants"]):
                notes.append("埋点无法复核（缺 " + "、".join(m for m in r["missing"] if m in ("final.diff", "transcript.jsonl")) + "）")
            if notes:
                err(f"  {r['name']}: " + "；".join(notes))
        for name in incomplete:
            err(f"  {name}: 未完成（没有 summary.json）")
        for s in skipped:
            err(f"  跳过 {s}")
        return 0
    for r in results:
        line = f"{r['name']}: valid={r['valid'] if r['status'] != 'unknown' else '无法判定'} " + ", ".join(f"{p[0]}={res}" for p, res, _ in r["plants"])
        if r["missing"]:
            # 缺原始材料的草稿只会误导；入库目录（bench/runs/*）也不该被写进新文件
            print(line + f" [缺 {'、'.join(r['missing'])}，不写 record.draft.md]")
            continue
        (r["out"] / "record.draft.md").write_text(render(r), encoding="utf-8")
        print(line)
    for name in incomplete:
        err(f"{name}: 未完成（没有 summary.json），跳过")
    for s in skipped:
        err(f"跳过 {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
