# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. 项目上下文

**项目性质：** myHarness 是 Harness 工程化方法论项目，承载一个 **Java + DDD** 风格的后端实战，用以验证三层 Harness 在真实工程中的有效性。当前 M7 完成 / M8 待启动。

**技术栈：**

- 语言：Java 17+
- 框架：Spring Boot（具体版本以 `pom.xml` 为准）
- 构建：Maven
- 架构：DDD（Domain-Driven Design）—— 战略上分限界上下文（BC），战术上严格分层
- 数据：MySQL（通过只读 MCP 接入查询能力）
- 文档：Markdown，配 gitnexus 做代码索引

**目录结构（约定，未实例化时按本约定生成）：**

```
.
├── CLAUDE.md                  # 行为准则（每会话注入）
├── AGENTS.md                  # agent 索引
├── README.md                  # 项目简介与路线
├── pom.xml                    # Maven 主构建（未实例化）
├── src/
│   └── main/java/<base>/
│       ├── interfaces/        # ① 用户接口层：Controller / DTO / Assembler
│       ├── application/       # ② 应用层：用例编排 / 事务边界 / CommandHandler
│       ├── domain/            # ③ 领域层：Entity / VO / Aggregate / DomainService / DomainEvent / Repository 接口
│       └── infrastructure/    # ④ 基础设施层：Repository 实现 / 适配器 / MQ / 外部 RPC
├── src/test/                  # 单测 / 集成测
├── docs/
│   ├── AGENTS.backend.md      # 后端 agent 索引
│   └── ddd-conventions.md     # DDD 约定（按需建）
└── .claude/                   # Harness 配置（hooks / agents / commands / rules）
```

DDD 依赖方向 **严格单向**：interfaces → application → domain ← infrastructure。**domain 层不允许依赖任何外层**。

## 6. 禁忌事项

- **不要** 让 `domain/` 层 import 任何 Spring / JPA / MyBatis / Jackson 等基础设施类。
- **不要** 在 `interfaces/` 层直接调 Repository（必须经 application 层）。
- **不要** 在 `application/` 层写业务规则（业务规则属于 domain）。
- **不要** 让 Entity 暴露 setter（业务方法表达意图，非贫血模型）。
- **不要** 跨聚合根直接持有引用（用 ID 引用 + Repository 查询）。
- **不要** 在 hook 脚本中调用未在本机安装的工具（先 `command -v` 兜底）。
- **不要** 提交 `.idea/`、`target/`、`*.class`、`.env*`（已在 .gitignore）。
- **不要** 对生产库执行任何写操作（MCP 已强制 readonly，但 review 时仍要警惕）。
- **不要** 引入未在 README 声明的依赖或语言栈。

## 7. 测试 / 校验命令

> 注：M7 完成（六维度框架就绪），M8 待启动 — `src/` 与 `pom.xml` 暂未实例化；以下 `mvn` 命令为 M8 启用后的约定，当前会因无 pom.xml 报错。

```bash
# Java / Maven（M4 后启用）
mvn clean compile              # 编译
mvn test                       # 单测
mvn verify                     # 单测 + 集成测 + 静态检查
mvn dependency:tree            # 看依赖树（排冲突）

# 文档 / 配置（当前可用）
npx prettier --check "**/*.{md,json,yml,yaml}"
npx prettier --write  "**/*.{md,json,yml,yaml}"

# 工程实践 / 项目自检（当前可用）
/audit-practices               # 15 维度工程化自检（对照 engineering-practices.md 15 节）
/onboard                       # 新人 5 分钟全局上手
/sync-docs                     # 手动触发文档同步检查

# Git
git status --porcelain
```

## 8. gitnexus 路由（何时用哪个 skill）

本项目的代码已（或将）由 gitnexus 做索引；遇到以下场景**优先**用对应 skill 而不是手写 Grep/Glob：

| 场景                             | 优先 Skill                 |
| -------------------------------- | -------------------------- |
| 探索陌生模块、画依赖图、看调用链 | `gitnexus-exploring`       |
| 调试报错、追溯异常源头           | `gitnexus-debugging`       |
| 改名 / 拆分 / 移动前的影响面分析 | `gitnexus-impact-analysis` |
| 重构动手                         | `gitnexus-refactoring`     |
| review PR / 评估合并风险         | `gitnexus-pr-review`       |
| 不知道怎么用 / 看可用工具        | `gitnexus-guide`           |
| 索引 / 重建 / 清理仓库           | `gitnexus-cli`             |

**首次使用前**：用 `gitnexus-cli` 跑 `analyze`，确保索引已建。索引落后于代码时（commit 后未重跑），优先 `gitnexus-cli` 重新索引再查询。

## 9. 人工决策清单（PreToolUse 会拦下并问你）

以下操作命中黑名单 → 直接拒绝；命中**灰名单** → hook 退出 2 + 提示主对话**询问用户授权**：

| 类别         | 黑名单（直接拦）                          | 灰名单（人工授权）                                             |
| ------------ | ----------------------------------------- | -------------------------------------------------------------- |
| 文件         | 写 `.env` / `*.key` / `id_rsa` / 凭据目录 | —                                                              |
| 命令         | `rm -rf /` / `chmod 777 /` / `curl \| sh` | —                                                              |
| Git          | 强推到 main/master/prod                   | 删 commit / 批量 rebase                                        |
| **DDD 边界** | —                                         | **改 `domain/` 下聚合根 / Repository 接口 / DomainEvent 定义** |
| **依赖**     | —                                         | **改 `pom.xml` 中 spring-boot / 主 ORM / 数据库驱动版本**      |

被灰名单拦下时，**必须**让用户明确说"授权"再继续，不可绕过。

## 10. 子目录指引

- 后端 agent 设计：`docs/AGENTS.backend.md`
- DDD 约定（实例化后）：`docs/ddd-conventions.md`
- 工程化规则：`.claude/rules/engineering-practices.md`
- 路线图：`docs/roadmap.md`（M4-M8 六维度计划）
- 决策记录：`docs/adr/`（公开追溯）

## 11. 项目记忆（Memory）

本项目启用了 Claude Code 内置 memory 系统，索引在 `~/.claude/projects/D--myGithub-myHarness/memory/MEMORY.md`，含两类条目：

- **决策原因**（`decision_*`）：补充 ADR 写不下的"为什么没选 Y"、"何时该重审"
- **项目踩坑**（`pitfall_*`）：jq 不可用、SQL 检测误伤、settings.local 已 tracked、hook 自我拦截、Windows 路径、格式 hook 幂等性等

**遇到下列场景时主动查 MEMORY.md**：

- 写 / 调试 hook 脚本前 → 看 `pitfall_jq_not_in_path` / `pitfall_hook_self_block`
- 加 PreToolUse 规则前 → 看 `pitfall_sql_detection_overscan` / `decision_grey_list_over_pure_block`
- 加 .gitignore 条目时 → 看 `pitfall_settings_local_already_tracked`
- 用 Bash 工具碰路径问题 → 看 `pitfall_windows_path_d_drive`
- 讨论技术选型替代方案 → 看 `decision_*` 系列

载体分工详见 `docs/memory-conventions.md`：CLAUDE.md（每会话注入硬规则）/ ADR（公开决策追溯）/ Memory（协作偏好与踩坑）。
