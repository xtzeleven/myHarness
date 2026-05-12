#!/usr/bin/env bash
# Stop hook：会话结束前
#  1) 显示未提交变更摘要（>20 文件给警告）
#  2) 写 .claude/.session.state（gitignored）供下次 SessionStart 读
# 失败不要让会话挂掉，所有错误兜底 echo 后 exit 0

set -uo pipefail

# plugin 模式 Claude Code 注入 CLAUDE_PROJECT_DIR；standalone 模式 fallback
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" 2>/dev/null || exit 0

command -v git >/dev/null 2>&1 || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

changes="$(git status --porcelain 2>/dev/null)"
count="$(printf '%s' "$changes" | grep -c . || true)"
preview="$(printf '%s' "$changes" | head -20)"

# === 1. 摘要输出 ===
{
  echo ""
  echo "──────────────────────────────────────────"
  if [ "$count" -eq 0 ]; then
    echo "[stop-check] 工作树干净 ✅"
  else
    echo "[stop-check] 检测到 ${count} 处未提交变更"
    echo "$preview"
    if [ "$count" -gt 20 ]; then
      echo "..."
      echo "⚠️  变更超过 20 个文件，建议分批提交或先用 git status 复核"
    fi
  fi
  echo "──────────────────────────────────────────"
} >&2

# === 2. 写 .session.state（M5 引入，loop-architecture.md 中描述） ===
state_file=".claude/.session.state"
mkdir -p .claude

branch="$(git branch --show-current 2>/dev/null || echo '')"
head_sha="$(git log -1 --pretty='%h' 2>/dev/null || echo '')"
head_msg="$(git log -1 --pretty='%s' 2>/dev/null || echo '')"
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo '')"

# 用 python 写 JSON 避免引号转义问题
python - "$state_file" "$branch" "$head_sha" "$head_msg" "$ts" "$count" <<'PY' 2>/dev/null || true
import json, sys, os
state_file, branch, head, msg, ts, count = sys.argv[1:7]

# 保留旧 state 中可能的 pending_steps（hook 不知道用户实际做到哪步，由用户/Driver 维护）
prev = {}
if os.path.exists(state_file):
    try:
        prev = json.load(open(state_file))
    except Exception:
        prev = {}

state = {
    "ended_at": ts,
    "branch": branch,
    "head_sha": head,
    "head_msg": msg,
    "uncommitted_count": int(count or 0),
    # 这些字段由 Driver 在会话中维护（M5 后约定）；hook 不擦除已有值
    "current_task": prev.get("current_task"),
    "pending_steps": prev.get("pending_steps", []),
    "blocked_on": prev.get("blocked_on"),
    "last_checkpoint": prev.get("last_checkpoint"),
}
with open(state_file, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=2, ensure_ascii=False)
PY

exit 0
