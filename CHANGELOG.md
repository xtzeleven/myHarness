# Changelog

记录本项目可观察到的变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
版本遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

由于本项目是工程化方法论项目而非软件包，"版本"对应 **里程碑（M0–MN）**。

## [Unreleased]

> **分支说明**：本 CHANGELOG 对应 `plugin-branch`（活分支）。`main` 分支冻结于 M7 后置 / M8 启动前状态（standalone 形态，仓库根 `.claude/{hooks,agents,...}` 仍在），不合回。详见 [README "🌿 分支模型"](README.md#-分支模型) 与 [ADR-0006](docs/adr/0006-cleanup-claude-dir.md)。

### M8' Plugin 化（B 阶段 → ADR-0006 实施）

**战略**：M8 Java DDD 实例化 → 废弃（[ADR-0005](docs/adr/0005-pivot-to-plugin.md)）；B 阶段完成后清空仓库根 `.claude/{agents,commands,hooks,rules,scripts}/`，仓库根 = pure plugin（[ADR-0006](docs/adr/0006-cleanup-claude-dir.md)）。

#### Added

- [ADR-0005](docs/adr/0005-pivot-to-plugin.md) plugin 化战略转向 / [ADR-0006](docs/adr/0006-cleanup-claude-dir.md) `.claude/` 清空决策
- `plugin/` 完整骨架：`.claude-plugin/plugin.json` manifest + agents (8) + commands (5) + hooks (6 + 4 tests) + skills (1) + rules (1) + scripts (2) + `.mcp.json` + `.env.example` + README
- `plugin/skills/harness-guidelines/SKILL.md`:通用准则 §1-4 拆为 model-invoked skill（G8）
- `plugin/hooks/hooks.json`:hook 注册（用 `${CLAUDE_PLUGIN_ROOT}` + `${CLAUDE_PROJECT_DIR}`，去 cwd 假设）
- `plugin/commands/onboard.md` 双模式（summary / init）：G9 改写，init 模式产 CLAUDE.md 模板让用户手贴
- `scripts/dev.sh`:自举模式启动器（`claude --plugin-dir ./plugin "$@"`）
- `.github/workflows/plugin-validate.yml`:plugin 自身 5 job 校验（manifest schema / bash 语法 / agent frontmatter / env-vars-aligned / smoke / bypass-guard）
- `.github/required-files.txt`:CI 必需文件清单单点真源（lint.yml + scheduled.yml 共用）
- `docs/g13-external-validation.md` + `docs/g13-findings.md`:plugin 外部验证 runbook + 结果
- bypass env namespace：`CLAUDE_PLUGIN_HARNESS_BYPASS`（兼容旧名 `HARNESS_BYPASS`）

#### Changed

- 仓库根 `.claude/{agents,commands,hooks,rules,scripts}/` 全部清空（ADR-0006 选项 B 实施于 `plugin-branch`）；保留 `settings.json`（去 hooks 段）/ `settings.local.json`（.gitignore）/ 运行时产物
- `.github/workflows/lint.yml` 简化：`.claude/agents` 必需文件 / hook shebang+x 等 job 转 `plugin-validate.yml`；trigger 加 `plugin-branch`；AGENTS.md 链接校验改查 `plugin/agents/*.md`
- `.github/workflows/plugin-validate.yml` trigger 加 `plugin-branch`（避免活分支 CI 裸奔）
- `.github/workflows/scheduled.yml` stale-check 取 `main` + `plugin-branch` 两分支最新 commit，避免 main 冻结误告 stale
- `README.md` / `CLAUDE.md` / `AGENTS.md` 措辞从"Java DDD 后端实战"改为"plugin 仓库 + Java/DDD 扩展套件"（G14）；README 加"🌿 分支模型"节
- 8 个 agent 加"适用：Java/JVM 项目"等限定；SKILL description 加中英双语 + ALWAYS invoke 关键词强化召唤率
- `pre-tool-use.sh` hint 6 处去掉 `.claude/agents/` 硬路径，改语义化（G6）
- audit log 位置定为 `${CLAUDE_PROJECT_DIR}/.claude/.audit.log`（G7），plugin 目录不污染

#### Removed

- `.claude/agents/` `.claude/commands/` `.claude/hooks/` `.claude/rules/` `.claude/scripts/`（语义已迁 `plugin/`；ADR-0006 commit d895862）

#### Fixed

- **F9**:Sub-agent 沉默失败检测（应对 API 代理 panic / new-api nil pointer 等基础设施抖动）— `subagent-stop.sh` 加 `_detect_silent_failure()`：无 schema 块 + (空输出 / 错误关键词 panic/timeout/500/connection-reset/rate-limit / 短输出 <50 字符) → 写 audit log `status: silent_failure` + stderr 提示主 Claude 降级到主对话；新增 `test_subagent_stop.sh` 10 case；plugin-validate.yml 注册新测试
- **F8**:Windows 反斜杠路径让 PreToolUse 灰名单全失效（H2 验证发现，致命跨平台 bug）— `pre-tool-use.sh` 提取 file_path 后立即 `${file_path//\\//}` 规范化；新增 5 case 回归测试覆盖反斜杠 domain 路径 / 带盘符前缀 / secrets 路径 / 不误伤 application 层；commit ce6ff49
- **F1**:bypass audit log `reason` 反映实际触发的 env 名（旧名 `HARNESS_BYPASS` 触发时不再误写 `CLAUDE_PLUGIN_HARNESS_BYPASS`）
- **H1-H5 / M1/M2/M4/M5 / S2-S5 / F2-F4** 共 16 项跨"装上就坏 / 功能性退化 / 结构性缺陷"修复（详见 plugin-branch commit history：b62c63c H 级 / 7ff7d9c M+S 级 / 7fba6ca F1 / 64314ed SKILL / 260ccc1 G14）
- npm cache key 缺失：加 `package-lock.json`（dcb26eb）
- `.session.state` / `.claude/settings.local.json` 误 tracked：`git rm --cached`（091848b）

#### 验证

- plugin smoke test **84 case 全过**（含 F1 audit-reason 回归 2 case + F8 反斜杠路径回归 5 case + F9 沉默失败检测 10 case）
- G13 自动验证 18/18 ✅:空仓库基线 5 / Java 灰名单 3 / Python 静默 5 / Bypass 3 / 审计日志 2
- **G13 手工 H1-H7 全 ✅**（2026-05-13 用户交互验证，详见 [docs/g13-findings.md](docs/g13-findings.md)）

### M7 后置 / M8 启动前清账

#### Added

- `docs/agent-output-schema.md`：sub-agent 输出 schema 契约（`status` / `degraded_from` / `escalate_to` / `risks`），让 SubagentStop hook 能解析"成败/降级/升级"信号
- `.claude/hooks/subagent-stop.sh`：SubagentStop hook，解析 sub-agent 输出末尾的 `<!-- harness:agent-output -->` 块，写 audit log + 非 ok 状态 stderr 提示
- `.claude/hooks/tests/test_pre_tool_use.sh`：26 case smoke test（黑名单 / 灰名单 / 不误伤 / 敏感文件 / DDD 边界 / 主依赖 / bypass 全覆盖），tempdir 隔离 audit log 写入
- `docs/adr/0004-deprecate-bypass-once.md`：废弃 `.bypass-once` 单次授权机制（5/9 实验残留），统一走 `HARNESS_BYPASS=1` + commit marker + CI 拒合三道
- `docs/improvement-backlog.md`：完整 follow-up 清单（A/B/C/D/E 5 类，含工作量与修法）

#### Changed

- `.claude/hooks/format.sh`：PostToolUse 加 audit log（记录 `executed` 事件含 tool/target/ext），不仅做格式化；带 `HARNESS_BYPASS=1` 时记 `bypass: true`
- `.claude/scripts/audit-log-summary.py`：加 6 个聚合参数（`--by-hook/tool/action/agent/ext/day`）+ `--hook` 过滤；`by-ext` 只统计 PostToolUse，`by-agent` 只统计 SubagentStop
- `.claude/settings.json`：注册 SubagentStop hook（共 5 类 hook）
- `.github/workflows/lint.yml`：加 `hook-test` job 跑 smoke test；必需清单加 `subagent-stop.sh` + `agent-output-schema.md` + `test_pre_tool_use.sh`；hook shebang+x 校验扩到 `.claude/hooks/**/*.sh`
- `.claude/rules/engineering-practices.md §15` Bypass policy：加 `.bypass-once` 废弃声明 + 引 ADR-0004
- `docs/adr/README.md`：登记 ADR-0004
- `README.md`：修复 8 处漂移（badge / 当前状态 / 节数 / Hooks 描述 / commands 数 / 阶段表 M3→M8 / 文档导航 / 目录速览），M4-M7 全部打 ✅，M8 标当前
- `CLAUDE.md §7`：M3 → M7 完成；`/audit-practices` 14 维度 → 15 维度

#### Fixed

- README 多处过期描述（M3 实际已是 M7 完成；`.claude/commands/` 4 个 → 5 个）

#### 验证

- SubagentStop hook 4 case 通过（ok / degraded / escalate / 无 schema 静默 skip）
- PostToolUse audit log 4 case 通过（Edit / Write / 空 file_path 不记 / bypass 标记）
- pre-tool-use 26 case smoke test 仍全过（未破坏现有）
- audit-log-summary 6 聚合视角输出干净（PreToolUse / PostToolUse 不混淆）

#### 计划中（已废弃）

- ~~M8：Java DDD 实例化（pom.xml + src/，六维度回归测试）~~ — 由 [ADR-0005](docs/adr/0005-pivot-to-plugin.md) 转为 M8' Plugin 化

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
- 删除根级空 `skills/` 目录（plugin skill 不在此）
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
