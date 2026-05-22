# Changelog

记录本项目可观察到的变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
版本遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

由于本项目是工程化方法论项目而非软件包，"版本"对应 **里程碑（M0–MN）**。

## [Unreleased] — M8-T0 Tier 1 完成 / M8 主线 Phase 1 骨架 + Phase 2 P2.1-P2.3 / P2.4-P2.6 待启动

### 2026-05-22 — M8-T3 / P2.3：`OrderRepository` 实现（infrastructure 层 / MyBatis-Plus + items JSON）

#### Added

- `src/main/java/com/example/harness/infrastructure/order/persistence/`（**首次落地** infrastructure 层）：
  - `OrderPO.java`：`@TableName(value="orders", autoResultMap=true)`，`@TableId(ASSIGN_UUID)` UUID 主键；`items` 用 `@TableField(value="items_json", typeHandler=JacksonTypeHandler.class)` 走方案 B（JSON 列）
  - `OrderMapper.java`：`extends BaseMapper<OrderPO>` 空接口；CRUD 全走 MyBatis-Plus 内置 `insert` / `selectById` / `selectList(LambdaQueryWrapper)`
  - `OrderPersistenceAdapter.java`：`@Repository implements OrderRepository`；构造器注入 OrderMapper；3 方法体走 selectById 判定 insert vs updateById、LambdaQueryWrapper 查 active；含 private static `toPO`/`toDomain` 转换
- `src/test/resources/application.yml`（**首次落地** test 资源）：测试环境排除 `DataSource / DataSourceTransactionManager / Flyway / MybatisPlusAutoConfiguration` autoconfig — 让 `HarnessApplicationTests.contextLoads` 不被新加的 `@Repository` Adapter 拖死（main 配置已排除前 3 项，本文件 + MybatisPlusAutoConfiguration）

#### Changed

- `domain/order/Order.java`：加 `public static Order reconstitute(OrderId, String customerId, List<OrderItem>, OrderStatus)` 给 Repository 实现重建已存在聚合用。javadoc 明示"仅供 Repository 实现使用，业务流程必须走 place()"，不重复 place 的 items 校验（历史"边缘合法"数据须能复原）

#### 验证

- ✅ AC#1.a：`grep -rE "^import com\.baomidou\.mybatisplus" src/main/java/com/example/harness/infrastructure/` → 7 个 import（BaseMapper / LambdaQueryWrapper / @TableId / @TableField / @TableName / @IdType / JacksonTypeHandler），**仅**在 OrderMapper / OrderPersistenceAdapter / OrderPO 3 个文件内
- ✅ AC#1.b：`grep -rnE "^import (com\.baomidou|org\.springframework|jakarta\.persistence|com\.fasterxml\.jackson)" src/main/java/com/example/harness/domain/` → 空输出（domain/ 仍纯净）
- ⚠️ **AC#2 待端到端验证**（save → findById → equals）：依赖 P2.6 Migration + testcontainers MySQL；本机 Java 1.8 跑不了，留 P1.5+P2.6 一起跑
- ⚠️ **预期 hint 仍未触发**（D9 Windows path bug 持续）：本批次新建 infrastructure/ 应触发 `hint-infrastructure-layer`，新加 reconstitute() 应触发 `hint-domain-layer`，实测两个都没触发 — D9 影响面进一步确认

#### 未完 follow-up

- **AC#2 端到端跑通**（本机 JDK 17 + Docker + P2.6 Migration）
- **D9 Windows path bug** — P2.3 后建议立即修，否则 P2.4 改 application 层 hint 仍不触发
- **P2.4 PlaceOrderHandler**：依赖 P2.3 ✅ + P2.2 ✅，可直接启动
- **MyBatis-Plus + Lombok `@Value` Jackson 反序列化**：OrderItem 用 Lombok `@Value`（无默认构造），P2.6 跑测试时如 Jackson 反序列化失败，需给 OrderItem 加 `@JsonCreator` + `@JsonProperty`（此改动会触发 hint-domain-layer，但 D9 未修前实际不会拦）

### 2026-05-22 — M8-T3 / P2.2：`OrderRepository` 接口（domain 层）

#### Added

- `src/main/java/com/example/harness/domain/order/repository/OrderRepository.java`：
  - `Order save(Order order)`
  - `Optional<Order> findById(OrderId id)`
  - `List<Order> findActiveByCustomer(String customerId)`（active 当前定义 = `status == PENDING`，javadoc 写明）
- 子包 `domain/order/repository/`（首次落地；后续聚合的 Repository 同样走 `domain/<bc>/repository/` 子包）

#### 验证

- ✅ AC#1：`grep "^import " OrderRepository.java` 仅 `java.util.{List,Optional}` + `com.example.harness.domain.order.{Order,OrderId}`，无 infrastructure / spring import
- ✅ AC#2：方法名"表达业务意图"（`findActiveByCustomer` 而非 `findByStatusAndCustomerId`），返回类型聚合根 `Order` / `List<Order>` / `Optional<Order>`
- ⚠️ **灰名单未触发（Windows 路径分隔符 bug）**：`ddd-aggregate-boundary` 规则 `file_path_matches: 'src/main/java/.*/domain/'` 用正斜杠，Windows 上 Claude Code 传入的 `file_path` 是反斜杠 `D:\...\src\main\java\...\domain\...`，正则不匹配 → 规则在 Windows 上全失效。用户在主对话已显式授权写本文件（M8-T1 同款"声明授权"流程），但 hook 端没拦下 → audit log 仅有 PostToolUse `executed` 记录，无 `ask_user` 记录。新 backlog 项**候选 D9** 跟踪修法（dispatcher 评估 `file_path_matches` 时 normalize path / 或 yaml 用 `[/\\]` 兼容写法）

#### 未完 follow-up

- **候选 D9**：所有 `file_path_matches` 规则在 Windows 上失效（dispatcher path normalize 或 yaml 规则兼容写法）。影响：`ddd-aggregate-boundary` / `write-credentials-dir` / `hint-domain-layer` / `hint-infrastructure-layer` / `hint-application-layer` / `hint-migration-files` / `hint-spring-config` / `hint-agent-md` 8 条规则。建议下次 commit 前修
- P2.3 `OrderRepository` 实现（infrastructure 层 + MyBatis-Plus）— **依赖**：本机 JDK 17（跑 mvn test 验证 testcontainers MySQL）

### 2026-05-22 — M8-T3 / P2.1：`Order` 聚合根 + `OrderItem` / `OrderId` VO + `EmptyOrderException`

#### Added

- `src/main/java/com/example/harness/domain/order/`（第一个 BC `order` 的 domain 建模）：
  - `OrderId.java`：typed identifier VO（Lombok `@Value` 包 UUID + `generate()` 工厂）
  - `OrderItem.java`：VO（Lombok `@Value`：`sku` / `quantity` / `unitPrice: BigDecimal`）
  - `OrderStatus.java`：enum `PENDING / CONFIRMED / REJECTED / EXPIRED`（与 [m8-event-storm](docs/m8-event-storm.md) 时间线一致）
  - `Order.java`：聚合根（**不用 Lombok 注解**避免 `@Data` 暴露 setter）。手写 private ctor + `public static Order place(customerId, items)` factory；`items` 经 `List.copyOf` 不可变；`equals/hashCode` 仅基于 `id`（DDD 标准）
  - `EmptyOrderException.java`：domain exception，`place()` 当 items 为 null / empty 时抛
- `src/test/java/com/example/harness/domain/order/` 3 个测试类：
  - `OrderIdTest`：typed equality / `generate()` 唯一性
  - `OrderItemTest`：全字段 `equals/hashCode` + 反射断言"字段全 final 无 setter"（守护 AC#3 不被未来 PR 退化）
  - `OrderTest`：`place_returnsPendingOrder` / 空 items 抛 / null items 抛 / `items()` 不可变 / `equals` 仅基于 id（覆盖 AC#2 + 聚合根标识语义）

#### 验证

- ✅ AC#1（`grep -rE "^import (org\.springframework|jakarta\.persistence|com\.fasterxml\.jackson)" src/main/java/com/example/harness/domain/` 空输出）— 仅 import `java.*` + `lombok.Value`
- ✅ AC#2 / AC#3 代码层满足；测试断言守护
- ✅ PreToolUse hook 全程无 `BLOCKED` / `⚠️ 待人工授权`（5 个文件名均不命中 `ddd-aggregate-boundary` 的 `(Aggregate|Repository|Event)\.java$` 正则）；仅触发 `💡 提示: 改 domain 层前建议调 ddd-architect agent`（hint 性，本会话已去重）
- ⚠️ `./mvnw test -Dtest='Order*'` 验证待手动：本机 Java 1.8 不满足 Java 17 toolchain，待 P1.5 装好 JDK 17 后随 P1.5 一并跑

#### 未完 follow-up

- 本机装 JDK 17 后 `./mvnw test -Dtest='Order*'` 跑 5+2+2 = 9 个测试方法（含 P1.5 验证）
- P2.2 `OrderRepository` 接口（domain 层）— **会触发 `ddd-aggregate-boundary` 灰名单**，下次开工时请准备显式授权
- P2.4 PlaceOrderHandler 时给 `Order` 加 `confirm()` / `reject()` / `expire()` 状态转移方法 + 同步 `OrderPlaced` / `OrderConfirmed` 等 DomainEvent
- 引入 Customer BC 后把 `Order.customerId: String` 升级为 typed `CustomerId` VO

### 2026-05-22 — D8 hook 规则补强：Bash 写 pom.xml / domain/ 也拦下

#### Added

- `.claude/rules/policies/ask-user.yaml`：补 2 灰名单规则覆盖"Bash 绕过 Edit/Write 拦截"盲点：
  - `bash-pom-write`：Bash 通过 `>` 重定向 / `tee` / `sed -i` 写 `pom.xml` → 触发同 `pom-major-deps` 主依赖审查
  - `bash-domain-boundary-write`：Bash 通过 `>` 重定向 / `tee` / `sed -i` 写 `src/main/java/.../domain/*.java` → 触发同 `ddd-aggregate-boundary` DDD 边界审查
- `.claude/hooks/tests/test_pre_tool_use.sh`：新增"Bash 写敏感文件"区段 5 case（28 → 33 total）：
  - 4 命中（pom redirect / pom tee / pom sed -i / domain redirect）
  - 1 false-positive 防御（`cat pom.xml` 应放行）

#### Changed

- `docs/improvement-backlog.md`：D8 → §E（E49 完成项，标 ✅）

#### 验证

- `bash .claude/hooks/tests/test_pre_tool_use.sh`：33/33 全过
- `python .claude/scripts/policy-dispatch.py --validate`：all rules pass schema check
- 关闭 2026-05-21 段"未完 follow-up" 的 D8 条目

### 2026-05-21 — M8-T1 + M8-T2：Phase 1 项目骨架 + U1-U5 拍板

#### Added

- `pom.xml`：Spring Boot 3.3.5 parent + Java 17 toolchain。主依赖按 U1/U2/U5 拍板：
  - **MyBatis-Plus** `mybatis-plus-spring-boot3-starter` 3.5.9（U1）
  - **MySQL** `mysql-connector-j`（U2 testcontainers + MySQL）
  - **Flyway** `flyway-core` + `flyway-mysql`（U5）
  - Web / Validation / Lombok（按 [engineering-practices §13](.claude/rules/engineering-practices.md) 限定使用）
  - 测试：spring-boot-starter-test + testcontainers-mysql 1.20.3 + testcontainers-junit-jupiter
- `.mvn/wrapper/maven-wrapper.properties` + `mvnw` + `mvnw.cmd`：Maven Wrapper 锁 maven 3.9.9，distributionUrl 改官方 repo（CI 可用，不依赖本机 Nexus 镜像）
- `src/main/java/com/example/harness/`：包基址 `com.example.harness`（U4）+ DDD 四层目录骨架 `{interfaces,application,domain,infrastructure}/` 各含 `.gitkeep`（含层职责注释 + 规则指针）
- `src/main/java/com/example/harness/HarnessApplication.java`：`@SpringBootApplication` 主类放包根，不进 4 层任一子包（既触发包扫描覆盖全层，又避免主类污染分层）
- `src/main/resources/application.yml`：最小配置（`spring.application.name` + port 8080 + mybatis-plus 全局 + 日志层级）。Phase 1 阶段 `spring.autoconfigure.exclude` 排除 DataSource/DataSourceTransactionManager/Flyway autoconfig，让 Spring Boot 能空启动（M8-T3 加 BC 时移除该排除）
- `src/main/resources/db/migration/.gitkeep`：Flyway migration 目录占位（首个脚本 M8-T5 / P2.6 才写）
- `src/test/java/com/example/harness/HarnessApplicationTests.java`：`@SpringBootTest` 冒烟测试（`contextLoads`）

#### Changed

- `docs/m8-decomposition.md`：U1-U5 全部拍板标 2026-05-21（MyBatis-Plus / testcontainers+MySQL / order / com.example.harness / Flyway）+ 注明 U6-U8 按 engineering-practices §13 默认 + Phase 1 骨架实施状态
- `CLAUDE.md` §5 项目性质段："M8 待启动" → "M8-T0 Tier 1 已完成 / M8 主线 Phase 1 骨架已落地 / Phase 2 待启动"
- `CLAUDE.md` §7 测试命令注释："pom.xml 与 src/ 暂未实例化" → "Phase 1 骨架已落地，mvn 命令可用（前置 JDK 17）"
- `README.md` L6 status badge：`M7 done | M8-T0 done | M8 phase1 skeleton`
- `README.md` L14 当前状态 + L59-60 路线表：M8-T0 ✅ 完成 / M8 ⏳ Phase 1 骨架完成 / Phase 2 待启动
- `docs/improvement-backlog.md` §D 加 D8：hook 规则补强（Bash heredoc / `>` 重定向写敏感文件不被拦的盲点，建议 M8-T1 commit 后立即修）

#### 验证

- ✅ `pom.xml` 写入命中 PreToolUse 灰名单 `pom-major-deps`（用户 Q1 已显式授权），改用 `cat > pom.xml` heredoc 写入；手动 audit log 留痕：`hook=ManualAudit action=authorized_write target=pom.xml reason="user Q1 grant + Bash heredoc tool-scope gap"`。**Follow-up**：hook 规则补强见 D8
- ✅ `mvn -N wrapper:wrapper -Dmaven=3.9.9 -Dtype=only-script` 成功生成 mvnw/.cmd/wrapper.properties（本机 mvn 3.6.3 + Java 1.8 也能跑该 goal）
- ✅ `npx prettier --check src/main/resources/application.yml` 全过
- ⚠️ **P1.5 `./mvnw clean compile` 验证待手动**：本机 Java 1.8 不满足 `.tool-versions` 锁 Java 17 / Spring Boot 3 要求。装好 JDK 17 后跑 `./mvnw clean compile && ./mvnw test`，`HarnessApplicationTests.contextLoads` 应通过

#### 未完 follow-up

- 本机 Java 17 装好后跑 `./mvnw clean compile` 验证 Phase 1 骨架（P1.5）
- M8-T3 / P2.1 启动时，移除 `application.yml` 中的 `spring.autoconfigure.exclude`（DataSource/Flyway autoconfig）

### 2026-05-21 — M8-T0e/f：跨阶段一致性检查 command + 首发实战

#### Added

- `.claude/commands/cross-stage-check.md`：产研全链路**文档间**漂移检查 command（5 维度：产物存在性 / 状态一致性 / 范围漂移 / 引用链断裂 / 时间线漂移），覆盖 [ADR-0008](docs/adr/0008-process-capability-expansion.md) Tier 1 能力 H。与 `/sync-docs` 互补：sync-docs 查"代码 ↔ 文档"，cross-stage-check 查"文档 ↔ 文档"；不调 agent / 不动文件 / 不扫代码。**M8-T0e**

#### Changed

- `AGENTS.md` 路由速查表：加 "检查产研全链路文档间漂移 → 命令 `/cross-stage-check`" 一行
- `README.md` L6 status badge / L14 当前状态 / L59 路线表：M8-T0 进行中 + M8 主线待启动 精确化（修 cross-stage-check 首发实战发现的 [P2.3-P2.5] 措辞漂移）
- `CLAUDE.md` §5 项目性质段："当前进度" 加入 M8-T0 落地状态（修 [P2.2]）
- `docs/improvement-backlog.md` L4 Status："M7 后置 / M8-T0 前置阶段 / M8 主线启动前需消化"（修 [P2.6]）
- `docs/roadmap.md` §10 修订记录：加 v0.4 (2026-05-20) "M8-T0 前置阶段引入 + Tier 1 资产落地"（修 [P5.1]）
- `CHANGELOG.md` `[Unreleased]` 标题："M7 后置 / M8-T0 前置阶段 / M8 主线启动前"（修 [P2.1]）；同时补 2026-05-20 / 2026-05-21 入账段（修 [P3.1]）

#### 验证

- `/cross-stage-check` 首发实战 (**M8-T0f**)：扫 myHarness 自身命中 7 项漂移（5 必修 + 2 需用户拍板）。本批次：5 必修全修 + 2 用户拍板均确认改
- `.claude/.audit.log` 留痕：`hook=CrossStageCheck action=scanned target=all-stages-20260521`
- 5 个 Tier 1 资产 frontmatter 检查：2 agents 含 `model: sonnet` + 触发场景关键词；1 command 含 description + argument-hint

### 2026-05-20 — M8-T0a~d：产研全链路扩张 + Tier 1 前两组资产落地

#### Added

- `docs/adr/0008-process-capability-expansion.md`：产研全链路 Harness 能力扩张决策。盘点 16 项能力（60% 零件已就位），按 4 Tier 分批落地；Tier 1 = 需求拆解+AC / 事件风暴+服务划分 / 跨阶段一致性检查；明示 4 条边界约束（语言/技术栈无关 + 实战载体不空跑 + 首发对象绑实物 + 失败回退）+ Tier 4 触发条件机制化。与 [ADR-0002](docs/adr/0002-java-ddd-backend.md) / [ADR-0007](docs/adr/0007-revoke-plugin-pivot.md) 正交。**M8-T0 启动决策**
- `.claude/agents/requirement-decomposer.md`：需求拆解 + AC 生成 agent（INVEST 必检 / Gherkin AC / 语言技术栈无关 / 不擅自做技术选型 / 不可测需求拒绝输出）。**M8-T0a**
- `docs/m8-decomposition.md`：用 requirement-decomposer 拆 M8 章节为 3 phase / 16 subtask（P1.1-P3.5）+ 每条 Gherkin AC + 拓扑图 + Self-application 验证 + U1-U8 待澄清清单。**M8-T0b 首发实战**
- `.claude/agents/event-storm.md`：通用事件风暴 + 服务边界候选 agent（事件命名过去式 / 不依赖 DDD 术语 / 服务边界 ≥ 2 方案 / 不擅自做技术选型 / 拒绝对开发任务流做事件风暴）。**M8-T0c**
- `docs/m8-event-storm.md`：用 event-storm 对 M8 Phase 2 PlaceOrder 业务流做事件风暴 → 12 事件（7 happy + 5 异常）+ 5 actor + 3 服务边界方案（推荐方案 A 适配 M8）+ 反模式自查 + 与 ddd-architect 衔接建议。**M8-T0d 首发实战**

#### Changed

- `AGENTS.md` 路由速查表 + 自定义 Agents 表：加 `requirement-decomposer` / `event-storm` 两行
- `CLAUDE.md` §5 项目性质段：加 "能力维度：M8 主线（Java DDD 代码侧）+ M8-T0 前置阶段（产研全链路流程性能力...）"
- `docs/roadmap.md` §7：加 M8-T0 前置阶段表（6 子任务）+ Tier 2/3/4 嵌入说明（按 ADR-0008 §决定·6）
- `.claude/hooks/session-start.sh`：hook 可移植性修复（commit `db0a45e`）
- `docs/adr/README.md` + 多处 markdown 表：prettier 表格对齐（commit `d58382a`）

#### 验证

- 两个新 agent frontmatter 含 `model: sonnet` + 触发场景关键词，满足 [ADR-0008 §边界约束] 与 [roadmap §7 M8-T0 成功标准]
- m8-decomposition / m8-event-storm 文末含 `<!-- harness:agent-output -->` schema 块，与 [agent-output-schema.md] 一致
- m8-decomposition.md Self-application 验证全过（INVEST 不达标项有 ⚠️ + 说明 / AC 无模糊词 / 16 子任务拆 3 phase × ≤7）
- m8-event-storm.md 反模式自查全过（事件命名过去式 / actor 不含"系统" / 服务边界 3 方案 / 12 事件 / happy + 异常都有）

### 2026-05-19 — P2 剩余低成本组合（C1 / C6 / C8 / C10 / C12 / C16 → E43-E48）

#### Added

- `.claude/hooks/pre-compact.sh` + settings.json `PreCompact` 注册：压缩前 stdout 输出 "必保留：CLAUDE.md 锚点 / 当前任务 / 用户授权 / 未提交改动"，避免 compaction 丢关键状态。**C12 / E47**
- `.claude/scripts/memory-growth-summary.py`：扫 memory 目录按类型（decision/pitfall/pref/session/ref）统计 7/30 天新增 + 体积 + MEMORY.md 索引漂移检查；目录派生支持 `--memory-dir` / `CLAUDE_MEMORY_DIR` / 自动从 cwd 推算（实测 `D--myGithub-myHarness` 规则）。**C16 / E48**
- `docs/prompt-caching-notes.md`（8 节）：Claude Code 内置 cache 行为 + 适合/不适合 cache 的内容 + 保 cache hit 的工程实践 + 反模式速查 + 度量信号。**C8 / E45**
- `docs/policy-model-selection.md §5 Fallback`：opus → sonnet / sonnet → haiku / 全不可用 → 用户的降级规则，含本会话踩到的 `claude-opus-4-6 已下线` 实测案例。**C6 / E44**

#### Changed

- `.claude/commands/commit.md`：加 step 7 — commit 完成后调用 `session-state.py done-step` / `clear` 同步进度，让 SessionStart 准确反映未完事项。**C1 / E43**
- `.claude/scripts/audit-log-summary.py`：新增 `--failures` 视角，聚合三类失败相关信号（PreToolUse dispatcher error / SubagentStop status=failed|blocked / SubagentStop degraded_from 非空）。**C10 / E46**
- `docs/improvement-backlog.md`：C1/C6/C8/C10/C12/C16 改 ✅ E43-E48；§E 追加 6 条完成记录。

#### 验证

- `bash .claude/hooks/tests/test_pre_tool_use.sh` 28 case 全过。
- `python .claude/scripts/audit-log-summary.py --failures`：自动识别历史 10 条 yaml 解析失败（已修复 / audit 留痕）。
- `python .claude/scripts/memory-growth-summary.py`：5 decision + 6 pitfall = 11 条；MEMORY.md 索引与目录一致。
- `bash .claude/hooks/pre-compact.sh`：4 段必保留提示输出正常（项目锚点 / 任务进展 / 用户授权 / 未提交改动）。

### 2026-05-19 — Worktree 集成（E41 / D6 落地）

#### Added

- `docs/worktree-usage.md`：worktree 完整使用规范（何时用 / 怎么开 / 跨 worktree 状态聚合表 / 反模式 / 与现有机制协同）。
- `.worktreeinclude`：列出新建 worktree 时自动复制的 untracked + gitignored 文件（`.env*` / `.claude/settings.local.json`）。
- `CLAUDE.md §10`：加 worktree-usage.md 指针。
- `docs/improvement-backlog.md §E`：追加 E41。

#### Changed

- `.claude/scripts/policy-dispatch.py`：新增 `_resolve_audit_log_path()` 函数 — 子 worktree（`git rev-parse --git-common-dir` 返回绝对路径时）写主仓库 `.claude/.audit.log`；主 worktree / 非 git 仓库走 cwd 相对原路径；`HARNESS_AUDIT_LOG_PATH` env var 显式覆盖。
- `.claude/scripts/audit-log-summary.py`：同步实现 `_resolve_audit_log_path()`；`load_entries()` 接受 `log_path` 形参；CLI 加 `--log-path <path>` 覆盖默认解析。
- `.gitignore`：加 `.claude/worktrees/`。

#### 验证

- 模拟主 + 子 worktree（`git worktree add`）：子 worktree 内 `_resolve_audit_log_path()` 返回主仓库 `.claude/.audit.log` 绝对路径；主 worktree 返回相对路径，老行为不变。
- `bash .claude/hooks/tests/test_pre_tool_use.sh` 28 case 全过（tempdir 内非 git 仓库 → 自动 fallthrough 到 cwd 相对，与原 hook 行为一致）。

### 2026-05-19 — Auto mode 集成（E40）

#### Added

- `.claude/rules/engineering-practices.md §15`：新增 "Permission Mode policy（auto mode 集成）" 节，给 5 种 mode 的项目立场表 + auto 落地 5 条规则 + 3 条反模式。
- `CLAUDE.md §9`：加一段说明 — 黑+灰名单在所有 permission mode 下都先评估，auto 的分类器不替代用户授权。
- `.claude/hooks/tests/test_pre_tool_use.sh`：新增 2 case（ask-auto-mode-extra-hint / audit-log-records-permission-mode），总 28 case。
- `docs/improvement-backlog.md §D`：新增 D7 — Auto mode 深度集成（扩 yaml 规则覆盖"软风险"，需观察 daily 使用数据后判断）。

#### Changed

- `.claude/scripts/policy-dispatch.py`：
  - `audit_log()` 加 `permission_mode` 形参，写入每条 JSONL 记录
  - `main()` 从 stdin `payload.permission_mode` 读取并透传到所有 audit_log 调用（deny / ask_user / bypass 三路径全覆盖）
  - auto mode 下命中 `ask_user` 规则时额外输出 "↑ 当前 permission_mode=auto，分类器**不可**替代用户授权" 提醒
- `.claude/scripts/audit-log-summary.py`：新增 `--by-permission-mode` 聚合视角；老记录（字段引入前）归类为 `(legacy)`，便于识别切换点。
- `docs/improvement-backlog.md §E`：追加 E40。

#### 验证

- `bash .claude/hooks/tests/test_pre_tool_use.sh` 28 case 全过（含 2 个新 permission_mode case）。
- `python .claude/scripts/audit-log-summary.py --by-permission-mode` 当前 260 条历史记录全归 `(legacy)`，新写入的 case 显示 `auto`。
- prettier 改动文件全过。

### 2026-05-19 — P2 低成本组合（C2 / C5 / C9 / C11）

#### Added

- `.claude/scripts/statusline.py`：Claude Code 状态栏脚本，输出"项目 │ 分支(dirty 标记) │ 模型 · token 估算"，settings.json 注册。**C5 / E37**
- `AGENTS.md`："Skill vs Agent vs 主对话"小节，职责对照表 + 判断顺序 + 反例。**C9 / E38**

#### Changed

- `docs/loop-architecture.md §3`：新增"硬上限"小节（串行链 ≤ 4 / 并行 ≤ 5 / retry ≤ 2 / 同 agent 单任务 ≤ 3 / escalation ≤ 3 / degradation ≤ 2 / 单任务挂钟 ≤ 30min），明确触顶后必须停下问用户。**C2 / E36**
- `.claude/scripts/policy-dispatch.py`：bypass 分支累计过去 7 天 `bypass=true` 次数 ≥ 阈值（默认 3，`HARNESS_BYPASS_WARN_AT` 可调）→ 红字 stderr 提醒收敛。**C11 / E39**
- `.claude/rules/engineering-practices.md §15 Bypass policy`：同步阈值告警条目。**C11**
- `docs/improvement-backlog.md`：C2 / C5 / C9 / C11 工作量列改 ✅ E36-E39，§E 追加四条完成记录。

#### 验证

- `bash .claude/hooks/tests/test_pre_tool_use.sh` 26 case 仍全过。
- statusline.py 手测：注入 mock JSON 输出 `项目 │ 分支 │ 模型 · token`，ANSI 颜色与 dirty 标记生效。
- bypass 阈值告警手测：预置 2 条历史 + 触发第 3 次 → 红字提醒按预期出现。

### 2026-05-15 — P0-P3 系统性清账（架构 + CI 残留 + telemetry 闭环）

#### Added

- `docs/policy-model-selection.md`：模型选择策略单点真源（agent 默认表 + 通用场景表 + 优先级与升级规则）。**P1-B**
- `.claude/hooks/tests/test_subagent_stop.sh`：6 case smoke test（ok / degraded / escalate / blocked / 无 schema 静默 skip / 非法 JSON 不崩）。**P2-H**
- `.github/workflows/lint.yml` 新 job `agent-schema-check`：每个 agent .md 必含 `harness:agent-output` 示例。**P2-G**
- `.github/workflows/lint.yml` 新 job `commit-lint`：commit 消息走 Conventional Commits 正则强制。**P3-K**
- `.github/workflows/scheduled.yml` 新 job `weekly-audit-reminder`：每周一开 issue 提醒本机跑 `audit-log-summary.py`（audit log 是 .gitignored 本地文件，CI 看不到，改用 reminder 模式）。**P2-F / B6**
- `.claude/rules/policies/{deny,ask-user,hints}.yaml`：所有 PreToolUse 规则数据（35 条）外移到 yaml；`README.md` 给 schema 与维护流程。**P1-A**
- `.claude/scripts/policy-dispatch.py`：python 规则评估器（cmd_contains_any / cmd_matches / file_basename_in / new_content_present 等谓词，audit log + bypass + hint 去重三合一）。**P1-A**
- `.claude/scripts/session-state.py`：`.session.state` CLI helper（`set-task` / `add-step` / `done-step` / `blocked` / `clear` / `show`），主对话长任务时自觉调用，让 SessionStart 显示"上次未完事项"。**P1-C**
- `CLAUDE.md §12`：会话状态约定（M5-T6）。**P1-C**

#### Changed

- **ADR-0007 残留清扫**（**P0**）：
  - `.github/required-files.txt` 删 6 个 `plugin/*` 条目 + 删 `.github/workflows/plugin-validate.yml` 条目
  - `git rm .github/workflows/plugin-validate.yml`（plugin/ 已撤，workflow 僵尸化）
- `.mcp.json`：`@benborla29/mcp-server-mysql` 钉版本 `@2.0.8`，注释加禁用 @latest 提示。**P1-E**
- `AGENTS.md` Model Selection Policy 章：从完整表改为指向 policy-model-selection.md 的摘要。**P1-B**
- `.claude/rules/engineering-practices.md §15`：模型选择 policy 子节由表改为指针。**P1-B**
- `README.md`：加"前置要求"段（bash / python / Node 20+ / Windows 须 Git Bash 或 WSL）。**P1-D**
- `CLAUDE.md §5`：加平台前置说明（Windows 非 git-bash 终端 hook 静默失败）。**P1-D**
- `CLAUDE.md §11`：MEMORY 硬路径（`~/.claude/projects/D--myGithub-myHarness/memory/`）→ 改为"客户端自动派生，不固化到仓库"。**P3-N**
- `.claude/hooks/pre-tool-use.sh`：从 256 行 bash 规则脚本退化为 6 行 dispatcher 转发器；规则全部在 yaml。**P1-A**
- `.claude/hooks/session-start.sh`：每会话开始时清空 `.session.hints`。**P2-I**
- `.prettierrc.json`：yaml 文件改用 `singleQuote: true`（避免 `\s` 在双引号下被解析为非法转义）。**P1-A**
- `.github/workflows/lint.yml`：
  - `npm ci || npm install` → `npm ci`（移除 fallback，强制 lockfile 一致）。**P3-M**
  - `hook-test` job 加 `pip install pyyaml` + yaml parse 校验 + 接入 `test_subagent_stop.sh`。**P1-A / P2-H**
- `.github/workflows/scheduled.yml` `weekly-tool-versions`：移除 "(Future M7)" placeholder，落地为 `locked vs latest` 比较 + 漂移开 issue（含升级命令）。**P3-L**
- `.github/required-files.txt`：加 `docs/policy-model-selection.md` + `test_subagent_stop.sh` + `policies/{README,deny,ask-user,hints}` + `policy-dispatch.py` + `session-state.py`。

#### Fixed

- ADR-0007（撤销 plugin 化）执行不彻底导致 `lint.yml structure-check` 必 fail；本批清扫后恢复 CI 红→绿。

#### 验证

- pre-tool-use 26 case smoke test 仍全过（dispatcher 替换 bash case 后行为等价）
- subagent-stop 6 case smoke test 全过（新增）
- 3 个 policies yaml 文件 PyYAML 解析通过（35 条规则全部加载）
- session-state.py 手动验 set-task / add-step / done-step / blocked / clear / show 全链路 OK
- hint 去重手动验证：同 file_path 第 2 次 Edit 不输出 hint
- prettier --check：本批触动文件全部合规（pre-existing warns 不在本批范围）

#### M8 启动前剩余 follow-up

_本批 P1-A / P1-C 已全部落地，无未完 follow-up。_

---

### 此前 [Unreleased] 项

### Added

- `docs/agent-output-schema.md`：sub-agent 输出 schema 契约（`status` / `degraded_from` / `escalate_to` / `risks`），让 SubagentStop hook 能解析"成败/降级/升级"信号
- `.claude/hooks/subagent-stop.sh`：SubagentStop hook，解析 sub-agent 输出末尾的 `<!-- harness:agent-output -->` 块，写 audit log + 非 ok 状态 stderr 提示
- `.claude/hooks/tests/test_pre_tool_use.sh`：26 case smoke test（黑名单 / 灰名单 / 不误伤 / 敏感文件 / DDD 边界 / 主依赖 / bypass 全覆盖），tempdir 隔离 audit log 写入
- `docs/adr/0004-deprecate-bypass-once.md`：废弃 `.bypass-once` 单次授权机制（5/9 实验残留），统一走 `HARNESS_BYPASS=1` + commit marker + CI 拒合三道
- `docs/improvement-backlog.md`：完整 follow-up 清单（A/B/C/D/E 5 类，含工作量与修法）

### Changed

- `.claude/hooks/format.sh`：PostToolUse 加 audit log（记录 `executed` 事件含 tool/target/ext），不仅做格式化；带 `HARNESS_BYPASS=1` 时记 `bypass: true`
- `.claude/scripts/audit-log-summary.py`：加 6 个聚合参数（`--by-hook/tool/action/agent/ext/day`）+ `--hook` 过滤；`by-ext` 只统计 PostToolUse，`by-agent` 只统计 SubagentStop
- `.claude/settings.json`：注册 SubagentStop hook（共 5 类 hook）
- `.github/workflows/lint.yml`：加 `hook-test` job 跑 smoke test；必需清单加 `subagent-stop.sh` + `agent-output-schema.md` + `test_pre_tool_use.sh`；hook shebang+x 校验扩到 `.claude/hooks/**/*.sh`
- `.claude/rules/engineering-practices.md §15` Bypass policy：加 `.bypass-once` 废弃声明 + 引 ADR-0004
- `docs/adr/README.md`：登记 ADR-0004
- `README.md`：修复 8 处漂移（badge / 当前状态 / 节数 / Hooks 描述 / commands 数 / 阶段表 M3→M8 / 文档导航 / 目录速览），M4-M7 全部打 ✅，M8 标当前
- `CLAUDE.md §7`：M3 → M7 完成；`/audit-practices` 14 维度 → 15 维度

### Fixed

- README 多处过期描述（M3 实际已是 M7 完成；`.claude/commands/` 4 个 → 5 个）

### 验证

- SubagentStop hook 4 case 通过（ok / degraded / escalate / 无 schema 静默 skip）
- PostToolUse audit log 4 case 通过（Edit / Write / 空 file_path 不记 / bypass 标记）
- pre-tool-use 26 case smoke test 仍全过（未破坏现有）
- audit-log-summary 6 聚合视角输出干净（PreToolUse / PostToolUse 不混淆）

### 计划中

- M8：Java DDD 实例化（pom.xml + src/，六维度回归测试）—— 详见 [docs/improvement-backlog.md](docs/improvement-backlog.md) §B "M8 启动前必修"

## [M7] - 2026-05-09 — Tools 治理 + Policy 机制化

### Added

- **工具版本锁**：`package.json`（prettier 3.3.3）+ `.prettierrc.json`（格式约定）+ `.tool-versions`（asdf/mise 风格：node 20 / python 3.13 / java 17 / maven 3.9）
- `docs/tools-fallback.md`：工具失效降级路径（gitnexus → grep / MCP → schema dump / prettier → 跳过）+ "降级 ≠ 失败"原则 + 不该降级的场景
- `engineering-practices.md §15 Policy 机制化`：模型选择 / 降级 / 拒绝继续 / 升级链 / bypass / 审计 6 类元规则
- `.claude/scripts/audit-log-summary.py`：JSONL 审计日志摘要工具，支持 --tail / --bypass / --since
- AGENTS.md 加 "Model Selection Policy" 章 + "Tools Lock" 章 + "Audit Log" 章
- 8 个 agent frontmatter 加 model 选择注释（YAML `# why this model`）
- CI bypass-guard job：commit message 含 `BYPASS:` / 环境含 `HARNESS_BYPASS=1` 时直接 fail

### Changed

- PreToolUse hook 加 `_audit_log()` 函数：deny / ask_user / bypass 全部写 `.claude/.audit.log`（JSONL，已 .gitignore）
- PreToolUse hook 加 `HARNESS_BYPASS=1` 检测：env 设置时放行黑+灰名单但**强制写审计**（bypass: true 标记）
- CI lint.yml format-check 改用 `npm ci` 装 pinned prettier，与本地一致
- `/audit-practices` 命令从 14 维度扩到 **15 维度**（加 Policy 机制化）
- engineering-practices 评分尺度更新为"适用于全部 15 节"

### 验证

- audit log 4 类记录正常写入（deny / ask_user×2 / bypass）
- bypass 模式：HARNESS_BYPASS=1 时 `rm -rf /` 放行但 audit 标 bypass:true ✅
- summary 工具按动作 / 工具 / 原因正确统计

## [M6] - 2026-05-09 — Context 治理

### Added

- `docs/context-management.md`：三类注入来源、token 预算（自动注入 ≤ 8K）、按需注入机制、压缩策略、M8 后子目录 CLAUDE.md 拆分原则
- `.claude/scripts/audit-context-cost.py`：tiktoken 优先（fallback char/4）的 token 审计脚本，分 6 大类汇总 + 预算检查 + 减重建议
- `.claude/commands/audit-context.md`：`/audit-context` slash 命令，包装审计脚本
- PreToolUse hook 加按需注入 hint：根据 file_path 与 cmd 模式输出 `💡 提示:` 前缀的建议（11 种触发场景，14/14 测试通过），不阻塞

### Baseline 数据（M6 完成时）

- 自动注入：3589 tokens（占 8K 预算的 45% ✅）
- 常被 prefetch：6451 tokens（README + AGENTS.md + CHANGELOG）
- Rules 按需：4078 tokens
- Agents 总和：11220 tokens（仅 spawn 时计入单个）
- Docs 总和：18066 tokens（按需 Read，不计预算）

## [M4-M5] - 2026-05-09 — Memory 启用 + Loop 架构

### Added

- **M4 Memory**：启用 Claude Code 内置 memory（`~/.claude/projects/<id>/memory/`）
  - 5 条决策类记忆（Java DDD / MySQL 只读 / 三层架构 / 灰名单 / python over jq）
  - 6 条踩坑类记忆（jq 不可用 / SQL 误伤 / settings.local 已 tracked / hook 自拦 / Windows 路径 / format hook 幂等）
  - `MEMORY.md` 索引（按主题分组）
  - `docs/memory-conventions.md`：CLAUDE.md / ADR / Memory 三载体分工矩阵
  - CLAUDE.md §11 加 memory 引用与常见查阅场景
- **M5 Loop 架构**：
  - `docs/loop-architecture.md`：Driver / Worker 角色、调度决策树、并行/串行硬规则、retry/escalation/degradation 三策略、`.session.state` 中断恢复机制、自反馈环
  - `docs/periodic-tasks.md`：会话内 `/loop` skill + 仓库级 GitHub Actions 定时（D2 决策："两都要"）
  - `.github/workflows/scheduled.yml`：每日结构自检 / 每周 stale-check / 每周工具版本漂移（仅 open issue，不 fail repo）
  - `.claude/hooks/session-start.sh`：注入分支 / 最近 commit / 上次会话状态 / Memory 索引摘要 / 工具就绪状态
  - AGENTS.md 加自反馈环表 + 升级链表 + 降级链
- `docs/roadmap.md`：M4-M8 六维度路线总览（Loop / Context / Tools / Permission Gate / Memory / Policy）

### Changed

- Stop hook（stop-check.sh）扩展为同时写 `.session.state`（含分支 / head / 未提交数）供下次会话读
- settings.json 注册 SessionStart hook
- lint.yml required 列表扩到 25 项（加 session-start.sh / scheduled.yml / 4 份 docs）

## [M3] - 2026-05-09 — Layer 3 质量门禁

### Added

- `.gitignore` 覆盖 IDE / OS / Node / Python / Java / 密钥六类
- `.github/workflows/lint.yml`：prettier + 必需文件 + JSON 校验 + AGENTS 链接 + .gitignore 防泄密 + .mcp.json 变量同步
- `.mcp.json` 占位（MySQL 只读 MCP，强制 `ALLOW_*=false`）+ `.env.example`
- 6 个新 agent：`ddd-architect` `spring-boot-reviewer` `maven-build-doctor` `schema-analyst` `migration-author` `docs-keeper`
- 2 个新 command：`/onboard` `/sync-docs`
- engineering-practices §12（DDD 分层）§13（Java/Spring 风格）§14（MCP 治理）
- CLAUDE.md §5-§10（项目上下文 / 禁忌 / 测试命令 / gitnexus 路由 / 人工决策清单 / 子目录指引）
- PreToolUse hook 灰名单：DDD 边界改动、主依赖升级、`mvn deploy`、DDL/DML 数据库命令、危险 git 历史改写
- ADR 0001-0003（三层架构 / Java DDD / MCP+gitnexus）
- 本 CHANGELOG

### Changed

- `/audit-practices` 从 11 维度扩到 14 维度，对应 engineering-practices 14 节
- README badge `WIP M2` → `WIP M3`，路线图加 M4-M6
- PreToolUse hook 改用 python 解析 JSON（jq 不可用时 sed 在转义引号上截断）
- PreToolUse SQL 检测精确化：仅在命令以 `mysql`/`psql`/`mysqldump` 起头时检查，避免误伤含 SQL 字面量的普通命令
- format.sh 与 pre-tool-use.sh 统一用 python 解析
- engineering-practices "评分尺度" 移到全文末（覆盖全部 14 节）

### Fixed

- `.claude/settings.local.json` 之前已被 git 跟踪，现 `git rm --cached` 移出
- 删除根级空 `skills/` 目录
- CLAUDE.md gitnexus 死链 `https://github.com/` 移除

## [M2] - 2026-05-08 — Layer 2 反馈循环

### Added

- PostToolUse format hook（按后缀分发 prettier/ruff）
- Stop hook（会话结束变更摘要）
- 2 个 agent：`tdd-cycle-driver`（红绿重构）、`code-reviewer`（独立评审）
- 2 个 command：`/audit-practices`（11 维度）、`/commit`（标准化提交）
- AGENTS.md 索引

## [M1] - 2026-05-08 — Layer 1 约束

### Added

- CLAUDE.md 行为准则（4 节通用规则 + 7 节项目上下文）
- `.claude/rules/engineering-practices.md`（11 节通用工程化规则）
- PreToolUse hook 黑名单（rm -rf 根、强推主分支、写敏感文件）

## [M0] - 2026-05-08 — 项目立项

### Added

- README 三层 Harness 架构假设
- 项目结构：`docs/` `skills/`（占位）
