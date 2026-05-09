#!/usr/bin/env bash
# Stop hook：会话结束前检查未提交变更
# 变动 >20 文件给警告（stderr 输出会显示给用户）

set -uo pipefail

command -v git >/dev/null 2>&1 || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

changes="$(git status --porcelain 2>/dev/null)"
[ -z "$changes" ] && exit 0

count="$(printf '%s\n' "$changes" | wc -l | tr -d ' ')"
preview="$(printf '%s\n' "$changes" | head -20)"

{
  echo ""
  echo "──────────────────────────────────────────"
  echo "[stop-check] 检测到 ${count} 处未提交变更"
  echo "$preview"
  if [ "$count" -gt 20 ]; then
    echo "..."
    echo "⚠️  变更超过 20 个文件，建议分批提交或先用 git status 复核"
  fi
  echo "──────────────────────────────────────────"
} >&2

exit 0
