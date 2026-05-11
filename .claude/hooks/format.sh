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

# === 秘钥泄漏检测（事后审计，不阻止；命中只 stderr 警告 + 写 audit）===
HOOK_SECRET_FILE="$file_path" python - <<'PY' 2>&1 || true
import os, re, sys, datetime, json

if sys.platform.startswith("win"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

fp = os.environ.get("HOOK_SECRET_FILE", "")
if not fp or not os.path.exists(fp):
    sys.exit(0)

# 排除：审计日志自身、测试脚本（含 password=test 之类）、schema 示例文档
SKIP_PATTERNS = (
    ".audit.log",
    "test_pre_tool_use.sh",
    "test_user_prompt_submit.sh",
    "agent-output-schema.md",
    "improvement-backlog.md",
    "engineering-practices.md",
    ".session.state",
)
for s in SKIP_PATTERNS:
    if s in fp:
        sys.exit(0)

try:
    content = open(fp, encoding="utf-8", errors="ignore").read()
except Exception:
    sys.exit(0)

# 大文件截断（避免巨型文件全扫慢）
if len(content) > 200_000:
    content = content[:200_000]

# 高危秘钥模式
patterns = [
    (r"-----BEGIN[ \t]+[A-Z ]*PRIVATE[ \t]+KEY-----", "私钥（PEM）"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key"),
    (r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}", "OpenAI sk-* token"),
    (r"\bghp_[A-Za-z0-9]{36,}", "GitHub personal access token"),
    (r"\bgho_[A-Za-z0-9]{36,}", "GitHub OAuth token"),
    (r"\bghs_[A-Za-z0-9]{36,}", "GitHub server-to-server token"),
    (r"\bxox[abps]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT"),
    # password = xxx：长度 ≥ 10 且非占位符（test/example/fake/placeholder/$/{</...）
    (r"(?i)(password|passwd|pwd)\s*[=:]\s*[\"'`]?(?!(?:test|example|fake|placeholder|xxx|\$|\{|<))[A-Za-z0-9!@#$%^&*_+=.~/-]{10,}", "password= 字面量"),
    (r"(?i)(api[_-]?key|secret[_-]?key)\s*[=:]\s*[\"'`]?(?!(?:test|example|fake|placeholder|xxx|\$|\{|<))[A-Za-z0-9_+/=-]{16,}", "API/secret key 字面量"),
]

hits = []
for pat, label in patterns:
    m = re.search(pat, content)
    if m:
        snippet = m.group(0)[:40] + ("..." if len(m.group(0)) > 40 else "")
        hits.append((label, snippet))

if not hits:
    sys.exit(0)

# 写 audit log（每个命中独立一行，便于按 reason 聚合）
log_dir = ".claude"
try:
    os.makedirs(log_dir, exist_ok=True)
    for label, snip in hits:
        entry = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "hook": "PostToolUse",
            "action": "secret_suspect",
            "tool": "format-hook",
            "target": fp[:200],
            "reason": f"{label}: {snip}",
            "bypass": False,
        }
        with open(f"{log_dir}/.audit.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
except Exception:
    pass

# stderr 红色警告
RED = "\033[31m"
RESET = "\033[0m"
print(f"{RED}[post-tool-use] ⚠️⚠️⚠️ 疑似秘钥在 {fp}：{RESET}", file=sys.stderr)
for label, snip in hits:
    print(f"{RED}  - {label}: {snip}{RESET}", file=sys.stderr)
print(
    f"{RED}[post-tool-use] 主 Claude：立刻让用户 review 该改动，确认非真凭据；必要时 git restore 撤销。{RESET}",
    file=sys.stderr,
)
PY

exit 0
