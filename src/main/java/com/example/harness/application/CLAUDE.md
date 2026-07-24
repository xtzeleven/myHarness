# application/ — 应用层规则

> 用例编排层。本文是子目录 CLAUDE.md，与根 [CLAUDE.md](../../../../../../CLAUDE.md) 叠加生效。

## 1. 准入清单（必须满足）

- **职责单一**：每个 Handler 只编排一个用例（`PlaceOrderHandler` / `ConfirmOrderHandler` / ...）。
  不在一个 Handler 里塞多个无关用例。
- **handle() 方法形态**：
  - 严格四步：**接命令 → 调 domain → 调 repo → 发事件**
  - **禁 `if/else/switch` 业务规则**（业务规则在 domain 层表达；本层只编排）
  - 异常**冒泡**，不 try/catch 默认吃掉 —— interfaces 层 `@RestControllerAdvice` 翻译
- **`@Transactional` 仅标在本层用例方法上**：domain / infrastructure / interfaces 都不准带。
- **依赖方向**：
  - 允许 `application → domain`（编排 domain 类型）
  - 允许 `application → org.springframework.*`（事务 / 事件 / 依赖注入）
  - **禁** `application → infrastructure`（不准 import infrastructure 实现类，只依赖 domain 层 Repository 接口）
- **入参 Command**：
  - 用 `record` 表达不可变意图
  - 字段校验留给 interfaces 层（`@Valid`）；本层 Command 入口可放 `Objects.requireNonNull` 但不重复字段级校验
  - 复用 domain VO（如 `OrderItem`）是允许的，避免无差别的 DTO ↔ Command 映射

## 2. 决策升级

| 信号                                              | 升级动作                                                                                |
| ------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Handler 出现 `if/else` 处理"是不是已下过单"等业务 | 停。把判断推回 domain（如 `Order.hasActive()`），让 `ddd-architect` 评审                |
| 想注入 `RestTemplate` / `WebClient` 调外部服务    | 用 anti-corruption layer（domain port + infrastructure adapter）；让 `ddd-architect` 评 |
| 同一事务跨多个聚合写                              | 停。重新审视聚合边界；让 `ddd-architect` 评                                             |
| `@Transactional(propagation=...)` 调参            | 让 `spring-boot-reviewer` 评，避免误用 REQUIRES_NEW 等                                  |

## 3. 当前用例快照

- `PlaceOrderHandler.handle(PlaceOrderCommand)` → `OrderId`
  - 调用：`Order.place` / `OrderRepository.save` / `ApplicationEventPublisher.publishEvent(OrderPlaced)`

## 4. 触发后端 agent

| 信号                             | 优先 agent             |
| -------------------------------- | ---------------------- |
| `@Transactional` 边界 / 传播行为 | `spring-boot-reviewer` |
| 用例编排是不是越界写了业务规则   | `ddd-architect`        |
| 循环依赖 / Bean 注入问题         | `spring-boot-reviewer` |
| 事件发布 vs MQ 选择              | `ddd-architect`        |

## 5. 测试约定

- 单测放在 `src/test/java/.../application/...`，命名 `<HandlerName>Test.java`
- Mock `OrderRepository` + `ApplicationEventPublisher`（不引 `@SpringBootTest`，纯 Mockito 跑得更快）
- 覆盖：**正常路径**（repo.save + publishEvent 各 1 次）+ **失败路径**（domain 异常冒泡，repo/publisher 不被触达）

## 6. 反模式（PR review 必拦）

- ❌ `@Transactional(readOnly = true)` 标在写操作上 —— 静默丢失提交
- ❌ Handler 直 new domain VO 替代 domain factory（绕过校验）
- ❌ catch `Exception` 写日志后 swallow —— 让事务静默回滚但 HTTP 还 200
- ❌ 同一 Handler 跨多个聚合写 —— 应拆为多 Handler + DomainEvent 异步联动
- ❌ `this.foo()` 自调用 `@Transactional` 方法 —— 不走代理，注解失效
