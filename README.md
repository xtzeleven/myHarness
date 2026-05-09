# myHarness

> 自用 Harness 工程级实践
> _Real-world coding benchmark for AI assistants_

![Status](https://img.shields.io/badge/status-WIP%20M3-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)
![Models](https://img.shields.io/badge/models-8%2B-green)

## 🎯 项目简介

从 Harness 原理开始，构建持续迭代框架，用一个 **Java + DDD** 后端实战来验证三层 Harness 在真实工程中的有效性。

> **当前状态**：M3 阶段（质量门禁层落地中）。`src/` 与 `pom.xml` 暂未实例化，`mvn` 命令为约定，待 M4 启用。

## 🛠️ 技术路线

### 三层 Harness 架构

- **Layer 1：约束层（Constraint Harness）**
  在 LLM 行动**之前**注入规则与禁忌，让"错误的代码写不出来"。
  - `CLAUDE.md`：每次会话自动注入的行为准则（10 节，含 Java/DDD 上下文与 gitnexus 路由）
  - `.claude/rules/engineering-practices.md`：14 节工程化规则（11 通用 + DDD 分层 / Java&Spring / MCP 治理）
  - `.claude/hooks/pre-tool-use.sh`：黑名单（直接拦：`rm -rf /`、强推主分支、写敏感文件）+ 灰名单（人工授权：DDD 边界改动、主依赖升级、DDL/DML、`mvn deploy`）

- **Layer 2：反馈循环层（Feedback Loop）**
  在 LLM 行动**期间与之后**给出即时信号，让"错的能立刻被纠"。
  - **Hooks**：PostToolUse（按后缀分发 prettier/ruff）+ Stop（变更摘要 + >20 警告）
  - **8 个 Sub-agents**：`tdd-cycle-driver`（TDD 红绿重构）、`code-reviewer`（通用评审）、`ddd-architect`（DDD 战略战术，opus）、`spring-boot-reviewer`（Spring 反模式）、`maven-build-doctor`（构建诊断）、`schema-analyst`（schema/SQL 分析，走 MySQL MCP）、`migration-author`（Flyway/Liquibase）、`docs-keeper`（文档漂移检测）
  - **4 个 Slash commands**：`/audit-practices`（14 维度自检）、`/commit`（标准化提交）、`/onboard`（新人 5 分钟上手）、`/sync-docs`（文档同步检查）
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

| 阶段   | 目标                                           | 状态      |
| ------ | ---------------------------------------------- | --------- |
| **M0** | 项目立项，写下三层架构假设                     | ✅ 完成   |
| **M1** | Layer 1 落地（CLAUDE.md + rules + PreToolUse） | ✅ 完成   |
| **M2** | Layer 2 落地（hooks + agents + commands）      | ✅ 完成   |
| **M3** | Layer 3 落地（CI + 提交规范 + 必需文件门禁）   | 🟢 当前   |
| **M4** | 实例化 Java DDD 骨架（pom.xml + src/）         | ⏳ 待启动 |
| **M5** | 接入第二个真实项目，对照本框架做差异分析       | ⏳ 待启动 |
| **M6** | 总结 8+ 模型在本框架下的表现差异               | ⏳ 待启动 |

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
  rules/engineering-practices.md     14 节工程化规则
  hooks/
    pre-tool-use.sh                  黑+灰双层防御
    format.sh                        PostToolUse 格式化
    stop-check.sh                    会话结束变更摘要
  agents/                            8 个：tdd-cycle-driver / code-reviewer
                                    / ddd-architect / spring-boot-reviewer
                                    / maven-build-doctor / schema-analyst
                                    / migration-author / docs-keeper
  commands/                          4 个：audit-practices / commit / onboard / sync-docs

docs/
  AGENTS.backend.md                  后端 agent 索引（Java/DDD 实战）
  adr/                               架构决策记录

.github/workflows/lint.yml           CI 质量门禁
```

## 🧭 关键文档导航

| 想了解          | 看                                                                               |
| --------------- | -------------------------------------------------------------------------------- |
| 行为准则        | [CLAUDE.md](CLAUDE.md)                                                           |
| Agent 用哪个    | [AGENTS.md](AGENTS.md) 路由速查                                                  |
| 后端 Agent 协作 | [docs/AGENTS.backend.md](docs/AGENTS.backend.md)                                 |
| 工程化规则      | [.claude/rules/engineering-practices.md](.claude/rules/engineering-practices.md) |
| 关键决策记录    | [docs/adr/](docs/adr/)                                                           |
| 变更历史        | [CHANGELOG.md](CHANGELOG.md)                                                     |
