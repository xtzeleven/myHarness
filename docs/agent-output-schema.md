# Agent Output Schema — Sub-agent 输出契约

**Status**: Accepted（M7 后置 / SubagentStop telemetry 启用）
**Date**: 2026-05-11

> **本文回答**：sub-agent 完成任务时，**输出末尾**应附一段机器可读的 schema 块，让 `SubagentStop` hook 能解析"成败 / 降级 / 升级"信号，闭合 telemetry 与 escalation policy。

## 1. 为什么需要 schema

无 schema 时：

- 自反馈环（`AGENTS.md` "自反馈环"表）靠"主 Worker 输出含「建议」或「草图」"字符串匹配 — 脆且易漏
- degradation 报告靠主 Claude 在主对话上下文中识别，写不进 `.audit.log`
- 跨 agent 升级（escalation）没有结构化触发条件

有 schema 后：

- `SubagentStop` hook 解析 → 自动写 `.claude/.audit.log`
- 主对话与 hook 间有可比对的"事实信号"
- 长期可统计：哪个 agent 经常 degraded？哪条 escalation 路径走得多？

## 2. Schema 块格式

在 agent 输出的**末尾**附加一段 HTML 注释块（主对话渲染时不可见，但 hook 可解析）：

```
<!-- harness:agent-output -->
status: ok | degraded | stop | escalate
degraded_from: <tool-or-model>           # 仅 status=degraded 时
escalate_to: <user | agent-name>          # 仅 status=escalate 时
risks: <one-line summary>                 # 可选
<!-- /harness:agent-output -->
```

### 字段定义

| 字段            | 必需      | 取值                                    | 意义                      |
| --------------- | --------- | --------------------------------------- | ------------------------- |
| `status`        | ✅        | `ok` / `degraded` / `stop` / `escalate` | 见下表                    |
| `degraded_from` | 视 status | 工具名 / 模型名                         | 哪个工具/模型失败，被替代 |
| `escalate_to`   | 视 status | `user` 或 agent 名                      | 转交给谁                  |
| `risks`         | 可选      | 单行文字                                | 主要风险摘要              |

### Status 含义

| status     | 何时用                        | hook 行为                        |
| ---------- | ----------------------------- | -------------------------------- |
| `ok`       | 正常完成，无降级              | 写 audit（静默）                 |
| `degraded` | 部分工具/模型失败，用替代完成 | 写 audit + stderr 提示主对话     |
| `stop`     | 无法完成且无替代              | 写 audit + stderr 提示主对话停   |
| `escalate` | 需要更高权限或另一 agent      | 写 audit + stderr 提示主对话转交 |

## 3. 示例

### 正常完成

```markdown
（agent 主体输出 ...）

## 评审结论

通过。

<!-- harness:agent-output -->

status: ok

<!-- /harness:agent-output -->
```

### 降级完成

```markdown
（agent 输出 ...）

## 降级说明

`gitnexus-impact-analysis` 不可用，已用 `git grep` 替代；跨聚合引用扫描可能漏。

<!-- harness:agent-output -->

status: degraded
degraded_from: gitnexus-impact-analysis
risks: 跨聚合引用扫描可能漏；建议合并前用 IDE "Find Usages" 复核

<!-- /harness:agent-output -->
```

### 升级到用户

```markdown
（agent 输出 ...）

## 我无法判断

需要选 `OrderItem` 是聚合根还是 `Order` 的内部实体，涉及业务规则取舍。

<!-- harness:agent-output -->

status: escalate
escalate_to: user
risks: 聚合边界决策影响事务范围与一致性

<!-- /harness:agent-output -->
```

### 升级到另一 agent

```markdown
（spring-boot-reviewer 输出 ...）

## 发现 DDD 边界问题

`@Transactional` 在 domain 层。本 agent 范围只判 Spring 反模式，建议交 `ddd-architect`。

<!-- harness:agent-output -->

status: escalate
escalate_to: ddd-architect
risks: 事务边界泄漏 + 领域纯净性问题，需 DDD 层面判定

<!-- /harness:agent-output -->
```

## 4. Agent 何时该加

**强制场景**（M8 启动时必填）：

- 任何 review / audit 类 agent：`code-reviewer` / `spring-boot-reviewer` / `ddd-architect` / `docs-keeper`
- 任何可能降级的 agent：`schema-analyst`（MCP 失败时）

**可选场景**：

- 实现类 agent：`tdd-cycle-driver` / `migration-author`（输出主体是代码，schema 块在末尾的 markdown 注释里）

**不强制**：

- M7 阶段是逐步推广。**没加 schema 的 agent 仍正常工作**，hook silently skip，不报错不阻塞。

## 5. 与 hook 的关系

`.claude/hooks/subagent-stop.sh`：

1. 从 sub-agent 输出中提取第一个 `<!-- harness:agent-output --> ... <!-- /harness:agent-output -->` 块
2. 按行解析键值（忽略注释行 `#` 与空行）
3. 写 `.claude/.audit.log` 一行 JSONL（`hook: "SubagentStop"`）
4. **非 `ok` 状态时**：stderr 输出 `[subagent-stop] ⚠️ Agent <name> status=...`，提示主对话

详见 [`.claude/hooks/subagent-stop.sh`](../.claude/hooks/subagent-stop.sh)。

## 6. 与 AGENTS.md "自反馈环" 的关系

[AGENTS.md "自反馈环"](../AGENTS.md) 触发条件之前靠"主 Worker 输出含「建议」"字符串匹配。

启用 schema 后：

- `status: degraded` → 自动触发反馈 Worker（reviewing 类）
- `status: escalate` 且 `escalate_to: <agent-name>` → 主对话按字段转交，不再猜测
- `status: escalate` 且 `escalate_to: user` → 主对话停下问用户，不再自己接续

主对话仍是协调者，但**触发条件从主观判断升级为可比对事实**。

## 7. 反模式

- ❌ schema 块放在中间（破坏输出可读性；hook 找第一个，可能拿到错误内容）
- ❌ 多个 schema 块（hook 只取第一个，其他被忽略且无警告）
- ❌ 用 `status: degraded` 但不填 `degraded_from`（hook 写 audit 时 `degraded_from=""`，分析时无法追责）
- ❌ 用 `status: escalate` 但 `escalate_to` 留空（hook 不知道转给谁，等于 stop）
- ❌ 把 schema 当 enforcement（hook 不阻止 agent 输出，是 telemetry 信号不是 gate）
- ❌ schema 块里塞业务内容（schema 是元数据，业务结论留在主体输出里）

## 8. 迁移路径

- **当前**：所有 agent 默认无 schema → hook silently skip
- **M8 前**：先给 `ddd-architect` / `spring-boot-reviewer` / `schema-analyst` 加（review/audit/可降级类）
- **M8 中**：每个 agent 文件末尾补"输出范例"节，含 schema 块
- **M9**：在 agent frontmatter 校验中加 schema 必填项（可选 enforcement，CI 拦不带 schema 的 agent 文件）

## 9. 与其他文档的关系

- [AGENTS.md](../AGENTS.md) "自反馈环" / "升级链" 表：触发与转交的语义来源
- [.claude/rules/engineering-practices.md §15](../.claude/rules/engineering-practices.md) Policy 机制化：本 schema 是 "拒绝继续 / 升级链" 的执行入口
- [docs/loop-architecture.md §3](loop-architecture.md) Degradation：本 schema 把 degradation 从文档约定变为可写入审计的事件
- [docs/tools-fallback.md §7](tools-fallback.md) audit log：本 schema 让 `audit-log-summary.py --type degrade` 真有数据可统计
