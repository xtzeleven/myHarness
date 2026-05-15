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

| #   | 维度            | 项                                                                                 | 工作量 | 关联                  |
| --- | --------------- | ---------------------------------------------------------------------------------- | ------ | --------------------- |
| B4  | Context Manager | `audit-context-cost.py` 加每会话 token baseline 入 audit log（每周 GH Actions 跑） | 1 h    | 长期追踪 context 膨胀 |

_B1 / B2 / B3 / B5 / B6 已完成。详见 §E（B1→E14 / B2→E15 / B3→E16 / B5→E17 / B6→E25 weekly-audit-reminder）。_

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
| C4  | Context Manager | PreToolUse hint 去重（per session）—— 同一 file_path 多次 Edit 只提示一次                                                     | ✅ E28                         |
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
| C19 | Model Selection Policy 在 3 处重复（§15 / AGENTS.md 表 / agent frontmatter 注释） | ✅ E22 | 抽 `docs/policy-model-selection.md` 单点真源，其他"详见"     |
| C20 | agent 自反馈环触发靠字符串匹配（部分由 SubagentStop schema 解决）                 | —      | 与 B5 协同：schema 推广后 AGENTS.md 自反馈表改用 status 触发 |

_C17 / C18 / C21 已完成。详见 §E（C17→E18 / C18→E19 / C21→E20）。C4 / C19 本批完成（E28 / E22）。_

### 本批新引入的 follow-up（架构改动，尚待方案确认）

| #   | 项                                                                                          | 工作量 | 说明                                                                                                                        |
| --- | ------------------------------------------------------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------- |
| F1  | **P1-A**: 规则数据外移到 `.claude/rules/policies/*.yaml`，pre-tool-use.sh 退化为 dispatcher | 半天   | M8 实例化后规则会暴增，bash case 不可扩展。schema：`{tool, pattern, action, reason}`。需先与用户确认 yaml schema 与迁移路径 |
| F2  | **P1-C**: session 状态恢复落地（Stop 写 in-progress，SessionStart 读并提醒续跑）            | 1-2 h  | roadmap M5-T6 已写但未实现。需先约定数据契约：`current_task` / `pending_steps` / `last_checkpoint` 由谁写、何时写           |

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
| E21 | **P0**: ADR-0007 残留清理（required-files.txt 删 6 个 plugin 条目 + git rm plugin-validate.yml）    | 2026-05-15  |
| E22 | **P1-B**: `docs/policy-model-selection.md` 单点真源；AGENTS.md / engineering-practices §15 改指针   | 2026-05-15  |
| E23 | **P1-D**: README + CLAUDE.md 声明 bash + python + Git Bash/WSL 平台前置要求                         | 2026-05-15  |
| E24 | **P1-E**: `.mcp.json` 锁 `@benborla29/mcp-server-mysql@2.0.8`，禁用 @latest                         | 2026-05-15  |
| E25 | **P2-F**: scheduled.yml 加 weekly-audit-reminder job（每周提醒本地跑 audit-log-summary）            | 2026-05-15  |
| E26 | **P2-G**: lint.yml 加 agent-schema-check job（每 agent 必含 `harness:agent-output` 示例）           | 2026-05-15  |
| E27 | **P2-H**: `test_subagent_stop.sh` 6 case + lint.yml hook-test job 接入                              | 2026-05-15  |
| E28 | **P2-I**: PreToolUse hint 去重（`.claude/.session.hints` per-session，SessionStart 清空）           | 2026-05-15  |
| E29 | **P3-K**: lint.yml 加 commit-lint job（Conventional Commits 正则强制）                              | 2026-05-15  |
| E30 | **P3-L**: scheduled.yml weekly-tool-versions 落地（locked vs latest 比较 + 漂移开 issue）           | 2026-05-15  |
| E31 | **P3-M**: lint.yml 移除 `npm ci \|\| npm install` fallback，强制 lockfile 一致                      | 2026-05-15  |
| E32 | **P3-N**: CLAUDE.md §11 MEMORY 硬路径 → 由 Claude Code 客户端派生的相对说明                         | 2026-05-15  |

---

## F. 维护说明

- **新发现追加到 A/B/C 末尾**，按优先级
- **完成的项移到 §E**（不删，保留追溯）
- **季度审视**：每三个月扫一遍 P2/P3，关掉过时的
- **与 roadmap.md 不同**：roadmap 是阶段总规划；本文是阶段内 follow-up 清单
