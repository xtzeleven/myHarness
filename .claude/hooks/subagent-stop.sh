#!/usr/bin/env bash
# SubagentStop hook：sub-agent 完成时解析输出
#
# 在 sub-agent 输出末尾找 <!-- harness:agent-output --> 块（详见
# docs/agent-output-schema.md），写一行 JSONL 到 .claude/.audit.log，
# 非 ok 状态时 stderr 提示主对话。
#
# 失败永远不挂住会话（exit 0），所有解析问题静默吞掉。
#
# 协议字段：status / degraded_from / escalate_to / risks。

set -uo pipefail

payload="$(cat)"

# 用 env var 传 payload 给 python（避开 heredoc 占用 stdin 的坑）
HOOK_PAYLOAD="$payload" python - <<'PY' 2>&1 || true
import json, os, sys, re, datetime

# Windows console 默认 cp936；stderr 输出中文 / emoji 走 utf-8
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


def pick(d, keys):
    if not isinstance(d, dict):
        return ""
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return ""


# agent 名（Claude Code 字段名未公开稳定，尝试多种）
agent_name = (
    pick(data, ["subagent_type", "agent", "agent_name"])
    or pick(data.get("tool_input", {}), ["subagent_type", "agent"])
    or "unknown"
)

# sub-agent 文本输出（同样多字段尝试）
output = ""
for key in ("output", "result", "content", "tool_response", "response"):
    v = data.get(key)
    if not v:
        continue
    if isinstance(v, dict):
        v = v.get("content") or v.get("text") or json.dumps(v)
    elif isinstance(v, list):
        # tool_response 常见为 [{type:"text", text:"..."}]
        parts = []
        for item in v:
            if isinstance(item, dict):
                parts.append(item.get("text") or item.get("content") or "")
            else:
                parts.append(str(item))
        v = "\n".join(parts)
    output = str(v)
    break

# 找第一个 schema 块
m = re.search(
    r"<!--\s*harness:agent-output\s*-->(.*?)<!--\s*/harness:agent-output\s*-->",
    output,
    re.DOTALL,
)
if not m:
    # 无 schema 块：silently skip（不强制 agent 加 schema）
    sys.exit(0)

schema_text = m.group(1)

# 按行解析 key: value（忽略空行 / 注释行）
parsed = {}
for line in schema_text.splitlines():
    s = line.strip()
    if not s or s.startswith("#"):
        continue
    if ":" not in s:
        continue
    k, v = s.split(":", 1)
    # 去掉行内注释 "# ..."
    v = v.split("#", 1)[0].strip()
    parsed[k.strip()] = v

status = parsed.get("status", "")
degraded_from = parsed.get("degraded_from", "")
escalate_to = parsed.get("escalate_to", "")
risks = parsed.get("risks", "")

# 写 audit log
log_dir = ".claude"
try:
    os.makedirs(log_dir, exist_ok=True)
    entry = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "hook": "SubagentStop",
        "agent": str(agent_name),
        "status": status,
        "degraded_from": degraded_from,
        "escalate_to": escalate_to,
        "risks": risks,
        "bypass": False,
    }
    with open(f"{log_dir}/.audit.log", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
except Exception:
    pass

# 非 ok 状态：stderr 提示主对话
if status and status != "ok":
    print(f"[subagent-stop] ⚠️ Agent {agent_name} status={status}", file=sys.stderr)
    if degraded_from:
        print(f"  degraded_from: {degraded_from}", file=sys.stderr)
    if escalate_to:
        print(f"  escalate_to: {escalate_to}", file=sys.stderr)
    if risks:
        print(f"  risks: {risks}", file=sys.stderr)
    print(
        "[subagent-stop] 主 Claude：根据 status 决定下一步（degraded→可继续/写明 / stop→停下问用户 / escalate→按 escalate_to 转交）",
        file=sys.stderr,
    )
PY

exit 0
