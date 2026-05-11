# Improvement Backlog — Harness 完备性 follow-up

**Date**: 2026-05-11
**Status**: 活跃跟踪（M7 后置 / M8 启动前需消化）

> **本文用途**：记录已发现、暂未修的改进项。每条带优先级、工作量、修法、关联。完成一项就划掉（保留历史不删）。新发现的也追加到这里，避免遗忘。
>
> **范围**：八维度系统化分析（Agent Loop / Context Manager / LLM Call / Tool Router / Permission Gate / Hooks / Subagent / Telemetry）+ 前两轮 audit 剩余项。
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

| #   | 维度            | 项                                                                                          | 工作量 | 关联                                  |
| --- | --------------- | ------------------------------------------------------------------------------------------- | ------ | ------------------------------------- |
| B4  | Context Manager | `audit-context-cost.py` 加每会话 token baseline 入 audit log（每周 GH Actions 跑）          | 1 h    | 长期追踪 context 膨胀                 |
| B6  | Telemetry       | scheduled.yml 加每周 audit log 摘要 issue（自动 open issue 附 `audit-log-summary.py` 输出） | 30 min | 让 telemetry "活"起来，不只是本地能查 |

_B1 / B2 / B3 / B5 已完成。详见 §E（B1→E14 / B2→E15 / B3→E16 / B5→E17）。_

### 前两轮 audit 剩余 P1

_B7–B10 全部完成。详见 §E（B7→E12 / B8→E8 / B9→E9 / B10→E10）。_

---

## C. 质量改进（P2）

### 八维度 gap 中的 P2

| #   | 维度            | 项                                                                                                                            | 工作量                         |
| --- | --------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| C1  | Agent Loop      | `.session.state.current_task` / `pending_steps` 维护 trigger：在 `/commit` 完成或 `/audit-practices` 跑完后写 last_checkpoint | 1 h                            |
| C2  | Agent Loop      | loop 步数 / 时间硬上限（防长链路失控）                                                                                        | 30 min（仅文档）               |
| C3  | Context Manager | compaction sub-agent：上下文超 50% 时主动 spawn summarizer                                                                    | 2-3 h                          |
| C4  | Context Manager | PreToolUse hint 去重（per session）—— 同一 file_path 多次 Edit 只提示一次                                                     | 1 h                            |
| C5  | Context Manager | statusLine 配置：显示项目 / 分支 / 模型 / token 使用                                                                          | 30 min                         |
| C6  | LLM Call        | opus → sonnet 自动 fallback（当 opus API 不可用）                                                                             | 1 h（仅文档约定，hook 内不动） |
| C7  | LLM Call        | LLM cost / token usage 度量脚本（tiktoken 估算）                                                                              | 半天                           |
| C8  | LLM Call        | prompt caching 文档化：哪些 prompt 适合 cache                                                                                 | 1 h                            |
| C9  | Tool Router     | Skill vs Agent 路由原则（文档化"何时用 skill / agent / 主对话"）                                                              | 30 min                         |
| C10 | Tool Router     | 工具失败频次自动统计（依赖 telemetry）                                                                                        | 1 h                            |
| C11 | Permission Gate | bypass 用量阈值告警（用 N 次后 stderr 警告）                                                                                  | 30 min                         |
| C12 | Hooks           | `PreCompact` hook：上下文压缩前注入"务必保留"                                                                                 | 1 h                            |
| C13 | Subagent        | 新 agent 引入自动验证（喂假 prompt 看主 Claude 是否路由对）                                                                   | 半天                           |
| C14 | Subagent        | agent invocation count（依赖 SubagentStop telemetry 累积）                                                                    | 已部分启用，仅缺统计入口       |
| C15 | Telemetry       | 外部观测平台接入（langfuse / honeycomb / OTLP）                                                                               | 1 天                           |
| C16 | Telemetry       | memory 增长 telemetry：决策类 vs 踩坑类增长率                                                                                 | 1 h                            |

### 前两轮 audit 剩余 P2

| #   | 项                                                                                | 工作量 | 修法                                                         |
| --- | --------------------------------------------------------------------------------- | ------ | ------------------------------------------------------------ |
| C19 | Model Selection Policy 在 3 处重复（§15 / AGENTS.md 表 / agent frontmatter 注释） | 30 min | 抽 `docs/policy-model-selection.md` 单点真源，其他"详见"     |
| C20 | agent 自反馈环触发靠字符串匹配（部分由 SubagentStop schema 解决）                 | —      | 与 B5 协同：schema 推广后 AGENTS.md 自反馈表改用 status 触发 |

_C17 / C18 / C21 已完成。详见 §E（C17→E18 / C18→E19 / C21→E20）。_

---

## D. 设计判断点（P3，可商榷）

| #   | 项                                                        | 讨论方向                                           |
| --- | --------------------------------------------------------- | -------------------------------------------------- |
| D1  | `.claude/policies/` 目录化 vs 散在 .md                    | 现状散在但可读；若要可程序解析则集中化             |
| D2  | 三层 Harness vs 六维度视角并存                            | README 加"视角注解段"；或在 ADR 写明两套视角的关系 |
| D3  | ADR-0001 "L1 工程化规则（14 节）" 历史快照是否更新        | ADR 通常不改；建议保留作为快照证据                 |
| D4  | Hook 跨平台支持（PowerShell / fish 用户）                 | 当前要 bash；可在 README 声明前置要求              |
| D5  | `output style` 配置（engineering-practices §11 提到可选） | 是否要项目专属 output style？未必必要              |

---

## E. 已完成（参考 / 不删，保留追溯）

| #   | 项                                                                                                  | 完成 commit |
| --- | --------------------------------------------------------------------------------------------------- | ----------- |
| E1  | Top 3 #1: README 漂移修复                                                                           | c067ee2     |
| E2  | Top 3 #2: `.bypass-once` 废弃 ADR-0004 + engineering-practices §15 声明                             | c067ee2     |
| E3  | Top 3 #3: hook 自动化测试（26 case smoke test）+ CI 集成                                            | c067ee2     |
| E4  | 八维度 #1: SubagentStop hook + agent output schema                                                  | b63538a     |
| E5  | 八维度 #2: PostToolUse audit log + audit-log-summary 聚合（--by-hook/tool/action/agent/ext/day）    | b63538a     |
| E6  | A3: CLAUDE.md "M3 阶段" / "14 维度" → "M7 完成" / "15 维度"                                         | b63538a     |
| E7  | A4: CHANGELOG.md [Unreleased] 段补全（八维度 + ADR-0004 + smoke test 全部入账）                     | b63538a     |
| E8  | B8: onboard.md "M0-M5" → "M0-M8"                                                                    | 2ab8383     |
| E9  | B9: commit.md:107 "永不在 main 实验性提交" 软化为承认当前单人项目现状                               | 2ab8383     |
| E10 | B10: AGENTS.backend.md "6 个后端 agent" → "5 个" + 列表正确                                         | 2ab8383     |
| E11 | A1+A2 扩面：7 个 hook 全部 git mode 100755（4 老 hook + UserPromptSubmit + 2 测试）                 | 本批 commit |
| E12 | B7: lint.yml + scheduled.yml 必需文件清单去重 → 抽 `.github/required-files.txt` 单点真源            | 本批 commit |
| E13 | engineering-practices.md:351 "M3 阶段" 残留 → "M7 完成 / M8 待启动"                                 | 本批 commit |
| E14 | B1: UserPromptSubmit hook 拦截敏感词（`.claude/hooks/user-prompt-submit.sh` 13 个高危模式 + 测试）  | 前批 commit |
| E15 | B2: PostToolUse 事后秘钥检测（`format.sh:109-200` 9 类秘钥模式 + 跳过列表 + 红色 stderr + 测试）    | 前批 commit |
| E16 | B3: `docs/mcp-onboarding.md` 完整 8 章节（5 步流程 / 分类 / 安全清单 / 反模式 / 范例）              | 前批 commit |
| E17 | B5: 3 个 agent 加 schema 范例（ddd-architect / spring-boot-reviewer / schema-analyst 4 状态全覆盖） | 前批 commit |
| E18 | C17: engineering-practices §0 阅读顺序加"6. 元规则：第 15 节"                                       | 本批 commit |
| E19 | C18: `.gitignore` 加 `.claude/.audit.log` 显式行（与 `.session*` 风格一致）                         | 本批 commit |
| E20 | C21: memory-conventions.md `pref_*` / `session_*` 注解 "M4.5/M5 启用" → "按需启用，暂未推进"        | 本批 commit |
| EG1 | G1-G5 + G10/G11: plugin/ 骨架（manifest + agents/commands/scripts/hooks/rules/.mcp.json + README）  | 前批 commit |
| EG6 | G6: pre-tool-use hint 6 处去掉 .claude/agents/ 硬路径，改语义化；plugin smoke 63 case 全过          | 前批 commit |
| EG7 | G7: audit log 位置决策 — 保留用户项目根 `.claude/.audit.log`（与 standalone Claude Code 生态一致）  | 本批 commit |

---

## G. M8' Plugin 化任务清单（M7 后置 / 战略转向）

**Date**: 2026-05-11
**Driver**: [ADR-0005](adr/0005-pivot-to-plugin.md)

> 本节是 [roadmap.md §7](roadmap.md) M8' Plugin 化的细化任务。完成项移到 §E，命名 `EG*`（如 EG1 = 完成 G1）。

| #   | 项                                                                                                      | 工作量 | 关联 / 备注                             |
| --- | ------------------------------------------------------------------------------------------------------- | ------ | --------------------------------------- |
| G1  | 起 `plugin/` 目录骨架 + `plugin/.claude-plugin/plugin.json`（name / version / description / author）    | 30 min | ✅ EG1                                  |
| G2  | 复制 `.claude/agents/*` → `plugin/agents/*`（8 个）                                                     | 10 min | ✅ EG1                                  |
| G3  | 复制 `.claude/commands/*` → `plugin/commands/*`（5 个）                                                 | 10 min | ✅ EG1                                  |
| G4  | 复制 `.claude/scripts/*` → `plugin/scripts/`（或挂 `plugin/bin/`）                                      | 10 min | ✅ EG1（位置选 scripts/）               |
| G5  | 写 `plugin/hooks/hooks.json`（迁 `.claude/settings.json` hooks 段，格式与 settings.json 兼容）          | 30 min | ✅ EG1                                  |
| G6  | hook 内部路径替换为 `${CLAUDE_PLUGIN_ROOT}/...` + smoke test 全过                                       | 1-2 h  | ✅ EG6                                  |
| G7  | 决策审计日志位置：plugin 私有 vs 用户项目根 vs 用户 `~/.harness/`                                       | 30 min | ✅ EG7（保留用户项目根）                |
| G8  | 把 CLAUDE.md §1-4（通用准则）拆为 `plugin/skills/harness-guidelines/SKILL.md`（model-invoked）          | 1.5 h  | M8'-T5 关键挑战 1 一期                  |
| G9  | 改写 `/harness:onboard`：首次跑时产出"建议贴到用户项目 CLAUDE.md 的段落"（来自原 §5-10）                | 1 h    | M8'-T5 关键挑战 1 二期                  |
| G10 | 复制 `engineering-practices.md` → `plugin/rules/`；让 `/harness:audit-practices` 显式 Read              | 15 min | ✅ EG1                                  |
| G11 | 复制 `.mcp.json` → `plugin/.mcp.json`；新增 `plugin/.env.example` 说明 .env 在用户侧维护                | 20 min | 部分（.mcp.json ✅，.env.example 待办） |
| G12 | 写 `plugin/README.md`（安装 / 用法 / 调用前缀 / 已知限制 / 与 myHarness 仓库的关系）                    | 1 h    | ✅ EG1（初版）                          |
| G13 | 本地 `claude --plugin-dir ./plugin` 端到端验证：空 demo 项目 + 一个非 Java demo                         | 1 h    | M8'-T8 成功标准                         |
| G14 | 同步修订 CLAUDE.md / README.md / AGENTS.md 中"项目性质 = Java DDD 后端实战"措辞为"plugin 仓库"视角      | 30 min | 战略转向回声修订                        |
| G15 | 决策 `.claude/` 与 `plugin/` 共存期长度：是否在 M8' 完成后清空原 `.claude/`，让仓库根成为纯 plugin 仓库 | —      | 后置决策（视 G13 验证结果）             |

_预估总成本 ~ 7-8 小时（不含 marketplace 发布）。建议按 G1-G6 → G7-G11 → G12-G14 → G15 四批次推进，每批一次 commit。_

---

## F. 维护说明

- **新发现追加到 A/B/C 末尾**，按优先级
- **完成的项移到 §E**（不删，保留追溯）
- **季度审视**：每三个月扫一遍 P2/P3，关掉过时的
- **与 roadmap.md 不同**：roadmap 是阶段总规划；本文是阶段内 follow-up 清单
