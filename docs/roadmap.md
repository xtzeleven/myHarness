# Roadmap — 六维度 Harness 工程化路线（M4–M8）

**Status**: Proposed（待 review）
**Date**: 2026-05-09
**Audience**: 项目维护者与未来加入的协作者

> **本文回答**：M3 完成质量门禁后，"工程级 Harness"的下一步该按什么顺序补齐六维度，每步做什么，做完怎么验证。
> **本文不是 ADR**。ADR 记录已做的决策；本文是规划未来 4 个里程碑的工作。

---

## 0. 出发点：为什么需要本文

[ADR-0001](adr/0001-three-layer-harness.md) 定下三层 Harness 架构（约束 / 反馈 / 门禁），是**结构视角**。
本文换成**机制视角**，按 LLM Harness 经典抽象的六维度审视：**Loop / Context / Tools / Permission Gate / Memory / Policy**。

两套视角不冲突：三层架构是"按时间分阶段"，六维度是"按机制分类型"。

## 1. 维度现状评分

截至 M3 完成时（2026-05-09）：

| 维度                | 评分 | 关键 gap                                                                                                                                   |
| ------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Loop**            | ❌   | 无显式 agent loop 架构；sub-agent 调度临时；无重试 / 升级 / 降级策略；`/loop` skill 未利用                                                 |
| **Context Manager** | ⚠️   | CLAUDE.md 全量注入未做 token 审计；无按需注入；无压缩 / 分片；无子目录 CLAUDE.md                                                           |
| **Tools**           | ⚠️   | 工具集与 MCP 接入了；fallback / 版本锁 / 发现治理空缺                                                                                      |
| **Permission Gate** | ✅   | 黑+灰双层、文件防御、deny 列表；缺审计日志、emergency override                                                                             |
| **Memory**          | ❌   | **完全未启用** Claude Code 内置 `~/.claude/projects/<id>/memory/`；靠 CLAUDE.md / ADR / CHANGELOG 静态文档替代，无法承载用户偏好与项目踩坑 |
| **Policy**          | ⚠️   | 路由表与规则文档化了；无 model selection / fallback / escalation 机制                                                                      |

**结论**：六维度只完成 1.5 维（Permission Gate 强、Tools 中等），距离"工程级"还有 3 个里程碑。

## 2. 路线总览

```
M4 (memory) ──────► M5 (loop) ──┐
                                │
                                ▼
M6 (context) ◄───── M7 (tools+policy) ─► M8 (Java DDD 实例化)
```

依赖关系：

- **M4 必须在 M5 之前**（loop 状态需要 memory 持久化中间检查点）
- **M5 必须在 M7 之前**（policy 是 loop 的元规则）
- M6 与 M7 可并行
- M8 是六维度框架的回归测试场，应当在 M4-M7 完成后启动

预估总成本：M4 ~40min / M5 ~90min / M6 ~60min / M7 ~90min / M8 视代码规模而定。

---

## 3. M4 — Memory 启用 ⭐ 最优先

### 目标

启用 Claude Code 内置 memory 系统承载**决策原因**与**项目踩坑**两类记忆，让下次会话自动用上。

### 范围（已与用户确认）

- ✅ **决策原因**（补充 ADR）：ADR 写"决定 X"，memory 写"为什么没选 Y / 当时还考虑过什么 / 否决条件何时变化要重审"
- ✅ **项目踩坑**：jq 不可用、SQL 检测过宽、settings.local 已 tracked、hook 测试自我拦截、Windows 路径翻译等
- ❌ 不在本里程碑：用户协作偏好（推迟到 M4.5）、会话事实（M5 跟 Loop 一起）

### 子任务

| 编号  | 子任务                          | 产出                                                                                                                                                                                                                         |
| ----- | ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M4-T1 | 写 `docs/memory-conventions.md` | 定义"什么进 ADR / 什么进 memory / 什么进 CLAUDE.md"的分工矩阵                                                                                                                                                                |
| M4-T2 | 写决策原因类 memory（5 条）     | `decision_java_ddd_choice.md` / `decision_mysql_readonly_only.md` / `decision_three_layer_vs_alternatives.md` / `decision_grey_list_over_pure_block.md` / `decision_python_over_jq.md`                                       |
| M4-T3 | 写项目踩坑类 memory（6 条）     | `pitfall_jq_not_in_path.md` / `pitfall_sql_detection_overscan.md` / `pitfall_settings_local_already_tracked.md` / `pitfall_hook_self_block.md` / `pitfall_windows_path_d_drive.md` / `pitfall_format_hook_recursion_risk.md` |
| M4-T4 | 写 `MEMORY.md` 索引             | Claude Code 标准入口，每条 memory 一行                                                                                                                                                                                       |
| M4-T5 | 在 CLAUDE.md 加引用             | 让主 Claude 知道有 memory 可查                                                                                                                                                                                               |

### 成功标准

- [ ] 新会话提到"调试 hook"时主 Claude 主动想到 jq 不可用、SQL 检测误伤等先例
- [ ] ADR 与 memory 内容**明确分工**，重叠部分用"详见 ADR-NNNN"指针引用
- [ ] memory 条目命名遵循 `decision_*` / `pitfall_*` / 后续 `pref_*`（M4.5）/ `session_*`（M5）前缀
- [ ] `MEMORY.md` 索引每行 < 150 字符

### 风险与权衡

- **风险**：memory 写多了会膨胀注入成本（在 M6 解决）
- **权衡**：memory 不能完全替代 ADR——ADR 是公开决策追溯（入 git），memory 是 Claude 协作上下文（不入 git）
- **失败信号**：如果新会话主 Claude 仍然重复踩同样的坑，说明 memory 命名没让它自然路由

---

## 4. M5 — Loop 架构

### 目标

把"主对话 → 临时 spawn agent → 汇合"的隐式模式，升级为显式架构：调度规则、重试策略、自反馈环、周期任务。

### 子任务

| 编号  | 子任务                         | 产出                                                                                                                        |
| ----- | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| M5-T1 | 写 `docs/loop-architecture.md` | 主对话与 sub-agent 关系图、生命周期、终止条件                                                                               |
| M5-T2 | 定义调度规则                   | "并行 vs 串行 vs 汇合" 决策树；如：`code-reviewer` + `spring-boot-reviewer` 并行，`ddd-architect` → `migration-author` 串行 |
| M5-T3 | 定义三类策略                   | retry（瞬时失败重试）/ escalation（sonnet → opus / agent → 用户）/ degradation（gitnexus 不可用 → grep）                    |
| M5-T4 | 设计周期任务                   | 用 `/loop` skill：每日 `/audit-practices`、每 PR 后 `/sync-docs`、每周 docs-keeper 全量扫                                   |
| M5-T5 | 自反馈环                       | docs-keeper 检查 ddd-architect 输出文档化；audit-practices 检查自身规则的执行；让 agent 互相审核                            |
| M5-T6 | 在 settings.json 注册周期 hook | SessionStart hook 注入"上次会话未完事项"（从 memory 读）                                                                    |

### 成功标准

- [ ] 长任务能从中断点恢复（如 audit-practices 跑到一半 hook 阻塞，重启时从 memory 读检查点续跑）
- [ ] sub-agent 调度有路径化记录（不是每次主对话临时决定）
- [ ] `/loop` skill 至少配 2 个真实周期任务
- [ ] 每个 agent 的 frontmatter 加 `escalation:` 字段（升级到谁）

### 风险与权衡

- **风险**：过度设计 loop 反而让简单任务变复杂；要保持"简单任务直接做"的逃生通道
- **权衡**：自反馈环加深质量但增成本；先在关键 agent（ddd-architect）启用，不全开

---

## 5. M6 — Context 治理

### 目标

审计 token 成本；建立按需注入；CLAUDE.md 子目录化。

### 子任务

| 编号  | 子任务            | 产出                                                                                                             |
| ----- | ----------------- | ---------------------------------------------------------------------------------------------------------------- |
| M6-T1 | 写 token 审计脚本 | `.claude/scripts/audit-context-cost.py`：算 CLAUDE.md + rules + AGENTS 三件套的 token 数（用 tiktoken）          |
| M6-T2 | 子目录 CLAUDE.md  | M8 实例化代码后，按 DDD 层拆：`src/main/java/<base>/domain/CLAUDE.md`（领域纯净规则）等                          |
| M6-T3 | 按需注入提示      | hook 检测到 "正在改 pom.xml" → stderr 提示 "考虑读 maven-build-doctor 规则"；主 Claude 看到 stderr 主动 prefetch |
| M6-T4 | 上下文压缩策略    | 长会话超过窗口阈值时，用 sub-agent 总结历史（agent 比主对话便宜）                                                |

### 成功标准

- [ ] M3→M6 后，每会话注入 token 减少 ≥ 30%（具体数 M6-T1 跑完才知）
- [ ] 主 Claude 在 Maven 问题上自动 prefetch maven-build-doctor 提示
- [ ] 子目录 CLAUDE.md 与根 CLAUDE.md 不重复（"我说过的不再说一遍"）

### 风险与权衡

- **风险**：按需注入靠 hook 提示词不可强制，主 Claude 可能忽略；接受 best-effort
- **权衡**：子目录 CLAUDE.md 让规则更聚焦但增加维护点；只在确有差异时拆

### 依赖

- M8 实例化代码后才有"子目录"可拆；T1/T3/T4 可在 M5 完成后立刻做

---

## 6. M7 — Tools 治理 + Policy 机制化

### 目标

锁工具版本；设计 fallback chain；写 model selection / escalation policy；hook 加审计日志。

### 子任务

| 编号  | 子任务                              | 产出                                                                                                                   |
| ----- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| M7-T1 | 锁工具版本                          | `package.json` 锁 prettier@3 / `pom.xml` 锁 maven-compiler-plugin / `.tool-versions`（asdf 风格）                      |
| M7-T2 | Fallback chain                      | `docs/tools-fallback.md`：gitnexus → grep → manual；MySQL MCP → schema dump 文件；prettier → 跳过                      |
| M7-T3 | Model selection policy              | AGENTS.md 加 "model 选择"章：opus（战略 / 长链路设计） / sonnet（默认） / haiku（轻量改写）；每 agent frontmatter 显式 |
| M7-T4 | Hook 审计日志                       | hook 把拦截事件写到 `.claude/.audit.log`（已 .gitignore），格式 JSONL：`{ts, hook, tool, target, action, reason}`      |
| M7-T5 | Emergency override                  | `HARNESS_BYPASS=1` 环境变量下 hook 放行但**强制写审计**；用于紧急情况，不可常用                                        |
| M7-T6 | engineering-practices §15 Policy 章 | 把 policy 文档化：何时升 opus、何时降级、何时拒绝继续                                                                  |

### 成功标准

- [ ] CI 与本地工具版本一致（`prettier@3.x.y` 完全一致）
- [ ] 审计日志可回放：从 `.claude/.audit.log` 能重建一次会话的所有 hook 拦截
- [ ] `HARNESS_BYPASS=1` 时 hook 不拦但日志加 `reason: bypass` 标记
- [ ] 每个 agent 的 model 选择有"为什么用这个"的依据

### 风险与权衡

- **风险**：emergency override 被滥用；用 stderr 红色警告 + 强制审计 + 文档化"何时合规使用" 三道弱约束
- **权衡**：审计日志是"可观测性"；不强制启用（默认开），用户嫌烦可在 settings.json 关

---

## 7. M8 — 实例化 Java DDD 骨架（六维度回归测试场）

> **载体决策**：参见 [ADR-0002](adr/0002-java-ddd-backend.md)。Java/Spring/Maven/DDD 栈最容易踩坑（Lombok / `@Transactional` / N+1 / 循环依赖），在最容易出错的栈上验证 Harness 有效性最具说服力。

> **产研全链路扩张**：参见 [ADR-0008](adr/0008-process-capability-expansion.md)。M8-T1~T8 主线之前 / 之中嵌入 4 个 Tier 的产研流程性能力（Tier 1 先做：需求拆解+AC / 事件风暴+服务划分 / 跨阶段一致性检查），首发实战对象 = M8 本身 + myHarness 自身。

### M8-T0 — 前置阶段（产研流程性能力）

按 [ADR-0008](adr/0008-process-capability-expansion.md) Tier 1，M8 主线启动前先落地 3 个语言/技术栈无关的流程性资产，并以 M8 计划本身作为首发实战对象：

| 编号   | 子任务                                                                               | 产物                                       |
| ------ | ------------------------------------------------------------------------------------ | ------------------------------------------ |
| M8-T0a | 建 `requirement-decomposer` agent（覆盖需求拆解 + 验收标准 AC 生成）                 | `.claude/agents/requirement-decomposer.md` |
| M8-T0b | 用 T0a 拆 M8-T1~T8 章节为 INVEST 子任务 + Gherkin AC                                 | `docs/m8-decomposition.md`                 |
| M8-T0c | 建 `event-storm` agent（去 DDD 化的轻量事件风暴 + 服务边界候选）                     | `.claude/agents/event-storm.md`            |
| M8-T0d | 用 T0c 对 M8-T0b 拆解结果做事件风暴                                                  | `docs/m8-event-storm.md`                   |
| M8-T0e | 建 `/cross-stage-check` command（产研全链路漂移检查）                                | `.claude/commands/cross-stage-check.md`    |
| M8-T0f | 用 T0e 扫 myHarness 自身：roadmap ↔ ADR ↔ CHANGELOG ↔ MEMORY.md ↔ AGENTS.md 漂移 | 漂移清单（命令运行时输出，不固化文档）     |

**M8-T0 成功标准**：

- [ ] 3 个 Tier 1 资产 frontmatter 含 `model:` 与触发场景
- [ ] T0b / T0d 两份产物质量 ≥ 本文 §7 现有 M8 章节
- [ ] T0f 漂移清单为空或漂移已修；漂移检测能识别本节自身落地后的状态
- [ ] `/audit-practices` 跑分不退化

**Tier 2/3/4 嵌入说明**：Tier 2（测试用例生成 + 改动分析增强 + code review 增强）随 M8-T3 完成后启动；Tier 3（release notes + ADR 草稿 + 文档同步增强）随 M8-T8 完成后启动；Tier 4 按触发条件随时启动。详见 [ADR-0008](adr/0008-process-capability-expansion.md) §决定·2。

### 目标

真起 `pom.xml` + `src/`，让 M4-M7 建立的六维度框架在真实 Java 代码上跑一遍，把"框架就位"升级为"框架在真实工程中证明可用"。

### 范围

- 最小 Spring Boot 3 项目 + 一个示例限界上下文（拟用 `order` 作为 BC）
- DDD 战略分层落地：`interfaces / application / domain / infrastructure` 严格单向依赖
- 5 个后端 agent（`ddd-architect` / `spring-boot-reviewer` / `maven-build-doctor` / `schema-analyst` / `migration-author`）各跑一遍真实任务
- M6 子目录 CLAUDE.md 落到 `domain/` / `application/` 等关键层
- M5 周期任务挂上：每 PR 跑 `docs-keeper`

### 子任务

| 编号  | 子任务                                                                                                |
| ----- | ----------------------------------------------------------------------------------------------------- |
| M8-T1 | `pom.xml` + 基础结构（Spring Boot 3 / Java 17+ / Maven Wrapper）                                      |
| M8-T2 | 落地 DDD 四层目录骨架 `src/main/java/<base>/{interfaces,application,domain,infrastructure}/`          |
| M8-T3 | 第一个 BC（`order`）的最小聚合：聚合根 + 值对象 + Repository 接口（domain）+ Repository 实现（infra） |
| M8-T4 | interfaces 层最小 Controller + application 层 CommandHandler（接收 DTO，调 domain，调 Repository）    |
| M8-T5 | Flyway/Liquibase migration + 与 schema-analyst / migration-author 联调                                |
| M8-T6 | 5 个后端 agent 各跑一遍真实任务，记录效果与漏检                                                       |
| M8-T7 | M6 子目录 CLAUDE.md：`domain/CLAUDE.md`（聚合规则）+ `application/CLAUDE.md`（事务/编排规则）         |
| M8-T8 | `docs-keeper` 接入 CI（PR-level 自动跑）                                                              |

### 成功标准

- [ ] `mvn verify` 在干净仓库上全过（单测 + 集成测 + 静态检查）
- [ ] PreToolUse 灰名单在 `domain/` 改动上**真的拦下**并要求人工授权（覆盖 ADR-0001 灰名单设计）
- [ ] 5 个后端 agent 各被实际任务激活至少一次，输出可执行建议
- [ ] M6 子目录 CLAUDE.md 在编辑相应层时**自动注入**生效
- [ ] gitnexus 索引建立完成，调用链 / 影响面查询可用

### 关键挑战

1. **DDD 边界自动检测的准确率**：灰名单当前只识别路径前缀（`domain/`），改动是否真的"破坏边界"需要 agent 二次判断
2. **Lombok / `@Transactional` 隐式行为**：spring-boot-reviewer 能否识别常见反模式（事务传播失效 / setter 注入 / 异常吞噬）
3. **MCP schema 与代码 Entity 漂移**：schema-analyst 走只读 MySQL MCP 查实际表结构 vs JPA Entity 注解，漂移如何呈现
4. **测试覆盖度不足以触发的边界**：需要在示例代码里**故意**埋一些反模式，验证各 agent 是否发现

### 风险

- pom 依赖冲突导致首日编译不过 — `maven-build-doctor` 先行体检
- DDD 教科书化 over-engineering — 严守"最小一个 BC"，不为了演示而堆叠
- 后端 agent 在没有真实代码时只能空跑，验证不充分 — T6 必须建立在 T3-T5 完成的真实代码之上

---

## 8. 关键决策点（待用户确认）

| #   | 决策点                                   | 当前倾向                                                                                     |
| --- | ---------------------------------------- | -------------------------------------------------------------------------------------------- |
| D1  | M4 memory 写多少条？                     | **决策类 5 条 + 踩坑类 6 条**起步，后续按 session 自然增长                                   |
| D2  | M5 周期任务用 `/loop` skill 还是 cron？  | **`/loop` skill**（在 Claude Code 会话内）+ GitHub Actions 定时 workflow（仓库级）           |
| D3  | M6 子目录 CLAUDE.md 多深？               | M8 实例化后再决定；**默认两层**（src/main/java/<base>/domain/CLAUDE.md），不再深入到聚合粒度 |
| D4  | M7 audit log 是否提交 git？              | **不提交**（已 .gitignore，含会话敏感信息）                                                  |
| D5  | M7 emergency bypass 是否对生产 PR 有效？ | **CI 检测到 `HARNESS_BYPASS=1` 的 commit message 直接 fail**（本地可用，远端不可用）         |

## 9. 不在本路线的事项

明确**不做**的，避免范围蔓延：

- 多语言 Harness（Python / Go / Rust）—— 留给后续项目
- 跨项目 Harness 模板提取 —— M8 之后再考虑
- 本地 LLM / 离线 Claude —— 不在 Claude Code 假设内
- agent 商店 / 跨团队共享 agent —— 单项目先稳住

---

## 10. 修订记录

| 版本 | 日期       | 变更                                                          |
| ---- | ---------- | ------------------------------------------------------------- |
| v0.1 | 2026-05-09 | 初稿，提议 M4-M8                                              |
| v0.2 | 2026-05-12 | M4-M7 逐步完成；曾短暂 pivot 到 plugin（ADR-0005/0006）       |
| v0.3 | 2026-05-19 | 撤回 plugin pivot（ADR-0007），恢复 M8 Java DDD 路线；M7 完成 |
