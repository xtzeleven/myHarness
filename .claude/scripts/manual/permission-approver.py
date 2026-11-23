#!/usr/bin/env python3
"""最小 MCP stdio server：permission prompt tool，一律批准并记日志（模拟用户点"同意"）。

供 permission-mode-check.sh 的 host 轮使用（--permission-prompt-tool mcp__approver__approve）。
"""
import json, sys, os, datetime
LOG = os.environ["G1_APPROVER_LOG"]
def send(m): sys.stdout.write(json.dumps(m) + "\n"); sys.stdout.flush()
for line in sys.stdin:
    try: m = json.loads(line)
    except Exception: continue
    mid, meth = m.get("id"), m.get("method")
    if meth == "initialize":
        send({"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": m["params"].get("protocolVersion", "2024-11-05"),
              "capabilities": {"tools": {}}, "serverInfo": {"name": "approver", "version": "0"}}})
    elif meth == "tools/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [{"name": "approve", "description": "approve permission prompts",
              "inputSchema": {"type": "object", "properties": {"tool_name": {"type": "string"}, "input": {"type": "object"}, "tool_use_id": {"type": "string"}}}}]}})
    elif meth == "tools/call":
        a = m["params"].get("arguments") or {}
        with open(LOG, "a") as f:
            f.write(json.dumps({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "tool": a.get("tool_name"), "input": a.get("input")}, ensure_ascii=False) + "\n")
        send({"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": json.dumps({"behavior": "allow", "updatedInput": a.get("input") or {}})}]}})
    elif mid is not None:
        send({"jsonrpc": "2.0", "id": mid, "result": {}})
