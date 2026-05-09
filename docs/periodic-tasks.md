# Periodic Tasks — 周期任务设计

**Status**: Accepted (M5-T4)
**Date**: 2026-05-09

> **本文回答**：项目级与会话级的周期任务怎么配？哪些自检该自动跑？

按 [roadmap §8 D2](roadmap.md#8-关键决策点待用户确认) 的决策：**会话内 `/loop` skill + 仓库级 GitHub Actions 定时**两道并行。

## 1. 会话内（/loop skill）

### 用法

`/loop` 在 Claude Code 当前会话内**周期触发**指定的 prompt 或 slash command。两种模式：

**固定间隔**：
```
/loop 30m /audit-practices
```
每 30 分钟跑一次 `/audit-practices`，直到用户停止或会话结束。

**动态间隔（默认）**：
```
/loop /audit-practices
```
默认 10 min；适合长会话中的"后台健康检查"。

### 推荐周期任务（会话内）

| 场景 | 命令 | 何时启用 |
|------|------|---------|
| 长 review 会话健康检查 | `/loop 30m /audit-practices` | 跑大型 review > 1 小时时 |
| 文档持续巡检 | `/loop 1h /sync-docs` | 修代码 + 修文档同时进行的会话 |
| 测试守护 | `/loop 5m mvn -q test` | M8 实例化代码后；TDD 红绿期间 |

### 不该用 /loop 的场景

- 一次性任务（写一个文件 → 不要 `/loop`）
- 需要用户输入的任务（loop 内没法 AskUserQuestion）
- 有破坏性副作用的（如 `/loop git push`，绝对不行）
- 会话结束就该停的（loop 不跨会话）

### 与 loop-architecture.md 的关系

`/loop` 是**Driver 主动触发**的周期；不进入主对话的 spawn 链。**周期任务不写 `.session.state`**，避免污染主任务进度。

## 2. 仓库级（GitHub Actions 定时）

### 已有：`lint.yml`

由 push / PR 触发，跑 prettier + 必需文件 + JSON 校验 + AGENTS 链接 + .gitignore 防泄密 + .mcp.json 变量同步 + git +x 校验。**不周期**。

### 新增：`scheduled.yml`（M5 引入）

定时跑工程化健康检查，独立于 PR / push。

#### 触发节奏

- **每天 09:00 UTC**：审计实践健康度（结构 + memory 索引一致性）
- **每周一 03:00 UTC**：依赖 / 工具版本漂移检查
- **手动**：`workflow_dispatch`

#### 跑什么

| Job | 内容 | 失败动作 |
|-----|------|---------|
| daily-structure-audit | 跑 lint.yml 同样的 structure-check job | 创建 issue（不阻塞） |
| weekly-stale-check | 看仓库是否 7 天无 commit + 是否有 PR > 14 天未合 | 仅警告（issue / 评论） |
| weekly-tool-versions | 检查 prettier / actions 版本是否过期 | 仅警告 |

**重要**：调度型 workflow **不能**直接 fail repo（会噪音）；用 issue / 评论方式给提示，而不是 status check。

### 触发关系

```
push/PR  ──► lint.yml          ──► block merge if fail
schedule ──► scheduled.yml     ──► open issue (no block)
manual   ──► workflow_dispatch ──► 任一 yml 都可手动触发
```

## 3. 与 hook 的关系

| 触发 | 谁 | 何时 | 关系 |
|------|---|------|------|
| 工具调用前 | PreToolUse hook | 每次调工具 | **不周期** |
| 工具调用后 | PostToolUse hook | 每次写文件 | **不周期** |
| 会话开始 | SessionStart hook | 一次性 | 注入"上次会话未完" |
| 会话结束 | Stop hook | 一次性 | 写 .session.state |
| 会话内周期 | `/loop` | 用户/Driver 启动 | 不写 state |
| 仓库周期 | GH Actions schedule | cron | 完全独立于会话 |

## 4. 反模式

- ❌ 用 `/loop` 跑会改文件的命令（如 `/loop /commit`）—— 周期写文件等于自动提交，危险
- ❌ 用 GH Actions schedule 跑 push 类操作 —— 调度任务应只读 / 只创 issue
- ❌ schedule 失败时直接 fail repo —— 会让 main 一直红，应当只 open issue
- ❌ 把周期任务的状态写进 `.session.state` —— 污染主任务进度
- ❌ /loop 与 GH Actions 重复同一项检查 —— 选一道，不要两边都跑

## 5. M5 后的扩展

- **M6**：context 治理后，加 `/loop /audit-context-cost.py`（每周看 token 注入成本）
- **M7**：审计日志启用后，加每日审计日志摘要 issue
- **M8**：实例化代码后，加 `/loop 5m mvn -q test`（TDD 期间）
