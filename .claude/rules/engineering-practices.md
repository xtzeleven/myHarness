# Engineering Practices — Harness 工程化规则

> `audit-practices` 命令对照本文 11 节执行。每节给出**为什么**、**怎么做**、**什么算达标**。

## 0. 阅读顺序

1. **Layer 1 约束层**：第 1–3 节（CLAUDE.md / rules / PreToolUse）
2. **Layer 2 反馈循环**：第 4–6 节（Hooks / Agents / Commands）
3. **Layer 3 质量门禁**：第 7–9 节（CI / Git / 测试）
4. **支撑层**：第 10–11 节（文档 / 可观测）
5. **领域专项**：第 12–14 节（DDD 分层 / Java&Spring 风格 / MCP 治理）

---

## 1. CLAUDE.md 完备性

**为什么**：CLAUDE.md 是每次会话第一份注入上下文。它缺失的内容，模型只能靠猜或重新搜代码，会议成本最高。

**怎么做**：根目录 CLAUDE.md 覆盖 7 节

- 行为准则（思考优先 / 简单优先 / 外科手术 / 目标驱动）
- 项目上下文（性质、阶段）
- 技术栈
- 目录结构
- 禁忌事项
- 测试 / 校验命令
- 子目录 CLAUDE.md 索引（如有）

**达标**：新人（或新会话）只读 CLAUDE.md 就能写出符合本项目风格的第一个 PR。

---

## 2. Rules 文档（本文）

**为什么**：CLAUDE.md 谈"做什么 / 不做什么"，Rules 谈"为什么这么定 + 如何审计"。两者分离避免 CLAUDE.md 膨胀。

**怎么做**：`.claude/rules/engineering-practices.md` 即本文；其他规则按主题拆（如 `security.md` / `naming.md`）。

**达标**：每条规则带"为什么 + 怎么做 + 什么算达标"三段；可被 `/audit-practices` 引用打勾。

---

## 3. PreToolUse 防御

**为什么**：Stop hook 是事后提醒，PostToolUse 是事后清理；只有 PreToolUse 能阻止危险操作发生。

**怎么做**：`.claude/hooks/pre-tool-use.sh` 至少拦截

**黑名单（直接 exit 2）：**

- `rm -rf /`、`rm -rf ~`、`rm -rf $HOME`
- `git push --force` 到 `main` / `master`
- 写入敏感文件：`.env`、`*.key`、`*.pem`、`id_rsa`、`*.p12`
- `chmod 777`、`curl | sh`

**灰名单（exit 2 + 提示主对话向用户索要授权）：**

- 改 `domain/` 下聚合根 / Repository 接口 / DomainEvent 定义（DDD 边界）
- 改 `pom.xml` 中 `spring-boot` / 主 ORM（MyBatis/JPA）/ MySQL 驱动版本
- 删 commit / 批量 rebase / `git reset --hard origin/*`

退出码 2 阻止 + stderr 给原因；灰名单消息以 `⚠️ 待人工授权:` 开头，便于主对话识别。

**达标**：手动构造危险命令时被拦下；正常命令不误伤；灰名单触发时主对话能正确暂停问用户。

---

## 4. Hooks（PostToolUse / Stop / SessionStart / UserPromptSubmit）

**为什么**：Hook 是反馈循环的载体。没 hook = 每次都要靠人提醒。

**怎么做**：

- **PostToolUse**：Edit/Write 后按后缀分发格式化（已实现）
- **Stop**：会话结束前 `git status --porcelain | head -20`，>20 警告（已实现）
- **PreToolUse**：见第 3 节
- **SessionStart**（可选）：开会话时跑 `git log -5` + `git status` 自动注入
- **UserPromptSubmit**（可选）：每次用户提问前注入"今天日期 / 当前分支"

**达标**：四类 hook 至少有 PostToolUse + Stop + PreToolUse 三个，脚本带 `command -v` 兜底。

---

## 5. Agents

**为什么**：长链路任务（评审 / TDD / 安全审查）开 sub-agent 隔离上下文，主对话不会被污染。

**怎么做**：`.claude/agents/<name>.md`，frontmatter 含 `name` / `description`（必须含触发场景！）/ `tools` / `model`。

**达标**：高频场景至少有 1 个专项 agent；description 写得让主 Claude 能正确路由。索引在根级 `AGENTS.md`。

---

## 6. Commands

**为什么**：复用流程化提示词。`/commit`、`/audit-practices`、`/review` 等让动作可预期。

**怎么做**：`.claude/commands/<name>.md`，frontmatter 可选 `description` / `argument-hint`；正文是给 Claude 的指令模板。

**达标**：日常重复动作（提交、评审、自检）都有命令；新人无需记流程。

---

## 7. CI / 质量门禁

**为什么**：本地 hook 会被绕过（`--no-verify`），CI 是不可绕的最后一道。

**怎么做**：`.github/workflows/lint.yml` 至少跑

- `prettier --check "**/*.{md,json}"`
- 关键文件存在性（`CLAUDE.md` / `.gitignore` / `AGENTS.md`）
- 后续接代码：`npm test` / `pytest` / `mvn test`

**达标**：PR 不通过 CI 不能合入 main；workflow 文件本身在 lint 范围内。

---

## 8. Git 卫生

**为什么**：脏仓库会污染 diff、增加误提交风险，Stop hook 会一直警告。

**怎么做**：

- `.gitignore` 覆盖 IDE / OS / 语言 / 密钥四类
- 提交粒度：一个 logical change 一次 commit
- 提交格式：Conventional Commits（`feat:` / `fix:` / `docs:` / `chore:`）
- 不提交 `.claude/settings.local.json`（个人配置）
- 用 `/commit` 命令统一动作

**达标**：`git status --porcelain` 干净；`git log --oneline -10` 都是 conventional 格式。

---

## 9. 测试 / 校验

**为什么**：无验证 = 看不见的回归。文档项目也有"文档测试"（链接有效性、格式正确）。

**怎么做**：

- 代码项目：单测 + 集成测 + e2e
- 文档项目：`prettier --check` + 链接检查（如 lychee）+ 关键文件存在性
- 工程化项目（本项目）：跑 `/audit-practices` 当冒烟测试

**达标**：可一键 `make test` / `npm test` 或对应命令验全部门禁。

---

## 10. 文档同步

**为什么**：README 与代码不一致 = 误导用户与未来的自己。

**怎么做**：

- README 与代码现状一致；WIP 显式标记
- 路线图带阶段（M0/M1/M2…）和当前位置
- 重要决策写 ADR（`docs/adr/NNNN-<topic>.md`）
- CHANGELOG 至少标注每个 release

**达标**：陌生人读 README 能 30 秒内说清"这是什么 / 现在做到哪 / 下一步是啥"。

---

## 11. 可观测 / 审计

**为什么**：会话与流程要可回溯，否则改进无依据。

**怎么做**：

- statusLine 显示项目 / 分支 / 模型
- output style 可选项目专属
- session 结束的 Stop hook 把 `git status` 留在终端
- 关键决策提交到 git，不只在对话里说

**达标**：任何 PR 能从代码追到决策；任何决策能从会话追到代码改动。

---

## 评分尺度

- ✅ **达标**：本节"达标"条件全满足
- ⚠️ **部分**：基础在但缺一两项
- ❌ **缺失**：未实施

`/audit-practices` 输出按此尺度。

---

## 12. DDD 分层规则

**为什么**：DDD 的价值来自**层间依赖单向**与**领域纯净**。一旦 domain 层被框架污染，模型就退化为 CRUD 化的贫血对象，DDD 等于白做。

**怎么做**：

**依赖方向（严格单向）：**

```
interfaces  →  application  →  domain  ←  infrastructure
```

**各层准入：**

| 层                | 允许                                                                        | 禁止                                                  |
| ----------------- | --------------------------------------------------------------------------- | ----------------------------------------------------- |
| `interfaces/`     | 收 HTTP / RPC、DTO ↔ Command 转换、调 application                           | 直接调 Repository、写业务规则                         |
| `application/`    | 用例编排、事务边界（`@Transactional` 仅在此）、调 domain                    | 写业务规则、import infra 实现类                       |
| `domain/`         | Entity / VO / Aggregate / DomainService / DomainEvent / Repository **接口** | import 任何 Spring / JPA / MyBatis / Jackson / Web 类 |
| `infrastructure/` | Repository **实现**、外部适配器、MQ、第三方 SDK                             | 反向调 application 或 interfaces                      |

**模型规则：**

- **聚合根**：跨聚合用 ID 引用，不持有对方对象引用
- **Entity**：业务方法表达意图，不要暴露 setter；`equals/hashCode` 基于 ID
- **VO**：不可变（`final` 字段、无 setter），`equals/hashCode` 基于全部字段
- **DomainService**：只在"操作不属于任何单一聚合"时使用，避免成为 service 万能袋
- **DomainEvent**：不可变；事件名用过去式（`OrderPlaced`、`PaymentCaptured`）

**事务边界：** `@Transactional` 只标在 `application/` 的用例方法上。**禁止**在 `domain/` 或 `infrastructure/` 标。

**达标**：

- `git grep -l "import org.springframework" src/main/java/**/domain/` 返回空
- `git grep -l "@Transactional" src/main/java/**/domain/` 返回空
- 所有 `Repository` 接口在 `domain/`，实现在 `infrastructure/`
- 跨聚合调用经 `Application` 层编排，不在 `domain/` 直接 import 别的 BC 包

---

## 13. Java / Spring 风格

**为什么**：Java/Spring 有几条踩了就难调的反模式，明确写下避免每个新人重新踩坑。

**怎么做**：

**约束清单：**

- **不滥用 Lombok**：`@Data` 在 Entity / Aggregate 上**禁止**（暴露 setter 破坏不变量）；`@Value` 仅用于 VO；优先用编译期可见的代码而非全注解。
- **避免循环依赖**：发现 `BeanCurrentlyInCreationException` 不要用 `@Lazy` 绕，先看是否分层错误。
- **`@Transactional` 仅在 application 层**；自调用（`this.foo()`）不会走代理，注解失效。
- **N+1 查询**：JPA `@OneToMany` 默认懒加载，循环里读关联数据 = N+1。用 `JOIN FETCH` 或显式批量。
- **Optional 用法**：返回 `Optional<T>` 表"可能不存在"；**禁止** `Optional` 作字段或方法参数。
- **null 边界**：公共方法参数用 `Objects.requireNonNull` 或 `@NonNull`；不在 domain 层依赖 `org.springframework.lang.NonNull`，用 JSR-305 或 Jakarta。
- **异常**：domain 层抛 domain exception（`OrderNotFoundException`），interfaces 层翻译为 HTTP；不直接抛 `RuntimeException`。
- **日志**：用 SLF4J，参数化（`log.info("placed order {}", id)`），不要字符串拼接；敏感字段（手机号、token）**禁止**打日志。

**达标**：`mvn verify` 通过 + 上述约束在 PR review 中可被 `code-reviewer` / `spring-boot-reviewer` 自动捕获。

---

## 14. MCP 治理

**为什么**：MCP 让 LLM 直接接外部资源（DB、文件、API），权限和血缘必须管控，否则就是把 root shell 交给 LLM。

**怎么做**：

**接入清单：**

- **MySQL（只读）**：通过 `.mcp.json` 配只读 user，`GRANT SELECT, SHOW VIEW` 仅；连接信息走环境变量（`${MYSQL_HOST}` 等），**绝不**硬编码到 `.mcp.json`。
- **gitnexus**：通过 skill（已可用），不走 MCP；建议做完代码改动后用 `gitnexus-cli` 重建索引。

**安全规则：**

- 所有数据库 MCP **必须** readonly。即使是 dev 库，也强制走只读账号。
- `.env` / `.env.local` 在 `.gitignore`，仅在本机维护连接信息。
- PreToolUse hook 检查 `Bash` 调用中包含 `INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE` 的 SQL 文本时拦下（即使在只读 MCP 上也防误调）。
- 项目根放 `.env.example` 列必需变量名（不含值），便于新人接入。

**达标**：

- `.mcp.json` 不含明文凭据
- `.env` 在 `.gitignore` 且不在 git history
- `.env.example` 存在且与 `.mcp.json` 引用变量一致
- 数据库账号确认仅有 `SELECT` 权限
