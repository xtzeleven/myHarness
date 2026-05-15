#!/usr/bin/env bash
# Smoke test for .claude/hooks/subagent-stop.sh
#
# 喂典型 payload，断言：
#  1) audit log 是否写入（.claude/.audit.log 行数变化）
#  2) status 字段被正确解析
#  3) 非 ok 状态时 stderr 含告警
#  4) 无 schema 块时 silently skip（log 不增）

set -uo pipefail

VERBOSE=0
[ "${1:-}" = "-v" ] && VERBOSE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SCRIPT_DIR/../subagent-stop.sh"
[ -f "$HOOK" ] || { echo "FATAL: $HOOK 不存在"; exit 1; }

TMPDIR="$(mktemp -d 2>/dev/null || mktemp -d -t harness-subagent-test)"
trap 'rm -rf "$TMPDIR"' EXIT
mkdir -p "$TMPDIR/.claude"
cd "$TMPDIR"

PASS=0
FAIL=0
FAIL_CASES=()

# run_case <name> <exp_log_increment> <exp_stderr_keyword> <payload_json>
run_case() {
  local name="$1" exp_inc="$2" exp_kw="$3" payload="$4"

  local before=0 after=0
  [ -f .claude/.audit.log ] && before="$(wc -l < .claude/.audit.log | tr -d ' ')"

  local actual_output
  actual_output="$(printf '%s' "$payload" | bash "$HOOK" 2>&1)" || true

  [ -f .claude/.audit.log ] && after="$(wc -l < .claude/.audit.log | tr -d ' ')"
  local actual_inc=$((after - before))

  local ok=true reasons=""
  if [ "$actual_inc" != "$exp_inc" ]; then
    ok=false
    reasons="log_inc=$actual_inc expected=$exp_inc"
  fi
  if [ -n "$exp_kw" ] && ! echo "$actual_output" | grep -qF "$exp_kw"; then
    ok=false
    reasons="$reasons kw_miss=\"$exp_kw\""
  fi

  if $ok; then
    PASS=$((PASS + 1))
    echo "  ✅ $name"
    [ "$VERBOSE" = "1" ] && [ -n "$actual_output" ] && echo "     $(echo "$actual_output" | head -1)"
  else
    FAIL=$((FAIL + 1))
    FAIL_CASES+=("$name [$reasons]")
    echo "  ❌ $name [$reasons]"
    [ -n "$actual_output" ] && echo "     stderr: $(echo "$actual_output" | head -2 | tr '\n' '|')"
  fi
}

echo "=== SubagentStop hook smoke test ==="
echo "Hook:    $HOOK"
echo "Workdir: $TMPDIR"
echo ""

# 1) ok 状态：log+1，stderr 无 ⚠️
PAYLOAD_OK='{"subagent_type":"code-reviewer","output":"Review done.\n<!-- harness:agent-output -->\nstatus: ok\nrisks: none\n<!-- /harness:agent-output -->"}'
run_case "ok-status-logged-no-warn" 1 "" "$PAYLOAD_OK"

# 2) degraded：log+1，stderr 含 status=degraded + degraded_from
PAYLOAD_DEGRADED='{"subagent_type":"ddd-architect","output":"Partial result.\n<!-- harness:agent-output -->\nstatus: degraded\ndegraded_from: opus\nrisks: limited reasoning depth\n<!-- /harness:agent-output -->"}'
run_case "degraded-status-warns" 1 "status=degraded" "$PAYLOAD_DEGRADED"

# 3) escalate：log+1，stderr 含 status=escalate + escalate_to
PAYLOAD_ESCALATE='{"subagent_type":"code-reviewer","output":"Cannot proceed.\n<!-- harness:agent-output -->\nstatus: escalate\nescalate_to: ddd-architect\nrisks: boundary issue\n<!-- /harness:agent-output -->"}'
run_case "escalate-status-warns" 1 "escalate_to: ddd-architect" "$PAYLOAD_ESCALATE"

# 4) 无 schema 块：log 不增，silently skip
PAYLOAD_NOSCHEMA='{"subagent_type":"docs-keeper","output":"Plain output without schema."}'
run_case "no-schema-silent-skip" 0 "" "$PAYLOAD_NOSCHEMA"

# 5) 非法 JSON：silently skip（hook 不应崩）
PAYLOAD_BADJSON='not json at all'
run_case "bad-json-silent-skip" 0 "" "$PAYLOAD_BADJSON"

# 6) blocked 状态（非 ok 任何值都应触发 warn）
PAYLOAD_BLOCKED='{"subagent_type":"schema-analyst","output":"<!-- harness:agent-output -->\nstatus: blocked\nrisks: MCP unreachable\n<!-- /harness:agent-output -->"}'
run_case "blocked-status-warns" 1 "status=blocked" "$PAYLOAD_BLOCKED"

echo ""
echo "──────────────────────────────────────────"
echo "PASS: $PASS   FAIL: $FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "失败 case："
  for c in "${FAIL_CASES[@]}"; do
    echo "  - $c"
  done
  exit 1
fi
echo "✅ All SubagentStop hook cases passed."
