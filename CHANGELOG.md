# Changelog

记录本项目可观察到的变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
版本遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

由于本项目是工程化方法论项目而非软件包，"版本"对应 **里程碑（M0–MN）**。

## [Unreleased]

### 计划中
- M7：Tools 治理 + Policy 机制化（版本锁、fallback chain、model selection、审计日志、emergency override）
- M8：Java DDD 实例化（pom.xml + src/，六维度回归测试）

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
