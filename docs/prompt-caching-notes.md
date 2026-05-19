# Prompt Caching Notes

**Status**: Reference (C8 文档化)
**Date**: 2026-05-19
**Audience**: 维护 CLAUDE.md / agents / commands / hooks 的人

> **本文回答**：本项目哪些"载体"会被 Claude Code 自动 cache？什么改动会"打掉" cache？怎么尽量保持 cache hit？
>
> 本项目**不使用** Anthropic SDK 写代码（无 `import anthropic`），所以本文不涉及 SDK 层 `cache_control` 字段；只覆盖 Claude Code CLI 用户能影响的部分。

## 1. Claude Code 内置 cache 行为

Claude Code 对**每会话**的 system prompt 与早段消息自动启用 Anthropic prompt caching（5 分钟 TTL，最长 1 小时增量延期）。**用户无需配置**。

### 自动入 cache 的载体（按"被打掉的代价"排序）

| 载体                                        | 入 cache 时机               | 改动一次的代价                                  |
| ------------------------------------------- | --------------------------- | ----------------------------------------------- |
| **CLAUDE.md**（每会话注入）                 | 会话开始时                  | **重 cache 全部**；高频改 = 每会话都 cache miss |
| `.claude/rules/engineering-practices.md`    | 被 CLAUDE.md / agent 引用时 | 中：仅引用它的会话 miss                         |
| `AGENTS.md`                                 | 主 Claude 路由时            | 中                                              |
| `~/.claude/projects/<dir>/memory/MEMORY.md` | SessionStart 注入           | 中：MEMORY.md 索引行                            |
| 单条 memory 文件（`decision_*` 等）         | 按需 Read 时                | 低（一次性读取）                                |
| Agent frontmatter / 正文                    | spawn agent 时              | 低：仅该 agent 子上下文                         |
| Hook 脚本本身                               | 执行时（不入 prompt cache） | 无 cache 影响                                   |

## 2. 适合 cache 的内容

**"稳定 + 大量 + 高频引用"** 三者交集是最佳 cache 候选：

- ✅ **CLAUDE.md 行为准则段（§1-§4）**：跨会话稳定，每会话注入 → 极适合
- ✅ **engineering-practices.md 节标题与结构**：表格 / 节目录类内容稳定
- ✅ **AGENTS.md 路由速查表**：agent 数量周期性变化，但行内描述稳定
- ✅ **ADR / memory（决策原因类）**：写完就冻结，几乎不改

## 3. 不适合 cache（或频繁打掉 cache）

- ❌ **会话事实**（当前 git status / 当前任务 / 剩余 TODO）：本来就该频繁变 → 不要写入 CLAUDE.md，应放 `.session.state`
- ❌ **临时实验性配置**：放 `.claude/settings.local.json`（gitignored）而非 settings.json
- ❌ **每次 audit 的临时输出**：用 stdout，不写进 markdown
- ❌ **CHANGELOG 头部**：每次发版变化，但 cache miss 仅影响"刚改完 CHANGELOG"那一会话，可接受
- ❌ **每次都改的 backlog §A/B/C 优先级**：频繁切换会损失 cache；幸好本项目 backlog 主要在 §E 追加，§A-§C 改动稀疏 → 实测影响小

## 4. 保 cache hit 的工程实践

### 4.1 文档结构稳定，行内迭代

CLAUDE.md / engineering-practices.md / AGENTS.md 已经按"小节固定，行级迭代"的方式维护：

- 节标题 / 表头 / 行顺序基本不动 → cache 友好
- 新增内容追加到既有节末尾，不重排
- 大改时（如撤 plugin / 加新维度）认 cache miss，但发生频率低

**反模式**：每次会话都改 CLAUDE.md 的 §1 行为准则 = 每会话都 cache miss。

### 4.2 频繁状态走 `.session.state`，不进 CLAUDE.md

- 当前任务 / pending steps / 阻塞原因 → `.session.state`（SessionStart 注入摘要，不入 cache 主体）
- 本会话临时偏好 / 实验配置 → `.claude/settings.local.json`

### 4.3 长内容按 5 分钟 TTL 节奏使用

ScheduleWakeup / loop 自动调度时已遵循 5 分钟边界（见 `docs/loop-architecture.md`）：

- 沉睡 ≤ 270s：cache 保持
- 沉睡 ≥ 1200s：明确认 miss + 用更长周期摊销

### 4.4 大段稳定内容用引用而非粘贴

例：AGENTS.md 不复述 engineering-practices §15 表，而是写"详见 …"。引用比展开 cache 友好（多个文件被 Read 时各自命中）。

## 5. 度量 cache 效率（如何知道是否生效）

本项目目前不直接读取 prompt cache token 数。两种可见信号：

- `statusline.py` 输出 `token` 字段（来自 Claude Code 注入的 cost JSON）—— 跨会话对比同类任务 token 用量
- `/audit-context` 估算注入成本（见 `.claude/commands/audit-context.md`） —— 看 CLAUDE.md / MEMORY.md / 规则文档的字节占比

cache miss 后单次会话 token 用量明显高（因为 system prompt 全量算钱），用 statusline + audit-context 周对周对比可识别异常。

## 6. 反模式速查

- ❌ **CLAUDE.md 写当日日期 / 当前 git HEAD** → 每天 / 每 commit 都 cache miss
- ❌ **每次新建 ADR 时改 ADR-0001** → ADR 应只追加，已写的不动
- ❌ **engineering-practices.md 加"todo: 等修"占位** → 等修是 backlog 的事，不进规则文档
- ❌ **MEMORY.md 索引行超 150 字 / 行后追加新行越界** → SessionStart 注入会截断，且打 cache
- ❌ **agent frontmatter description 频繁微调措辞** → 每次 spawn 都 miss 该 agent cache

## 7. 与 Anthropic SDK 项目的差异（仅作参考）

如果将来本项目衍生出 SDK 应用（非主目标），需要：

- 显式给长 system prompt 加 `cache_control: {"type": "ephemeral"}`
- 监控 `cache_creation_input_tokens` vs `cache_read_input_tokens` 比例
- 选型参考 `claude-api` skill（已在环境中）

当前本项目**纯 Claude Code 用户视角**，上述均不适用。

## 8. 修订记录

| 版本 | 日期       | 变更                  |
| ---- | ---------- | --------------------- |
| v0.1 | 2026-05-19 | 初稿（C8 / E42 落地） |
