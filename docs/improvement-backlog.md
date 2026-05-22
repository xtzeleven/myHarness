# Improvement Backlog — Harness 完备性 follow-up

**Date**: 2026-05-11
**Status**: 活跃跟踪（M7 后置 / M8-T0 前置阶段 / M8 主线启动前需消化）

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

### 本批新引入的 follow-up（已落地）

_F1 / F2 同批落地，详见 §E（F1→E33 / F2→E34）。_

---

## D. 设计判断点（P3，可商榷）

| #   | 项                                                                                                                                   | 讨论方向                                                                                       |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| D1  | `.claude/policies/` 目录化 vs 散在 .md                                                                                               | 现状散在但可读；若要可程序解析则集中化                                                         |
| D2  | 三层 Harness vs 六维度视角并存                                                                                                       | README 加"视角注解段"；或在 ADR 写明两套视角的关系                                             |
| D3  | ADR-0001 "L1 工程化规则（14 节）" 历史快照是否更新                                                                                   | ADR 通常不改；建议保留作为快照证据                                                             |
| D4  | Hook 跨平台支持（PowerShell / fish 用户）                                                                                            | 当前要 bash；可在 README 声明前置要求                                                          |
| D5  | `output style` 配置（engineering-practices §11 提到可选）                                                                            | 是否要项目专属 output style？未必必要                                                          |
| D6  | ~~worktree 引入 + audit log 跨 worktree 聚合~~                                                                                       | ✅ E41                                                                                         |
| D7  | Auto mode 深度集成：扩 deny.yaml / ask-user.yaml 覆盖"软风险"（大量删文件 / 改 CI workflow / 改 .gitignore），让分类器之外多一层规则 | 触发条件：实际开始 daily 用 auto mode 后通过 `--by-permission-mode` 看到 auto 下放行的可疑动作 |
| D8  | ~~Hook 规则补强：Bash heredoc / `>` 重定向 / tee / sed -i 写 pom.xml 或 domain/.java 绕过 Edit/Write 拦截~~                          | ✅ E49                                                                                         |

---

## E. 已完成（参考 / 不删，保留追溯）

| #   | 项                                                                                                                                                                                                                                                                                                                                                                                                             | 完成 commit |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| E1  | Top 3 #1: README 漂移修复                                                                                                                                                                                                                                                                                                                                                                                      | c067ee2     |
| E2  | Top 3 #2: `.bypass-once` 废弃 ADR-0004 + engineering-practices §15 声明                                                                                                                                                                                                                                                                                                                                        | c067ee2     |
| E3  | Top 3 #3: hook 自动化测试（26 case smoke test）+ CI 集成                                                                                                                                                                                                                                                                                                                                                       | c067ee2     |
| E4  | 八维度 #1: SubagentStop hook + agent output schema                                                                                                                                                                                                                                                                                                                                                             | b63538a     |
| E5  | 八维度 #2: PostToolUse audit log + audit-log-summary 聚合（--by-hook/tool/action/agent/ext/day）                                                                                                                                                                                                                                                                                                               | b63538a     |
| E6  | A3: CLAUDE.md "M3 阶段" / "14 维度" → "M7 完成" / "15 维度"                                                                                                                                                                                                                                                                                                                                                    | b63538a     |
| E7  | A4: CHANGELOG.md [Unreleased] 段补全（八维度 + ADR-0004 + smoke test 全部入账）                                                                                                                                                                                                                                                                                                                                | b63538a     |
| E8  | B8: onboard.md "M0-M5" → "M0-M8"                                                                                                                                                                                                                                                                                                                                                                               | 2ab8383     |
| E9  | B9: commit.md:107 "永不在 main 实验性提交" 软化为承认当前单人项目现状                                                                                                                                                                                                                                                                                                                                          | 2ab8383     |
| E10 | B10: AGENTS.backend.md "6 个后端 agent" → "5 个" + 列表正确                                                                                                                                                                                                                                                                                                                                                    | 2ab8383     |
| E11 | A1+A2 扩面：7 个 hook 全部 git mode 100755（4 老 hook + UserPromptSubmit + 2 测试）                                                                                                                                                                                                                                                                                                                            | 本批 commit |
| E12 | B7: lint.yml + scheduled.yml 必需文件清单去重 → 抽 `.github/required-files.txt` 单点真源                                                                                                                                                                                                                                                                                                                       | 本批 commit |
| E13 | engineering-practices.md:351 "M3 阶段" 残留 → "M7 完成 / M8 待启动"                                                                                                                                                                                                                                                                                                                                            | 本批 commit |
| E14 | B1: UserPromptSubmit hook 拦截敏感词（`.claude/hooks/user-prompt-submit.sh` 13 个高危模式 + 测试）                                                                                                                                                                                                                                                                                                             | 前批 commit |
| E15 | B2: PostToolUse 事后秘钥检测（`format.sh:109-200` 9 类秘钥模式 + 跳过列表 + 红色 stderr + 测试）                                                                                                                                                                                                                                                                                                               | 前批 commit |
| E16 | B3: `docs/mcp-onboarding.md` 完整 8 章节（5 步流程 / 分类 / 安全清单 / 反模式 / 范例）                                                                                                                                                                                                                                                                                                                         | 前批 commit |
| E17 | B5: 3 个 agent 加 schema 范例（ddd-architect / spring-boot-reviewer / schema-analyst 4 状态全覆盖）                                                                                                                                                                                                                                                                                                            | 前批 commit |
| E18 | C17: engineering-practices §0 阅读顺序加"6. 元规则：第 15 节"                                                                                                                                                                                                                                                                                                                                                  | 本批 commit |
| E19 | C18: `.gitignore` 加 `.claude/.audit.log` 显式行（与 `.session*` 风格一致）                                                                                                                                                                                                                                                                                                                                    | 本批 commit |
| E20 | C21: memory-conventions.md `pref_*` / `session_*` 注解 "M4.5/M5 启用" → "按需启用，暂未推进"                                                                                                                                                                                                                                                                                                                   | 本批 commit |
| E21 | **P0**: ADR-0007 残留清理（required-files.txt 删 6 个 plugin 条目 + git rm plugin-validate.yml）                                                                                                                                                                                                                                                                                                               | 2026-05-15  |
| E22 | **P1-B**: `docs/policy-model-selection.md` 单点真源；AGENTS.md / engineering-practices §15 改指针                                                                                                                                                                                                                                                                                                              | 2026-05-15  |
| E23 | **P1-D**: README + CLAUDE.md 声明 bash + python + Git Bash/WSL 平台前置要求                                                                                                                                                                                                                                                                                                                                    | 2026-05-15  |
| E24 | **P1-E**: `.mcp.json` 锁 `@benborla29/mcp-server-mysql@2.0.8`，禁用 @latest                                                                                                                                                                                                                                                                                                                                    | 2026-05-15  |
| E25 | **P2-F**: scheduled.yml 加 weekly-audit-reminder job（每周提醒本地跑 audit-log-summary）                                                                                                                                                                                                                                                                                                                       | 2026-05-15  |
| E26 | **P2-G**: lint.yml 加 agent-schema-check job（每 agent 必含 `harness:agent-output` 示例）                                                                                                                                                                                                                                                                                                                      | 2026-05-15  |
| E27 | **P2-H**: `test_subagent_stop.sh` 6 case + lint.yml hook-test job 接入                                                                                                                                                                                                                                                                                                                                         | 2026-05-15  |
| E28 | **P2-I**: PreToolUse hint 去重（`.claude/.session.hints` per-session，SessionStart 清空）                                                                                                                                                                                                                                                                                                                      | 2026-05-15  |
| E29 | **P3-K**: lint.yml 加 commit-lint job（Conventional Commits 正则强制）                                                                                                                                                                                                                                                                                                                                         | 2026-05-15  |
| E30 | **P3-L**: scheduled.yml weekly-tool-versions 落地（locked vs latest 比较 + 漂移开 issue）                                                                                                                                                                                                                                                                                                                      | 2026-05-15  |
| E31 | **P3-M**: lint.yml 移除 `npm ci \|\| npm install` fallback，强制 lockfile 一致                                                                                                                                                                                                                                                                                                                                 | 2026-05-15  |
| E32 | **P3-N**: CLAUDE.md §11 MEMORY 硬路径 → 由 Claude Code 客户端派生的相对说明                                                                                                                                                                                                                                                                                                                                    | 2026-05-15  |
| E33 | **P1-A**: 规则数据外移到 `.claude/rules/policies/{deny,ask-user,hints}.yaml`；`policy-dispatch.py` 取代 bash case；26+6 case 通过；CI 加 pyyaml install + yaml parse 校验                                                                                                                                                                                                                                      | 2026-05-15  |
| E34 | **P1-C**: `.claude/scripts/session-state.py` CLI（set-task / add-step / done-step / blocked / clear / show）；CLAUDE.md §12 约定调用时机                                                                                                                                                                                                                                                                       | 2026-05-15  |
| E35 | **P1 B4**: `audit-context-cost.py --audit-log` 追加一行 ContextAudit JSONL 到 .audit.log；scheduled.yml 加 weekly-context-audit job 每周开 issue 报 baseline + 预算检查                                                                                                                                                                                                                                        | 2026-05-15  |
| E36 | **P2 C2**: loop-architecture.md §3 加"硬上限"小节（串行链 ≤ 4 / 并行 ≤ 5 / retry ≤ 2 / agent 单任务 ≤ 3 / escalation ≤ 3 / degradation ≤ 2 / 挂钟 30min）                                                                                                                                                                                                                                                      | 2026-05-19  |
| E37 | **P2 C5**: statusLine 配置 — `.claude/scripts/statusline.py` 输出"项目 │ 分支(dirty 标记) │ 模型 · token"，settings.json 注册                                                                                                                                                                                                                                                                                  | 2026-05-19  |
| E38 | **P2 C9**: AGENTS.md 新增"Skill vs Agent vs 主对话"小节，给职责对照表 + 判断顺序 + 反例                                                                                                                                                                                                                                                                                                                        | 2026-05-19  |
| E39 | **P2 C11**: policy-dispatch.py 加 bypass 用量阈值告警（过去 7 天 ≥ 3 次 → 红字 stderr，阈值可由 `HARNESS_BYPASS_WARN_AT` 调）；engineering-practices §15 同步                                                                                                                                                                                                                                                  | 2026-05-19  |
| E40 | **Auto mode 集成**: policy-dispatch.py 读 PreToolUse payload.permission_mode 写入 audit log；auto 模式下灰名单输出额外提醒；audit-log-summary 加 `--by-permission-mode`；CLAUDE.md §9 + engineering-practices §15 新增 Permission Mode policy 节；test_pre_tool_use.sh 新增 2 case（28 total）                                                                                                                 | 2026-05-19  |
| E41 | **D6 worktree 集成**: policy-dispatch.py / audit-log-summary.py 加 `_resolve_audit_log_path()` 自动 worktree-aware（用 `git rev-parse --git-common-dir` 检测，子 worktree 写主仓库 `.audit.log`）；`HARNESS_AUDIT_LOG_PATH` env var 可覆盖；summary 加 `--log-path`；`.gitignore` 加 `.claude/worktrees/`；`.worktreeinclude` 列 `.env*` + settings.local；新建 `docs/worktree-usage.md`；CLAUDE.md §10 加指针 | 2026-05-19  |
| E43 | **P2 C1**: `/commit` 命令加 step 7 — commit 完成后用 session-state.py done-step / clear 同步进度，让 SessionStart 准确显示                                                                                                                                                                                                                                                                                     | 2026-05-19  |
| E44 | **P2 C6**: policy-model-selection.md 新增 §5 Fallback 规则节（opus → sonnet / sonnet → haiku / 全不可用 → 用户；agent 模型下线踩坑案例）                                                                                                                                                                                                                                                                       | 2026-05-19  |
| E45 | **P2 C8**: 新建 `docs/prompt-caching-notes.md`（8 节），覆盖 Claude Code 内置 cache 行为、适合/不适合 cache 的内容、保 cache hit 的工程实践、反模式速查                                                                                                                                                                                                                                                        | 2026-05-19  |
| E46 | **P2 C10**: `audit-log-summary.py` 加 `--failures` 视角，聚合 dispatcher error / sub-agent failed\|blocked / degraded_from 三类"工具失败相关信号"                                                                                                                                                                                                                                                              | 2026-05-19  |
| E47 | **P2 C12**: `.claude/hooks/pre-compact.sh` + settings.json PreCompact 注册 — 压缩前 stdout 输出"必保留：CLAUDE.md 锚点 / 当前任务进展 / 用户授权 / 未提交改动" 提示                                                                                                                                                                                                                                            | 2026-05-19  |
| E48 | **P2 C16**: `.claude/scripts/memory-growth-summary.py` — 按类型扫 memory 目录，统计 7/30 天新增 + 体积 + 索引漂移检查；目录派生支持 --memory-dir / CLAUDE_MEMORY_DIR / 自动从 cwd 推算                                                                                                                                                                                                                         | 2026-05-19  |
| E49 | **D8**: `ask-user.yaml` 加 `bash-pom-write` + `bash-domain-boundary-write` 2 灰名单规则（Bash `>` 重定向 / `tee` / `sed -i` 写 pom.xml 或 `src/main/java/.../domain/.java` 触发同 pom-major-deps / ddd-aggregate-boundary 审查）；test_pre_tool_use.sh 5 case → 33 total                                                                                                                                       | 2026-05-22  |
| E50 | **D9**: policy-dispatch.py main() 把 file_path 反斜杠 normalize 为正斜杠 → 让 Windows 上 8 条 file_path_matches 规则生效（ddd-aggregate-boundary / write-credentials-dir / hint-domain-layer / hint-infrastructure-layer / hint-application-layer / hint-migration-files / hint-spring-config / hint-agent-md）；test_pre_tool_use.sh 加 2 case → 35 total                                                     | 2026-05-22  |

---

## F. 维护说明

- **新发现追加到 A/B/C 末尾**，按优先级
- **完成的项移到 §E**（不删，保留追溯）
- **季度审视**：每三个月扫一遍 P2/P3，关掉过时的
- **与 roadmap.md 不同**：roadmap 是阶段总规划；本文是阶段内 follow-up 清单
