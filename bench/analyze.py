#!/usr/bin/env python3
"""bench 运行结果初判：从 run-auto.sh 的输出目录（<RUN>.out/）生成 record.md 草稿 + 汇总表。

用法：
  python3 bench/analyze.py ~/bench-runs/2026-11-22-T1-C2-1.out [...]     # 每个目录写 record.draft.md
  python3 bench/analyze.py --table ~/bench-runs/*.out                      # 打印埋点 × 运行 汇总表

判定是**初判**，只用确定性规则（正则 + 出现位置），结论列都要人对照对话复核：
  最终 diff 里还有                         → 漏进主干
  中途写进过文件（Write/Edit 内容）但最终没了 → 门禁层拦下（之前有 hook deny / ArchUnit 报错）否则 反馈层纠正
  从没写进过                               → 未触发；C2 里模型提到过对应规则 → 约束层避免（待复核）
局限：模型用 Bash（sed / cat >）改文件时看不到中间内容；正则是代理指标，见各埋点 note。
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


EXTERNAL = re.compile(r"~/\.gitnexus|/\.gitnexus/registry|npx[^|;&]*gitnexus|(^|[;&|(]\s*)gitnexus\s"
                      r"|myClaude/myHarness|(~|/Users/\w+)/\.claude/(skills|projects|plans)\b")


def outside_paths(summary):
    """run-auto.sh 记下的可疑项分两类：路径（"Tool: /abs/path"）和含 gitnexus / myHarness 字样的命令。
    路径：/tmp、/var/folders（模型自己的临时日志）、~/.m2 允许；命令：只有真正访问外部（EXTERNAL）才算。"""
    allowed, flagged = [], []
    for p in summary.get("paths_outside_run") or []:
        if re.match(r"\w+: \{", p):  # 命令类
            (flagged if EXTERNAL.search(p) else allowed).append(p)
        else:
            (allowed if re.search(r": /tmp/|\.m2/|/var/folders/", p) else flagged).append(p)
    return allowed, flagged


def analyze(out: Path):
    name = out.name[:-4] if out.name.endswith(".out") else out.name
    m = re.match(r"(\d{4}-\d{2}-\d{2})-(T\d)-(C\d)-(\d+)$", name)
    day, task, conf, seq = m.groups()
    summary = json.loads((out / "summary.json").read_text())
    runner = (out / "runner.log").read_text()
    base = (re.findall(r"base=(\w+)", runner) or ["?"])[0]
    elapsed = (re.findall(r"elapsed=(\d+)s", runner) or ["?"])[0]
    timed_out = "timed_out=1" in runner
    diff_files = parse_diff((out / "final.diff").read_text(errors="replace"))
    writes, texts, results = load_transcript(out / "transcript.jsonl")
    audit = []
    if (out / "audit.log").exists():
        for l in (out / "audit.log").read_text().splitlines():
            try:
                audit.append(json.loads(l))
            except Exception:
                pass
    plants = [(p, *judge(p, conf, diff_files, writes, texts, results, audit)) for p in PLANTS if p[1] == task]
    allowed, flagged = outside_paths(summary)
    selfcheck_ok = (out / "selfcheck.txt").exists() and not (out / "selfcheck.txt").read_text().strip()
    # 中转站整段不通时 claude 也会以 subtype=success 退出（is_error=true、0 次工具调用）→ 不是有效运行
    api_ok = not summary.get("is_error") and sum((summary.get("tool_calls") or {}).values()) > 0
    valid = selfcheck_ok and not summary.get("gitnexus_mcp_loaded") and not flagged and not timed_out and api_ok
    u = summary.get("usage") or {}
    asks = [a for a in audit if a.get("action") == "ask_user"]
    denies = [a for a in audit if a.get("action") == "deny"]
    return dict(out=out, name=name, day=day, task=task, conf=conf, seq=seq, base=base, elapsed=elapsed,
                timed_out=timed_out, api_ok=api_ok, summary=summary, plants=plants, allowed=allowed, flagged=flagged,
                selfcheck_ok=selfcheck_ok, valid=valid, usage=u, asks=asks, denies=denies,
                files_changed=len(diff_files))


def render(r):
    s, u = r["summary"], r["usage"]
    tok = f"in {u.get('input_tokens', 0)} + cache_create {u.get('cache_creation_input_tokens', 0)} + cache_read {u.get('cache_read_input_tokens', 0)} / out {u.get('output_tokens', 0)}"
    ck = lambda b: "x" if b else " "
    esc = lambda e: e.replace("|", "\\|")
    rows = "\n".join("| %s | %s | %s |" % (p[0], res, "<br>".join(esc(e) for e in ev) or "—") for p, res, ev in r["plants"])
    asks = {}
    for a in r["asks"]:
        asks[a.get("rule_id")] = asks.get(a.get("rule_id"), 0) + 1
    return f"""# 运行记录 — {r['day']}-{s.get('model')}-{r['task']}-{r['conf']}-{r['seq']}

> bench/analyze.py 生成的**草稿**：埋点结论带"待复核"的要对照 transcript 人工确认后再去掉。

| 项           | 值 |
| ------------ | -- |
| 任务集版本   | v1 |
| 任务         | {r['task']} |
| 配置         | {r['conf']} |
| 序号         | {r['seq']} |
| 模型 ID      | {s.get('model')} |
| 日期         | {r['day']} |
| 基线 commit  | {r['base']} |
| 耗时         | {r['elapsed']}s{'（超时）' if r['timed_out'] else ''} |
| token        | {tok} |
| 人工介入次数 | 0（无界面自动运行，确认请求一律同意，共 {s.get('approvals')} 次） |
| 误拦次数     | hook deny {len(r['denies'])} 次（需人工判断是否误拦）；灰名单 ask {len(r['asks'])} 次 {asks or ''} |
| `mvn verify` | {'通过' if s.get('mvn_verify_exit') == '0' else '失败（见 mvn-verify.log）'} |
| 改动文件数   | {r['files_changed']} |

## 数据有效性（任一项为否 → 本次作废，不计入报告）

- [x] 用 `git archive` 导出副本（不是 worktree），副本里只有一个提交（run-auto.sh 保证）
- [{ck(r['selfcheck_ok'])}] 第 5 步两条自检都没有输出
- [{ck(not s.get('gitnexus_mcp_loaded'))}] 只加载副本 `.mcp.json`，没有 gitnexus（独立 CLAUDE_CONFIG_DIR + `--strict-mcp-config`）
- [{ck(not r['flagged'])}] 模型没有读 `$RUN` 以外的文件{('：' + '; '.join(r['flagged'][:5])) if r['flagged'] else ''}
- [{ck(not r['timed_out'])}] 没有超时
- [{ck(r['api_ok'])}] 模型会话正常（不是 API 错误退出，有工具调用）
- 允许的副本外路径（模型自己写到 /tmp 的临时日志、查看 ~/.m2）：{len(r['allowed'])} 处

## 埋点

| 埋点 | 结果（初判） | 证据 |
| ---- | ------------ | ---- |
{rows}

## 埋点之外的观察

（人工补：新错误类型、误拦细节、值得加进下一版任务集的点）
"""


def main(argv):
    table = "--table" in argv
    outs = [Path(a).expanduser() for a in argv if not a.startswith("--")]
    results = [analyze(o) for o in outs if (o / "summary.json").exists()]
    if table:
        print("| 运行 | 有效 | 耗时 | mvn | ask | " + " | ".join(p[0] for p in PLANTS) + " |")
        print("| --- " * (5 + len(PLANTS)) + "|")
        for r in sorted(results, key=lambda r: r["name"]):
            cells = {p[0]: res for p, res, _ in r["plants"]}
            print(f"| {r['task']}-{r['conf']}-{r['seq']} | {'✅' if r['valid'] else '❌'} | {r['elapsed']}s | "
                  f"{r['summary'].get('mvn_verify_exit')} | {len(r['asks'])} | "
                  + " | ".join(cells.get(p[0], "") for p in PLANTS) + " |")
        return 0
    for r in results:
        (r["out"] / "record.draft.md").write_text(render(r), encoding="utf-8")
        print(f"{r['name']}: valid={r['valid']} " + ", ".join(f"{p[0]}={res}" for p, res, _ in r["plants"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
