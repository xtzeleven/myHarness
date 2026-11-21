#!/usr/bin/env bash
# PreToolUse hook — 薄壳，转发给 python dispatcher
#
# P1-A 后规则数据全部在 .claude/rules/policies/*.yaml；本脚本只负责调用 dispatcher。
# 失败要响（ADR-0009 / D1-A）：找不到 python 或 dispatcher 无法加载黑名单 → 拦截（exit 2）并告知修法；
# 灰名单走 stdout JSON permissionDecision=ask，由 Claude Code 原生弹窗确认。
#
# 改规则：编辑 yaml，无需碰本文件或 dispatcher。

py=""
for c in python python3; do
  if command -v "$c" >/dev/null 2>&1; then py="$c"; break; fi
done
if [ -z "$py" ]; then
  echo "[pre-tool-use] BLOCKED (fail-closed): 找不到 python / python3，门禁无法运行。装 Python 3 + pyyaml 后重试。" >&2
  exit 2
fi

exec "$py" "$(dirname "$0")/../scripts/policy-dispatch.py"
