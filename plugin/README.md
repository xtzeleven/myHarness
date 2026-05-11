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
├── hooks/         (6 + 3 tests)  # session-start / user-prompt-submit / pre-tool-use
│                                 # / format / stop-check / subagent-stop
│                                 # tests: pre-tool-use / secret-detection / user-prompt-submit
├── hooks/hooks.json              # hook 注册（用 ${CLAUDE_PLUGIN_ROOT}）
├── scripts/       (2)            # audit-context-cost.py / audit-log-summary.py
├── rules/         (1)            # engineering-practices.md（15 节）
└── .mcp.json                     # MySQL 只读 MCP（凭据在用户侧 .env）
```

调用所有命令统一加 `harness:` 前缀（namespace 由 plugin.json `name` 字段定义）。

## 与根 `.claude/` 的关系（共存期）

当前 myHarness 仓库根的 `.claude/`（原始 Harness 资产）与本 `plugin/`（plugin 化产物）**并行存在**：

- **根 `.claude/`**：在 myHarness 仓库内继续生效，作为 plugin 的"权威源"
- **`plugin/`**：plugin 化产物，给外部用户安装用

迁移完成后（M8' 全部任务收尾），二者将合并到单一源——由 [improvement-backlog.md G15](../docs/improvement-backlog.md) 决策。

## 已知限制

按 [improvement-backlog.md §G](../docs/improvement-backlog.md) 排期：

| #   | 限制                                                                                                                             | 修复任务                                            |
| --- | -------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| L2  | CLAUDE.md 11 节"硬注入"在 plugin 模式下丢失（plugin 没有项目级 CLAUDE.md 等价物）                                                | G8 / G9 — 通用准则拆 skill，项目模板进 onboard 命令 |
| L4  | pre-tool-use 灰名单含 `src/main/java/*/domain/*` 和 `pom.xml`，对非 Java 项目静默无副作用，但 agent description 仍带 Java 关键词 | G13 — 用非 Java demo 项目实测                       |
| L5  | MCP 凭据 `.env` 在用户项目侧维护，本 plugin 提供 `.env.example` 模板（待 G11 完成）                                              | G11                                                 |

## 路线 / 文档

- 战略决策：[ADR-0005](../docs/adr/0005-pivot-to-plugin.md)
- 里程碑路线：[roadmap.md §7](../docs/roadmap.md)（M8' Plugin 化）
- 任务清单：[improvement-backlog.md §G](../docs/improvement-backlog.md)（G1-G15）
- 三层架构：[ADR-0001](../docs/adr/0001-three-layer-harness.md)
- 工程化规则：[rules/engineering-practices.md](rules/engineering-practices.md)

## License

MIT（与 myHarness 主项目一致）。
