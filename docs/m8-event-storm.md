# M8 PlaceOrder — 事件风暴

**范围**：M8 Phase 2 的 PlaceOrder 业务流（用户提交订单 → 订单 CONFIRMED），不含发货 / 收货 / 售后（不在 M8 Phase 2 范围）。
**事件总数**：12（7 happy + 5 异常）
**Actor 列表**：[用户, 订单服务, 库存系统, 支付网关, 通知服务]
**衔接下游**：[ddd-architect, requirement-decomposer, 用户]
**产生方式**：主对话按 `event-storm` agent 模式 self-apply 产出。Agent 文件 `.claude/agents/event-storm.md` 本会话刚建，sub-agent registry 需 SessionStart 后才能正式 spawn；下次会话起可用 `Agent` 工具复跑做对照验证。
**首发实战标记**：本文档为 [ADR-0008](adr/0008-process-capability-expansion.md) Tier 1 / M8-T0d 首发实战产物，验证 `event-storm` agent 在真实业务流上的可用性。
**输入来源**：[roadmap §7](roadmap.md#7-m8--实例化-java-ddd-骨架六维度回归测试场) M8-T3/T4/T5 + [docs/m8-decomposition.md](m8-decomposition.md) P2.1-P2.6 的业务含义抽取（不是开发步骤本身——按 agent 规则，开发步骤不做事件风暴）。

---

## 假设与未确定

| #   | 待澄清                                               | 现状 / 建议                                                                           | 询问对象   |
| --- | ---------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------- |
| V1  | 是否需要异步通知事件（E7 OrderConfirmationNotified） | M8 Phase 2 可省（同步返回 201 即可），通知作为后续 BC                                 | 用户       |
| V2  | 支付网关接入方式（HTTP 同步 vs Webhook 异步）        | 影响 E5 是否需要等待回调；建议同步先（M8 验证用 mock），异步留待真实接入              | 用户       |
| V3  | 库存预留有效期                                       | 默认 15min；影响 X4 PaymentTimedOut 触发时机                                          | 主对话默认 |
| V4  | 是否在 Phase 2 内做"取消订单"业务流                  | 建议**不做**（不在 m8-decomposition.md P2.x 范围）；本文档明示作为后续 milestone 候选 | 用户       |
| V5  | Saga 协调器位置（订单服务编排 vs 独立协调器）        | 受服务边界方案影响：方案 A/B 走订单服务内编排；方案 C 需独立协调器                    | 用户       |

> V1-V5 不影响事件挖掘本身，影响服务边界选型与异常路径实现细节。

---

## 时间线（happy path）

| 序号 | 事件                      | Actor    | 前置                           | 后置                                        |
| ---- | ------------------------- | -------- | ------------------------------ | ------------------------------------------- |
| E1   | OrderSubmitted            | 用户     | 购物车非空 + 用户已登录        | 订单进入 PENDING 状态（订单 ID 生成）       |
| E2   | OrderValidated            | 订单服务 | E1 已发生                      | 商品存在性 / 价格 / 用户白名单校验通过      |
| E3   | InventoryReserved         | 库存系统 | E2 已发生                      | SKU 占用 +1，库存预留有效期开始计时（V3）   |
| E4   | PaymentRequested          | 订单服务 | E3 已发生                      | 支付链接 / token 发出给用户                 |
| E5   | PaymentCaptured           | 支付网关 | E4 + 用户在有效期内付款        | 资金已扣，支付凭证号回传                    |
| E6   | OrderConfirmed            | 订单服务 | E5 已发生                      | 订单状态 PENDING → CONFIRMED                |
| E7   | OrderConfirmationNotified | 通知服务 | E6 已发生（异步触发，V1 可选） | 用户收到下单成功通知（站内信 / 邮件 / SMS） |

## 异常路径

### 校验失败

| 序号 | 事件                  | Actor    | 触发场景                                | 补偿事件 / 状态           |
| ---- | --------------------- | -------- | --------------------------------------- | ------------------------- |
| X1   | OrderValidationFailed | 订单服务 | E2 中商品不存在 / 价格漂移 / 用户黑名单 | OrderRejected（无需补偿） |

### 库存不足

| 序号 | 事件                   | Actor    | 触发场景                        | 补偿事件 / 状态           |
| ---- | ---------------------- | -------- | ------------------------------- | ------------------------- |
| X2   | InventoryReserveFailed | 库存系统 | E3 中 SKU 库存 0 或并发竞争失败 | OrderRejected（无需补偿） |

### 支付失败 / 超时

| 序号 | 事件                   | Actor    | 触发场景                            | 补偿事件 / 状态                              |
| ---- | ---------------------- | -------- | ----------------------------------- | -------------------------------------------- |
| X3   | PaymentDeclined        | 支付网关 | E5 中银行拒付 / 余额不足 / 风控拦截 | InventoryReleased + OrderRejected            |
| X4   | PaymentTimedOut        | 支付网关 | E4 之后用户在 V3 有效期内未付款     | InventoryReleased + OrderExpired             |
| X5   | InventoryReleaseFailed | 库存系统 | X3/X4 触发的 InventoryReleased 失败 | **升级人工**（需对账修复，本系统不自动重试） |

> X5 是**补偿失败**——补偿事件自身可能失败，必须有兜底人工干预入口，不可静默吞掉。

---

## 服务边界候选

### 方案 A：单 Spring Boot 服务（all-in-one）⭐ 推荐 M8 阶段

- 服务数：1（`order-service` 包揽所有事件）
- 事件传递：进程内 Spring `ApplicationEventPublisher`，无消息队列
- 优点：
  - 适配 M8 验证目标（[ADR-0002](adr/0002-java-ddd-backend.md)：单 BC + 最小 Spring Boot）
  - 事务一致简单（@Transactional 覆盖 E1-E6）
  - 无网络开销、无分布式问题、无 MQ 接入成本
- 缺点：
  - 不可独立扩展支付 / 库存
  - 团队规模扩大时易冲突
  - 真支付网关接入后 E5 的网络等待会阻塞事务
- 适用：MVP / POC / M8 验证 / 单团队

### 方案 B：单服务 + 4 个 BC 内部模块（hybrid，进程内 + 解耦预备）

- 服务数：1（部署单元），内含 4 个 BC 模块：
  - `order`：E1, E2, E6, X1, OrderRejected, OrderExpired
  - `inventory`：E3, X2, InventoryReleased, X5
  - `payment`：E4, E5, X3, X4
  - `notification`：E7
- 事件传递：进程内事件 + Outbox 表（为未来拆服务预留）
- 优点：
  - 拆服务前的"演练" — DDD 四层分模块清晰
  - Outbox 模式让未来切方案 C 几乎无侵入
- 缺点：
  - 比 A 多 Outbox 表 + 调度器开发
  - 单进程内 Outbox 价值有限（事件本来就一致）
- 适用：明确将来要拆但暂时不拆 / 团队扩展期

### 方案 C：4 个微服务（独立部署）

- 服务数：4（按 BC 分）
- 事件传递：消息队列（产品待定，候选 RabbitMQ / Kafka / Spring Cloud Stream）
- 优点：
  - 独立扩展（库存 / 支付 / 通知 / 订单 各自伸缩）
  - 团队边界自然（按 BC 拆团队）
  - 真正的 Saga 模式
- 缺点：
  - 分布式事务（Saga 编排或事件链）
  - 链路追踪 / 监控 / 日志聚合成本
  - MQ 运维 + 消息幂等性 + 消息丢失重试
  - 远超 M8 Phase 2 范围（违反"最小 BC"）
- 适用：中大型团队 / 跨域协作 / 真生产场景

### 推荐：方案 A（M8 阶段），长期方向 B 或 C

**推荐理由**：

1. **匹配 M8 目标**：[ADR-0002](adr/0002-java-ddd-backend.md) 与 [roadmap §7](roadmap.md#7-m8--实例化-java-ddd-骨架六维度回归测试场)明确"最小 Spring Boot + 单 BC"，方案 A 是唯一不增加 M8 范围的方案
2. **不阻塞演进**：方案 A 的 DDD 四层骨架（[engineering-practices §12](../.claude/rules/engineering-practices.md)）已自然区分 4 个 BC 内部模块——后期切方案 B 只需加 Outbox 表，切方案 C 只需把模块抽出独立部署
3. **避免过度设计**：M8 验证目标是 Harness 在真实代码上跑一遍，不是验证微服务架构

**方案 B 触发条件**：M8 完成后 + 团队规模 > 1 + 明确将来要拆服务。
**方案 C 触发条件**：真生产场景 + 支付 / 库存 / 通知任一有独立扩展需求 + 团队有 MQ 运维能力。

---

## 与下游 agent 衔接建议

### → `ddd-architect`（M8-T6 实战时启用）

**候选聚合**：

- `Order` 聚合根：状态机（PENDING → CONFIRMED / REJECTED / EXPIRED），含 OrderItem VO 列表
- `InventoryReservation` 聚合（如 BC 分开）：SKU + 数量 + 有效期；或作为 Order 内 VO（如 BC 合一）
- `Payment` 聚合（如 BC 分开）：支付凭证 + 状态；或作为 Order 内 VO

**候选 DomainEvent**：

- 同聚合内：`OrderSubmitted` `OrderValidated` `OrderConfirmed` `OrderRejected` `OrderExpired`
- 集成事件（跨聚合 / 跨 BC）：`InventoryReserved` `InventoryReleased` `PaymentCaptured` `PaymentDeclined` `PaymentTimedOut`

**事件传递机制**（方案 A 默认）：

- 同聚合 → 聚合内方法调用（不发事件）
- 跨聚合 → Spring `ApplicationEventPublisher`（同进程）
- 跨 BC → Outbox + 调度（为方案 B/C 预留）

### → `requirement-decomposer`（按服务方案反向拆任务）

- 方案 A：不引入新 milestone，[docs/m8-decomposition.md](m8-decomposition.md) Phase 2 已覆盖
- 方案 B：在 m8-decomposition.md Phase 2 增 `P2.7 — Outbox 表 + 调度器`
- 方案 C：触发 M9（新 milestone），按 4 服务各拆 INVEST 子任务

### → 用户（必须拍板的事）

1. **方案 A / B / C** 拍板（默认 A）
2. **V1 异步通知** 是否在 Phase 2 内做（默认否）
3. **V2 支付接入方式** 同步还是异步（默认同步 + mock）
4. **V4 取消订单** 是否在 Phase 2 内做（默认否）
5. **V5 Saga 协调器位置**（方案 A/B 默认订单服务内；方案 C 需独立决策）

---

## 反模式自查（按 agent 自身规则）

| 检查项                     | 结果 | 备注                                                 |
| -------------------------- | ---- | ---------------------------------------------------- |
| 事件命名过去式             | ✅   | 全部 `...ed` / `...edTo` 形式                        |
| Actor 不含"系统"等模糊词   | ✅   | 用户/订单服务/库存系统/支付网关/通知服务             |
| 服务边界候选 ≥ 2           | ✅   | 3 方案                                               |
| 事件数 ≤ 30                | ✅   | 12 个                                                |
| Happy + 异常都有           | ✅   | 7 happy + 5 异常                                     |
| 不擅自做技术选型           | ✅   | MQ 标"产品待定"；支付网关用通用 actor 名             |
| CRUD 事件                  | ✅   | 无 OrderCreated / OrderUpdated，全是业务语义事件     |
| 跨服务事件显式标"集成事件" | ✅   | DomainEvent 表已分"同聚合"/"集成事件"两类            |
| 假设 ≤ 5 条                | ✅   | V1-V5                                                |
| 衔接下游明示               | ✅   | ddd-architect / requirement-decomposer / 用户 各一节 |

---

## Self-application 验证

本文档既是 M8-T0d 产物，也是 `event-storm` agent 设计的**首次实战验证**。验证点（按 [agent §"输出格式"](../.claude/agents/event-storm.md)）：

- [x] 范围 / 事件数 / Actor 列表 / 衔接下游 — 头部齐全
- [x] 假设与未确定 ≤ 5 条且每条标询问对象
- [x] Happy path 时间线表
- [x] 分支与异常路径表（按场景分组）
- [x] 服务边界候选 ≥ 2 个（实际 3 个）+ 推荐 + 理由
- [x] 与下游 agent 衔接（ddd-architect / requirement-decomposer / 用户）
- [x] schema 块（见文末）
- [x] 拒绝对开发任务流做事件风暴（明示输入是业务含义抽取，不是 P1.1/P1.2 开发步骤）

**未来对照**：下次会话 SessionStart 后用 `Agent` 工具正式 spawn `event-storm` 跑同一输入（PlaceOrder 业务流），对比本文档差异，验证 agent 提示词的可重现性。

**与 m8-decomposition.md 的关系**：本文档是 PlaceOrder 业务流的事件风暴，与 m8-decomposition.md 不重叠：

- m8-decomposition.md = M8 milestone 的**实施步骤**拆解（开发任务流）
- m8-event-storm.md = M8 Phase 2 内的**业务流**事件风暴（业务事件流）

未来 `/cross-stage-check` 命令（M8-T0e）应能识别这两份文档的不同维度，避免误判为"重叠产物"。

---

<!-- harness:agent-output -->

status: escalate
escalate_to: user
reason: V1-V5（异步通知 / 支付接入 / 库存有效期 / 取消订单 / Saga 协调器位置）需用户拍板才能定服务边界方案；当前推荐方案 A 适配 M8，但长期方向 B/C 需用户战略决策
risks: 1) X5 补偿失败需人工干预入口设计，本系统不自动重试；2) 方案 A 下真支付网关接入时 E5 网络等待会阻塞事务，需 Phase 3 验证；3) 通知服务被吸收到 order-service 中，推送量大时需后续拆出

<!-- /harness:agent-output -->
