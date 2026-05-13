#!/usr/bin/env bash
# Smoke test for plugin/hooks/subagent-stop.sh
#
# 验证两类行为：
#   1. F9: 沉默失败检测（new-api panic / empty / 错误关键词 / 短输出）
#   2. 既有 schema 块解析（status=ok/degraded/escalate）
#
# 失败永远不挂会话（hook exit 0），但 stderr / audit log 应有信号。
#
# 用法：
#   bash plugin/hooks/tests/test_subagent_stop.sh
#   bash plugin/hooks/tests/test_subagent_stop.sh -v

set -uo pipefail

VERBOSE=0
[ "${1:-}" = "-v" ] && VERBOSE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SCRIPT_DIR/../subagent-stop.sh"
[ -f "$HOOK" ] || { echo "FATAL: $HOOK 不存在"; exit 1; }

TMPDIR="$(mktemp -d 2>/dev/null || mktemp -d -t harness-subagent-test)"
trap 'rm -rf "$TMPDIR"' EXIT
mkdir -p "$TMPDIR/.claude"
export CLAUDE_PROJECT_DIR="$TMPDIR"

PASS=0
FAIL=0

# run_case <name> <exp_stderr_keyword> <payload_json>
# stderr 为空字符串 = 期望静默（既有 silently skip）
run_case() {
  local name="$1" exp_kw="$2" payload="$3"

  local actual exit_code=0
  actual="$(printf '%s' "$payload" | bash "$HOOK" 2>&1)" || exit_code=$?

  local ok=true reasons=""
  # hook 永远 exit 0
  if [ "$exit_code" != "0" ]; then
    ok=false
    reasons="exit=$exit_code (期望 0)"
  fi
  if [ -n "$exp_kw" ]; then
    if ! echo "$actual" | grep -qF "$exp_kw"; then
      ok=false
      reasons="$reasons kw_miss=\"$exp_kw\""
    fi
  else
    # 期望静默：stderr 应为空
    if [ -n "$actual" ]; then
      ok=false
      reasons="$reasons expected_silent_but_got=\"$(echo "$actual" | head -1)\""
    fi
  fi

  if $ok; then
    PASS=$((PASS + 1))
    echo "  ✅ $name"
    [ "$VERBOSE" = "1" ] && [ -n "$actual" ] && echo "     $(echo "$actual" | head -1)"
  else
    FAIL=$((FAIL + 1))
    echo "  ❌ $name — $reasons"
    [ "$VERBOSE" = "1" ] && echo "     stderr: $actual"
  fi
}

echo "=== SubagentStop hook smoke test ==="
echo "Hook: $HOOK"
echo ""

# --- F9 沉默失败检测 ---
echo "## F9 沉默失败检测（new-api panic 等）"

run_case "silent-empty-output" "疑似沉默失败" \
  '{"subagent_type":"code-reviewer","output":""}'

run_case "silent-no-output-field" "疑似沉默失败" \
  '{"subagent_type":"ddd-architect"}'

run_case "silent-panic-keyword" "疑似沉默失败" \
  '{"subagent_type":"code-reviewer","output":"upstream error: new-api panic / nil pointer at line 42"}'

run_case "silent-timeout-keyword" "疑似沉默失败" \
  '{"subagent_type":"schema-analyst","output":"Request timeout after 180s"}'

run_case "silent-500-error" "疑似沉默失败" \
  '{"subagent_type":"docs-keeper","output":"500 error from upstream"}'

run_case "silent-too-short" "疑似沉默失败" \
  '{"subagent_type":"maven-build-doctor","output":"Error."}'

# --- 既有行为：正常 schema 块 ---
echo ""
echo "## 既有 schema 块解析"

# status=ok → 静默（不打扰主对话）
run_case "schema-ok-silent" "" \
  "$(cat <<'JSON'
{"subagent_type":"code-reviewer","output":"评审完毕。下面是 schema:\n<!-- harness:agent-output -->\nstatus: ok\nrisks: 无\n<!-- /harness:agent-output -->\nReview 内容..."}
JSON
)"

# status=degraded → stderr 提示
run_case "schema-degraded-warns" "status=degraded" \
  "$(cat <<'JSON'
{"subagent_type":"schema-analyst","output":"<!-- harness:agent-output -->\nstatus: degraded\ndegraded_from: mcp-readonly\nrisks: MCP 不可用，改用 grep\n<!-- /harness:agent-output -->"}
JSON
)"

# status=escalate → stderr 提示
run_case "schema-escalate-warns" "status=escalate" \
  "$(cat <<'JSON'
{"subagent_type":"code-reviewer","output":"<!-- harness:agent-output -->\nstatus: escalate\nescalate_to: human\nrisks: 涉及敏感凭据，需人工审\n<!-- /harness:agent-output -->"}
JSON
)"

# --- 长输出但无 schema 块 → 静默（不强制要求 agent 加 schema）---
echo ""
echo "## 长输出无 schema 不强制"

run_case "long-output-no-schema-silent" "" \
  '{"subagent_type":"code-reviewer","output":"这是一段很长的正常输出，没有 schema 块，但内容充分。代码评审完毕，发现 3 个 minor 改进点和 1 个 nit。建议加类型注解、补 __all__、拆 module 入口。结论：作为 stub 通过，零阻塞。"}'

echo ""
echo "──────────────────────────────────"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo "  Total:  $((PASS + FAIL))"
echo "──────────────────────────────────"

[ "$FAIL" -eq 0 ]
