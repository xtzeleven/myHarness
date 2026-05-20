# ADR 0008 — 产研全链路 Harness 能力扩张

**Status**: Accepted
**Date**: 2026-05-20
**Stage**: 能力维度扩张（不动 M8 主线）
**Relates to**: [ADR-0002](0002-java-ddd-backend.md), [ADR-0007](0007-revoke-plugin-pivot.md)

## 背景

myHarness 在 M7 完成后进入"M8 启动前清账"阶段（CHANGELOG `[Unreleased]`），P0/P1 全清。此时项目主导者提出**通用产研流程性能力**诉求，原始列举 10 项：需求拆解、头脑风暴、事件风暴、能力中心 / 服务划分、全链路 trace、改动项分析、安全分析、性能分析、code review、变更文档自动更新。

经全链路对照（详见本 ADR §决定·1），原 10 项**覆盖产研流程约 70%**，但缺以下关键环节：

- **验收标准（AC）生成**：拆解只到任务级，AC 是质量门槛源头，缺失会让 code review 没参照、测试用例靠猜
- **API / 接口契约设计**：服务划分后的必然产物，是后续 trace / review 的基线
- **测试用例生成（从 AC 反推）**：已有 `tdd-cycle-driver` 只管红绿循环，"该写哪些测试"是前期空白
- **release notes / CHANGELOG 自动生成**：发布阶段的变更入账，myHarness 自身已有实操经验可抽象
- **事故复盘（post-mortem）协作**：闭环到 memory pitfall\_\* 系统
- **跨阶段一致性检查**：元能力，扫需求 ↔ 设计 ↔ 代码 ↔ 测试 ↔ 发布产物漂移

补全后共 **16 项能力**，覆盖度 ~95%。

现状盘点：约 **60% 能力已有零件**（planning-with-files / TaskCreate / ddd-architect / gitnexus-\_ / security-review / code-reviewer / docs-keeper / sync-docs / spring-boot-reviewer / tdd-cycle-driver），但事件风暴 / 服务划分 / 性能分析强绑 Java / DDD，需求拆解只到任务级，跨阶段一致性是空白。

直接扩张该方向不冲突已有架构，但需规避两类历史教训：

1. [ADR-0007](0007-revoke-plugin-pivot.md) 撤销 plugin 化的核心原因之一是 **"agent 没有实战载体就是空跑，无法验证有效性"**
2. ADR-0007 明确否决"双线维护"，警示**注意力分散**

## 决定

### 1. 全链路能力地图（16 项）

| 阶段   | 编号 | 能力                       | 状态                                         |
| ------ | ---- | -------------------------- | -------------------------------------------- |
| 需求   | #1   | 需求拆解                   | 已有 planning-with-files skill，需正式 agent |
|        | A    | 验收标准（AC）生成         | 🆕                                           |
|        | B    | 优先级排序（RICE/MoSCoW）  | 🆕                                           |
|        | #2   | 头脑风暴                   | 0 起点                                       |
| 设计   | #3   | 事件风暴                   | ddd-architect 已有，需去 DDD 化轻量版        |
|        | #4   | 能力中心 / 服务划分        | ddd-architect 已有，需去 BC 强绑             |
|        | C    | API / 接口契约设计         | 🆕                                           |
|        | D    | ADR 草稿生成               | 🆕 (myHarness 自身已有 8 ADR 实操可抽象)     |
| 开发   | E    | 测试用例生成（从 AC 反推） | 🆕 (衔接已有 tdd-cycle-driver)               |
|        | #6   | 改动项分析                 | gitnexus-impact-analysis 已有                |
|        | #9   | code review                | code-reviewer / spring-boot-reviewer 已有    |
| 质量   | #7   | 安全分析                   | security-review command 已有                 |
|        | #8   | 性能分析                   | spring-boot-reviewer 偏 Spring，需通用版     |
|        | #5   | 全链路 trace               | gitnexus-exploring 已有                      |
| 发布   | #10  | 变更文档同步               | sync-docs / docs-keeper 已有                 |
|        | F    | release notes 生成         | 🆕                                           |
|        | G    | 事故复盘协作               | 🆕                                           |
| 元能力 | H    | 跨阶段一致性检查           | 🆕 (sync-docs 的产研全链路扩展版)            |

### 2. 分批策略（4 个 Tier）

| Tier                      | 能力                                                                                     | 首发实战                                                                                       | 触发条件     |
| ------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------ |
| **Tier 1**（本 ADR 落地） | #1 拆解 + A AC 生成（合一）<br>#3 事件风暴 + #4 服务划分（合一）<br>H 跨阶段一致性检查   | 拆 M8 计划 + 事件风暴 M8 子任务 + 用 myHarness 自身做 H 首发（needs ↔ ADR ↔ CHANGELOG 漂移） | 立即         |
| Tier 2                    | E 测试用例生成 + #6 改动分析 + #9 code review 增强                                       | M8 第一个聚合落地后                                                                            | M8-T3 完成后 |
| Tier 3                    | F release notes + D ADR 草稿 + #10 文档同步增强                                          | M8 第一次发布后                                                                                | M8-T8 完成后 |
| Tier 4                    | #2 头脑风暴 / #7 安全增强 / #8 通用性能 / #5 业务 trace / G 复盘 / B 优先级 / C API 契约 | 真实场景触发再做                                                                               | 见下表       |

### 3. Tier 1 首批落地（3 agent 单元 / 5 项能力）

本 ADR 范围内**仅落地 Tier 1**，后续会话起手：

| 资产                     | 类型    | 覆盖能力 | 首发实战对象                                                                                    |
| ------------------------ | ------- | -------- | ----------------------------------------------------------------------------------------------- |
| `requirement-decomposer` | agent   | #1 + A   | 拆 M8 章节为 INVEST 子任务 + 每条配 Gherkin AC，产物 `docs/m8-decomposition.md`                 |
| `event-storm`            | agent   | #3 + #4  | 对 M8 拆解后的子任务做事件风暴，输出时间线 + 角色 + 服务边界候选，产物 `docs/m8-event-storm.md` |
| `/cross-stage-check`     | command | H        | 扫 myHarness 自身：roadmap ↔ ADR ↔ CHANGELOG ↔ MEMORY.md ↔ AGENTS.md 漂移，输出漂移清单     |

### 4. 边界约束（强制，对所有 Tier 1-4 适用）

- **语言 / 技术栈无关**：agent frontmatter 与正文**禁止** import Java / Spring / DDD 术语作为前提；DDD / Spring 视角作为"可选输出维度"
- **实战载体不空跑**：每个新 agent 引入后必须在 M8 计划或 myHarness 自身上跑过 ≥ 1 次，产出文档化
- **首发对象绑实物**：Tier 1 首发对象明确（见 §决定·3），后续 Tier 启动时需在 ADR 增补条目中明确首发对象
- **失败回退**：任一 Tier 首批 agent 首次实战若"产出 < 主对话直接做"，本 ADR 触发重审

### 5. Tier 4 触发条件

| 能力              | 触发条件                                                    |
| ----------------- | ----------------------------------------------------------- |
| #2 头脑风暴 agent | 真有"开放性设计需扩散"场景出现                              |
| #7 通用安全分析   | security-review command 在 M8 真实代码上跑过后明确缺口      |
| #8 通用性能分析   | spring-boot-reviewer 在 M8 实战后明确证明 Java 之外覆盖不足 |
| #5 业务流 trace   | gitnexus 索引建立 + 调用链查询稳定后，且有跨服务业务场景    |
| G 事故复盘协作    | 第一次出真实 bug 需复盘时                                   |
| B 优先级排序      | 需求拆解输出 ≥ 10 条且需排序时                              |
| C API 契约设计    | Tier 2 完成 + 第一个对外接口出现时                          |

### 6. 与 M8 主线的关系

- ✅ M8 主线（T1-T8）范围不变，[ADR-0002](0002-java-ddd-backend.md) 不撤
- ✅ Tier 1 命名为 **M8-T0 前置阶段**（roadmap §7 后续会话加段）；Tier 2/3 嵌入 M8 中后期；Tier 4 独立于 M8 按需触发
- ❌ 不撤已有 8 agent / 6 command 中任何一个
- ❌ 不动 engineering-practices.md §12（DDD 分层）/ §13（Java / Spring 风格）
- ❌ 不增加 PreToolUse 灰名单（流程性能力不涉及破坏性操作）

### 7. 文档同步范围（不在本 ADR 内执行）

后续会话落地：

- `docs/roadmap.md` §7 M8 章节加 T0 段 + Tier 2/3 嵌入说明
- `CLAUDE.md` §5 项目上下文加一行（产研全链路 + M8 主线并存）
- `AGENTS.md` 加 Tier 1 资产索引
- 长期：每 Tier 启动时增补本 ADR 的"已落地"标记

本 ADR 仅做决策记录，文件改动在下一会话起手。

## 替代方案与权衡

| 候选                                               | 否决原因                                                                                                                                          |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **路 A**：完全转通用 Harness，搁置 M8              | 重蹈 [ADR-0007](0007-revoke-plugin-pivot.md) 覆辙——agent 没真实产物可跑就是空跑；myHarness 自身工程化已收敛，自审边际收益归零，必须有外部实战载体 |
| **路 B**：M8 + 流程 Harness 双线并行（不绑 M8-T0） | ADR-0007 已明确否决"双线维护"；流程 agent 与 M8 解耦后会失去实战触发点，回到路 A 的空跑问题                                                       |
| **另起姊妹项目（如 myHarness-flow）**              | 增加跨仓库治理成本（README / CI / agent 同步）；流程能力天然依附"被流程化的项目"，独立仓库找不到对象                                              |
| **不做，等 M8 完成后再说**                         | 流程能力是真实诉求，60% 零件已就位不利用造成沉没成本；M8 启动本身就需要需求拆解 / 事件风暴，正好实战                                              |
| **一次铺开 16 项能力**                             | 注意力分散风险（ADR-0007 教训），且部分能力（如 C API 契约 / E 测试用例）依赖 M8 落地后才有对象                                                   |
| **仅做最初 3 个（拆解 / 事件风暴 / 改动分析）**    | 覆盖度不足，缺元能力 H 则 16 项能力之间无法形成闭环；AC 生成是质量门槛源头，不补则 review / 测试无锚点                                            |

## 后果

**能力面**：

- Tier 1 落地后即覆盖产研流程 5 项能力（含 1 项元能力）：需求侧（拆解 + AC）、设计侧（事件风暴 + 服务划分）、跨阶段一致性
- 长期常驻 3 个 Tier 1 资产（2 agents + 1 command），可独立于 M8 用于任何项目场景
- M8 启动质量提升：拆解 + AC + 事件风暴产物比 roadmap §7 当前 M8 章节更细，T1-T8 执行不确定性下降
- 元能力 H 让 myHarness 首次具备"产研全链路漂移检测"，超越单点 sync-docs 命令

**维护成本**：

- agent 总数从 8 → 10、command 从 6 → 7；AGENTS.md / engineering-practices §5（Agents）需 1 次同步更新
- 引入"流程 agent 不能空跑"的隐性约束，未来每加一个流程 agent 都需配首次实战
- 文档负担：M8-T0 在 roadmap / CLAUDE.md / AGENTS.md 三处需保持一致；漂移由元能力 H 例行兜底（产研内闭环）

**信息边界**：

- 本 ADR 不预承诺 Tier 2/3/4 任何资产；触发条件机制化，避免范围蔓延
- 若 Tier 1 首次实战不达标，本 ADR 触发重审——不视为失败决策，视为"在最小代价下验证假设"

**与 ADR-0007 的关系**：

- 本 ADR 不撤 / 不超越 ADR-0007；两者**正交**：ADR-0007 解决"形态分发"问题（不做 plugin 包），本 ADR 解决"能力维度"问题（扩产研全链路）
- 共享原则：实战载体强制、双线维护警惕、ADR 不可变追溯

## 何时重审

触发本 ADR 重审的信号（任一即可）：

1. Tier 1 任一 agent 首次实战产出质量 < 主对话直接做
2. M8-T1~T8 启动后明显进度下滑，且能归因到"注意力分散到流程 agent 上"
3. Tier 4 触发条件被频繁满足却未及时跟进（说明分批过严）
4. 出现新的形态需求（如再次有 plugin 化诉求），需同步检视本 ADR 与 ADR-0007 是否仍一致
5. 跨阶段一致性检查（H）发现 ADR / roadmap / CHANGELOG / MEMORY 漂移频繁，说明文档治理机制需重新设计

## 相关

- [ADR-0002](0002-java-ddd-backend.md) — M8 Java DDD 实战载体（不变）
- [ADR-0007](0007-revoke-plugin-pivot.md) — 撤销 plugin 化（教训来源：空跑 / 双线维护）
- [roadmap.md §7](../roadmap.md) — M8 章节（下一会话加 T0 段 + Tier 2/3 嵌入说明）
- [AGENTS.md](../../AGENTS.md) — 下一会话加 Tier 1 资产索引
- [CLAUDE.md §5](../../CLAUDE.md) — 下一会话加"产研全链路 + M8 主线并存"一行
