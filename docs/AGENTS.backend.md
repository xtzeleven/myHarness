# AGENTS — Backend (Java + DDD)

> **状态**：✅ 已激活。本项目按 **Java + Spring Boot + Maven + DDD 四层架构**执行；下列 agent 已就位。

## 适用范围

当出现以下任一信号时，主 Claude 应优先把任务派给本目录中的对应 agent，而不是自己上手：

- 文件在 `src/main/java/<base>/{domain,application,infrastructure,interfaces}/` 下
- 改动 `pom.xml` / `application*.yml` / `db/migration/`
- 提到 Spring / JPA / MyBatis / Maven / MySQL / DDD 概念

## 已激活 Agent

下列 agent 实例化于 `.claude/agents/`，详见 [AGENTS.md](../AGENTS.md) 总索引。本表给出**何时用 + 何时不用**的边界。

### 1. `ddd-architect` — DDD 架构顾问

|              |                                                                                               |
| ------------ | --------------------------------------------------------------------------------------------- |
| **何时用**   | 限界上下文划分、聚合边界判断、Entity/VO 决策、Repository 接口设计、领域事件命名与时机         |
| **何时不用** | Spring 配置（→ `spring-boot-reviewer`）、SQL 优化（→ `schema-analyst`）、纯实现细节（主对话） |
| **模型**     | opus（战略判断需要更强模型）                                                                  |
| **写权限**   | 否（只给设计建议与伪代码）                                                                    |

### 2. `spring-boot-reviewer` — Spring 反模式审查

|              |                                                                                                    |
| ------------ | -------------------------------------------------------------------------------------------------- |
| **何时用**   | `@Transactional` 边界、循环依赖、N+1、Bean 作用域、Lombok 滥用、Web 层暴露 Entity                  |
| **何时不用** | DDD 结构问题（→ `ddd-architect`）、Maven 构建（→ `maven-build-doctor`）、SQL（→ `schema-analyst`） |
| **模型**     | sonnet                                                                                             |
| **写权限**   | 否（只读评审）                                                                                     |

### 3. `maven-build-doctor` — Maven 构建医生

|              |                                                                                                                 |
| ------------ | --------------------------------------------------------------------------------------------------------------- |
| **何时用**   | `mvn` 编译/打包失败、依赖冲突（NoSuchMethodError / NoClassDefFoundError）、scope 选择、profile 不生效、模块依赖 |
| **何时不用** | Java 代码本身的 bug（→ 主对话或 `spring-boot-reviewer`）                                                        |
| **模型**     | sonnet                                                                                                          |
| **写权限**   | 给修复方案，pom.xml 改动走 PreToolUse 灰名单需用户授权                                                          |

### 4. `schema-analyst` — Schema/SQL 分析

|              |                                                                          |
| ------------ | ------------------------------------------------------------------------ |
| **何时用**   | 表结构、索引覆盖、`EXPLAIN`、慢 query、N+1 定位、ER 图、外键设计         |
| **何时不用** | 写迁移（→ `migration-author`）、纯 Java 性能（→ `spring-boot-reviewer`） |
| **模型**     | sonnet                                                                   |
| **写权限**   | **绝不写库**。通过 mysql-readonly MCP 仅做 SELECT / EXPLAIN              |

### 5. `migration-author` — 迁移脚本作者

|              |                                                                               |
| ------------ | ----------------------------------------------------------------------------- |
| **何时用**   | 写 Flyway/Liquibase migration、加列/改字段/删表方案、向后兼容性校验、回滚预案 |
| **何时不用** | 现状分析（→ `schema-analyst`）、纯运行时 query 改写（→ `schema-analyst`）     |
| **模型**     | sonnet                                                                        |
| **写权限**   | 是（写 `db/migration/V*.sql`），但 🔴 危险变更必须用户确认                    |

## 协作规则

### Agent 之间的派发顺序

典型场景的推荐顺序：

| 场景                  | 推荐顺序                                                                                                 |
| --------------------- | -------------------------------------------------------------------------------------------------------- |
| 新需求开发            | `ddd-architect`（设计）→ 主对话/`tdd-cycle-driver`（实现）→ `spring-boot-reviewer`（自检）               |
| 性能问题              | `schema-analyst`（看 SQL/索引）→ `spring-boot-reviewer`（看 N+1/事务）→ 必要时 `migration-author` 加索引 |
| 升 spring-boot 大版本 | `maven-build-doctor`（兼容性）→ `spring-boot-reviewer`（API 变更影响）                                   |
| 加一张表              | `ddd-architect`（这归哪个 BC / 是新聚合吗）→ `schema-analyst`（设计建议）→ `migration-author`（落 DDL）  |
| review PR             | `code-reviewer`（通用）+ `spring-boot-reviewer`（Java 部分）+ `schema-analyst`（如果含 query）           |

### 工具权限分级

| 等级                 | Agent                                                                                 | 工具                                              |
| -------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------- |
| **只读**             | `ddd-architect` `spring-boot-reviewer` `schema-analyst` `code-reviewer` `docs-keeper` | Read/Glob/Grep/Bash（无 Edit/Write）              |
| **可写代码**         | `tdd-cycle-driver` `migration-author`                                                 | + Edit/Write                                      |
| **可执行高风险命令** | `maven-build-doctor`                                                                  | Bash（构建命令）；改 pom.xml 走 PreToolUse 灰名单 |

## 与 PreToolUse hook 的协作

agent 在尝试以下动作时会被 [pre-tool-use.sh](../.claude/hooks/pre-tool-use.sh) 拦下，需用户授权：

- 改 `domain/` 下聚合根 / Repository 接口 / DomainEvent
- 改 `pom.xml` 中 spring-boot / 主 ORM / mysql 驱动版本
- `mvn deploy` / `mvn release:*`
- 含 INSERT/UPDATE/DELETE/DROP/ALTER 的 mysql 命令

agent 不应试图绕过；遇到 ⚠️ 提示时把动作描述给主对话，让主对话向用户索要授权。

## 待补 Agent（按需启动）

| 候选                    | 何时实例化                                      |
| ----------------------- | ----------------------------------------------- |
| `api-contract-reviewer` | 引入 OpenAPI / GraphQL schema 后                |
| `security-auditor`      | 接受外部输入（认证 / 文件上传）的功能进入主线后 |
| `perf-profiler`         | 出现需要 profiling 的真实性能问题时             |

新增时按 [AGENTS.md "新增 agent 清单"](../AGENTS.md#新增-agent-清单) 走，并在本文登记。

---

**Last reviewed**: 2026-05-09 — 6 个后端 agent 已激活，对应 Java + DDD + MySQL 场景。
