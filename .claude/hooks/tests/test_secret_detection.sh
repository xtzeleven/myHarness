#!/usr/bin/env bash
# Smoke test for secret detection in .claude/hooks/format.sh (PostToolUse hook)
#
# 在 tempdir 创建含 / 不含秘钥的文件，喂 format.sh，断言 stderr 是否含警告。

set -uo pipefail

VERBOSE=0
[ "${1:-}" = "-v" ] && VERBOSE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SCRIPT_DIR/../format.sh"
[ -f "$HOOK" ] || { echo "FATAL: $HOOK 不存在"; exit 1; }

TMPDIR="$(mktemp -d 2>/dev/null || mktemp -d -t harness-secret-test)"
trap 'rm -rf "$TMPDIR"' EXIT
mkdir -p "$TMPDIR/.claude"
cd "$TMPDIR"

PASS=0
FAIL=0
FAIL_CASES=()

# run_case <name> <expect_hit:0|1> <file_content> <ext:default md>
run_case() {
  local name="$1" expect="$2" content="$3" ext="${4:-md}"
  local target="$TMPDIR/case_${name}.${ext}"

  printf '%s' "$content" > "$target"

  local payload
  payload=$(printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$target")

  local output exit_code=0
  output="$(printf '%s' "$payload" | bash "$HOOK" 2>&1)" || exit_code=$?

  local has_warn=0
  echo "$output" | grep -qF '疑似秘钥' && has_warn=1

  local ok=true
  [ "$exit_code" = "0" ] || ok=false
  [ "$has_warn" = "$expect" ] || ok=false

  if $ok; then
    PASS=$((PASS + 1))
    echo "  ✅ $name"
    [ "$VERBOSE" = "1" ] && [ "$has_warn" = "1" ] && echo "$output" | grep '疑似' | head -1 | sed 's/^/     /'
  else
    FAIL=$((FAIL + 1))
    FAIL_CASES+=("$name [exit=$exit_code has_warn=$has_warn expect=$expect]")
    echo "  ❌ $name [exit=$exit_code has_warn=$has_warn expect=$expect]"
    echo "$output" | head -3 | sed 's/^/     /'
  fi
}

echo "=== Secret detection smoke test ==="
echo "Hook:    $HOOK"
echo "Workdir: $TMPDIR"
echo ""

# --- 干净内容（不应触发）---
echo "## 干净内容"
run_case "plain-doc" 0 "# README\n\n本项目介绍"
run_case "code-no-secret" 0 "function add(a, b) { return a + b; }" "js"
run_case "password-placeholder" 0 'password="<your-password-here>"'
run_case "password-test-value" 0 'password=testpassword123'
run_case "password-example" 0 'password=example-only'
run_case "password-env-ref" 0 'password=\${DB_PASSWORD}'
run_case "short-string" 0 "ok"

# --- 应触发：AWS / GitHub / OpenAI / Slack ---
echo ""
echo "## AWS / GitHub / OpenAI / Slack"
run_case "aws-access-key" 1 "AWS_KEY=AKIAIOSFODNN7EXAMPLE"
run_case "github-pat" 1 "TOKEN=ghp_abcdefghijklmnopqrstuvwxyz0123456789AB"
run_case "openai-sk" 1 "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz0123"
run_case "slack-token" 1 "SLACK_BOT_TOKEN=xoxb-1234567890-abcdefghij"

# --- 应触发：PEM / JWT ---
echo ""
echo "## PEM / JWT"
run_case "pem-private-key" 1 "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
run_case "jwt-token" 1 "Authorization: Bearer eyJabcdefghij.eyJ1234567890abcd.signature1234"

# --- 应触发：password / api_key 字面量 ---
echo ""
echo "## password/api_key 字面量"
run_case "real-password" 1 'password="Hunter2#Strong!Pa55"'
run_case "api-key-literal" 1 'api_key="ak_live_1234567890abcdefghijkl"'
run_case "secret-key-literal" 1 'secret_key=abcdef0123456789secretvalue'

# --- 跳过的文件名（不应触发）---
echo ""
echo "## 跳过的特殊文件名"
SKIP_DIR="$TMPDIR/skip"
mkdir -p "$SKIP_DIR"
echo 'AKIAIOSFODNN7EXAMPLE2' > "$SKIP_DIR/agent-output-schema.md"
payload=$(printf '{"tool_name":"Edit","tool_input":{"file_path":"%s/agent-output-schema.md"}}' "$SKIP_DIR")
output="$(printf '%s' "$payload" | bash "$HOOK" 2>&1)" || true
if echo "$output" | grep -qF '疑似秘钥'; then
  FAIL=$((FAIL + 1)); echo "  ❌ skip-schema-doc (warned but should skip)"
else
  PASS=$((PASS + 1)); echo "  ✅ skip-schema-doc"
fi

echo ""
echo "──────────────────────────────────"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo "  Total:  $((PASS + FAIL))"
echo "──────────────────────────────────"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "失败用例:"
  for c in "${FAIL_CASES[@]}"; do
    echo "  - $c"
  done
  exit 1
fi

exit 0
