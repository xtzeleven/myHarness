---
description: 产研全链路文档间漂移检查 — 扫 roadmap / ADR / CHANGELOG / MEMORY.md / AGENTS.md / m8-*.md / improvement-backlog 之间的不一致
argument-hint: "[focus] 可选：维度（existence / status / scope / reference / timeline）或文档（adr / roadmap / changelog / memory / agents / m8 / backlog）"
---

# /cross-stage-check

产研全链路**文档间**漂移检查的**显式入口**。判据真源已迁到 skill `cross-stage-check`（`.claude/skills/cross-stage-check/SKILL.md`）——那里维护 5 检测维度（存在性 / 状态 / 范围 / 引用链 / 时间线）、与 `/sync-docs` 的边界、执行步骤、输出格式、audit log 写入。

**执行**：加载并按 `cross-stage-check` skill 的完整流程跑；把本命令的 `$ARGUMENTS` 作为 skill 的 focus 参数透传：

- `$ARGUMENTS` 为空 → 全 5 维度 × 全文档矩阵扫
- `$ARGUMENTS` = 维度名（`existence` / `status` / `scope` / `reference` / `timeline`）→ 聚焦该维度
- `$ARGUMENTS` = 文档名（`adr` / `roadmap` / `changelog` / `memory` / `agents` / `m8` / `backlog`）→ 聚焦该文档与其他文档的漂移

> 为什么留命令又建 skill：skill 让主 Claude 在"查下文档之间有没有对不上"这类自然语言下**自主路由**；命令保留给习惯敲 `/cross-stage-check` 的显式触发。两者共用同一份判据（skill），不重复维护。

> 边界不变：本命令**绝不扫代码**（代码↔文档漂移走 `/sync-docs`）、**绝不调 agent**、**绝不直接改文件**。
