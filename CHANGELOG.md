# Changelog

记录本项目可观察到的变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
版本遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

由于本项目是工程化方法论项目而非软件包，"版本"对应 **里程碑（M0–MN）**。

## [Unreleased] — M7 后置 / M8 启动前清账

### 2026-05-15 — P0-P3 系统性清账（架构 + CI 残留 + telemetry 闭环）

#### Added

- `docs/policy-model-selection.md`：模型选择策略单点真源（agent 默认表 + 通用场景表 + 优先级与升级规则）。**P1-B**
- `.claude/hooks/tests/test_subagent_stop.sh`：6 case smoke test（ok / degraded / escalate / blocked / 无 schema 静默 skip / 非法 JSON 不崩）。**P2-H**
- `.github/workflows/lint.yml` 新 job `agent-schema-check`：每个 agent .md 必含 `harness:agent-output` 示例。**P2-G**
- `.github/workflows/lint.yml` 新 job `commit-lint`：commit 消息走 Conventional Commits 正则强制。**P3-K**
- `.github/workflows/scheduled.yml` 新 job `weekly-audit-reminder`：每周一开 issue 提醒本机跑 `audit-log-summary.py`（audit log 是 .gitignored 本地文件，CI 看不到，改用 reminder 模式）。**P2-F / B6**
- `.claude/rules/policies/{deny,ask-user,hints}.yaml`：所有 PreToolUse 规则数据（35 条）外移到 yaml；`README.md` 给 schema 与维护流程。**P1-A**
- `.claude/scripts/policy-dispatch.py`：python 规则评估器（cmd_contains_any / cmd_matches / file_basename_in / new_content_present 等谓词，audit log + bypass + hint 去重三合一）。**P1-A**
- `.claude/scripts/session-state.py`：`.session.state` CLI helper（`set-task` / `add-step` / `done-step` / `blocked` / `clear` / `show`），主对话长任务时自觉调用，让 SessionStart 显示"上次未完事项"。**P1-C**
- `CLAUDE.md §12`：会话状态约定（M5-T6）。**P1-C**

#### Changed

- **ADR-0007 残留清扫**（**P0**）：
  - `.github/required-files.txt` 删 6 个 `plugin/*` 条目 + 删 `.github/workflows/plugin-validate.yml` 条目
  - `git rm .github/workflows/plugin-validate.yml`（plugin/ 已撤，workflow 僵尸化）
- `.mcp.json`：`@benborla29/mcp-server-mysql` 钉版本 `@2.0.8`，注释加禁用 @latest 提示。**P1-E**
- `AGENTS.md` Model Selection Policy 章：从完整表改为指向 policy-model-selection.md 的摘要。**P1-B**
- `.claude/rules/engineering-practices.md §15`：模型选择 policy 子节由表改为指针。**P1-B**
- `README.md`：加"前置要求"段（bash / python / Node 20+ / Windows 须 Git Bash 或 WSL）。**P1-D**
- `CLAUDE.md §5`：加平台前置说明（Windows 非 git-bash 终端 hook 静默失败）。**P1-D**
- `CLAUDE.md §11`：MEMORY 硬路径（`~/.claude/projects/D--myGithub-myHarness/memory/`）→ 改为"客户端自动派生，不固化到仓库"。**P3-N**
- `.claude/hooks/pre-tool-use.sh`：从 256 行 bash 规则脚本退化为 6 行 dispatcher 转发器；规则全部在 yaml。**P1-A**
- `.claude/hooks/session-start.sh`：每会话开始时清空 `.session.hints`。**P2-I**
- `.prettierrc.json`：yaml 文件改用 `singleQuote: true`（避免 `\s` 在双引号下被解析为非法转义）。**P1-A**
- `.github/workflows/lint.yml`：
  - `npm ci || npm install` → `npm ci`（移除 fallback，强制 lockfile 一致）。**P3-M**
  - `hook-test` job 加 `pip install pyyaml` + yaml parse 校验 + 接入 `test_subagent_stop.sh`。**P1-A / P2-H**
- `.github/workflows/scheduled.yml` `weekly-tool-versions`：移除 "(Future M7)" placeholder，落地为 `locked vs latest` 比较 + 漂移开 issue（含升级命令）。**P3-L**
- `.github/required-files.txt`：加 `docs/policy-model-selection.md` + `test_subagent_stop.sh` + `policies/{README,deny,ask-user,hints}` + `policy-dispatch.py` + `session-state.py`。

#### Fixed

- ADR-0007（撤销 plugin 化）执行不彻底导致 `lint.yml structure-check` 必 fail；本批清扫后恢复 CI 红→绿。

#### 验证

- pre-tool-use 26 case smoke test 仍全过（dispatcher 替换 bash case 后行为等价）
- subagent-stop 6 case smoke test 全过（新增）
- 3 个 policies yaml 文件 PyYAML 解析通过（35 条规则全部加载）
- session-state.py 手动验 set-task / add-step / done-step / blocked / clear / show 全链路 OK
- hint 去重手动验证：同 file_path 第 2 次 Edit 不输出 hint
- prettier --check：本批触动文件全部合规（pre-existing warns 不在本批范围）

#### M8 启动前剩余 follow-up

_本批 P1-A / P1-C 已全部落地，无未完 follow-up。_

---

### 此前 [Unreleased] 项

### Added

- `docs/agent-output-schema.md`：sub-agent 输出 schema 契约（`status` / `degraded_from` / `escalate_to` / `risks`），让 SubagentStop hook 能解析"成败/降级/升级"信号
- `.claude/hooks/subagent-stop.sh`：SubagentStop hook，解析 sub-agent 输出末尾的 `<!-- harness:agent-output -->` 块，写 audit log + 非 ok 状态 stderr 提示
- `.claude/hooks/tests/test_pre_tool_use.sh`：26 case smoke test（黑名单 / 灰名单 / 不误伤 / 敏感文件 / DDD 边界 / 主依赖 / bypass 全覆盖），tempdir 隔离 audit log 写入
- `docs/adr/0004-deprecate-bypass-once.md`：废弃 `.bypass-once` 单次授权机制（5/9 实验残留），统一走 `HARNESS_BYPASS=1` + commit marker + CI 拒合三道
- `docs/improvement-backlog.md`：完整 follow-up 清单（A/B/C/D/E 5 类，含工作量与修法）

### Changed

- `.claude/hooks/format.sh`：PostToolUse 加 audit log（记录 `executed` 事件含 tool/target/ext），不仅做格式化；带 `HARNESS_BYPASS=1` 时记 `bypass: true`
- `.claude/scripts/audit-log-summary.py`：加 6 个聚合参数（`--by-hook/tool/action/agent/ext/day`）+ `--hook` 过滤；`by-ext` 只统计 PostToolUse，`by-agent` 只统计 SubagentStop
- `.claude/settings.json`：注册 SubagentStop hook（共 5 类 hook）
- `.github/workflows/lint.yml`：加 `hook-test` job 跑 smoke test；必需清单加 `subagent-stop.sh` + `agent-output-schema.md` + `test_pre_tool_use.sh`；hook shebang+x 校验扩到 `.claude/hooks/**/*.sh`
- `.claude/rules/engineering-practices.md §15` Bypass policy：加 `.bypass-once` 废弃声明 + 引 ADR-0004
- `docs/adr/README.md`：登记 ADR-0004
- `README.md`：修复 8 处漂移（badge / 当前状态 / 节数 / Hooks 描述 / commands 数 / 阶段表 M3→M8 / 文档导航 / 目录速览），M4-M7 全部打 ✅，M8 标当前
- `CLAUDE.md §7`：M3 → M7 完成；`/audit-practices` 14 维度 → 15 维度

### Fixed

- README 多处过期描述（M3 实际已是 M7 完成；`.claude/commands/` 4 个 → 5 个）

### 验证

- SubagentStop hook 4 case 通过（ok / degraded / escalate / 无 schema 静默 skip）
- PostToolUse audit log 4 case 通过（Edit / Write / 空 file_path 不记 / bypass 标记）
- pre-tool-use 26 case smoke test 仍全过（未破坏现有）
- audit-log-summary 6 聚合视角输出干净（PreToolUse / PostToolUse 不混淆）

### 计划中

- M8：Java DDD 实例化（pom.xml + src/，六维度回归测试）—— 详见 [docs/improvement-backlog.md](docs/improvement-backlog.md) §B "M8 启动前必修"

## [M7] - 2026-05-09 — Tools 治理 + Policy 机制化

### Added

- **工具版本锁**：`package.json`（prettier 3.3.3）+ `.prettierrc.json`（格式约定）+ `.tool-versions`（asdf/mise 风格：node 20 / python 3.13 / java 17 / maven 3.9）
- `docs/tools-fallback.md`：工具失效降级路径（gitnexus → grep / MCP → schema dump / prettier → 跳过）+ "降级 ≠ 失败"原则 + 不该降级的场景
- `engineering-practices.md §15 Policy 机制化`：模型选择 / 降级 / 拒绝继续 / 升级链 / bypass / 审计 6 类元规则
- `.claude/scripts/audit-log-summary.py`：JSONL 审计日志摘要工具，支持 --tail / --bypass / --since
- AGENTS.md 加 "Model Selection Policy" 章 + "Tools Lock" 章 + "Audit Log" 章
- 8 个 agent frontmatter 加 model 选择注释（YAML `# why this model`）
- CI bypass-guard job：commit message 含 `BYPASS:` / 环境含 `HARNESS_BYPASS=1` 时直接 fail

### Changed

- PreToolUse hook 加 `_audit_log()` 函数：deny / ask_user / bypass 全部写 `.claude/.audit.log`（JSONL，已 .gitignore）
- PreToolUse hook 加 `HARNESS_BYPASS=1` 检测：env 设置时放行黑+灰名单但**强制写审计**（bypass: true 标记）
- CI lint.yml format-check 改用 `npm ci` 装 pinned prettier，与本地一致
- `/audit-practices` 命令从 14 维度扩到 **15 维度**（加 Policy 机制化）
- engineering-practices 评分尺度更新为"适用于全部 15 节"

### 验证

- audit log 4 类记录正常写入（deny / ask_user×2 / bypass）
- bypass 模式：HARNESS_BYPASS=1 时 `rm -rf /` 放行但 audit 标 bypass:true ✅
- summary 工具按动作 / 工具 / 原因正确统计

## [M6] - 2026-05-09 — Context 治理

### Added

- `docs/context-management.md`：三类注入来源、token 预算（自动注入 ≤ 8K）、按需注入机制、压缩策略、M8 后子目录 CLAUDE.md 拆分原则
- `.claude/scripts/audit-context-cost.py`：tiktoken 优先（fallback char/4）的 token 审计脚本，分 6 大类汇总 + 预算检查 + 减重建议
- `.claude/commands/audit-context.md`：`/audit-context` slash 命令，包装审计脚本
- PreToolUse hook 加按需注入 hint：根据 file_path 与 cmd 模式输出 `💡 提示:` 前缀的建议（11 种触发场景，14/14 测试通过），不阻塞

### Baseline 数据（M6 完成时）

- 自动注入：3589 tokens（占 8K 预算的 45% ✅）
- 常被 prefetch：6451 tokens（README + AGENTS.md + CHANGELOG）
- Rules 按需：4078 tokens
- Agents 总和：11220 tokens（仅 spawn 时计入单个）
- Docs 总和：18066 tokens（按需 Read，不计预算）

## [M4-M5] - 2026-05-09 — Memory 启用 + Loop 架构

### Added

- **M4 Memory**：启用 Claude Code 内置 memory（`~/.claude/projects/<id>/memory/`）
  - 5 条决策类记忆（Java DDD / MySQL 只读 / 三层架构 / 灰名单 / python over jq）
  - 6 条踩坑类记忆（jq 不可用 / SQL 误伤 / settings.local 已 tracked / hook 自拦 / Windows 路径 / format hook 幂等）
  - `MEMORY.md` 索引（按主题分组）
  - `docs/memory-conventions.md`：CLAUDE.md / ADR / Memory 三载体分工矩阵
  - CLAUDE.md §11 加 memory 引用与常见查阅场景
- **M5 Loop 架构**：
  - `docs/loop-architecture.md`：Driver / Worker 角色、调度决策树、并行/串行硬规则、retry/escalation/degradation 三策略、`.session.state` 中断恢复机制、自反馈环
  - `docs/periodic-tasks.md`：会话内 `/loop` skill + 仓库级 GitHub Actions 定时（D2 决策："两都要"）
  - `.github/workflows/scheduled.yml`：每日结构自检 / 每周 stale-check / 每周工具版本漂移（仅 open issue，不 fail repo）
  - `.claude/hooks/session-start.sh`：注入分支 / 最近 commit / 上次会话状态 / Memory 索引摘要 / 工具就绪状态
  - AGENTS.md 加自反馈环表 + 升级链表 + 降级链
- `docs/roadmap.md`：M4-M8 六维度路线总览（Loop / Context / Tools / Permission Gate / Memory / Policy）

### Changed

- Stop hook（stop-check.sh）扩展为同时写 `.session.state`（含分支 / head / 未提交数）供下次会话读
- settings.json 注册 SessionStart hook
- lint.yml required 列表扩到 25 项（加 session-start.sh / scheduled.yml / 4 份 docs）

## [M3] - 2026-05-09 — Layer 3 质量门禁

### Added

- `.gitignore` 覆盖 IDE / OS / Node / Python / Java / 密钥六类
- `.github/workflows/lint.yml`：prettier + 必需文件 + JSON 校验 + AGENTS 链接 + .gitignore 防泄密 + .mcp.json 变量同步
- `.mcp.json` 占位（MySQL 只读 MCP，强制 `ALLOW_*=false`）+ `.env.example`
- 6 个新 agent：`ddd-architect` `spring-boot-reviewer` `maven-build-doctor` `schema-analyst` `migration-author` `docs-keeper`
- 2 个新 command：`/onboard` `/sync-docs`
- engineering-practices §12（DDD 分层）§13（Java/Spring 风格）§14（MCP 治理）
- CLAUDE.md §5-§10（项目上下文 / 禁忌 / 测试命令 / gitnexus 路由 / 人工决策清单 / 子目录指引）
- PreToolUse hook 灰名单：DDD 边界改动、主依赖升级、`mvn deploy`、DDL/DML 数据库命令、危险 git 历史改写
- ADR 0001-0003（三层架构 / Java DDD / MCP+gitnexus）
- 本 CHANGELOG

### Changed

- `/audit-practices` 从 11 维度扩到 14 维度，对应 engineering-practices 14 节
- README badge `WIP M2` → `WIP M3`，路线图加 M4-M6
- PreToolUse hook 改用 python 解析 JSON（jq 不可用时 sed 在转义引号上截断）
- PreToolUse SQL 检测精确化：仅在命令以 `mysql`/`psql`/`mysqldump` 起头时检查，避免误伤含 SQL 字面量的普通命令
- format.sh 与 pre-tool-use.sh 统一用 python 解析
- engineering-practices "评分尺度" 移到全文末（覆盖全部 14 节）

### Fixed

- `.claude/settings.local.json` 之前已被 git 跟踪，现 `git rm --cached` 移出
- 删除根级空 `skills/` 目录
- CLAUDE.md gitnexus 死链 `https://github.com/` 移除

## [M2] - 2026-05-08 — Layer 2 反馈循环

### Added

- PostToolUse format hook（按后缀分发 prettier/ruff）
- Stop hook（会话结束变更摘要）
- 2 个 agent：`tdd-cycle-driver`（红绿重构）、`code-reviewer`（独立评审）
- 2 个 command：`/audit-practices`（11 维度）、`/commit`（标准化提交）
- AGENTS.md 索引

## [M1] - 2026-05-08 — Layer 1 约束

### Added

- CLAUDE.md 行为准则（4 节通用规则 + 7 节项目上下文）
- `.claude/rules/engineering-practices.md`（11 节通用工程化规则）
- PreToolUse hook 黑名单（rm -rf 根、强推主分支、写敏感文件）

## [M0] - 2026-05-08 — 项目立项

### Added

- README 三层 Harness 架构假设
- 项目结构：`docs/` `skills/`（占位）
