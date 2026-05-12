#!/usr/bin/env bash
# scripts/dev.sh — 启动 Claude Code 自举模式
#
# ADR-0006 后，myHarness 仓库自身的 Harness 资产全在 plugin/ 下；
# 开发期用 `claude --plugin-dir ./plugin` 加载本仓库的 plugin，等于持续 dogfooding。
#
# 用法：
#   bash scripts/dev.sh             # 等价 claude --plugin-dir ./plugin
#   bash scripts/dev.sh --resume    # 透传 claude 参数
#
# 如果 claude CLI 不在 PATH 中，会给出安装提示。

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/plugin"

if [ ! -d "$PLUGIN_DIR/.claude-plugin" ]; then
  echo "ERROR: $PLUGIN_DIR/.claude-plugin/ 不存在 — 你是否在 myHarness 根目录跑这个脚本？" >&2
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "ERROR: claude CLI 未安装。" >&2
  echo "       npm install -g @anthropic-ai/claude-code" >&2
  exit 1
fi

exec claude --plugin-dir "$PLUGIN_DIR" "$@"
