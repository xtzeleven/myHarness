# Context Management — 上下文治理

**Status**: Accepted (M6)
**Date**: 2026-05-09

> **本文回答**：每会话注入了多少 token？哪些是浪费？怎样按需而非全量加载？长会话怎么收尾？M8 后子目录 CLAUDE.md 怎么拆？

## 1. 三类注入来源

| 来源                       | 何时                           | 是否每会话             | 控制方法           |
| -------------------------- | ------------------------------ | ---------------------- | ------------------ |
| **CLAUDE.md（项目根）**    | 会话开始自动                   | ✅ 全量                | 控字数 + 拆子目录  |
| **CLAUDE.md（子目录）**    | 主对话进入对应目录时按需       | ❌ 局部                | M8 后启用          |
| **`.claude/rules/*.md`**   | 主对话主动 Read                | ❌                     | 按需               |
| **`.claude/agents/*.md`**  | 主对话决定 spawn 时            | ❌                     | sub-agent 隔离     |
| **`docs/*.md`**            | 主对话主动 Read                | ❌                     | 按需               |
| **Memory**                 | MEMORY.md 索引被加载，条目按需 | ⚠️ 索引每次 + 条目按需 | 索引 ≤ 150 char/行 |
| **SessionStart hook 输出** | 会话开始                       | ✅                     | 控输出长度         |
| **PreToolUse hint stderr** | 工具调用前（M6-T3 引入）       | ❌                     | 仅在高价值场景触发 |

**只有第一项（项目根 CLAUDE.md）和 SessionStart 输出真正"每会话付费"**。其他都是按需加载。优化重点应该放在前两者。

## 2. Token 预算

**目标**：每会话**自动注入**部分（不含按需 Read 的） ≤ **8K tokens**。

| 部件                          | 当前估算 | 目标上限 |
| ----------------------------- | -------- | -------- |
| CLAUDE.md（项目根）           | ~3K      | 4K       |
| MEMORY.md 索引                | ~0.5K    | 1K       |
| SessionStart 输出             | ~0.3K    | 0.5K     |
| 系统模板 / 工具描述（不可控） | ~?       | —        |
| **合计自动注入**              | ~3.8K    | ≤ 8K     |

按需注入的 rules / agents / docs 不计入预算（只算实际被加载的）。

## 3. M6-T1 Token 审计脚本

详见 `.claude/scripts/audit-context-cost.py`。能力：

- 列出"每会话自动注入"候选文件的 token 数
- 列出按需 Read 候选（rules / agents / docs）的 token 数
- Top-N 消费者排名
- 给出"减重建议"（如某节超过阈值建议拆出去）

调用方式：

```bash
python .claude/scripts/audit-context-cost.py            # 全部
python .claude/scripts/audit-context-cost.py --auto     # 仅自动注入
python .claude/scripts/audit-context-cost.py --top 10   # Top 10
```

或用 `/audit-context` 命令（M6-T1.1）。

## 4. M6-T3 按需注入（PreToolUse hint）

主 Claude 不可能每次工具调用前主动判断"是否需要某 agent 的规则"。在 `pre-tool-use.sh` 加 hint 段：根据 file_path / command 模式输出 stderr **建议**，主 Claude 看到后可主动 prefetch。

| 触发模式                                      | 提示内容                                                 |
| --------------------------------------------- | -------------------------------------------------------- |
| 改 `pom.xml`                                  | "考虑读 maven-build-doctor 与 engineering-practices §13" |
| 改 `src/main/java/.../domain/` 下文件         | "考虑读 ddd-architect 与 engineering-practices §12"      |
| 改 `src/main/java/.../infrastructure/` 下文件 | "考虑读 spring-boot-reviewer"                            |
| 改 `db/migration/` 下文件                     | "考虑读 migration-author 规则"                           |
| 调 `mysql`/`psql` SELECT 类                   | "考虑用 schema-analyst 而非手拼 SQL"                     |
| 改 `.mcp.json` / `.env.example`               | "考虑读 engineering-practices §14（MCP 治理）"           |
| 改 `application.yml`                          | "考虑读 spring-boot-reviewer §5（配置）"                 |

**关键约束**：hint 只输出**已存在的文件路径**作为建议，不直接注入内容。让主 Claude 判断要不要 Read。

**关键约束**：hint **不阻塞**（exit 0），只 stderr 输出 `💡 提示:` 前缀的建议。

## 5. M6-T4 上下文压缩策略

### 自动 compaction

Claude Code 有内置 auto-compact，在上下文接近耗尽时自动总结。本项目**不重写 auto-compact**，但补两道：

1. **会话主动总结**：长会话超过 ~50% 上下文时，由 Driver 主动用 sub-agent 总结当前进度（spawn `docs-keeper` 或自定义 summarizer）写入 `.session.state` 的 `current_task` + `pending_steps`。
2. **检查点写入 memory**：会话结束前如有重要中间结论，主动写一条 `session_*.md` memory。

### 不该做的

- ❌ 把整个 git diff 粘进对话（用 `git diff --stat` 摘要 + 必要时按文件 Read）
- ❌ 一次读 5+ 个 agent 文件（按需读，不预热）
- ❌ 把 sub-agent 输出原文回贴主对话（让 sub-agent 输出本身就是摘要）

## 6. M8 后：子目录 CLAUDE.md

按 [roadmap D3](roadmap.md#8-关键决策点待用户确认)：**默认两层**，不深入到聚合粒度。

### 拆分原则

子目录 CLAUDE.md 只放该目录**特有**的规则；通用规则留在根 CLAUDE.md。"我说过的不再说一遍"。

### 计划布局（M8 实例化后）

```
CLAUDE.md                                       根：行为准则 + 项目上下文（全量注入）
src/main/java/<base>/
├── interfaces/CLAUDE.md                        DTO 命名 / Web 层规则 / 不调 Repository
├── application/CLAUDE.md                       事务边界 / Command Handler 风格
├── domain/CLAUDE.md                            ⭐ 重点：纯净规则、聚合规则、VO/Entity 决策
└── infrastructure/CLAUDE.md                    Repository 实现 / 适配器规范
```

### domain/CLAUDE.md 应包含

- 严禁 `import org.springframework`、`import javax.persistence`
- 聚合根的写规则（无 setter / equals 基于 ID 等）
- Repository 接口风格（业务意图命名而非 SQL 投射）
- 领域事件命名（过去式）

### 不该包含

- 任何 application / infrastructure / interfaces 层的规则（在它们各自 CLAUDE.md 中）
- 与根 CLAUDE.md 重复的内容（如行为准则）

## 7. 审计周期

- **每会话开始**：SessionStart 自动跑（不算 audit）
- **手动**：`/audit-context` 跑 token 审计
- **每周**：GH Actions `scheduled.yml` 加一个 `weekly-context-audit` job（M6 后追加）
- **里程碑边界**：每完成一个 M 跑一次手动 `/audit-context`，记录 baseline

## 8. 反模式

- ❌ 把 agent 描述粘到 CLAUDE.md（agent 应当被 spawn 而非注入）
- ❌ 把 ADR 全文塞 CLAUDE.md（ADR 是公开决策追溯，按需 Read）
- ❌ 给 hint 加阻塞性 exit（hint 是建议，不是规则）
- ❌ 让 SessionStart 输出超过 1K token（注入开销大于收益）
- ❌ 子目录 CLAUDE.md 重复根 CLAUDE.md 的内容（增加注入但无新信息）
- ❌ 把 memory 内容直接塞 CLAUDE.md（绕过按需机制）

## 9. 与已有组件关系

| 组件                             | 在 Context 治理中的角色                  |
| -------------------------------- | ---------------------------------------- |
| CLAUDE.md（根）                  | 自动注入主体；M6 后通过 audit 脚本控字数 |
| `engineering-practices.md` 15 节 | 按需 Read；不进 CLAUDE.md                |
| `MEMORY.md` 索引                 | SessionStart 已注入摘要；条目按需加载    |
| `agents/*.md`                    | sub-agent 隔离；不进主对话               |
| `docs/*.md`                      | 按需 Read；不进 CLAUDE.md                |
| SessionStart hook                | 注入"已知最小 useful 状态"               |
| PreToolUse hint（M6 新增）       | 高价值改动时建议 prefetch                |

## 10. M6 完成标准（审计指标）

- [ ] 跑 `/audit-context` 给出 baseline token 数
- [ ] 自动注入 ≤ 8K（如超应拆/精简）
- [ ] 每个 hint 触发模式至少有 2 个真测试 case（避免误导）
- [ ] hint 输出统一 `💡 提示:` 前缀，便于主 Claude 识别
- [ ] M8 后启用子目录 CLAUDE.md 时本文 §6 作为 checklist
