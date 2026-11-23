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
# 环境变量：CLAUDE_BIN（默认 claude）、BENCH_MODEL（默认 sonnet）、BENCH_TIMEOUT（秒，默认 3600）、
#           BENCH_JOBS（默认 3）、BENCH_ROOT（默认 ~/bench-runs）、JAVA_HOME（mvnw 用，模型会话里也可用）
set -u
SRC="$(cd "$(dirname "$0")/.." && pwd)"
APPROVER="$SRC/.claude/scripts/manual/permission-approver.py"
B=$1; ROOT="${BENCH_ROOT:-$HOME/bench-runs}"; DAY=$(date +%Y-%m-%d)
CFG="${BENCH_CLAUDE_CONFIG:-$ROOT/.claude-config}"

if [ ! -f "$CFG/settings.json" ]; then
  mkdir -p "$CFG" && chmod 700 "$CFG"
  ( umask 077; python3 -c "import json,os,sys
d=json.load(open(os.path.expanduser('~/.claude/settings.json')))
json.dump({k:d[k] for k in ('env','model') if k in d}, open(sys.argv[1],'w'), indent=2)" "$CFG/settings.json" )
fi
if grep -q '"name": *"myHarness"' "$HOME/.gitnexus/registry.json" 2>/dev/null; then
  echo "ABORT: gitnexus 注册表里还有 myHarness（索引含答案文件）。先 gitnexus remove myHarness" >&2; exit 1
fi

if [ "${2:-}" = all ]; then
  for t in T1 T2 T3; do for c in C0 C2; do for s in 1 2; do echo "$B $t $c $s"; done; done; done |
    xargs -P "${BENCH_JOBS:-3}" -L 1 bash "$0"
  exit 0
fi

TASK=$2; CONF=$3; SEQ=$4
RUN="$ROOT/$DAY-$TASK-$CONF-$SEQ"; OUT="$RUN.out"
rm -rf "$RUN" "$OUT"; mkdir -p "$RUN" "$OUT"
log() { echo "[$TASK-$CONF-$SEQ] $*" | tee -a "$OUT/runner.log"; }

# 任务提示词：从基线 commit 的 README 原样取
PROMPT=$(git -C "$SRC" show "$B:bench/README.md" | sed -n "s/^- \*\*$TASK\*\*：\`\(.*\)\`$/\1/p")
[ -n "$PROMPT" ] || { log "ABORT: README 里找不到 $TASK 的提示词"; exit 1; }

# 1. 导出不带历史的副本
git -C "$SRC" archive "$B" | tar -x -C "$RUN" && cd "$RUN" || exit 1
# 2. 所有配置：删写有埋点答案的文件
rm -rf bench docs/improvement-plan.md docs/rule-inventory.md \
  docs/improvement-backlog.md docs/improvement-backlog-archive.md CHANGELOG.md
# 2b. 基线 84e90f4 的 G11 测试拿 T3-a 的列名当示例（2026-11-23 发现），副本里换成中性名字（主仓库已另改）
f=.claude/scripts/tests/test_check_migration_immutability.py
[ -f "$f" ] && perl -pi -e 's/total_amount/remark/g' "$f"
# 3. C0：去掉 Harness
[ "$CONF" = C0 ] && rm -rf .claude .githooks CLAUDE.md src/main/java/com/example/harness/*/CLAUDE.md
# 4. 单提交基线仓库
git init -q -b main && git add -A && git -c user.name=bench -c user.email=bench@localhost commit -qm "bench baseline"
git config user.name bench; git config user.email bench@localhost
[ -d .githooks ] && git config core.hooksPath .githooks
# 5. 自检：有输出就不跑
leak=$( { git grep -l -w -E 'setStatus|CustomerId|AFTER_COMMIT|total_amount' -- ':!src'; git grep -l -E '埋点|期望被拦' -- .; } 2>/dev/null)
if [ -n "$leak" ]; then log "ABORT: 自检有输出：$leak"; echo "$leak" > "$OUT/selfcheck.txt"; exit 1; fi
: > "$OUT/selfcheck.txt"

# 6. 跑模型：只加载副本 .mcp.json（防 gitnexus 索引泄漏），确认请求一律同意
cat > "$OUT/approver.mcp.json" <<J
{"mcpServers":{"approver":{"command":"python3","args":["$APPROVER"],"env":{"G1_APPROVER_LOG":"$OUT/approvals.log"}}}}
J
log "start $(date -u +%FT%TZ) base=$B model=${BENCH_MODEL:-sonnet}"
start=$(date +%s)
CLAUDE_CONFIG_DIR="$CFG" "${CLAUDE_BIN:-claude}" -p "$PROMPT" --model "${BENCH_MODEL:-sonnet}" --permission-mode default \
  --strict-mcp-config --mcp-config .mcp.json "$OUT/approver.mcp.json" \
  --permission-prompts host --permission-prompt-tool mcp__approver__approve \
  --output-format stream-json --verbose --debug-file "$OUT/claude-debug.log" \
  > "$OUT/transcript.jsonl" 2> "$OUT/claude.err" &
pid=$!; i=0
while kill -0 $pid 2>/dev/null && [ $i -lt "${BENCH_TIMEOUT:-3600}" ]; do sleep 5; i=$((i+5)); done
timed_out=0; if kill -0 $pid 2>/dev/null; then timed_out=1; kill $pid; sleep 2; kill -9 $pid 2>/dev/null; fi
log "end $(date -u +%FT%TZ) elapsed=$(( $(date +%s) - start ))s timed_out=$timed_out"

# 7. 收集（写到副本外的 $OUT）
B0=$(git rev-list --max-parents=0 HEAD)
./mvnw -B verify > "$OUT/mvn-verify.log" 2>&1; echo "exit=$?" >> "$OUT/mvn-verify.log"
bash .github/scripts/check-migration-immutability.sh "$B0" > "$OUT/ci-local.log" 2>&1; echo "exit=$?" >> "$OUT/ci-local.log"
git add -A && git diff --cached "$B0" > "$OUT/final.diff"
cp .claude/.audit.log "$OUT/audit.log" 2>/dev/null || true
python3 - "$OUT" "$RUN" "$CFG" <<'PY' > "$OUT/summary.json"
import json, sys, re, os
out, run, cfg = sys.argv[1], sys.argv[2], sys.argv[3]
own = (run, os.path.realpath(run), os.path.join(cfg, "projects"))  # 副本 + Claude Code 自己的大输出落盘
tools, outside, result, usage, model, is_error = {}, [], None, None, None, None
for line in open(f"{out}/transcript.jsonl", encoding="utf-8", errors="replace"):
    try: m = json.loads(line)
    except Exception: continue
    if m.get("type") == "system" and m.get("subtype") == "init": model = m.get("model")
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
print(json.dumps({
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
log "done: $(python3 -c "import json;d=json.load(open('$OUT/summary.json'));print(d['result'],'is_error',d['is_error'],'tools',sum(d['tool_calls'].values()),'mvn',d['mvn_verify_exit'],'gitnexus',d['gitnexus_mcp_loaded'],'outside',len(d['paths_outside_run']))")"
