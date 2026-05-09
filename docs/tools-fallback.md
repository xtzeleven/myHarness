# Tools Fallback Chain — 工具失效降级路径

**Status**: Accepted (M7-T2)
**Date**: 2026-05-09

> **本文回答**：MCP 挂了 / gitnexus 索引过期 / prettier 跑不动 / agent 给不出建议时，应当如何降级才能完成主任务？

详见 [loop-architecture.md §3 Degradation](loop-architecture.md) 与 [engineering-practices.md §15 Policy](.claude/rules/engineering-practices.md)。本文给**具体路径**。

## 1. 降级原则

1. **完成主任务优先**：能交付就交付，不要因工具不可用拒绝
2. **显式标注降级**：输出顶部写 "**已降级**: <原工具> 不可用，使用 <替代>"
3. **写审计日志**：每次降级写一条 `.claude/.audit.log`（M7-T4 引入）
4. **不无限链式降级**：每个工具最多 2 级降级，再降则升级到用户

## 2. 工具降级路径

### 代码探索

```
gitnexus-exploring         (结构化检索 / 调用图 / AST)
        ↓ 索引过期 / 不可用
gitnexus-cli reanalyze     (尝试重建索引一次)
        ↓ 仍不可用
Glob + Grep                (文件名 + 内容搜索)
        ↓ 仓库太大无法搜
ls + cat 手动 trace        (最末路)
```

### 影响面分析（重构前）

```
gitnexus-impact-analysis   (符号 / 引用 / 跨文件)
        ↓ 不可用
git grep + manual trace    (按符号名搜，限 src/)
        ↓
ddd-architect agent + 给方案带不确定性    (问用户)
```

### Schema / SQL

```
schema-analyst (走 mysql-readonly MCP)
        ↓ MCP 连接失败
读 src/main/resources/schema.sql / db/migration/*.sql
        ↓ 文件不存在
问用户提供 ddl 截屏 / dump
        ↓ 仍不可用
拒绝继续，明确告知"无 schema 上下文，给不出可信建议"
```

### 代码评审

```
code-reviewer / spring-boot-reviewer (按专项)
        ↓ agent 输出含 "我不确定"
升级 sonnet → opus 重跑一次
        ↓ 仍不确定
升级到用户（"以下 N 处需你判断"）
```

### 格式化

```
prettier (npx) via PostToolUse hook
        ↓ npx 不可用
跳过格式化（输出标注 "未格式化，请手动 prettier --write"）
        ↓ 不影响主任务
```

### 测试（M8 后）

```
mvn test
        ↓ 编译失败
maven-build-doctor agent 诊断
        ↓ 修复后重试
        ↓ 仍失败
读单测一一手动模拟，写 fix 后再跑
```

### 文档同步

```
docs-keeper agent
        ↓ 不可用 / 漂移过多
/sync-docs 命令（手动多采样 + 主对话总结）
        ↓
人工 review 关键文档 (README + CLAUDE + ADR)
```

## 3. 降级 ≠ 失败

降级**仍交付主任务**，只是质量 / 范围有标注：

```
[ddd-architect] 已降级: gitnexus-impact-analysis 不可用（索引过期 7 天），使用 git grep 替代

聚合边界建议：将 Order 与 OrderItem 划入同一聚合根...
[降级影响] 跨聚合引用扫描可能漏；建议合并前用户用 IDE 的 "Find Usages" 复核
```

不是：

```
[ddd-architect] 工具不可用，无法完成任务
```

## 4. 不该降级的场景

某些任务一旦工具不可用就**应该停**而非降级：

| 任务 | 为什么不降级 |
|------|----------|
| 写生产 SQL migration | schema-analyst 不可用 → 必须停（盲改 schema 风险高） |
| 升 spring-boot 大版本 | maven-build-doctor 不可用 → 必须停（兼容性看不见） |
| 跨 BC 重构 | gitnexus-impact-analysis 不可用 → 应停或显式声明"未做影响面分析，仅本 BC 内安全" |
| 删 commit / 改 git 历史 | 任何 hook / 工具问题 → 直接停，问用户 |

**判断准则**：降级后输出仍**对用户有价值**就降；变成"不如不做"就停。

## 5. 与 Permission Gate 的关系

降级**不绕过** Permission Gate：

- 黑名单仍 deny（任何降级都不能改写）
- 灰名单仍要 ask_user（降级期间用户授权一次仍只对当前授权）
- bypass 不应用于降级（bypass 是紧急情况绕 hook，与降级不同）

## 6. 反模式

- ❌ 静默降级（不在输出顶部标注，让用户以为是正常流程）
- ❌ 无限降级（A→B→C→D→E... 走十级，最后发现起初就该停）
- ❌ 把降级当借口（agent 一次 retry 失败就降级，没用尽可用资源）
- ❌ 降级后不写审计日志（无法回放）
- ❌ Permission Gate 失效时降级（hook 都坏了应当停而非降级）

## 7. 与 audit log 的关系

降级写 JSONL 到 `.claude/.audit.log`（M7-T4）：

```json
{"ts": "...", "hook": "agent", "tool": "schema-analyst", "target": "mysql-readonly MCP", "action": "degrade", "reason": "MCP connection failed", "fallback": "schema.sql"}
```

跑 `python .claude/scripts/audit-log-summary.py --type degrade` 可统计降级频次，发现高频降级目标 → 优先修。
