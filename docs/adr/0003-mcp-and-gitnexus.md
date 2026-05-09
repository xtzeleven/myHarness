# ADR 0003 — MySQL 只读 MCP + gitnexus skill 接入

**Status**: Accepted
**Date**: 2026-05-09

## 背景

让 sub-agent（`schema-analyst`）能查表结构、看索引、跑 EXPLAIN，必须给数据访问能力。同时让代码探索（`gitnexus-exploring` 等）有结构化检索而非纯文本 grep。

## 决定

### MCP — MySQL 只读

- 配置：`.mcp.json` + `.env.example`
- 客户端：`@benborla29/mcp-server-mysql`
- 强制：`ALLOW_INSERT_OPERATION` / `ALLOW_UPDATE_OPERATION` / `ALLOW_DELETE_OPERATION` / `ALLOW_DDL_OPERATION` 全部 `false`
- 凭据：走 `.env` 环境变量（`${MYSQL_HOST}` 等），**绝不**硬编码
- 数据库账号：`GRANT SELECT, SHOW VIEW` 仅

### Skill — gitnexus 系列

用本机 Claude Code 环境提供的 7 个 skill（cli / exploring / debugging / impact-analysis / refactoring / pr-review / guide），**不**通过 MCP 接入。

路由策略写在 CLAUDE.md §8 与 AGENTS.md 顶部"路由速查"。

## 替代方案

### A. 给 MCP 写权限（即使是 dev 库）

- 👎 LLM 一旦走偏会污染数据，影响后续测试
- 👎 dev 库经常被开发者复用，破坏共享环境
- ❌ 弃用

### B. 把数据库凭据写进 `.mcp.json`（不走 env）

- 👍 配置简单
- 👎 `.mcp.json` 入 git，凭据泄露
- ❌ 弃用

### C. 用 gitnexus 替代代码 Grep

- 👍 结构化检索，懂 Java symbol、AST、调用图
- 👎 索引落后于代码时给错误结果
- ✅ 采纳，但要求"做完代码改动后用 `gitnexus-cli` 重建索引"（写入 CLAUDE.md §8）

## 后果

- 多一道 PreToolUse 灰名单：直接调 `mysql` / `psql` 客户端跑 DDL/DML 时拦下
- engineering-practices.md 加 §14 MCP 治理
- 新 agent `schema-analyst` 通过 MCP 工作；`migration-author` 不通过 MCP，只写 SQL 文件
- gitnexus 索引就绪是隐性前提，写入 onboard 检查清单

## 相关

- MCP 治理规则：[../../.claude/rules/engineering-practices.md](../../.claude/rules/engineering-practices.md) §14
- gitnexus 路由：[../../CLAUDE.md](../../CLAUDE.md) §8
- agent 实现：[../../.claude/agents/schema-analyst.md](../../.claude/agents/schema-analyst.md)
