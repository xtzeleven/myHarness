#!/usr/bin/env bash
# UserPromptSubmit hook：用户提交 prompt 时早期敏感词检测
#
# 不阻止用户提交（exit 0），但对主对话给 stderr 警告 + 写 audit log。
# 检测命中后主 Claude 应该："理解用户意图 → 改写指令 → 必要时停下问用户"，
# 而不是直接照搬到工具调用。
#
# 设计取舍：宁可有 false positive 多警告，也不漏掉真高危词。
# 误警告对工作流影响小（只是 stderr 一句话）；漏检会让危险命令一路下到 PreToolUse。

set -uo pipefail

payload="$(cat)"

# 用 env var 传 payload，与其他 hook 一致
HOOK_PAYLOAD="$payload" python - <<'PY' 2>&1 || true
import json, os, sys, re, datetime

if sys.platform.startswith("win"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

raw = os.environ.get("HOOK_PAYLOAD", "")
try:
    data = json.loads(raw)
except Exception:
    sys.exit(0)

# 取 prompt 文本（Claude Code 字段名可能变，尝试多种）
prompt = ""
for k in ("prompt", "user_prompt", "message", "input", "content", "text"):
    v = data.get(k)
    if not v:
        continue
    if isinstance(v, dict):
        v = v.get("prompt") or v.get("text") or v.get("content") or ""
    elif isinstance(v, list):
        v = "\n".join(str(x) for x in v)
    prompt = str(v)
    break

if not prompt:
    sys.exit(0)

# 高危模式（命中即警告）
# 注意：使用 IGNORECASE；模式尽量精确避免误伤
patterns = [
    (r"\brm\s+-rf\s+/(\s|$|\*)", "rm -rf 根目录"),
    (r"\brm\s+-rf\s+~(\s|$)", "rm -rf 家目录"),
    (r"\brm\s+-rf\s+\$HOME", "rm -rf $HOME"),
    (r"\bDROP\s+(DATABASE|SCHEMA|TABLE)", "SQL DROP"),
    (r"\bTRUNCATE\s+TABLE", "SQL TRUNCATE"),
    (r"--no-verify\b", "绕过 git hook（--no-verify）"),
    (r"\bgit\s+push\s+(--force|-f)\b", "git 强推（force push）"),
    (r"\bchmod\s+-R?\s*777\b", "chmod 777"),
    (r"\bcurl\b[^|]*\|\s*(sh|bash)\b", "curl|sh 远程脚本"),
    (r"\b(?:CLAUDE_PLUGIN_)?HARNESS_BYPASS=1\b", "用户提及 HARNESS_BYPASS（请确认场景）"),
    (r"\bsudo\s+rm\b", "sudo rm"),
    (r"\bgit\s+reset\s+--hard\s+origin/(main|master|prod)", "git reset --hard 远端主分支"),
    (r":\(\)\s*\{\s*:\|:&\s*\}\s*;:", "fork bomb"),
]

hits = []
snippets = {}
for pat, label in patterns:
    m = re.search(pat, prompt, re.IGNORECASE)
    if m:
        hits.append(label)
        snippets[label] = m.group(0)[:60]

if not hits:
    sys.exit(0)

# 写 audit log
project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
log_dir = os.path.join(project_dir, ".claude") if project_dir else ".claude"
try:
    os.makedirs(log_dir, exist_ok=True)
    entry = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "hook": "UserPromptSubmit",
        "action": "warn",
        "reason": "; ".join(hits),
        "tool": "user-prompt",
        "target": prompt[:200],
        "bypass": False,
    }
    with open(os.path.join(log_dir, ".audit.log"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
except Exception:
    pass

# stderr 警告主对话
print(f"[user-prompt-submit] ⚠️ 用户 prompt 含敏感模式（{len(hits)} 项）：", file=sys.stderr)
for h in hits:
    print(f"  - {h}: {snippets[h]!r}", file=sys.stderr)
print(
    "[user-prompt-submit] 主 Claude：先理解用户意图，必要时改写指令或停下询问，不要直接照搬到工具调用。",
    file=sys.stderr,
)
PY

exit 0
