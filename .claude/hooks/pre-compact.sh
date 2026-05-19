#!/usr/bin/env bash
# PreCompact hook：上下文压缩前注入"必须保留"提示，让 compaction 不丢关键状态。
#
# Claude Code 在上下文接近耗尽时会自动 compact（摘要早段消息）。本 hook 在 compact
# 触发前跑，stdout 内容会作为"建议保留"提示注入到压缩流程，提醒 LLM 不要把这些丢掉。
#
# 触发场景：上下文超阈值前 / 手动 /compact 命令。
#
# 失败兜底 exit 0，不阻断 compaction。

set -uo pipefail

cd "$(dirname "$0")/../.." 2>/dev/null || exit 0

sep="──────────────────────────────────────────"

echo ""
echo "$sep"
echo "▶ PreCompact: 务必在压缩摘要中保留以下内容"
echo "$sep"

# 1. CLAUDE.md 核心约束（行为准则 + 禁忌）—— 跨会话稳定，cache 友好
echo ""
echo "## 必保留：项目硬规则锚点"
echo "  - CLAUDE.md §1-§4 (行为准则 / 简单优先 / 外科手术 / 目标驱动)"
echo "  - CLAUDE.md §6 (禁忌事项：domain 层不依赖 Spring / 不跨聚合直接引用 etc.)"
echo "  - CLAUDE.md §9 (人工决策清单：黑+灰名单)"
echo "  - .claude/rules/engineering-practices.md §12 (DDD 分层) / §15 (Policy 机制化)"

# 2. 当前会话任务（从 .session.state 读）
state_file=".claude/.session.state"
if [ -f "$state_file" ]; then
  echo ""
  echo "## 必保留：当前任务进展"
  python -c "
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
try:
    s = json.load(open('$state_file', encoding='utf-8'))
    t = s.get('current_task') or '<无>'
    pending = s.get('pending_steps') or []
    blocked = s.get('blocked_on')
    print(f'  - 当前任务: {t}')
    if pending:
        print(f'  - 未完步骤 ({len(pending)}):')
        for p in pending[:8]:
            print(f'    · {p}')
        if len(pending) > 8:
            print(f'    · ... 等 {len(pending) - 8} 项')
    if blocked:
        print(f'  - 阻塞: {blocked}')
except Exception:
    pass
" 2>/dev/null || true
fi

# 3. 用户的显式授权（防止压缩后忘记，又去问一次）
echo ""
echo "## 必保留：本会话内的用户授权"
echo "  - 任何 PreToolUse 灰名单触发后用户给的"授权"指令"
echo "  - 用户对方向 / 范围的明确选择（AskUserQuestion 答案）"
echo "  - 用户已"提交"或"完成"的 step 不要重复执行"

# 4. 未提交改动概要（让压缩后仍知道有 N 个文件待 commit）
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  changed="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${changed:-0}" -gt 0 ]; then
    echo ""
    echo "## 必保留：未提交改动 ($changed 文件)"
    git status --porcelain 2>/dev/null | head -10 | sed 's/^/  /'
    [ "$changed" -gt 10 ] && echo "  ... 等 $((changed - 10)) 个"
  fi
fi

echo ""
echo "$sep"
echo ""

exit 0
