# AGENTS.md — Agent 索引

> 本项目所有自定义 agent 与可用 skill 的总索引。Agent 文件存放在 `.claude/agents/`。

## 路由速查（"我该用哪个"）

| 你想做的事                              | 优先用                                              |
| --------------------------------------- | --------------------------------------------------- |
| 探索陌生代码 / 画依赖图 / 查调用链      | skill `gitnexus-exploring`                          |
| 调试报错 / 追溯异常                     | skill `gitnexus-debugging`                          |
| 重命名 / 拆分前的影响面分析             | skill `gitnexus-impact-analysis`                    |
| 重构动手                                | skill `gitnexus-refactoring`                        |
| review PR / 评估合并风险                | skill `gitnexus-pr-review` 或 agent `code-reviewer` |
| 索引 / 重建仓库索引                     | skill `gitnexus-cli`                                |
| 拆需求 / 列子任务 / 写 Gherkin AC       | agent `requirement-decomposer`                      |
| 事件风暴 / 业务事件流 / 服务边界候选    | agent `event-storm`                                 |
| 实现新功能 / 修 bug（带测试）           | agent `tdd-cycle-driver`                            |
| DDD 边界 / 聚合 / 领域事件设计          | agent `ddd-architect`                               |
| Spring 反模式审查 / @Transactional 问题 | agent `spring-boot-reviewer`                        |
| Maven 编译 / 依赖冲突 / 打包失败        | agent `maven-build-doctor`                          |
| 表结构 / 索引 / SQL 性能                | agent `schema-analyst`                              |
| 写数据库 migration                      | agent `migration-author`                            |
| 检查代码与文档是否漂移                  | agent `docs-keeper`（或命令 `/sync-docs`）          |
| 检查产研全链路文档间漂移                | 命令 `/cross-stage-check`                           |
| 新人 5 分钟上手                         | 命令 `/onboard`                                     |
| 工程化自检                              | 命令 `/audit-practices`                             |
| 标准化提交                              | 命令 `/commit`                                      |

## 自定义 Agents

| Agent                    | 文件                                                                  | 触发关键词                                                        | 模型     | 工具范围                                       |
| ------------------------ | --------------------------------------------------------------------- | ----------------------------------------------------------------- | -------- | ---------------------------------------------- |
| `requirement-decomposer` | [requirement-decomposer.md](.claude/agents/requirement-decomposer.md) | 拆需求 / INVEST / 写验收标准 / 列子任务 / 拆里程碑                | sonnet   | Read, Glob, Grep, Bash（**只读**）             |
| `event-storm`            | [event-storm.md](.claude/agents/event-storm.md)                       | 事件风暴 / 业务事件流 / 服务边界候选 / Actor 梳理                 | sonnet   | Read, Glob, Grep, Bash（**只读**）             |
| `tdd-cycle-driver`       | [tdd-cycle-driver.md](.claude/agents/tdd-cycle-driver.md)             | 新功能 / 修 bug / TDD / 红绿重构                                  | sonnet   | Bash, Edit, Write, Read, Glob, Grep            |
| `code-reviewer`          | [code-reviewer.md](.claude/agents/code-reviewer.md)                   | review PR / 当前分支 / 指定文件 / 安全审查                        | sonnet   | Read, Glob, Grep, Bash（**只读**）             |
| `ddd-architect`          | [ddd-architect.md](.claude/agents/ddd-architect.md)                   | 限界上下文 / 聚合边界 / Entity vs VO / 领域事件 / Repository 设计 | **opus** | Read, Glob, Grep, Bash（**只读**）             |
| `spring-boot-reviewer`   | [spring-boot-reviewer.md](.claude/agents/spring-boot-reviewer.md)     | @Transactional / 循环依赖 / N+1 / Bean 作用域 / Lombok 滥用       | sonnet   | Read, Glob, Grep, Bash（**只读**）             |
| `maven-build-doctor`     | [maven-build-doctor.md](.claude/agents/maven-build-doctor.md)         | mvn 编译失败 / 依赖冲突 / NoSuchMethodError / scope / profile     | sonnet   | Read, Glob, Grep, Bash                         |
| `schema-analyst`         | [schema-analyst.md](.claude/agents/schema-analyst.md)                 | 表结构 / 索引 / 慢 SQL / EXPLAIN / N+1 / ER 图                    | sonnet   | Read, Glob, Grep, Bash + MySQL MCP（**只读**） |
| `migration-author`       | [migration-author.md](.claude/agents/migration-author.md)             | Flyway / Liquibase / 加列 / 改字段 / 迁移脚本 / 回滚              | sonnet   | Read, Glob, Grep, Bash, Edit, Write            |
| `docs-keeper`            | [docs-keeper.md](.claude/agents/docs-keeper.md)                       | 文档漂移 / sync docs / README 过期 / 新人看不懂                   | sonnet   | Read, Glob, Grep, Bash（**只读**）             |

## 可用 Skills（外部，已在环境中）

gitnexus 系列 skill 由本机 Claude Code 环境直接提供，**不在 `.claude/agents/` 目录下**。详见 CLAUDE.md 第 8 节"gitnexus 路由"：

- `gitnexus-cli` / `gitnexus-exploring` / `gitnexus-debugging` / `gitnexus-impact-analysis` / `gitnexus-refactoring` / `gitnexus-pr-review` / `gitnexus-guide`

## 相关文档（按主题）

| 主题                | 文档                                                                             |
| ------------------- | -------------------------------------------------------------------------------- |
| 后端 agent 详细约定 | [docs/AGENTS.backend.md](docs/AGENTS.backend.md)                                 |
| 行为准则            | [CLAUDE.md](CLAUDE.md)                                                           |
| 工程化规则（15 节） | [.claude/rules/engineering-practices.md](.claude/rules/engineering-practices.md) |
| Slash 命令          | [.claude/commands/](.claude/commands/)                                           |
| Hook 脚本           | [.claude/hooks/](.claude/hooks/)                                                 |
| MCP 配置            | [.mcp.json](.mcp.json) + [.env.example](.env.example)                            |

## 触发约定

- **主对话路由**：主 Claude 读 description 关键词决定是否分派给 sub-agent。
- **显式调用**：用户说"用 ddd-architect 看一下"也行。
- **最小权限**：评审 / 审计 / 分析类 agent 默认只读。
- **不重叠**：一个场景对应一个最合适的 agent；多个能干同一件事的 → 在路由表里收敛到一个。

## Skill vs Agent vs 主对话（路由原则）

三者职责不同，先按下表筛，再用上面"路由速查"具体匹配：

| 载体       | 何时用                                                                   | 决定权   | 上下文       |
| ---------- | ------------------------------------------------------------------------ | -------- | ------------ |
| **主对话** | 任务 ≤ 3 步、直接动手 / 一次问答能闭环、不需要专项知识                   | Driver   | 主上下文     |
| **Skill**  | 用户主动调用的能力包（`/commit` / `gitnexus-*`）；有固定流程或工具栈封装 | **用户** | 主上下文     |
| **Agent**  | 主对话委派的子工作流；需要隔离上下文、专项知识、并行/串行多 Worker       | Driver   | 独立子上下文 |

**判断顺序（先匹配先用）：**

1. 用户显式输入 `/<name>` 或"用 X 看一下" → 走 skill / agent，按用户意图
2. 任务命中某 agent description 触发关键词且超出主对话 3 步 → spawn agent
3. 任务能 1-3 步内闭环 + 不需要专项 review / 设计判断 → 主对话直接做
4. 任务涉及探索/索引（gitnexus 系列） → 优先 skill，索引落后时用 `gitnexus-cli` 重建

**反例：**

- ❌ 把 `code-reviewer` agent 当 skill（用户主动 `/code-reviewer`）→ skill 是流程化提示词，agent 是隔离上下文的 sub-Claude，混用会丢隔离价值
- ❌ 简单改 typo 也 spawn agent → 浪费上下文，主对话 1 步搞定
- ❌ 同时 spawn 多个职责重叠的 agent → 输出冲突，应在路由表先收敛

## 新增 agent 清单

1. 在 `.claude/agents/<name>.md` 写文件，frontmatter 必含：
   - `name`：与文件名一致
   - `description`：职责 + **触发场景示例**（关键词要具体到主 Claude 能路由）
   - `tools`：最小权限集
   - `model`：通常 `sonnet`，复杂战略问题用 `opus`
2. 在本文 **"自定义 Agents" 表**与 **"路由速查"表**各登记一行
3. 自检：用 `/audit-practices agents` 看路由是否清晰

## 反模式

- ❌ description 写 "代码评审专家" 没触发关键词 → 主 Claude 不知道何时调
- ❌ 所有 agent `tools: *` → 失去隔离
- ❌ 多个 agent 职责重叠 → 路由变随机
- ❌ 评审类 agent 给 Edit/Write 权限 → 容易越权改代码
- ❌ 把 agent 当 skill 用 → skill 是用户主动调用的能力包，agent 是主对话委派的子工作流

## 自反馈环（M5 新增）

> 详见 [docs/loop-architecture.md §5](docs/loop-architecture.md)。让 agent 互相审，避免单 agent 偏见。**不全开**，只在以下高价值组合启用。

| 主 Worker                              | 反馈 Worker      | 触发场景                           | 反馈聚焦                                                                                         |
| -------------------------------------- | ---------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------ |
| `ddd-architect` 给出聚合设计           | `docs-keeper`    | 主 Worker 输出含"建议"或"草图"     | 设计是否完整文档化、是否含落地路径                                                               |
| `migration-author` 写完 migration 文件 | `schema-analyst` | 写文件后立即触发                   | migration 在已有 schema 上是否安全（兼容性 / 索引影响）                                          |
| `tdd-cycle-driver` 完成 GREEN 步       | `code-reviewer`  | 进入 REFACTOR 前                   | 实现是否符合通用 quality（命名 / 安全 / 异常）                                                   |
| 任一 Worker 改 `domain/` 边界          | `ddd-architect`  | PreToolUse 灰名单触发 + 用户授权后 | 改动是否符合 DDD 分层准入（[engineering-practices §12](.claude/rules/engineering-practices.md)） |

自反馈 ≠ 串行链：反馈 Worker **审**主 Worker 的输出，发现问题 → escalate 给 Driver；不在主 Worker 输出基础上"继续工作"。

## 升级链（M5 新增）

按 [loop-architecture §3 escalation](docs/loop-architecture.md) 的策略，每个 Worker 失败 / 卡住时的升级目标：

| Worker                   | 卡住时升级到              | 仍卡升级到                             |
| ------------------------ | ------------------------- | -------------------------------------- |
| `requirement-decomposer` | sonnet → opus             | Driver → 用户（需求模糊需人拍板）      |
| `event-storm`            | sonnet → opus             | Driver → 用户（服务边界决策需人拍板）  |
| `tdd-cycle-driver`       | sonnet → opus（同 agent） | Driver → 用户                          |
| `code-reviewer`          | sonnet → opus             | `spring-boot-reviewer`（专项）+ Driver |
| `ddd-architect`          | 已 opus，无可升           | Driver → 用户（设计决策需用户拍板）    |
| `spring-boot-reviewer`   | sonnet → opus             | `ddd-architect`（边界问题） + Driver   |
| `maven-build-doctor`     | sonnet → opus             | `spring-boot-reviewer`（运行时问题）   |
| `schema-analyst`         | sonnet → opus             | `ddd-architect`（建模问题）            |
| `migration-author`       | sonnet → opus             | `schema-analyst`（兼容性疑问）         |
| `docs-keeper`            | sonnet → opus             | Driver → 用户                          |

**规则**：

- 升级**永不向下**（用户决策后回到原层级）
- 跨 agent 升级时，**保留**原 Worker 的输出在上下文，反馈 Worker 看得到
- 同模型 retry 上限 **2 次**；超过即升级

## 降级链（M5 新增）

工具失败时的降级路径（详见 [loop-architecture §3 degradation](docs/loop-architecture.md)）：

```
gitnexus-exploring  → Glob + Grep   → ls + cat（手动）
gitnexus-impact-analysis → git grep + 手动 trace
schema-analyst (mysql MCP) → 读 schema.sql 文件 → 问用户
prettier (npx) → 跳过格式化（注明 "未格式化"）
```

降级时 Worker 必须在输出顶部注明 "**已降级**: <原工具>不可用，使用 <替代>"。

详见 [docs/tools-fallback.md](docs/tools-fallback.md)（M7-T2）。

## Model Selection Policy（M7 新增）

> **单点真源**：[docs/policy-model-selection.md](docs/policy-model-selection.md)。本节仅给摘要。

每个 agent 的默认模型与升级路径见上文 [policy-model-selection §2](docs/policy-model-selection.md#2-agent-默认模型表)。**改默认模型只在那里改**，本文不复述表格。

**摘要规则**：

- 用户显式指定 > agent frontmatter > policy 通用表 > Driver 当前模型
- 升级前必须 retry 当前模型 1 次
- 跨 agent 转交时**保留**会话上下文
- Driver（主对话）的模型由用户选择

## Tools Lock（M7 新增）

工具版本由这些文件约束：

| 工具     | 锁版本文件                          | 当前锁定                  |
| -------- | ----------------------------------- | ------------------------- |
| Node     | `.tool-versions`（asdf/mise）       | `nodejs 20.18.0`          |
| Python   | `.tool-versions`                    | `python 3.13.0`           |
| Java     | `.tool-versions`                    | `java temurin-17.0.13+11` |
| Maven    | `.tool-versions`                    | `maven 3.9.9`             |
| prettier | `package.json` + `.prettierrc.json` | `prettier 3.3.3`          |

CI 与本地用同一版本（CI 通过 `npm ci` 装；本地通过 `npm install` 或 hook 自动）。

## Audit Log（M7 新增）

所有 hook 拦截 / 灰名单触发 / 降级 / bypass → 写 `.claude/.audit.log`（已 .gitignore）。

跑摘要：

```bash
python .claude/scripts/audit-log-summary.py             # 全量
python .claude/scripts/audit-log-summary.py --tail 20   # 最近 20 条
python .claude/scripts/audit-log-summary.py --bypass    # 仅 bypass 记录
```

详见 [docs/tools-fallback.md §7](docs/tools-fallback.md)。
