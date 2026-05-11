#!/usr/bin/env bash
# PostToolUse hook
#   1. 写 audit log（记录 Edit/Write/MultiEdit 实际发生）
#   2. 按后缀分发格式化（prettier / ruff）
#
# 入参（stdin JSON）由 Claude Code 提供，含 tool_input.file_path
# 未安装的工具走 noop；audit 失败永不挂会话。

set -uo pipefail

payload="$(cat)"

# 用 env var 传 payload 给 python（与 subagent-stop.sh 同模式，避开 heredoc 占 stdin）
extract_fields() {
  HOOK_PAYLOAD="$payload" python - <<'PY' 2>/dev/null
import json, os, sys

raw = os.environ.get("HOOK_PAYLOAD", "")
try:
    data = json.loads(raw)
except Exception:
    sys.exit(0)

tool = data.get("tool_name", "") or ""
fp = (data.get("tool_input") or {}).get("file_path", "") or ""
# 输出两行：tool / file_path
print(tool)
print(fp)
PY
}

# 提取并按行读取
mapfile -t _fields < <(extract_fields)
tool_name="${_fields[0]:-}"
tool_name="${tool_name%$'\r'}"   # 去 Windows Python print 留下的尾 \r
file_path="${_fields[1]:-}"
file_path="${file_path%$'\r'}"

# === audit log ===
# 用 env var 把 5 个字段传给 python，写一行 JSONL
_audit_log() {
  local action="$1" reason="$2"
  local target="${file_path:-}"
  target="${target:0:200}"
  AUDIT_ACTION="$action" \
  AUDIT_REASON="$reason" \
  AUDIT_TOOL="${tool_name:-}" \
  AUDIT_TARGET="$target" \
  AUDIT_BYPASS="${HARNESS_BYPASS:-0}" \
  python - <<'PY' 2>/dev/null || true
import json, os, datetime

log_dir = ".claude"
os.makedirs(log_dir, exist_ok=True)
entry = {
    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "hook": "PostToolUse",
    "tool": os.environ.get("AUDIT_TOOL", ""),
    "target": os.environ.get("AUDIT_TARGET", ""),
    "action": os.environ.get("AUDIT_ACTION", ""),
    "reason": os.environ.get("AUDIT_REASON", ""),
    "bypass": os.environ.get("AUDIT_BYPASS", "0") == "1",
}
with open(f"{log_dir}/.audit.log", "a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
PY
}

# 记录 PostToolUse 发生（有 file_path 才记，避免空噪音）
if [ -n "${file_path:-}" ]; then
  ext_for_audit="${file_path##*.}"
  _audit_log "executed" "${tool_name:-?} -> .${ext_for_audit}"
fi

# === 格式化分发 ===
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
