---
description: 工程实践自检清单，对照 engineering-practices.md 15 节逐项打勾
argument-hint: "[focus] 可选：聚焦某一节名（如 ddd / java / mcp / hooks / policy）"
---

# /audit-practices

工程实践 15 维度自检的**显式入口**。判据真源已迁到 skill `audit-practices`（`.claude/skills/audit-practices/SKILL.md`）——那里维护 15 维度清单、执行步骤、输出模板、audit log 写入。

**执行**：加载并按 `audit-practices` skill 的完整流程跑；把本命令的 `$ARGUMENTS` 作为 skill 的 focus 参数透传：

- `$ARGUMENTS` 为空 → 全量 15 维度
- `$ARGUMENTS` = 关键词（`ddd` / `java` / `mcp` / `hooks` / `ci` / `policy` …）→ 仅深度审查该维度并给修复样例

> 为什么留命令又建 skill：skill 让主 Claude 在"帮我自检下工程实践"这类自然语言下**自主路由**；命令保留给习惯敲 `/audit-practices` 的显式触发。两者共用同一份判据（skill），不重复维护。
