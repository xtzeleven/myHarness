# Changelog

记录本项目可观察到的变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
版本遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

由于本项目是工程化方法论项目而非软件包，"版本"对应 **里程碑（M0–MN）**。

## [Unreleased]

### 计划中
- M4：实例化 `pom.xml` + `src/main/java/<base>/{interfaces,application,domain,infrastructure}/`
- M5：接入第二个真实项目，对照框架做差异分析
- M6：8+ 模型在本框架下的表现差异

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
