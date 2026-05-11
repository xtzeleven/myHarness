# myHarness

> 自用 Harness 工程级实践
> _Real-world coding benchmark for AI assistants_

![Status](https://img.shields.io/badge/status-M7%20done%20%7C%20M8%20next-green)
![License](https://img.shields.io/badge/license-MIT-blue)
![Models](https://img.shields.io/badge/models-8%2B-green)

## 🎯 项目简介

从 Harness 原理开始，构建持续迭代框架，用一个 **Java + DDD** 后端实战来验证三层 Harness 在真实工程中的有效性。

> **当前状态**：M7 完成 — 六维度 Harness 框架（Loop / Context / Tools / Permission Gate / Memory / Policy）就绪。M8 待启动：实例化 Java DDD 骨架（`pom.xml` + `src/`，作为六维度回归测试场）。

## 🛠️ 技术路线

### 三层 Harness 架构

- **Layer 1：约束层（Constraint Harness）**
  在 LLM 行动**之前**注入规则与禁忌，让"错误的代码写不出来"。
  - `CLAUDE.md`：每次会话自动注入的行为准则（10 节，含 Java/DDD 上下文与 gitnexus 路由）
  - `.claude/rules/engineering-practices.md`：15 节工程化规则（11 通用 + DDD 分层 / Java&Spring / MCP 治理 + Policy 机制化）
  - `.claude/hooks/pre-tool-use.sh`：黑名单（直接拦：`rm -rf /`、强推主分支、写敏感文件）+ 灰名单（人工授权：DDD 边界改动、主依赖升级、DDL/DML、`mvn deploy`）

- **Layer 2：反馈循环层（Feedback Loop）**
  在 LLM 行动**期间与之后**给出即时信号，让"错的能立刻被纠"。
  - **Hooks**：SessionStart（注入 git 态 / memory 索引 / 工具就绪）+ PreToolUse（黑灰双层 + 审计日志 + 按需 hint）+ PostToolUse（按后缀分发 prettier/ruff）+ Stop（变更摘要 + 写 `.session.state`）
  - **8 个 Sub-agents**：`tdd-cycle-driver`（TDD 红绿重构）、`code-reviewer`（通用评审）、`ddd-architect`（DDD 战略战术，opus）、`spring-boot-reviewer`（Spring 反模式）、`maven-build-doctor`（构建诊断）、`schema-analyst`（schema/SQL 分析，走 MySQL MCP）、`migration-author`（Flyway/Liquibase）、`docs-keeper`（文档漂移检测）
  - **5 个 Slash commands**：`/audit-practices`（15 维度自检）、`/audit-context`（token 注入审计）、`/commit`（标准化提交）、`/onboard`（新人 5 分钟上手）、`/sync-docs`（文档同步检查）
  - **gitnexus skills**：探索 / 调试 / 影响面 / 重构 / PR 评审 / 索引 七件套（外部环境提供）

- **Layer 3：质量门禁层（Quality Gates）**
  在 LLM **不可绕过**的位置兜底，让"绕过了也合不进 main"。
  - `.gitignore` 覆盖 IDE / OS / Node / Python / Java / 密钥 六类
  - GitHub Actions `lint.yml`：prettier --check + 必需文件存在性 + JSON 合法性 + AGENTS 链接有效性
  - 提交规范：Conventional Commits（由 `/commit` 命令统一动作）

### 数据 / MCP 接入

- `.mcp.json`：MySQL 只读 MCP（强制 `ALLOW_*=false`），凭据走 `.env`（在 .gitignore）
- `.env.example`：变量模板（与 `.mcp.json` 引用对齐）
- 数据库账号约束：仅 `GRANT SELECT, SHOW VIEW`

## 📊 阶段性路线

| 阶段   | 目标                                                                 | 状态    |
| ------ | -------------------------------------------------------------------- | ------- |
| **M0** | 项目立项，写下三层架构假设                                           | ✅ 完成 |
| **M1** | Layer 1 落地（CLAUDE.md + rules + PreToolUse）                       | ✅ 完成 |
| **M2** | Layer 2 落地（hooks + agents + commands）                            | ✅ 完成 |
| **M3** | Layer 3 落地（CI + 提交规范 + 必需文件门禁）                         | ✅ 完成 |
| **M4** | Memory 启用（决策原因 + 项目踩坑两类，索引 `MEMORY.md`）             | ✅ 完成 |
| **M5** | Loop 架构（Driver/Worker 调度 + 三策略 + `.session.state` 恢复）     | ✅ 完成 |
| **M6** | Context 治理（token 预算 ≤ 8K + 按需 hint + 子目录 CLAUDE.md 规划）  | ✅ 完成 |
| **M7** | Tools 治理 + Policy 机制化（版本锁 + 降级链 + bypass + audit log）   | ✅ 完成 |
| **M8** | 实例化 Java DDD 骨架（`pom.xml` + `src/`，六维度回归测试场）         | 🟢 当前 |

## 🚀 快速上手

```bash
git clone <repo> && cd myHarness

# 1. 看准则与规则
cat CLAUDE.md
cat .claude/rules/engineering-practices.md

# 2. 配 MCP（可选，需 MySQL 只读账号）
cp .env.example .env && vi .env

# 3. 跑自检
/audit-practices

# 4. 新人路径
/onboard backend
```

## 📁 目录速览

```
CLAUDE.md                            行为准则（10 节，每会话自动注入）
README.md                            本文件
AGENTS.md                            Agent 索引（路由表 + 8 agent）
CHANGELOG.md                         发布变更记录
.gitignore .env.example .mcp.json    Git / 环境 / MCP 配置

.claude/
  settings.json                      共享配置（hooks 注册）
  settings.local.json                本地权限（已 .gitignore，不入仓库）
  rules/engineering-practices.md     15 节工程化规则
  hooks/
    pre-tool-use.sh                  黑+灰双层防御 + 审计日志 + 按需 hint
    format.sh                        PostToolUse 格式化
    session-start.sh                 注入 git 态 / memory / 工具就绪
    stop-check.sh                    会话结束摘要 + 写 .session.state
  agents/                            8 个：tdd-cycle-driver / code-reviewer
                                    / ddd-architect / spring-boot-reviewer
                                    / maven-build-doctor / schema-analyst
                                    / migration-author / docs-keeper
  commands/                          5 个：audit-practices / audit-context
                                    / commit / onboard / sync-docs
  scripts/
    audit-context-cost.py            token 注入审计
    audit-log-summary.py             .audit.log 摘要

docs/
  roadmap.md                         六维度路线（M4-M8）
  loop-architecture.md               Driver/Worker 调度
  context-management.md              token 预算与按需注入
  tools-fallback.md                  工具降级链
  memory-conventions.md              memory 与 ADR 分工
  periodic-tasks.md                  /loop + GH Actions schedule
  AGENTS.backend.md                  后端 agent 索引（Java/DDD 实战）
  adr/                               架构决策记录

.github/workflows/
  lint.yml                           push/PR 质量门禁
  scheduled.yml                      每日结构 + 每周 stale 自检
```

## 🧭 关键文档导航

| 想了解          | 看                                                                               |
| --------------- | -------------------------------------------------------------------------------- |
| 行为准则        | [CLAUDE.md](CLAUDE.md)                                                           |
| Agent 用哪个    | [AGENTS.md](AGENTS.md) 路由速查                                                  |
| 后端 Agent 协作 | [docs/AGENTS.backend.md](docs/AGENTS.backend.md)                                 |
| 工程化规则      | [.claude/rules/engineering-practices.md](.claude/rules/engineering-practices.md) |
| 六维度路线      | [docs/roadmap.md](docs/roadmap.md)                                               |
| Loop 架构       | [docs/loop-architecture.md](docs/loop-architecture.md)                           |
| Context 治理    | [docs/context-management.md](docs/context-management.md)                         |
| 工具降级链      | [docs/tools-fallback.md](docs/tools-fallback.md)                                 |
| 关键决策记录    | [docs/adr/](docs/adr/)                                                           |
| 变更历史        | [CHANGELOG.md](CHANGELOG.md)                                                     |
