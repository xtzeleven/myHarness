# harness — Claude Code Plugin

> 把 myHarness 工程化方法论封装为可分发的 Claude Code plugin。三层防御（约束 / 反馈 / 门禁）+ Java DDD 扩展套件。

**Status**: 🚧 早期开发（v0.1.0）— B 阶段（骨架就位），hook 路径与 CLAUDE.md 拆分尚未完成（详见 [已知限制](#已知限制)）。

## 这是什么

把 [myHarness](..) 项目中验证过的 Harness 资产（6 类 hook、8 个 sub-agent、5 个 slash command、2 个审计脚本、15 节工程化规则、MySQL 只读 MCP）打包为单一 Claude Code plugin，任何 Claude Code 用户可一行命令安装到自己的项目。

## 本地测试（开发期）

```bash
# 在任意目标项目下
claude --plugin-dir /path/to/myHarness/plugin

# 试命令（注意 namespace 前缀）
/harness:audit-practices
/harness:onboard
/harness:commit

# 改 plugin 后热加载
/reload-plugins
```

## 内容

```
plugin/
├── .claude-plugin/plugin.json    # manifest（name=harness）
├── agents/        (8)            # tdd-cycle-driver / code-reviewer / docs-keeper
│                                 # + ddd-architect / spring-boot-reviewer
│                                 # + maven-build-doctor / schema-analyst / migration-author
├── commands/      (5)            # /harness:audit-practices / :audit-context
│                                 # /harness:commit / :onboard / :sync-docs
├── skills/        (1)            # harness-guidelines（通用行为准则，model-invoked）
├── hooks/         (6 + 4 tests)  # session-start / user-prompt-submit / pre-tool-use
│                                 # / format / stop-check / subagent-stop
│                                 # tests: pre-tool-use / secret-detection
│                                 #        user-prompt-submit / external-cwd
├── hooks/hooks.json              # hook 注册（用 ${CLAUDE_PLUGIN_ROOT}）
├── scripts/       (2)            # audit-context-cost.py / audit-log-summary.py
├── rules/         (1)            # engineering-practices.md（15 节）
├── .mcp.json                     # MySQL 只读 MCP（凭据在用户侧 .env）
└── .env.example                  # MCP env 模板，用户侧复制到项目根
```

调用所有命令统一加 `harness:` 前缀（namespace 由 plugin.json `name` 字段定义）。

## 与根 `.claude/` 的关系（共存期）

当前 myHarness 仓库根的 `.claude/`（原始 Harness 资产）与本 `plugin/`（plugin 化产物）**并行存在**：

- **根 `.claude/`**：在 myHarness 仓库内继续生效，作为 plugin 的"权威源"
- **`plugin/`**：plugin 化产物，给外部用户安装用

迁移完成后（M8' 全部任务收尾），二者将合并到单一源——由 [improvement-backlog.md G15](../docs/improvement-backlog.md) 决策。

## 已知限制

按 [improvement-backlog.md §G](../docs/improvement-backlog.md) 排期：

| #   | 限制                                                                                                                                   | 修复任务                                                           |
| --- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| L2  | ~~CLAUDE.md 通用准则在 plugin 模式下丢失~~ ✅ 已修：G8 拆为 `skills/harness-guidelines/` SKILL；G9 onboard `init` 模式产模板让用户贴   | 已完成（G8 / G9）                                                  |
| L4  | pre-tool-use 灰名单含 `src/main/java/*/domain/*` 和 `pom.xml`，对非 Java 项目静默无副作用；agent description 已加"适用：Java 项目"限定 | G13 — 用非 Java demo 项目实测（路径不匹配 = 静默 no-op，已设计好） |
| L5  | ~~MCP 凭据 `.env` 在用户项目侧维护，本 plugin 提供 `.env.example` 模板~~ ✅ 已修：`plugin/.env.example` 已就位                         | 已完成（G11）                                                      |

### 环境兼容性

| #   | 现象                                                                                                                                                                  | plugin 应对                                                                                                       |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| E1  | **OpenAI-compatible 代理网关**（new-api / one-api 等）在转发 Claude Code 的 sub-agent 调用时上游 panic（`nil pointer` / `500` / `0 tool uses 0 tokens`）。非 plugin bug | F9：SubagentStop hook 检测沉默失败（空输出 / panic / timeout / 500 / 短输出）→ stderr 提示主 Claude 降级到主对话回答 |
|     | **缓解**                                                                                                                                                              | 直连 `api.anthropic.com`，或确认代理版本支持 Claude Code 的 sub-agent invocation；F9 让 plugin 在代理抖动时不致 hang |

## 路线 / 文档

- 战略决策：[ADR-0005](../docs/adr/0005-pivot-to-plugin.md)
- 里程碑路线：[roadmap.md §7](../docs/roadmap.md)（M8' Plugin 化）
- 任务清单：[improvement-backlog.md §G](../docs/improvement-backlog.md)（G1-G15）
- 三层架构：[ADR-0001](../docs/adr/0001-three-layer-harness.md)
- 工程化规则：[rules/engineering-practices.md](rules/engineering-practices.md)

## License

MIT（与 myHarness 主项目一致）。
