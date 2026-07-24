# domain/ — DDD 领域层规则

> 本目录是 Order BC 的**领域模型核心**。本文是子目录 CLAUDE.md，与根 [CLAUDE.md](../../../../../../CLAUDE.md) 叠加生效（同一规则只此处更细，不重复全局已说明的）。

## 1. 准入清单（必须满足，不接受 PR）

- **不 import 任何外层框架**：禁 `org.springframework.*` / `jakarta.persistence.*` / `com.fasterxml.jackson.*` / `com.baomidou.*` / `lombok.Data`。
  - 允许：`java.*`、`java.util.*`、`org.springframework.lang.Nullable`（JSR-305 替代）✘ —— 改用 JDK 自带 `Objects.requireNonNull`。
  - Lombok 仅 `@Value`（VO 用）；**禁** `@Data` / `@Setter`。
- **不带任何 Spring 注解**：禁 `@Service` / `@Component` / `@Repository` / `@Transactional` / `@Bean`。事务边界在 application 层。
- **聚合根**（如 `Order`）：
  - private 构造器 + static factory（如 `Order.place(...)`） —— 所有创建路径强制走业务校验
  - 业务方法表达意图（`confirm()` / `reject()`），**禁** setter
  - `equals/hashCode` 仅基于 ID
  - 跨聚合用 **ID 引用**，不持有对方对象（`OrderId` 而非 `Order`）
- **VO**（如 `OrderItem` / `OrderId`）：
  - 全字段 `final`，无 setter
  - `equals/hashCode` 基于**全部字段**
  - Lombok `@Value` 是允许的简写
- **DomainEvent**（如 `OrderPlaced`）：
  - 不可变 record
  - 事件名**过去式**（`OrderPlaced` / `PaymentCaptured`），不带 `Event` 后缀
  - 含 `occurredAt`（`Instant`）
- **Repository 接口**：
  - 方法名表达**业务意图**（`findActiveByCustomer`），不是 CRUD 风格（`selectByXxx`）
  - 返回 `Optional<Aggregate>` 或 `List<Aggregate>`，不直接返 PO
- **Domain Exception**（如 `EmptyOrderException`）：
  - 继承 `RuntimeException`（不强制 `Exception` checked 链）
  - **禁**直接抛 `RuntimeException` —— 用语义化命名

## 2. 决策升级（遇下列情况主对话必须停下问用户，不可自决）

| 信号                                       | 升级动作                                                        |
| ------------------------------------------ | --------------------------------------------------------------- |
| 新增聚合根 / Repository 接口 / DomainEvent | PreToolUse 灰名单会拦下，主对话 AskUserQuestion                 |
| 跨 BC 引用（如 Order 直接 import Payment） | 停。要么用 ID 引用，要么走 ACL/防腐层；让用户决定               |
| 想给 Entity 加 setter "方便测试"           | 不行。改用 `reconstitute` 静态方法或工厂；让 ddd-architect 评审 |
| 想在 domain 层注入服务（`@Autowired`）     | 不行。把依赖反过来 —— application 层组合，domain 纯计算         |

## 3. 当前模型快照

- **聚合根**：`Order`
- **VO**：`OrderId` / `OrderItem`
- **枚举**：`OrderStatus`（PENDING / CONFIRMED / REJECTED / EXPIRED）
- **事件**：`OrderPlaced`（位于 `event/`）
- **Repository 接口**：`OrderRepository`（位于 `repository/`），实现在 `infrastructure/`
- **Domain Exception**：`EmptyOrderException`

## 4. 触发后端 agent（与根级 §8 互补）

| 信号                              | 优先 agent                        |
| --------------------------------- | --------------------------------- |
| 这块归哪个 BC / 是新聚合吗        | `ddd-architect`                   |
| 评审聚合边界 / VO 决策 / 事件设计 | `ddd-architect`                   |
| 这个改动会不会破坏不变量          | `ddd-architect` + `code-reviewer` |

`spring-boot-reviewer` 在本目录**不直接适用** —— domain 不该有 Spring 反模式可审。

## 5. 测试约定

- 单测放在 `src/test/java/.../domain/order/`，文件名 `<ClassName>Test.java`
- 不引入 Spring 测试上下文（`@SpringBootTest` / `@MockBean`） —— domain 测试应纯 POJO，毫秒级跑完
- AssertJ + JUnit 5 + Mockito（Mockito 仅在 DomainService 单测里用，VO/Entity 不需要）
