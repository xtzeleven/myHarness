#!/usr/bin/env bash
# PostToolUse format hook
# 入参（stdin JSON）由 Claude Code 提供，含 tool_input.file_path
# 仅对当前项目实际涉及的文件类型分发，未安装的工具走 noop

set -uo pipefail

payload="$(cat)"

# 提取 file_path（python 解析 JSON，与 pre-tool-use.sh 一致，避免 sed 在转义引号上截断）
file_path="$(printf '%s' "$payload" | python -c '
import json, sys
try:
    data = json.load(sys.stdin)
    sys.stdout.write(data.get("tool_input", {}).get("file_path", "") or "")
except Exception:
    pass
' 2>/dev/null)"

[ -z "${file_path:-}" ] && exit 0
[ ! -f "$file_path" ] && exit 0

ext="${file_path##*.}"

run_prettier() {
  command -v npx >/dev/null 2>&1 || { echo "[format] npx not found, skip" >&2; return 0; }
  npx --no-install prettier --write "$file_path" >/dev/null 2>&1 \
    || npx --yes prettier --write "$file_path" >/dev/null 2>&1 \
    || echo "[format] prettier failed on $file_path" >&2
}

run_ruff() {
  if command -v ruff >/dev/null 2>&1; then
    ruff format "$file_path" >/dev/null 2>&1 || echo "[format] ruff failed on $file_path" >&2
  fi
}

case "$ext" in
  md|json|js|ts|tsx|jsx|css|html|yml|yaml)
    run_prettier
    ;;
  py)
    run_ruff
    ;;
  java)
    : # 跳过：未要求强制 google-java-format
    ;;
  *)
    : # noop
    ;;
esac

exit 0
