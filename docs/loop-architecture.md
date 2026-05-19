# Loop Architecture — Agent 调度与中断恢复

**Status**: Accepted (M5)
**Date**: 2026-05-09

> **本文回答**：主对话与 sub-agent 怎么协作？任务跨多 agent 时怎么调度？某个 agent 失败时怎么办？长任务被中断后怎么续？

## 1. 角色与生命周期

### 角色

| 角色       | 谁                                             | 职责                                                        |
| ---------- | ---------------------------------------------- | ----------------------------------------------------------- |
| **Driver** | 主对话 Claude                                  | 接收用户请求、决定调度、汇总结果、对用户负责                |
| **Worker** | sub-agent                                      | 接受 Driver 委派、独立完成子任务、返回结构化结果            |
| **Hook**   | PreToolUse / PostToolUse / Stop / SessionStart | 在 Driver / Worker 行动前后注入约束                         |
| **Memory** | `~/.claude/projects/<id>/memory/`              | 跨会话状态 + 协作偏好 + 踩坑                                |
| **State**  | `.claude/.session.state` (gitignored)          | 当前会话**中间状态**（M5 引入），含未完任务 / 进度 / 检查点 |

### 生命周期

```
用户请求
  ↓
[Driver 接收]
  ↓
[Driver 拆解 → 调度决策] ──► 直接做（简单任务）
  │
  ├──► [Worker A] ──┐
  ├──► [Worker B] ──┼─► [Driver 汇合 → 检查 → 续派 / 完成]
  ├──► [Worker C] ──┘
  ↓
[Hook 拦截?] ─► 是 ─► [向用户索权] ─► 重试或调整
  ↓
[Driver 报告用户]
  ↓
[Stop hook 摘要 + State 持久化]
```

**Driver 永远不在 Worker 内部**——Worker 不能 spawn 别的 Worker（避免无界递归）。如果 Worker 觉得需要别人，**返回给 Driver**，由 Driver 决定下一步。

## 2. 调度决策树

Driver 收到任务后，先按下表决定调度方式：

```
任务 X
  │
  ├─ 简单且 ≤ 3 步？           ──► Driver 直接做（不 spawn）
  │  例: "改个 typo"、"读这个文件"
  │
  ├─ 单一专项 agent 能解？     ──► spawn 单个 Worker
  │  例: "review 这个 Spring 文件" → spring-boot-reviewer
  │
  ├─ 多 agent 但相互独立？    ──► 并行 spawn
  │  例: "全面 review PR" → code-reviewer + spring-boot-reviewer + schema-analyst（同时跑）
  │
  ├─ 多 agent 但有依赖？      ──► 串行 spawn
  │  例: "加一张表" → ddd-architect (设计) → schema-analyst (review) → migration-author (落 SQL)
  │
  └─ 需要用户决策？           ──► 暂停 + AskUserQuestion，不 spawn
     例: "选哪种聚合边界" → 给 2-3 候选问用户
```

### 并行的硬规则

并行 Worker **必须**满足：

- 输入相互独立（不依赖彼此输出）
- 输出可独立汇总（Driver 能合并，不需要互相补全）
- 不写同一文件（避免冲突；Worker 应只读，写由 Driver 执行）

不满足任一条 → 退化为串行。

### 串行的硬规则

串行 Worker 链 **必须**满足：

- 链长 ≤ 4（再深的拆成多次会话）
- 每环检查点：Driver 在每个 Worker 返回后**显式判定**是否继续，不自动接续
- 失败传播：第 N 环失败 → 不擦除前 N-1 环结果，记入 State，等用户决策

## 3. 三类策略

### Retry（重试）

**适用**：瞬时失败（网络抖动、命令超时、CI 偶发）。

| 失败类型                 | 重试                             |
| ------------------------ | -------------------------------- |
| 网络 / API 超时          | ≤ 3 次，指数退避（1s / 2s / 4s） |
| Bash 命令超时            | 1 次，加 timeout 倍增            |
| MCP 连接失败             | 1 次，仍失败 → 走 degradation    |
| Hook 输出"⚠️ 待人工授权" | **不重试**，转 escalation        |

**禁止重试**：任何失败信息显示是逻辑错误（语法错、找不到文件、权限问题）。重试只是浪费 token。

### Escalation（升级）

| 触发                         | 升级方向                           |
| ---------------------------- | ---------------------------------- |
| Worker 卡住 / 输出"我不确定" | sonnet → opus（同 agent 换模型）   |
| 同 agent 重试 2 次仍失败     | Worker → Driver（Driver 重新决策） |
| Driver 也无法决策            | Driver → 用户（AskUserQuestion）   |
| Hook 灰名单                  | 任何角色 → 用户（强制人工授权）    |
| 跨 BC / 跨技术栈问题         | 单一专项 agent → 多 agent 并行评审 |

升级**永不向下**：用户做出决定后，Driver 重新调度时回到原层级。

### Degradation（降级）

工具失败时的降级链：

```
gitnexus-exploring  ──失败──►  Glob + Grep  ──失败──►  ls + cat（手动）
gitnexus-impact-analysis ──失败──►  git grep + 手动 trace
mysql-readonly MCP  ──失败──►  读 schema.sql 文件  ──失败──►  问用户提供
prettier (npx)  ──失败──►  跳过格式化（Worker 注明"未格式化"）
ruff (本机)  ──失败──►  跳过（本项目无 .py 代码，不影响）
```

**降级原则**：能完成主任务前提下选最简路径；失败但仍交付（注明降级路径），不要因工具不可用而拒绝任务。

### 硬上限（防长链路失控）

为防止 retry/escalation/degradation 组合下无界消耗，本架构所有 loop 路径都有强制上限。**任何一项触顶必须立刻停下问用户**，不可静默继续：

| 维度              | 上限                           | 触顶后行为                                             |
| ----------------- | ------------------------------ | ------------------------------------------------------ |
| 串行链长度        | ≤ 4 环                         | 拆成多次会话，本会话写 `.session.state` 终止           |
| 并行 Worker       | ≤ 5 个/批次                    | 超 5 个 → Driver 收敛任务粒度后再分批                  |
| 单 Worker retry   | ≤ 2 次（同模型）               | 第 3 次 → escalate 模型 / 换 agent                     |
| 同 agent 累计调用 | ≤ 3 次/单任务                  | 第 4 次 → 升级到用户决策                               |
| Escalation 链     | ≤ 3 步（agent / model / 用户） | 第 3 步必须到用户；不允许 agent↔agent 互推            |
| Degradation 链    | ≤ 2 级（首选 → 备选 → 问用户） | 备选也失败 → 不得再换工具，转用户                      |
| 单任务挂钟        | ≤ 30 min（建议）               | 超 30 min 主动 checkpoint 到 `.session.state` 后再继续 |

**记账原则**：上限按"单任务"计；用户授权后开始新任务，计数器重置。Driver 在每次 Worker 返回时**显式**比对上限，不依赖直觉。

## 4. 中断与恢复

### 中断来源

1. 用户主动中断（Ctrl-C / 关会话）
2. 上下文窗口接近耗尽（compaction 触发）
3. Hook 灰名单未授权
4. 系统错误（API down 等）

### 恢复机制

引入 **`.claude/.session.state`**（已 .gitignore）记录：

```json
{
  "ended_at": "2026-05-09T16:42:00Z",
  "branch": "main",
  "head_sha": "abc1234",
  "head_msg": "feat: M5-T1 写 loop-architecture.md",
  "uncommitted_count": 2,
  "current_task": "M5-T1 写 loop-architecture.md",
  "pending_steps": ["M5-T1.3 中断恢复", "M5-T1.4 自反馈环"],
  "blocked_on": null,
  "last_checkpoint": "2026-05-09T16:42:00Z"
}
```

由 Stop hook 写入；SessionStart hook 读取并注入到上下文。

### 中断恢复流程

```
新会话开始
  ↓
SessionStart hook 注入：
  - 当前分支 / 最近 commit
  - .session.state 中的 pending_steps
  - MEMORY.md 索引（按需引用）
  ↓
Driver 看到 "上次会话有 3 步未完" 提示
  ↓
Driver 主动问用户："要续上次的 M5-T1，还是开新事？"
  ↓
续 → 从 pending_steps[0] 开始
新 → 把旧 state 归档到 memory/session_*.md
```

## 5. 自反馈环

让 agent 互相审，避免单 agent 偏见。

### 自反馈触发条件

只在以下场景启用（不全开，控制成本）：

| 主 Worker                       | 反馈 Worker      | 触发                                     |
| ------------------------------- | ---------------- | ---------------------------------------- |
| `ddd-architect` 给出聚合设计    | `docs-keeper`    | 设计是否完整文档化（建议是否含落地路径） |
| `migration-author` 写 migration | `schema-analyst` | migration 是否在已有 schema 上安全       |
| `tdd-cycle-driver` 完成 GREEN   | `code-reviewer`  | 实现是否符合通用 quality                 |
| 任何 Worker 改 `domain/` 边界   | `ddd-architect`  | 是否符合 DDD 分层准入                    |

### 自反馈 ≠ 串行链

区别：

- **串行**：A 输出是 B 输入，B 在 A 基础上**继续工作**
- **自反馈**：A 已完成，B **审查** A 的输出，发现问题 → escalate 给 Driver

自反馈不写同一文件，只产报告。

## 6. 周期任务（与本架构的衔接）

详见 `docs/periodic-tasks.md`（M5-T4 产出）。要点：

- 会话内：`/loop 30m /audit-practices` 定时跑工程化自检
- 仓库级：GitHub Actions 定时 workflow（每日 / 每 PR）

周期任务**不**修改 `.session.state`，避免污染主对话状态。

## 7. 反模式

- ❌ Worker 内 spawn 别的 Worker（无界递归）
- ❌ 并行 Worker 写同一文件（冲突）
- ❌ 串行链长度 > 4（拆成多次会话）
- ❌ Hook 灰名单触发后 retry（绕过授权）
- ❌ 自动 escalate 而不告知用户（用户应当永远知道当前层级）
- ❌ Driver 在 Worker 失败时静默重试 N 次（应有上限并告知）
- ❌ 跨会话状态写在 git 仓库（应在 .session.state，gitignored）

## 8. 与已有组件的关系

| 已有组件                     | 在本架构中的位置                                     |
| ---------------------------- | ---------------------------------------------------- |
| 8 个 sub-agent               | Worker 池；调度由本文规则                            |
| 4 个 slash command           | Driver 主动触发的多步流程（可包含 spawn Worker）     |
| PreToolUse hook 黑+灰        | 强制约束所有 Bash/Edit；灰名单触发 escalation 到用户 |
| PostToolUse format hook      | 工具调用后自动跑，不进入 loop（独立异步）            |
| Stop hook                    | 写 `.session.state`（M5 后开始）                     |
| SessionStart hook（M5 新增） | 读 `.session.state`、注入 memory 索引                |
| `/audit-practices`           | Driver 周期触发的健康检查                            |
| `/sync-docs`                 | Driver 触发，内部 spawn `docs-keeper`                |
| Memory（M4 启用）            | 决策原因 + 踩坑 + （M5 后）会话事实                  |

## 9. 下一步（M6+ 准备）

本文未涉及但 M6 / M7 要做的：

- **token 成本观测**（M6）：Worker 调用消耗多少 token，决定何时该启用 compaction
- **policy 机制化**（M7）：何时升 opus（不只是凭感觉），写入 settings.json 或 agent metadata
- **审计日志**（M7）：本文的 escalation / degradation 决策应有日志

## 10. 修订记录

| 版本 | 日期       | 变更          |
| ---- | ---------- | ------------- |
| v0.1 | 2026-05-09 | 初稿，M5 落地 |
