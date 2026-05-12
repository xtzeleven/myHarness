# myHarness

> 自用 Harness 工程级实践
> _Real-world coding benchmark for AI assistants_

![Status](https://img.shields.io/badge/status-M7%20done%20%7C%20M8'%20plugin%20in%20progress-green)
![License](https://img.shields.io/badge/license-MIT-blue)
![Models](https://img.shields.io/badge/models-8%2B-green)

## 🎯 项目简介

从 Harness 原理开始，把三层 Harness（约束 / 反馈 / 门禁）**封装为 Claude Code Plugin**（`plugin/` 子目录），让任何项目都能一行命令装上。Java/Spring/DDD/Maven 作为 plugin 的**扩展套件**保留（专项 agent + 灰名单），其他语言栈静默无副作用。

> **当前状态**：M7 完成（六维度 Harness 框架就绪）+ M8' Plugin 化进行中（plugin 资产已就位 + 外部验证通过自动部分，详见 [ADR-0005](docs/adr/0005-pivot-to-plugin.md) / [plugin/README.md](plugin/README.md)）。

## 🛠️ 技术路线

### 三层 Harness 架构

- **Layer 1：约束层（Constraint Harness）**
  在 LLM 行动**之前**注入规则与禁忌，让"错误的代码写不出来"。

  - `CLAUDE.md`：每次会话自动注入的行为准则（项目重定位 + 技术栈 + DDD 禁忌 + 测试命令 + gitnexus 路由）
  - `plugin/rules/engineering-practices.md`：15 节工程化规则（11 通用 + DDD 分层 / Java&Spring / MCP 治理 + Policy 机制化）
  - `plugin/hooks/pre-tool-use.sh`：黑名单（直接拦：`rm -rf /`、强推主分支、写敏感文件）+ 灰名单（人工授权：DDD 边界改动、主依赖升级、DDL/DML、`mvn deploy`）

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

| 阶段    | 目标                                                                | 状态    |
| ------- | ------------------------------------------------------------------- | ------- |
| **M0**  | 项目立项，写下三层架构假设                                          | ✅ 完成 |
| **M1**  | Layer 1 落地（CLAUDE.md + rules + PreToolUse）                      | ✅ 完成 |
| **M2**  | Layer 2 落地（hooks + agents + commands）                           | ✅ 完成 |
| **M3**  | Layer 3 落地（CI + 提交规范 + 必需文件门禁）                        | ✅ 完成 |
| **M4**  | Memory 启用（决策原因 + 项目踩坑两类，索引 `MEMORY.md`）            | ✅ 完成 |
| **M5**  | Loop 架构（Driver/Worker 调度 + 三策略 + `.session.state` 恢复）    | ✅ 完成 |
| **M6**  | Context 治理（token 预算 ≤ 8K + 按需 hint + 子目录 CLAUDE.md 规划） | ✅ 完成 |
| **M7**  | Tools 治理 + Policy 机制化（版本锁 + 降级链 + bypass + audit log）  | ✅ 完成 |
| **M8**  | ~~实例化 Java DDD 骨架（六维度回归测试场）~~ → 已废弃，见 ADR-0005  | ⏭️ 改向 |
| **M8'** | Plugin 化（封装 Harness 为 Claude Code Plugin，分发给任意项目）     | 🟢 当前 |

## 🚀 快速上手

```bash
git clone <repo> && cd myHarness

# 1. 看准则与规则
cat CLAUDE.md
cat plugin/rules/engineering-practices.md

# 2. 配 MCP（可选，需 MySQL 只读账号）
cp plugin/.env.example .env && vi .env

# 3. 启动 Claude Code（自举模式：用本仓库的 plugin/）
bash scripts/dev.sh                      # 一行启动；等价于 claude --plugin-dir ./plugin

# 4. 进入 Claude 后跑
/harness:audit-practices                 # 工程自检
/harness:onboard                         # 项目摘要
```

> **为什么要自举（ADR-0006）**：ADR-0006 后本仓库自身的 hooks/agents/commands 全在 `plugin/` 下，**不再**有 `.claude/{hooks,agents,...}`。开发期用 `bash scripts/dev.sh` 启动 = 用本仓库自己的 plugin 加载，等于每次会话都做一次回归测试。

## 📁 目录速览

```
CLAUDE.md                            行为准则（项目专属上下文，每会话自动注入）
README.md                            本文件
AGENTS.md                            Agent 索引（路由表，链接到 plugin/agents/）
CHANGELOG.md                         发布变更记录
.gitignore .env.example .mcp.json    Git / 环境 / MCP 配置（项目根级）

.claude/
  settings.json                      项目级 Claude Code 配置（hooks 由 plugin 提供）
  settings.local.json                本地权限（已 .gitignore，不入仓库）

plugin/                              ★ Harness 资产权威源（M8' 后唯一）
  .claude-plugin/plugin.json         plugin manifest（name=harness）
  .mcp.json + .env.example           MySQL 只读 MCP 配置
  skills/harness-guidelines/         通用行为准则 SKILL（model-invoked）
  agents/                            8 个：tdd-cycle-driver / code-reviewer
                                     / ddd-architect / spring-boot-reviewer
                                     / maven-build-doctor / schema-analyst
                                     / migration-author / docs-keeper
  commands/                          5 个：audit-practices / audit-context
                                     / commit / onboard / sync-docs
  hooks/                             6 个 hook + hooks.json + 4 套 smoke test
  rules/engineering-practices.md     15 节工程化规则
  scripts/                           audit-context-cost.py / audit-log-summary.py
  README.md                          plugin 用法 / 安装 / 已知限制

scripts/
  dev.sh                             一行启动 plugin 自举模式

docs/
  roadmap.md                         六维度路线（M4-M8'）
  loop-architecture.md               Driver/Worker 调度
  context-management.md              token 预算与按需注入
  tools-fallback.md                  工具降级链
  memory-conventions.md              memory 与 ADR 分工
  periodic-tasks.md                  /loop + GH Actions schedule
  AGENTS.backend.md                  后端 agent 索引（Java/DDD 扩展套件）
  g13-external-validation.md         plugin 外部验证 runbook
  g13-findings.md                    G13 验证结果
  adr/                               架构决策记录（含 ADR-0006 .claude/ 清理）

.github/workflows/
  lint.yml                           顶层质量门禁（prettier + 必需文件 + secrets）
  plugin-validate.yml                plugin 自身校验（manifest + smoke + bypass）
  scheduled.yml                      每日结构 + 每周 stale 自检
```

## 🧭 关键文档导航

| 想了解            | 看                                                                               |
| ----------------- | -------------------------------------------------------------------------------- |
| 行为准则          | [CLAUDE.md](CLAUDE.md)                                                           |
| **Plugin 用法**   | [plugin/README.md](plugin/README.md)                                             |
| **Plugin 化决策** | [docs/adr/0005-pivot-to-plugin.md](docs/adr/0005-pivot-to-plugin.md)             |
| Agent 用哪个      | [AGENTS.md](AGENTS.md) 路由速查                                                  |
| 后端 Agent 协作   | [docs/AGENTS.backend.md](docs/AGENTS.backend.md)                                 |
| 工程化规则        | [plugin/rules/engineering-practices.md](plugin/rules/engineering-practices.md) |
| 六维度路线        | [docs/roadmap.md](docs/roadmap.md)                                               |
| Loop 架构         | [docs/loop-architecture.md](docs/loop-architecture.md)                           |
| Context 治理      | [docs/context-management.md](docs/context-management.md)                         |
| 工具降级链        | [docs/tools-fallback.md](docs/tools-fallback.md)                                 |
| 关键决策记录      | [docs/adr/](docs/adr/)                                                           |
| 变更历史          | [CHANGELOG.md](CHANGELOG.md)                                                     |
