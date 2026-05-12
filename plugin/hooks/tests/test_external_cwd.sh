#!/usr/bin/env bash
# 外部 cwd 集成测试：验证 plugin 模式下 audit log 写到 CLAUDE_PROJECT_DIR 而非当前 cwd
# 这是 H4 / H2 修复的回归测试。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

pass=0
fail=0

assert_file_has() {
  local file="$1" pattern="$2" name="$3"
  if [ -f "$file" ] && grep -q "$pattern" "$file"; then
    echo "  ✅ $name"
    pass=$((pass + 1))
  else
    echo "  ❌ $name (file=$file pattern=$pattern)"
    fail=$((fail + 1))
  fi
}

assert_no_file() {
  local file="$1" name="$2"
  if [ ! -e "$file" ]; then
    echo "  ✅ $name"
    pass=$((pass + 1))
  else
    echo "  ❌ $name (unexpected file exists: $file)"
    fail=$((fail + 1))
  fi
}

echo "## 外部 cwd: plugin 模式下 audit log 路径"

tmp_project="$(mktemp -d)"
prev_cwd="$(pwd)"
cd "$tmp_project"

export CLAUDE_PROJECT_DIR="$tmp_project"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

# 1. 灰名单触发，audit log 应写到 $tmp_project/.claude/.audit.log
echo '{"tool_name":"Bash","tool_input":{"command":"mvn deploy"}}' \
  | bash "$PLUGIN_ROOT/hooks/pre-tool-use.sh" >/dev/null 2>&1

assert_file_has "$tmp_project/.claude/.audit.log" '"action": "ask_user"' "audit-log-written-to-project-dir"
assert_file_has "$tmp_project/.claude/.audit.log" '"tool": "Bash"' "audit-log-contains-tool"

# 2. cwd 已切到 tmp_project，但 audit log 不应误写到 $PLUGIN_ROOT/.claude/ 下
# （注意 $PLUGIN_ROOT 下没有 .claude/ 子目录，所以这里的断言是"plugin 没被污染"）
assert_no_file "$PLUGIN_ROOT/.claude" "plugin-root-no-claude-dir-created"

cd "$prev_cwd"
rm -rf "$tmp_project"
unset CLAUDE_PROJECT_DIR CLAUDE_PLUGIN_ROOT

echo ""
echo "──────────────────────────────────"
echo "  Passed: $pass"
echo "  Failed: $fail"
echo "  Total:  $((pass + fail))"
echo "──────────────────────────────────"

[ "$fail" -eq 0 ]
