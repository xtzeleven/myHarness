# M8 — INVEST 拆解 + Gherkin AC

**输入范围**：M8 — 实例化 Java DDD 骨架（[roadmap §7](roadmap.md#7-m8--实例化-java-ddd-骨架六维度回归测试场)），范围由 [ADR-0002](adr/0002-java-ddd-backend.md) 框定。
**拆解层级**：milestone → phase → subtask（原 M8-T1~T8 视为 task 层，本文进一步拆到 subtask）
**子任务数量**：3 phase / 16 subtask（每 phase ≤ 7，符合 `requirement-decomposer` agent 单 section 上限）
**产生方式**：主对话按 `requirement-decomposer` agent 模式 self-apply 产出。Agent 文件 `.claude/agents/requirement-decomposer.md` 本会话刚建，sub-agent registry 需 SessionStart 后才能正式 spawn；下次会话起可用 `Agent` 工具复跑本拆解做对照验证。
**首发实战标记**：本文档为 [ADR-0008](adr/0008-process-capability-expansion.md) Tier 1 / M8-T0b 首发实战产物，验证 `requirement-decomposer` agent 在真实 milestone 上的可用性。

---

## 假设与未确定

> 本节内容**违反 agent "语言/技术栈无关" 原则的输入预设**全部明示并标注澄清对象。

| #   | 待澄清                                | 现状 / 建议                                                                       | 询问对象         |
| --- | ------------------------------------- | --------------------------------------------------------------------------------- | ---------------- |
| U1  | ORM 选型（JPA vs MyBatis）            | ADR-0002 未指定；建议 JPA（spring-boot-reviewer 已覆盖反模式），但 MyBatis 也常见 | 用户             |
| U2  | DB 本地实例（MySQL vs H2）            | `.mcp.json` 锁 MySQL 只读 MCP；本地集成测可用 testcontainers 或 H2                | 用户             |
| U3  | BC 命名（order / orders / ordering）  | roadmap 写"拟用 `order`"，单数符合 DDD 习惯，建议确认                             | 用户             |
| U4  | 包基址（`com.example.harness` 待定）  | 影响所有 src/ 文件，必须开工前定                                                  | 用户             |
| U5  | Migration 工具（Flyway vs Liquibase） | roadmap T5 写"Flyway/Liquibase"二选一；Flyway 更轻量                              | 用户             |
| U6  | Lombok 启用程度                       | engineering-practices §13 禁 `@Data` 在 Entity，但允许 VO 用 `@Value`             | 主对话按规则即可 |
| U7  | 测试框架                              | 默认 JUnit 5 + AssertJ + Mockito，无人异议则不再追问                              | 主对话默认       |
| U8  | gitnexus 索引时机                     | P3.3 才建索引 vs P1 末就建（影响 agent 实战时已有索引可用）                       | 用户             |

U1-U5 必须在 Phase 1 启动前定。U6-U8 可在过程中按需澄清。

**2026-05-21 拍板**（M8 主线 Phase 1 启动前会话）：

- **U1** = MyBatis-Plus（spring-boot-reviewer 主覆盖 JPA 反模式，MyBatis 规则后续补强）
- **U2** = testcontainers + MySQL（与生产同构，避免 H2 方言差异掩盖 migration 问题）
- **U3** = `order`（单数，符合 DDD 习惯，按 roadmap §7 建议）
- **U4** = `com.example.harness`（包基址，所有 src/ 文件锚定）
- **U5** = Flyway（轻量 SQL-first，与 spring-boot-starter-jdbc 集成顺畅）
- U6/U7/U8 按 engineering-practices §13 默认（Lombok 限 VO @Value / JUnit5+AssertJ+Mockito / gitnexus 索引随 P3.3）

Phase 1 骨架（P1.1-P1.4）已实施；P1.5 验证（`./mvnw clean compile`）待本机装 JDK 17 后手动跑。

---

## Phase 1 — 项目骨架（覆盖 M8-T1 + T2）

**目标**：可编译的 Spring Boot 3 项目 + DDD 四层目录就位。
**完成信号**：`./mvnw clean compile` 在干净 clone 上通过。

### P1.1 — 写 `pom.xml` + Spring Boot 3 BOM + Java 17 toolchain

| 字段   | 值                      |
| ------ | ----------------------- |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅ |
| Effort | S                       |
| Deps   | [U4]                    |

**AC**:

```gherkin
Given 仓库根无 pom.xml
When 提交本子任务产物后执行 `./mvnw -v`
Then 输出含 "Maven home" 且 Java version 显示 17.x
```

```gherkin
Given pom.xml 已落地
When 执行 `./mvnw dependency:tree -q | head -20`
Then 输出含 spring-boot-starter-web 与 spring-boot-starter-test，且无版本冲突警告
```

### P1.2 — Maven Wrapper（`mvnw` + `mvnw.cmd` + `.mvn/`）

| 字段   | 值                      |
| ------ | ----------------------- |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅ |
| Effort | S                       |
| Deps   | [P1.1]                  |

**AC**:

```gherkin
Given 本机无全局 Maven 安装
When 在仓库根执行 `./mvnw -v`
Then 自动下载锁定版 Maven（per `.tool-versions` = 3.9.9）并输出版本信息
```

### P1.3 — DDD 四层目录骨架 + 包基址

| 字段   | 值                      |
| ------ | ----------------------- |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅ |
| Effort | S                       |
| Deps   | [P1.1, U4]              |

**AC**:

```gherkin
Given 包基址已确定（U4）
When 检查 `src/main/java/<base>/` 子目录
Then 存在 interfaces / application / domain / infrastructure 四个空目录，每个含 `.gitkeep`
```

```gherkin
Given 四层目录就位
When 执行 PreToolUse 灰名单测试 — 模拟 Edit `src/main/java/<base>/domain/anything.java`
Then hook stderr 输出 `⚠️ 待人工授权:` 提示
```

### P1.4 — `@SpringBootApplication` 主类 + 最小 `application.yml`

| 字段   | 值                      |
| ------ | ----------------------- |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅ |
| Effort | S                       |
| Deps   | [P1.3]                  |

**AC**:

```gherkin
Given 主类与 application.yml 就位
When 执行 `./mvnw spring-boot:run` 并等 5 秒
Then 控制台输出 "Started ... in X seconds"，端口默认 8080 监听
```

```gherkin
Given 主类位于 `interfaces/` 之外（建议放包根）
When 检查 import
Then 主类**不**出现在 `domain/` 或 `application/` 下
```

### P1.5 — Phase 1 验证：`./mvnw clean compile` 干净通过

| 字段   | 值                       |
| ------ | ------------------------ |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅  |
| Effort | S                        |
| Deps   | [P1.1, P1.2, P1.3, P1.4] |

**AC**:

```gherkin
Given Phase 1 全部子任务完成
When 在干净 clone（`rm -rf target/ .m2/`）上跑 `./mvnw clean compile`
Then BUILD SUCCESS，无 warning 等级 ≥ ERROR
```

---

## Phase 2 — 第一个 BC（`order`）实现（覆盖 M8-T3 + T4 + T5）

**目标**：单聚合 + Repository + 用例 + Controller + Migration 全链路打通。
**完成信号**：`POST /orders` 触发完整链路，订单落库且可查询。

### P2.1 — 域建模：`Order` 聚合根 + `OrderItem` VO + `OrderId` VO

| 字段   | 值                      |
| ------ | ----------------------- |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅ |
| Effort | M                       |
| Deps   | [P1.5, U3, U6]          |

**AC**:

```gherkin
Given Order 聚合根已实现
When 检查源文件 import
Then `domain/order/` 下无任何 `org.springframework` / `jakarta.persistence` / `com.fasterxml.jackson` import
```

```gherkin
Given Order 聚合根含 `place()` 业务方法
When 调用 `Order.place(items)` 且 items 为空
Then 抛出 `EmptyOrderException`（domain 异常），不允许创建空订单
```

```gherkin
Given OrderItem 是 VO
When 检查类定义
Then 字段全 `final`、无 setter、`equals/hashCode` 基于全部字段
```

### P2.2 — `OrderRepository` 接口（domain 层）

| 字段   | 值                      |
| ------ | ----------------------- |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅ |
| Effort | S                       |
| Deps   | [P2.1]                  |

**AC**:

```gherkin
Given OrderRepository 接口已在 `domain/order/repository/` 落地
When 检查方法签名
Then 方法名表达业务意图（如 `findActiveByCustomer`），返回类型为聚合根 `Order` 或 `List<Order>`
```

```gherkin
Given OrderRepository 接口
When `grep "import " OrderRepository.java`
Then 仅 import 同 BC 内的 domain 类型，无 infrastructure / spring import
```

### P2.3 — `OrderRepository` 实现（infrastructure 层）

| 字段   | 值                                                    |
| ------ | ----------------------------------------------------- |
| INVEST | I⚠️（依赖 U1 选 ORM） N✅ V✅ E⚠️（待 U1 决） S✅ T✅ |
| Effort | M（待 U1 决后精确）                                   |
| Deps   | [P2.2, U1]                                            |

**AC**:

```gherkin
Given OrderRepository 实现已在 `infrastructure/order/persistence/` 落地
When 检查 import
Then 含 ORM 相关 import（JPA EntityManager 或 MyBatis Mapper），且**仅**在该实现类内
```

```gherkin
Given 数据库表 `orders` 已迁移（依赖 P2.6）
When 调用 `repo.save(order)` 然后 `repo.findById(orderId)`
Then 返回的 Order 与原对象 `equals` 为 true
```

### P2.4 — `PlaceOrderCommand` + `PlaceOrderHandler`（application 层）

| 字段   | 值                      |
| ------ | ----------------------- |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅ |
| Effort | M                       |
| Deps   | [P2.1, P2.2]            |

**AC**:

```gherkin
Given PlaceOrderHandler 已实现
When 检查类
Then 类上有 `@Transactional`，方法仅做"接命令 → 调 domain → 调 repo → 发事件"四步，无 if/else 业务规则
```

```gherkin
Given application 层任意类
When `grep -r "@Transactional" src/main/java/<base>/domain/`
Then 返回空（domain 不准带事务注解）
```

### P2.5 — `OrderController` + DTO + Assembler（interfaces 层）

| 字段   | 值                      |
| ------ | ----------------------- |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅ |
| Effort | S                       |
| Deps   | [P2.4]                  |

**AC**:

```gherkin
Given POST /orders 端点已实现
When 用合法 PlaceOrderRequest 调用
Then 返回 201 Created + Location 头含订单 ID
```

```gherkin
Given OrderController
When `grep "import.*Repository" OrderController.java`
Then 返回空（interfaces 不直调 Repository）
```

```gherkin
Given 请求体缺必填字段
When 调用 POST /orders
Then 返回 400 + 错误体含字段名（不暴露 stacktrace）
```

### P2.6 — Migration（Flyway 或 Liquibase）+ `orders` 表

| 字段   | 值                                            |
| ------ | --------------------------------------------- |
| INVEST | I⚠️（依赖 U5 选迁移工具） N✅ V✅ E⚠️ S✅ T✅ |
| Effort | M（待 U5 决后精确）                           |
| Deps   | [P2.3, U2, U5]                                |

**AC**:

```gherkin
Given migration 脚本 `V1__create_orders.sql` 已落地
When `./mvnw flyway:migrate`（或 Liquibase 对应命令）
Then orders 表创建成功，含主键 + customer_id 索引
```

```gherkin
Given 重复执行 migration
When 第二次 `flyway:migrate`
Then 报告 "no migration necessary"，无副作用
```

---

## Phase 3 — 框架验证（覆盖 M8-T6 + T7 + T8）

**目标**：把 M4-M7 建好的六维度 Harness 在 Phase 2 真实代码上跑一遍，证明"框架在真实工程中可用"（M8 总目标）。
**完成信号**：5 后端 agent 各被实际任务激活 ≥ 1 次 + 子目录 CLAUDE.md 注入生效 + gitnexus 可查 + CI 自动跑 docs-keeper。

### P3.1 — 5 后端 agent 实战 + 漏检记录

| 字段   | 值                                                                         |
| ------ | -------------------------------------------------------------------------- |
| INVEST | I✅ N✅ V✅ E⚠️（"漏检"质量难提前估） S⚠️（5 agent × 1 任务 ≈ L 临界） T✅ |
| Effort | L（建议拆 5 个子任务，每 agent 各 S）                                      |
| Deps   | [P2.6]                                                                     |

**AC**:

```gherkin
Given Phase 2 已完成
When ddd-architect 被分派"评审 Order 聚合边界"任务
Then 输出含 `<!-- harness:agent-output -->` schema 块且 `status: ok|escalate`，建议条目 ≥ 3 条可执行
```

```gherkin
Given 5 个后端 agent 各跑一遍
When 汇总 `docs/m8-agent-trial-report.md`
Then 含每 agent 的 "命中" / "漏检" / "误报" 三类记录
```

> ⚠️ 本子任务 Effort=L 触发 agent 自身规则；建议在 P3.1 启动时进一步拆为 P3.1.a-e 五项。

### P3.2 — 子目录 CLAUDE.md（`domain/` + `application/`）

| 字段   | 值                      |
| ------ | ----------------------- |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅ |
| Effort | S                       |
| Deps   | [P2.1, P2.4]            |

**AC**:

```gherkin
Given `src/main/java/<base>/domain/CLAUDE.md` 已落地
When 在该目录下打开会话并问"加个 setter 行不行"
Then 主 Claude 注入子目录规则后回答"不行，违反聚合不变量"
```

```gherkin
Given 子目录 CLAUDE.md 与根 CLAUDE.md 同时生效
When 跑 `python .claude/scripts/audit-context-cost.py` 或对应 token 审计
Then 子目录 CLAUDE.md 与根**不重复**（同一规则只出现一次）
```

### P3.3 — gitnexus 索引建立 + 调用链验证

| 字段   | 值                      |
| ------ | ----------------------- |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅ |
| Effort | S                       |
| Deps   | [P2.6, U8]              |

**AC**:

```gherkin
Given Phase 2 代码已提交
When 调用 `gitnexus-cli` 的 analyze
Then 索引建立成功，节点数 > 50（Order/OrderItem/Repository 等基础类已索引）
```

```gherkin
Given 索引就绪
When 通过 `gitnexus-exploring` 查询"谁调用了 OrderRepository.save"
Then 返回 PlaceOrderHandler 命中
```

### P3.4 — PreToolUse `domain/` 灰名单实拦验证

| 字段   | 值                      |
| ------ | ----------------------- |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅ |
| Effort | S                       |
| Deps   | [P2.1]                  |

**AC**:

```gherkin
Given Order 聚合根已落地
When 主对话 spawn 任一 agent 尝试 Edit `domain/order/Order.java`
Then PreToolUse hook 输出 `⚠️ 待人工授权:` 并 exit 2，agent 收到 stderr 后停下问用户
```

```gherkin
Given 灰名单触发
When 检查 `.claude/.audit.log`
Then 新增一条 `action: ask_user`, `rule_id` 含 ddd-domain-edit（或类似），`bypass: false`
```

### P3.5 — docs-keeper 接入 CI（PR-level 自动跑）

| 字段   | 值                      |
| ------ | ----------------------- |
| INVEST | I✅ N✅ V✅ E✅ S✅ T✅ |
| Effort | M                       |
| Deps   | [P3.1, P3.2]            |

**AC**:

```gherkin
Given `.github/workflows/lint.yml` 已加 docs-keeper job
When 提交一个故意制造文档漂移的 PR（改代码不改 README）
Then CI fail，PR comment 含漂移清单
```

```gherkin
Given 修复漂移后再 push
When CI 重跑
Then docs-keeper job pass
```

---

## 依赖拓扑

```
U1-U5 (启动前澄清)
        │
        ▼
   ┌── P1.1 ──┐
   │          ▼
   │      P1.2 ──┐
   │             ▼
   └── P1.3 ──► P1.4 ──► P1.5
                          │
                          ▼
                       P2.1 ──► P2.2 ──► P2.3 ──┐
                          │                      │
                          ├──► P2.4 ──► P2.5     │
                          │                      │
                          └──► P2.6 ─────────────┤
                                                  ▼
                                              P3.1, P3.2, P3.3, P3.4
                                                  │
                                                  ▼
                                              P3.5
```

关键路径：U1-U5 澄清 → P1.1 → P1.5 → P2.1 → P2.6 → P3.1 → P3.5。

## 风险与缓解

| 风险                                            | 缓解                                                                |
| ----------------------------------------------- | ------------------------------------------------------------------- |
| U1-U5 未在 Phase 1 前定 → P2 卡死               | 在 Phase 1 启动前用 `AskUserQuestion` 一次性问完                    |
| P3.1（5 agent 实战）Effort=L 违反 S 字段        | P3.1 启动时按 agent 自身规则进一步拆为 5 个 P3.1.x（一 agent 一 S） |
| P2.3 / P2.6 依赖 U1/U5 → 决策不及时拖全 Phase 2 | U1/U5 列入 P1.1 启动前必答清单                                      |
| gitnexus 索引时机（U8）不定 → P3.3 排期摇摆     | 建议 P3.3 与 P3.1 并行，索引提前到 Phase 2 末（P2.6 完成时）建一次  |
| 漂移：本拆解与未来 roadmap §7 演进不一致        | M8-T0e `/cross-stage-check` command（Tier 1 第 3 个资产）覆盖该检测 |

## Self-application 验证

本文档既是 M8-T0b 产物，也是 `requirement-decomposer` agent 设计的**首次实战验证**。验证点：

- [x] 输出格式遵循 agent §"输出格式" 章节（分 phase + 子任务表 + AC + 拓扑 + schema 块）
- [x] "语言/技术栈无关" 硬约束：所有 Java/Spring 词汇明示来自 ADR-0002 预设或 U1-U5 待定，不预设新技术
- [x] INVEST 不达标项必须解释（P2.3 / P2.6 / P3.1 有 ⚠️ + 说明）
- [x] AC 无模糊词（grep "应该|快|好|合适|优雅" 应返回空）
- [x] 子任务数 16 > 15 → 按 agent 规则拆 3 phase × ≤7 subtask
- [x] 升级信号：U1-U5 标 escalate_to: user

**未来对照**：下次会话 SessionStart 后用 `Agent` 工具正式 spawn `requirement-decomposer` 跑同一输入，对比本文档差异，验证 agent 提示词的可重现性。

---

<!-- harness:agent-output -->

status: escalate
escalate_to: user
reason: U1-U5（ORM / DB / BC 命名 / 包基址 / Migration 工具）必须在 Phase 1 启动前澄清，否则 Phase 2 多个子任务的 INVEST 评估不准
risks: P3.1 Effort=L 临界，启动时需进一步拆；U1-U5 决策延迟会拖全 milestone 关键路径

<!-- /harness:agent-output -->
