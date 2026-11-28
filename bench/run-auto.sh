#!/usr/bin/env bash
# bench 无界面自动运行（G3 首批；D3 原定手工，2026-11-23 改为自动，见 bench/README.md）。
# 每一步对应 README「运行步骤（单次）」1–7；第 6 步把交互会话换成 claude -p，确认请求由
# .claude/scripts/manual/permission-approver.py 一律同意（模拟信任模型的用户），人工介入记 0。
#
# 用法：bash bench/run-auto.sh <基线commit> <T1|T2|T3> <C0|C2> <序号>
#       bash bench/run-auto.sh <基线commit> all        # 3 任务 × C0/C2 × 2 次，BENCH_JOBS 并发
# 隔离（2026-11-23 首批作废后加）：用户级 skills / hooks / MCP / 记忆会在 C0、C2 都加载（首批里 gitnexus skill
#   把模型引出副本）。所以 claude 用独立的 CLAUDE_CONFIG_DIR，只从 ~/.claude/settings.json 复制 env 与 model
#   （不打印，权限 600）；并要求 gitnexus 注册表里没有 myHarness（先 gitnexus remove，跑完再 analyze）。
# 输出目录不覆盖（2026-11-26）：$RUN / $RUN.out 由 claim-run-dirs.sh 原子占用，任一个已存在就报错退出、原样保留；
#   同日同任务同配置重跑要换序号（作废的也占号）。all 模式下有子运行没跑起来时，整体以非零退出。
# 尝试记录（2026-11-27）：占到目录后写 attempt-start.json（基线 / 配置 / 超时上限等已知条件），脚本结束时写
#   attempt-end.json（跑完 / 失败 / 被中断，停在哪一步）。两个文件都只写一次、不覆盖（attempt-record.py）。
#   all 模式另在 $ROOT/.batches/<批次>/ 汇总各子脚本的执行状态；样本有效不有效仍由 analyze.py 判，两件事分开。
# 环境变量：CLAUDE_BIN（默认 claude）、BENCH_MODEL（默认 sonnet）、BENCH_TIMEOUT（秒，默认 3600）、
#           BENCH_JOBS（默认 3）、BENCH_ROOT（默认 ~/bench-runs）、JAVA_HOME（mvnw 用，模型会话里也可用）
set -u
SRC="$(cd "$(dirname "$0")/.." && pwd)"
APPROVER="$SRC/.claude/scripts/manual/permission-approver.py"
B=""; ROOT="${BENCH_ROOT:-$HOME/bench-runs}"; DAY=$(date +%Y-%m-%d)
CFG="${BENCH_CLAUDE_CONFIG:-$ROOT/.claude-config}"

# 基线固定（2026-11-27）：传进来的可以是 HEAD / 分支名 / 短 SHA，这里解析成完整 commit SHA，只解析一次。
#   之后读提示词、读任务集版本、导出副本、写记录都用这个 SHA；运行途中引用被移动（切分支、新提交）不影响本次尝试。
#   all 模式由父脚本解析一次，把 SHA 传给每个子脚本；原始输入经 BENCH_BASE_INPUT 传下去，只用于记录和诊断。
B_INPUT=$1
[ -z "${BENCH_BATCH_ID:-}" ] || B_INPUT="${BENCH_BASE_INPUT:-$1}"
resolve_base() { # $1 = 传入的引用；成功时 B = 完整 SHA
  B=$(git -C "$SRC" rev-parse --verify -q "$1^{commit}" 2>/dev/null) && [ -n "$B" ] && return 0
  echo "ABORT: 基线解析不出 commit：传入 '$1'（原始输入 '${B_INPUT}'）。检查这个引用在 ${SRC} 里是否存在" >&2
  return 1
}

if [ ! -f "$CFG/settings.json" ]; then
  mkdir -p "$CFG" && chmod 700 "$CFG"
  ( umask 077; python3 -c "import json,os,sys
d=json.load(open(os.path.expanduser('~/.claude/settings.json')))
json.dump({k:d[k] for k in ('env','model') if k in d}, open(sys.argv[1],'w'), indent=2)" "$CFG/settings.json" )
fi
if grep -q '"name": *"myHarness"' "$HOME/.gitnexus/registry.json" 2>/dev/null; then
  echo "ABORT: gitnexus 注册表里还有 myHarness（索引含答案文件）。先 gitnexus remove myHarness" >&2; exit 1
fi

REC="$SRC/bench/attempt-record.py"
if [ "${2:-}" = all ]; then
  # 基线在父脚本里固定一次：plan.txt 里每一行都是同一个完整 SHA，子脚本不再各自解析引用
  resolve_base "$1" || exit 1
  export BENCH_BASE_INPUT="$B_INPUT"
  # 批次目录：每个子运行结束时往里写一条自己的结束记录（一次写入、不覆盖），批次结束后汇总成 batch.json
  export BENCH_BATCH_ID="$DAY-$(date +%H%M%S)-$$"; export BENCH_BATCH_DIR="$ROOT/.batches/$BENCH_BATCH_ID"
  mkdir -p "$ROOT/.batches" && mkdir "$BENCH_BATCH_DIR" 2>/dev/null ||
    { echo "ABORT: 建不了批次目录 ${BENCH_BATCH_DIR}（已存在或上级不可写），不覆盖" >&2; exit 1; }
  names=""
  for t in T1 T2 T3; do for c in C0 C2; do for s in 1 2; do names="$names $t-$c-$s"; echo "$B $t $c $s"; done; done; done > "$BENCH_BATCH_DIR/plan.txt"
  xargs -P "${BENCH_JOBS:-3}" -L 1 bash "$0" < "$BENCH_BATCH_DIR/plan.txt"
  rc=$?  # 子运行以 1 退出（ABORT）时 xargs 继续跑其余的，最后返回非零（GNU 123 / BSD 1）
  # 汇总只报子脚本的执行状态；样本是否有效由 analyze.py 另判（跑完的脚本也可能是超时 / API 错误的作废样本）
  # shellcheck disable=SC2086
  python3 "$REC" batch "$BENCH_BATCH_DIR" $names; brc=$?
  [ "$rc" -eq 0 ] || echo "FAILED: all 模式有子运行没跑起来或中止（xargs exit=${rc}），见上面各自的 ABORT 行" >&2  # 变量后紧跟全角字符时必须加花括号
  [ "$rc" -ne 0 ] || rc=$brc
  exit "$rc"
fi

TASK=$2; CONF=$3; SEQ=$4
RUN="$ROOT/$DAY-$TASK-$CONF-$SEQ"; OUT="$RUN.out"

# 结束记录（2026-11-27）：脚本怎么结束的、停在哪一步。写一次，不覆盖；只写进本次自己占到的 $OUT 和批次目录。
#   这里记的是脚本执行状态，不是样本有效性：超时 / API 错误的运行脚本照样"跑完"，有效性由 analyze.py 判。
STAGE=base; CLAIMED=0; ENDED=0; pid=""; MODEL_EXIT=""; timed_out_json=""; elapsed=""
finish() { # $1 = 退出码，$2 = 信号名（被信号中断时才有）
  [ "$ENDED" = 0 ] || return 0
  ENDED=1
  local code=$1 sig=${2:-} status=failed rc=0
  [ "$code" -ne 0 ] || status=completed
  [ -z "$sig" ] || status=interrupted
  set -- schema:=1 script_status="$status" stage="$STAGE" exit_code:="$code" signal="$sig" \
    timed_out:="$timed_out_json" model_exit:="$MODEL_EXIT" elapsed_s:="$elapsed" ended_at="$(date -u +%FT%TZ)"
  if [ "$CLAIMED" = 1 ]; then
    python3 "$REC" write "$OUT/attempt-end.json" "$@" || rc=1
    set -- "$@" out_dir="$OUT"
  fi
  if [ -n "${BENCH_BATCH_DIR:-}" ]; then
    python3 "$REC" write "$BENCH_BATCH_DIR/$TASK-$CONF-$SEQ.json" task="$TASK" conf="$CONF" seq="$SEQ" "$@" || rc=1
  fi
  return $rc
}
# 结束记录写不出来时，本来以 0 结束的也改成非零：没有记录的"成功"不算数
trap '_rc=$?; finish "$_rc" || { [ "$_rc" -ne 0 ] || exit 1; }' EXIT
trap '[ -z "$pid" ] || kill "$pid" 2>/dev/null; finish 130 INT; exit 130' INT
trap '[ -z "$pid" ] || kill "$pid" 2>/dev/null; finish 143 TERM; exit 143' TERM

# 固定基线：从这里往下 $B 是完整 SHA，不再用传入的引用
resolve_base "$1" || exit 1
RUNNER_COMMIT="$(git -C "$SRC" rev-parse -q --short HEAD)"  # 本脚本所在仓库的 HEAD，也只读一次

# 任务提示词：从基线 commit 的 README 原样取。放在占用目录之前：任务名写错不该占掉一个序号
STAGE=prompt
PROMPT=$(git -C "$SRC" show "$B:bench/README.md" | sed -n "s/^- \*\*$TASK\*\*：\`\(.*\)\`$/\1/p")
[ -n "$PROMPT" ] || { echo "[$TASK-$CONF-$SEQ] ABORT: README 里找不到 $TASK 的提示词" >&2; exit 1; }

# 占用 $RUN / $OUT：已存在就退出，不覆盖、不删除（规则见 claim-run-dirs.sh）
STAGE=claim
bash "$SRC/bench/claim-run-dirs.sh" "$RUN" "$OUT" || exit 1
CLAIMED=1
log() { echo "[$TASK-$CONF-$SEQ] $*" | tee -a "$OUT/runner.log"; }

# 开始记录：占到目录后马上写下"这次尝试在什么条件下开始"。之后脚本被强杀、没有任何收尾，也能从它知道基线 / 配置 / 上限
STAGE=start-record
TASK_SET="$(git -C "$SRC" show "$B:bench/README.md" | sed -n 's/^\*\*当前版本：\(v[0-9][0-9]*\)\*\*.*/\1/p' | head -1)"
python3 "$REC" write "$OUT/attempt-start.json" schema:=1 task="$TASK" conf="$CONF" seq="$SEQ" day="$DAY" \
  task_set="$TASK_SET" base_arg="$B_INPUT" base_commit="$B" runner_commit="$RUNNER_COMMIT" \
  exec_mode=headless-auto-approve model_arg="${BENCH_MODEL:-sonnet}" timeout_limit_s:="${BENCH_TIMEOUT:-3600}" \
  batch_id="${BENCH_BATCH_ID:-}" claimed_at="$(date -u +%FT%TZ)" run_dir="$RUN" out_dir="$OUT" ||
  { log "ABORT: 写不了开始记录 attempt-start.json（BENCH_TIMEOUT 不是数字？）"; exit 1; }

# 1. 导出不带历史的副本
STAGE=export
git -C "$SRC" archive "$B" | tar -x -C "$RUN" && cd "$RUN" || { log "ABORT: 导出基线副本失败"; exit 1; }
# 2. 所有配置：删写有埋点答案的文件
STAGE=strip
rm -rf bench docs/improvement-plan.md docs/rule-inventory.md \
  docs/improvement-backlog.md docs/improvement-backlog-archive.md CHANGELOG.md
# 2b. 基线 84e90f4 的 G11 测试拿 T3-a 的列名当示例（2026-11-23 发现），副本里换成中性名字（主仓库已另改）
f=.claude/scripts/tests/test_check_migration_immutability.py
[ -f "$f" ] && perl -pi -e 's/total_amount/remark/g' "$f"
# 3. C0：去掉 Harness
[ "$CONF" = C0 ] && rm -rf .claude .githooks CLAUDE.md src/main/java/com/example/harness/*/CLAUDE.md
# 4. 单提交基线仓库
STAGE=git-init
git init -q -b main && git add -A && git -c user.name=bench -c user.email=bench@localhost commit -qm "bench baseline" ||
  { log "ABORT: 建不了单提交基线仓库"; exit 1; }
git config user.name bench; git config user.email bench@localhost
[ -d .githooks ] && git config core.hooksPath .githooks
# 5. 自检：有输出就不跑
STAGE=selfcheck
leak=$( { git grep -l -w -E 'setStatus|CustomerId|AFTER_COMMIT|total_amount' -- ':!src'; git grep -l -E '埋点|期望被拦' -- .; } 2>/dev/null)
if [ -n "$leak" ]; then log "ABORT: 自检有输出：$leak"; echo "$leak" > "$OUT/selfcheck.txt"; exit 1; fi
: > "$OUT/selfcheck.txt"

# 6. 跑模型：只加载副本 .mcp.json（防 gitnexus 索引泄漏），确认请求一律同意
STAGE=model
cat > "$OUT/approver.mcp.json" <<J
{"mcpServers":{"approver":{"command":"python3","args":["$APPROVER"],"env":{"G1_APPROVER_LOG":"$OUT/approvals.log"}}}}
J
log "start $(date -u +%FT%TZ) base=$B model=${BENCH_MODEL:-sonnet}"
start=$(date +%s); started_at=$(date -u +%FT%TZ)
CLAUDE_CONFIG_DIR="$CFG" "${CLAUDE_BIN:-claude}" -p "$PROMPT" --model "${BENCH_MODEL:-sonnet}" --permission-mode default \
  --strict-mcp-config --mcp-config .mcp.json "$OUT/approver.mcp.json" \
  --permission-prompts host --permission-prompt-tool mcp__approver__approve \
  --output-format stream-json --verbose --debug-file "$OUT/claude-debug.log" \
  > "$OUT/transcript.jsonl" 2> "$OUT/claude.err" &
pid=$!; i=0; poll="${BENCH_POLL:-5}"  # BENCH_POLL：轮询间隔（秒），只为离线测试调小；真实运行用默认 5
while kill -0 $pid 2>/dev/null && [ $i -lt "${BENCH_TIMEOUT:-3600}" ]; do sleep "$poll"; i=$((i+poll)); done
timed_out=0; if kill -0 $pid 2>/dev/null; then timed_out=1; kill $pid; sleep 2; kill -9 $pid 2>/dev/null; fi
wait "$pid" 2>/dev/null; MODEL_EXIT=$?; pid=""  # 会话进程自己的退出码，只记录，不改变后面的流程
[ "$timed_out" = 1 ] && timed_out_json=true || timed_out_json=false
elapsed=$(( $(date +%s) - start ))
log "end $(date -u +%FT%TZ) elapsed=${elapsed}s timed_out=$timed_out"

# 7. 收集（写到副本外的 $OUT）
STAGE=collect
B0=$(git rev-list --max-parents=0 HEAD) && [ -n "$B0" ] || { log "ABORT: 收集失败：找不到副本的初始提交"; exit 1; }
# mvn verify / CI 脚本失败是样本的结果，照常记进日志；下面取不出 diff 才是收集本身失败
./mvnw -B verify > "$OUT/mvn-verify.log" 2>&1; echo "exit=$?" >> "$OUT/mvn-verify.log"
bash .github/scripts/check-migration-immutability.sh "$B0" > "$OUT/ci-local.log" 2>&1; echo "exit=$?" >> "$OUT/ci-local.log"
# final.diff 先写到 .partial，完整了才改名：git add / git diff 出错时不留半截的 final.diff，也不往下写 summary.json
#   （空的或半截的 diff 会被 analyze.py 读成"什么都没改"，样本可能被判为有效）
git add -A; add_rc=$?; diff_rc=0
if [ "$add_rc" -eq 0 ]; then git diff --cached "$B0" > "$OUT/final.diff.partial"; diff_rc=$?; fi
if [ "$add_rc" -ne 0 ] || [ "$diff_rc" -ne 0 ]; then
  rm -f "$OUT/final.diff.partial"
  log "ABORT: 收集失败（git add exit=${add_rc}，git diff exit=${diff_rc}），没有 final.diff，不写 summary.json"
  exit 1
fi
mv "$OUT/final.diff.partial" "$OUT/final.diff" || { log "ABORT: 收集失败：final.diff 落不了盘"; exit 1; }
cp .claude/.audit.log "$OUT/audit.log" 2>/dev/null || true
# meta：一次运行"在什么条件下跑的"，写进 summary.json，入库后不靠 runner.log 也能判有效性（口径见 README「统计口径」）
#   base_commit 存完整 SHA；task_set 从基线 commit 的 README 读（和提示词同源）；runner_commit 是本脚本所在仓库的 HEAD
STAGE=summary
export BENCH_META_BASE="$B"
export BENCH_META_TASK_SET="$TASK_SET"
export BENCH_META_RUNNER_COMMIT="$RUNNER_COMMIT"
export BENCH_META_TASK="$TASK" BENCH_META_CONF="$CONF" BENCH_META_SEQ="$SEQ" BENCH_META_DAY="$DAY"
export BENCH_META_TIMEOUT="${BENCH_TIMEOUT:-3600}" BENCH_META_ELAPSED="$elapsed" BENCH_META_TIMED_OUT="$timed_out"
export BENCH_META_STARTED="$started_at" BENCH_META_MODEL_ARG="${BENCH_MODEL:-sonnet}"
export BENCH_META_CLI_VERSION="$("${CLAUDE_BIN:-claude}" --version 2>/dev/null | head -1)"
python3 - "$OUT" "$RUN" "$CFG" <<'PY' > "$OUT/summary.json"
import json, sys, re, os
out, run, cfg = sys.argv[1], sys.argv[2], sys.argv[3]
own = (run, os.path.realpath(run), os.path.join(cfg, "projects"))  # 副本 + Claude Code 自己的大输出落盘
tools, outside, result, usage, model, is_error, cc_version = {}, [], None, None, None, None, None
for line in open(f"{out}/transcript.jsonl", encoding="utf-8", errors="replace"):
    try: m = json.loads(line)
    except Exception: continue
    if m.get("type") == "system" and m.get("subtype") == "init": model, cc_version = m.get("model"), m.get("claude_code_version")
    if m.get("type") == "assistant":
        for c in (m.get("message") or {}).get("content") or []:
            if c.get("type") == "tool_use":
                tools[c["name"]] = tools.get(c["name"], 0) + 1
                s = json.dumps(c.get("input"), ensure_ascii=False)
                for p in re.findall(r'(/(?:Users|private|tmp|var|home)[^\s"\'`]*)', s):
                    if not p.startswith(own):
                        outside.append(f'{c["name"]}: {p}')
                if "gitnexus" in s or "myHarness" in s: outside.append(f'{c["name"]}: {s[:160]}')
    if m.get("type") == "result": result, usage, is_error = m.get("subtype"), m.get("usage"), m.get("is_error")
dbg = open(f"{out}/claude-debug.log", errors="replace").read() if os.path.exists(f"{out}/claude-debug.log") else ""
audit = open(f"{out}/audit.log").read().splitlines() if os.path.exists(f"{out}/audit.log") else []
acts = {}
for l in audit:
    try: a = json.loads(l).get("action")
    except Exception: continue
    acts[a] = acts.get(a, 0) + 1
mvn = open(f"{out}/mvn-verify.log", errors="replace").read()
E = lambda k: os.environ.get("BENCH_META_" + k) or None
num = lambda k: int(E(k)) if (E(k) or "").isdigit() else None
selfcheck = f"{out}/selfcheck.txt"
meta = {
    "schema": 1, "task_set": E("TASK_SET"), "task": E("TASK"), "conf": E("CONF"), "seq": num("SEQ"), "day": E("DAY"),
    "base_commit": E("BASE"), "runner_commit": E("RUNNER_COMMIT"),
    "exec_mode": "headless-auto-approve",  # 确认请求一律同意，人工介入记 0
    "model_arg": E("MODEL_ARG"),           # --model 传的原值（别名）；真实模型 ID 在上一层的 model
    "claude_code_version": cc_version or E("CLI_VERSION"),  # 优先取会话 init 消息里的，取不到用 claude --version
    "timeout_limit_s": num("TIMEOUT"), "elapsed_s": num("ELAPSED"),  # elapsed 含 5 秒轮询粒度和超时后的终止等待
    "timed_out": {"0": False, "1": True}.get(E("TIMED_OUT")),
    "started_at": E("STARTED"),
    "selfcheck_clean": (os.path.getsize(selfcheck) == 0) if os.path.exists(selfcheck) else None,
}
print(json.dumps({
    "meta": meta,
    "model": model, "result": result, "is_error": is_error, "usage": usage, "tool_calls": tools,
    "gitnexus_mcp_loaded": 'MCP server "gitnexus"' in dbg,
    "paths_outside_run": sorted(set(outside))[:30],
    "audit_actions": acts,
    "approvals": sum(1 for _ in open(f"{out}/approvals.log")) if os.path.exists(f"{out}/approvals.log") else 0,
    "mvn_verify_exit": (re.findall(r"exit=(\d+)", mvn) or ["?"])[-1],
    "migration_check_exit": (re.findall(r"exit=(\d+)", open(f"{out}/ci-local.log").read()) or ["?"])[-1],
    "api_errors": dbg.count("API error"),
}, ensure_ascii=False, indent=1))
PY
python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$OUT/summary.json" 2>/dev/null ||
  { log "ABORT: summary.json 没生成完整（收集阶段缺文件？），本次没有可判定的汇总"; exit 1; }
log "done: $(python3 -c "import json;d=json.load(open('$OUT/summary.json'));print(d['result'],'is_error',d['is_error'],'tools',sum(d['tool_calls'].values()),'mvn',d['mvn_verify_exit'],'gitnexus',d['gitnexus_mcp_loaded'],'outside',len(d['paths_outside_run']))")"
STAGE=done
