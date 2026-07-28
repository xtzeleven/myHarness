# Improvement Backlog — Harness 完备性 follow-up

**Date**: 2026-05-11
**Status**: 活跃跟踪（M7 后置 / M8-T0 前置阶段 / M8 主线启动前需消化）

> **本文用途**：记录已发现、暂未修的改进项。每条带优先级、工作量、修法、关联。完成一项就划掉（保留历史不删）。新发现的也追加到这里，避免遗忘。
>
> **范围**：八维度系统化分析（Agent Loop / Context Manager / LLM Call / Tool Router / Permission Gate / Hooks / Subagent / Telemetry）+ 前两轮 audit 剩余项。此处"八维度"是 [roadmap](roadmap.md) 六维度机制视角（Loop / Context / Tools / Permission / Memory / Policy）在 review 时的更细粒度展开，不是独立的第三套心智模型。
>
> **三份记录类文档分工**（时间指针不重叠）：本文 = **候选待办池**（已发现未做）；[CHANGELOG](../CHANGELOG.md) = 已发生的逐条变更；[roadmap](roadmap.md) = 未来里程碑规划。完成项移入 [archive](improvement-backlog-archive.md)。
>
> **不在此列**：M8 实例化（roadmap）、跨项目复用（M9+）。

## 优先级图例

- 🔴 **P0**：紧急 / CI 会 fail / 每会话受影响 → 立即修
- 🟡 **P1**：M8 启动前必修 → 1 周内
- 🟢 **P2**：质量改进，时机合适时修 → 4 周内
- ⚪ **P3**：可商榷 / 长期 → 不限期

---

## A. 紧急（P0）

_全部完成。详见 §E（A1+A2→E11 / A3→E6 / A4→E7）。_

---

## B. M8 启动前必修（P1）

### 八维度 gap 中的 P1

_B1–B6 全部完成。详见 §E（B1→E14 / B2→E15 / B3→E16 / B4→E35 / B5→E17 / B6→E25 weekly-audit-reminder）。_

### 前两轮 audit 剩余 P1

_B7–B10 全部完成。详见 §E（B7→E12 / B8→E8 / B9→E9 / B10→E10）。_

---

## C. 质量改进（P2）

### 八维度 gap 中的 P2

| #   | 维度            | 项                                                                                                                            | 工作量                   |
| --- | --------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| C1  | Agent Loop      | `.session.state.current_task` / `pending_steps` 维护 trigger：在 `/commit` 完成或 `/audit-practices` 跑完后写 last_checkpoint | ✅ E43                   |
| C2  | Agent Loop      | loop 步数 / 时间硬上限（防长链路失控）                                                                                        | ✅ E36                   |
| C3  | Context Manager | compaction sub-agent：上下文超 50% 时主动 spawn summarizer                                                                    | 2-3 h                    |
| C4  | Context Manager | PreToolUse hint 去重（per session）—— 同一 file_path 多次 Edit 只提示一次                                                     | ✅ E28                   |
| C5  | Context Manager | statusLine 配置：显示项目 / 分支 / 模型 / token 使用                                                                          | ✅ E37                   |
| C6  | LLM Call        | opus → sonnet 自动 fallback（当 opus API 不可用）                                                                             | ✅ E44                   |
| C7  | LLM Call        | LLM cost / token usage 度量脚本（tiktoken 估算）                                                                              | 半天                     |
| C8  | LLM Call        | prompt caching 文档化：哪些 prompt 适合 cache                                                                                 | ✅ E45                   |
| C9  | Tool Router     | Skill vs Agent 路由原则（文档化"何时用 skill / agent / 主对话"）                                                              | ✅ E38                   |
| C10 | Tool Router     | 工具失败频次自动统计（依赖 telemetry）                                                                                        | ✅ E46                   |
| C11 | Permission Gate | bypass 用量阈值告警（用 N 次后 stderr 警告）                                                                                  | ✅ E39                   |
| C12 | Hooks           | `PreCompact` hook：上下文压缩前注入"务必保留"                                                                                 | ✅ E47                   |
| C13 | Subagent        | 新 agent 引入自动验证（喂假 prompt 看主 Claude 是否路由对）                                                                   | 半天                     |
| C14 | Subagent        | agent invocation count（依赖 SubagentStop telemetry 累积）                                                                    | 已部分启用，仅缺统计入口 |
| C15 | Telemetry       | 外部观测平台接入（langfuse / honeycomb / OTLP）                                                                               | 1 天                     |
| C16 | Telemetry       | memory 增长 telemetry：决策类 vs 踩坑类增长率                                                                                 | ✅ E48                   |

### 前两轮 audit 剩余 P2

| #   | 项                                                                                | 工作量 | 修法                                                         |
| --- | --------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------ |
| C19 | Model Selection Policy 在 3 处重复（§15 / AGENTS.md 表 / agent frontmatter 注释） | ✅ E22 | 抽 `docs/policy-model-selection.md` 单点真源，其他"详见"     |
| C20 | agent 自反馈环触发靠字符串匹配（部分由 SubagentStop schema 解决）                 | —      | 与 B5 协同：schema 推广后 AGENTS.md 自反馈表改用 status 触发 |

_C17 / C18 / C21 已完成。详见 §E（C17→E18 / C18→E19 / C21→E20）。C4 / C19 本批完成（E28 / E22）。_

### M8-T6 agent 实跑发现（2026-07-25，ddd-architect + spring-boot-reviewer 双跑 order BC）

> 两个后端 agent 独立审 order BC，7/8 审查点直接通过、无阻塞项。以下 3 条为真实发现，严重度均不高，作为债务留痕。**两 agent 独立命中同一处（C22）**是最强信号。

| #   | 维度        | 项                                                                                                                                                                     | 状态                                                                                                                        |
| --- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| C22 | 事件 / 事务 | `PlaceOrderHandler` 在 `@Transactional` 内同步 `publishEvent`：当前 OrderPlaced 无消费者故无活跃 bug；引入首个监听器前须改 `@TransactionalEventListener(AFTER_COMMIT)` | ✅ 已埋警示注释（`PlaceOrderHandler.java:39` publishEvent 上方，含修法 + 双 agent 依据）；引入 listener 时落地 AFTER_COMMIT |
| C23 | DDD 建模    | `Order` 用裸 `String customerId` 引用 Customer 聚合，与 `OrderId` 自身的 typed-id 主张自相矛盾                                                                         | ⏳ Customer BC 落地时引入 `CustomerId` VO；现无 Customer BC，用 String 合理                                                 |
| C24 | 性能（低）  | `OrderPersistenceAdapter.save` 新建路径必然 `selectById==null`，热路径多一次无用 SELECT                                                                                | ⏳ 效率项非 bug；可用 MyBatis-Plus `insertOrUpdate` 或上层显式表达 new/update 意图                                          |

> 另有 d-architect 提出的"事件产生逻辑下沉到聚合根"完整方案：会改 `Order` 聚合根（触发 DDD 灰名单），当前单入口收益不明确，判为过早抽象，暂不做；待第二个创建 Order 的入口（批量导入 / 后台补单）出现时重估。

### 本批新引入的 follow-up（已落地）

_F1 / F2 同批落地，详见 §E（F1→E33 / F2→E34）。_

---

## D. 设计判断点（P3，可商榷）

| #   | 项                                                                                                                                   | 讨论方向                                                                                                    |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| D1  | `.claude/policies/` 目录化 vs 散在 .md                                                                                               | 现状散在但可读；若要可程序解析则集中化                                                                      |
| D2  | 三层 Harness vs 六维度视角并存                                                                                                       | README 加"视角注解段"；或在 ADR 写明两套视角的关系                                                          |
| D3  | ADR-0001 "L1 工程化规则（14 节）" 历史快照是否更新                                                                                   | ADR 通常不改；建议保留作为快照证据                                                                          |
| D4  | Hook 跨平台支持（PowerShell / fish 用户）                                                                                            | 当前要 bash；可在 README 声明前置要求                                                                       |
| D5  | ~~`output style` 配置（engineering-practices §11 提到可选）~~                                                                        | ✅ 已建 `.claude/output-styles/harness-traceable.md`（2026-07-25，不设默认，会话级 `/output-style` 手动切） |
| D6  | ~~worktree 引入 + audit log 跨 worktree 聚合~~                                                                                       | ✅ E41                                                                                                      |
| D7  | Auto mode 深度集成：扩 deny.yaml / ask-user.yaml 覆盖"软风险"（大量删文件 / 改 CI workflow / 改 .gitignore），让分类器之外多一层规则 | 触发条件：实际开始 daily 用 auto mode 后通过 `--by-permission-mode` 看到 auto 下放行的可疑动作              |
| D8  | ~~Hook 规则补强：Bash heredoc / `>` 重定向 / tee / sed -i 写 pom.xml 或 domain/.java 绕过 Edit/Write 拦截~~                          | ✅ E49                                                                                                      |

---

## E. 已完成（归档）

E1–E50（截至 2026-05-22）已移到独立归档文件，保留追溯不删：见 [improvement-backlog-archive.md](improvement-backlog-archive.md)。

> **归档理由**：本文是"活跃 follow-up 清单"，已完成项越堆越长会淹没未决项，也让"陌生人 30 秒读懂"更难。完成的项归档，主文件只留 A/B/C/D 活跃项。新完成的项先在此登记一行摘要，季度审视时批量并入归档。

---

## F. 维护说明

- **新发现追加到 A/B/C 末尾**，按优先级
- **完成的项移到归档文件** [improvement-backlog-archive.md](improvement-backlog-archive.md)（不删，保留追溯）；本文只留活跃项
- **季度审视**：每三个月扫一遍 P2/P3，关掉过时的
- **与 roadmap.md 不同**：roadmap 是阶段总规划；本文是阶段内 follow-up 清单
