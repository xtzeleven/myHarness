# Policies — 规则数据外移（P1-A）

> 本目录是 PreToolUse hook 的**规则数据**单点真源。改规则只动 yaml，不碰 `.claude/scripts/policy-dispatch.py`。

## 文件分工

| 文件            | Action   | 退出码 | 输出前缀         |
| --------------- | -------- | ------ | ---------------- |
| `deny.yaml`     | deny     | 2      | `BLOCKED:`       |
| `ask-user.yaml` | ask_user | 2      | `⚠️ 待人工授权:` |
| `hints.yaml`    | hint     | 0      | `💡 提示:`       |

`ask_user` 是灰名单：主对话**必须停下**向用户索要授权后才能重试。`hint` 不阻塞，建议性。

## 规则 schema

```yaml
- id: kebab-case-id # 必填，唯一，给 audit log 用
  tool: Bash # 必填，单值或列表 [Edit, Write, MultiEdit]
  when: # 必填，所有条件 AND
    cmd_contains_any: [...] # Bash: 字面子串 OR
    cmd_matches: <ERE> # Bash: 大小写敏感正则
    cmd_imatches: <ERE> # Bash: 大小写不敏感正则
    file_basename_in: [...] # Edit/Write: basename 精确匹配 OR
    file_basename_glob: [...] # Edit/Write: basename glob OR
    file_basename_not_in: [...] # Edit/Write: basename 排除（白名单豁免）
    file_basename_matches: <ERE> # Edit/Write: basename 正则
    file_path_matches: <ERE> # Edit/Write: 完整路径正则
    new_content_imatches: <ERE> # Edit/Write: tool_input.new_string / .content 大小写不敏感
    new_content_present: false # Edit/Write: 仅当 new_content 为空时触发（如 pom.xml 整文件改写）
  reason: "<给主对话看的原因>"
```

**所有 `when.*` 字段 AND 关系**。要 OR 就拆成多条规则。

## 添加规则流程

1. 在 `deny.yaml` / `ask-user.yaml` / `hints.yaml` 加一条
2. 跑 `bash .claude/hooks/tests/test_pre_tool_use.sh` 确认现有 26 case 仍过
3. 在测试里加新规则的正反两 case（hit / no-hit）
4. 提交时 commit 信息含 "policy:" 前缀方便追溯

## 不要做的事

- ❌ 在 dispatcher 写 if/else 分支特化某条规则 → 用 yaml 表达
- ❌ 让规则 reason 含动态信息（如文件路径）→ reason 是模板，路径在 audit log 的 target 字段
- ❌ 跨文件复用 id → id 全局唯一
- ❌ 在 yaml 里写 Python 表达式 → 保持声明式

## 与 hook 链路的关系

```
Claude Code 调 tool
   ↓ stdin JSON
.claude/hooks/pre-tool-use.sh           # 薄壳，exec 给 python dispatcher
   ↓
.claude/scripts/policy-dispatch.py      # 加载 yaml + 评估 + 写 audit log + stderr 信号
   ↓ exit code
Claude Code（0=继续 / 2=拦截）
```

dispatcher 失败时**默认放行**（exit 0），避免 hook bug 拖死会话；同时把异常写到 `.claude/.audit.log` 便于排查。
