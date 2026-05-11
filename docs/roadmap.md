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

## 7. M8' — Plugin 化（取代 M8 Java DDD 实例化）

> ⚠️ **路线变更**：原 M8（实例化 Java DDD 骨架）已超越 by [ADR-0005](adr/0005-pivot-to-plugin.md)。新目标是把已稳定的 Harness 框架封装为 **Claude Code plugin**，让任何语言栈的项目都可直接安装使用。

### 目标

把 myHarness 当前所有就位的 Harness 资产（11 节 CLAUDE.md / 15 节 engineering-practices / 6 类 hook / 8 agent / 5 命令 / 2 脚本 / MCP）打包为单一 Claude Code plugin，本地 `claude --plugin-dir` 验证通过。

### 范围

- **同仓库子目录**：新建 `plugin/`；原 `.claude/` 在迁移期共存，M8' 完成后再决策是否清空
- **单一 plugin**：通用 + Java/DDD 一体；非 Java 项目自动静默 Java 路径检查（不匹配即跳过）
- **暂不发布到公开 marketplace**：先私有 / 团队用，后续视情况

### 子任务（详见 [improvement-backlog.md §G](improvement-backlog.md)）

| 编号   | 子任务                                                                           |
| ------ | -------------------------------------------------------------------------------- |
| M8'-T1 | ADR-0005 + roadmap 改向 + backlog §G 落地（本里程碑首步，本次会话完成）          |
| M8'-T2 | 新建 `plugin/` + `.claude-plugin/plugin.json` + 复制 agents / commands / scripts |
| M8'-T3 | 重写 `plugin/hooks/hooks.json`（迁 `.claude/settings.json` hooks 段）            |
| M8'-T4 | hook 内部路径替换为 `${CLAUDE_PLUGIN_ROOT}` + smoke test 全过                    |
| M8'-T5 | CLAUDE.md 拆分：通用准则 §1-4 → skill；项目模板 §5-10 → `/harness:onboard` 命令  |
| M8'-T6 | 审计日志位置决策（plugin 私有 vs 用户项目根）                                    |
| M8'-T7 | `plugin/README.md` + 用户手册 + 安装指引                                         |
| M8'-T8 | `claude --plugin-dir ./plugin` 端到端验证（空 demo 项目 + 一个非 Java 项目）     |

### 成功标准

- [ ] 本地 `claude --plugin-dir ./plugin` 在一个**全新空目录**中跑通：
  - `/harness:audit-practices` 输出合理（按 plugin 内 rules）
  - 改 `.env` 时 pre-tool-use 黑名单生效
  - PostToolUse format hook 跑通
- [ ] hook smoke test（≥ 26 case + 新增 plugin-path 用例）全部在 plugin 路径下通过
- [ ] CLAUDE.md / README.md / AGENTS.md 中"项目性质 = Java DDD 后端实战"段落更新为"plugin 仓库"视角
- [ ] roadmap / backlog / README 一致，不留漂移

### 关键挑战

详见 [ADR-0005 §"关键挑战"](adr/0005-pivot-to-plugin.md)：

1. **CLAUDE.md 硬注入丢失**（最大挑战，T5 解决）
2. **hook 路径硬编码**（T4 解决）
3. **DDD/Java 上下文与通用 Harness 耦合**（验证阶段用非 Java demo 测）
4. **审计日志位置**（T6 待决策）
5. **MCP 凭据** `.env` 仍在用户侧维护，plugin 提供 `.env.example` 模板

### 风险

- CLAUDE.md 等价机制缺失，可能让 plugin 用户失去"硬注入硬规则"体验 — 通过 onboard 命令半自动化缓解
- hook 路径重写后破坏现有 26 case smoke test — T4 必须全过才进入 T7
- DDD/Java 上下文对非 Java 用户产生"概念噪声"（即使路径不匹配，agent 描述里仍含 Java 关键词）— 验证时用一个非 Java demo 项目实测

### 历史：原 M8 计划（已废弃 by ADR-0005，保留作历史快照）

**原目标**：真起 `pom.xml` + `src/`，让 M4-M7 建立的六维度框架在真实 Java 代码上验证。

**原子任务**：

- 起最小 Spring Boot 3 + 一个示例 BC（如 `order` 限界上下文）
- 让 5 个后端 agent（ddd-architect / spring-boot-reviewer / maven-build-doctor / schema-analyst / migration-author）各跑一遍真实任务
- M6 子目录 CLAUDE.md 落到 `domain/` / `application/` 等
- M5 周期任务挂上：每 PR 跑 docs-keeper

**废弃理由**：见 [ADR-0005 §"决定"与"替代方案 C"](adr/0005-pivot-to-plugin.md)。简言之：Harness 框架自身已完整，plugin 化的边际价值（任何项目可用）大于再加一个 Java 工程样本。后端 agent 与 §12-§14 规则**保留**为 plugin 的 Java/DDD 扩展套件。

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

| 版本 | 日期       | 变更             |
| ---- | ---------- | ---------------- |
| v0.1 | 2026-05-09 | 初稿，提议 M4-M8 |
