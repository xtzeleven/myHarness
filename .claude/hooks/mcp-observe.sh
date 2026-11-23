#!/usr/bin/env bash
# PreToolUse hook（matcher mcp__.*）— MCP 调用只记审计，不拦（G13 / 规则清单 K4）
#
# 与 pre-tool-use.sh 相反：这里任何失败都放行（exit 0），观测不能变成门禁。
# 每次调用写一行 action=mcp_call：tool = mcp__<server>__<tool>，target = tool_input 前 200 字符。
# 看用量：python .claude/scripts/audit-log-summary.py --by-tool

py=""
for c in python python3; do
  if command -v "$c" >/dev/null 2>&1; then py="$c"; break; fi
done
if [ -n "$py" ]; then
  "$py" "$(dirname "$0")/../scripts/policy-dispatch.py" --observe-mcp >/dev/null 2>&1
fi
exit 0
