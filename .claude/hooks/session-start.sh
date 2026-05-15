#!/usr/bin/env bash
# SessionStart hook：会话开始时注入项目快照与未完事项
# 输出到 stdout，会被注入到主对话上下文（Claude Code 约定）
# 注：失败不要让会话挂掉，所有错误兜底 echo 后 exit 0

set -uo pipefail

cd "$(dirname "$0")/../.." 2>/dev/null || exit 0

separator="──────────────────────────────────────────"

print_section() {
  echo ""
  echo "$separator"
  echo "▶ $1"
  echo "$separator"
}

# 1. Git 当前态
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  print_section "Git 当前态"
  echo "branch:  $(git branch --show-current 2>/dev/null || echo 'detached')"
  echo "head:    $(git log -1 --pretty='%h %s' 2>/dev/null || echo '<no commits>')"

  changed="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${changed:-0}" -gt 0 ]; then
    echo "未提交变更: ${changed} 个文件"
    git status --porcelain 2>/dev/null | head -10
    [ "$changed" -gt 10 ] && echo "... 等 $((changed - 10)) 个"
  else
    echo "工作树干净"
  fi

  echo ""
  echo "最近 3 个 commit:"
  git log --oneline -3 2>/dev/null
fi

# 2. 上次会话未完事项（从 .session.state 读）
state_file=".claude/.session.state"
if [ -f "$state_file" ]; then
  print_section "上次会话状态"
  python -c "
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
try:
    s = json.load(open('$state_file', encoding='utf-8'))
    print(f\"上次任务: {s.get('current_task', '<未知>')}\")
    pending = s.get('pending_steps', [])
    if pending:
        print(f\"未完步骤 ({len(pending)} 项):\")
        for p in pending[:5]:
            print(f\"  - {p}\")
        if len(pending) > 5:
            print(f\"  ... 等 {len(pending) - 5} 项\")
    blocked = s.get('blocked_on')
    if blocked:
        print(f\"阻塞在: {blocked}\")
    print(f\"上次结束: {s.get('ended_at', '<无>')}\")
    print(f\"上次 head: {s.get('head_sha', '<无>')} {s.get('head_msg', '')}\")
except Exception as e:
    print(f\"<读 .session.state 失败: {e}>\")
" 2>/dev/null || echo "<.session.state 解析失败>"
fi

# 3. Memory 索引摘要
memory_index=""
home_dir="${HOME:-}"
user_name="${USER:-${USERNAME:-rw135}}"
for candidate in \
  "${home_dir}/.claude/projects/D--myGithub-myHarness/memory/MEMORY.md" \
  "/c/Users/${user_name}/.claude/projects/D--myGithub-myHarness/memory/MEMORY.md" \
  "/c/Users/rw135/.claude/projects/D--myGithub-myHarness/memory/MEMORY.md"; do
  if [ -f "$candidate" ]; then
    memory_index="$candidate"
    break
  fi
done

if [ -n "$memory_index" ]; then
  print_section "Memory 索引（按需查阅）"
  decision_count="$(grep -c '^- \[decision_' "$memory_index" 2>/dev/null || echo 0)"
  pitfall_count="$(grep -c '^- \[pitfall_' "$memory_index" 2>/dev/null || echo 0)"
  echo "决策类: ${decision_count} 条；踩坑类: ${pitfall_count} 条"
  echo ""
  echo "常用查阅场景（详见 CLAUDE.md §11）："
  echo "  写/调 hook → pitfall_jq_not_in_path / pitfall_hook_self_block"
  echo "  加 PreToolUse 规则 → pitfall_sql_detection_overscan"
  echo "  加 .gitignore → pitfall_settings_local_already_tracked"
  echo "  Bash 路径问题 → pitfall_windows_path_d_drive"
fi

# 4. 工具就绪状态
print_section "工具就绪"
for cmd in git python npx mvn java; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "  ✅ $cmd"
  else
    echo "  ❌ $cmd（未安装）"
  fi
done
[ -f .env ] && echo "  ✅ .env" || echo "  ⚠️  .env 缺失（MCP 不可用，详见 .env.example）"

# 5. 清空 .session.hints（P2-I：每会话重置 hint 去重缓存）
mkdir -p .claude 2>/dev/null || true
: > .claude/.session.hints 2>/dev/null || true

echo "$separator"
echo ""

exit 0
