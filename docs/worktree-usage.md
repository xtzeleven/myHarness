# Worktree 使用规范

**Status**: Accepted（D6 落地）
**Date**: 2026-05-19

> **本文回答**：什么时候用 git worktree？怎么开？跨 worktree 状态怎么共享？哪些坑别踩？

## 1. 何时用 worktree

- **典型场景**：边修线上紧急 hotfix，边在长 feature 分支推进；不想 stash / 切来切去
- **多 Claude Code session 并行**：每个 worktree 一个 Claude 进程，互不干扰；主 worktree 跑 feature，子 worktree 跑 review
- **subagent 隔离**：在 agent frontmatter 加 `isolation: worktree`，让 sub-agent 各自独立 checkout

**不该用 worktree 的场景**：

- 一次性小改 / 简单 typo → 直接在主 worktree 改
- 跟项目根目录强耦合的工具调试（修 hook / 修 settings.json） → 留在主 worktree
- 团队多人协作的同一分支 → 直接拉 PR，别开 worktree

## 2. 怎么开

### CLI

```bash
claude --worktree                  # Claude 帮你随机命名
claude --worktree my-feature       # 指定名字
claude --worktree my-feature --tmux  # 同时开 tmux session
```

worktree 创建在 `.claude/worktrees/<name>/`（已在 `.gitignore`）。

### 会话内

用户对主 Claude 说："**用 worktree 做这个**" → 主 Claude 调 `EnterWorktree` 工具。

**重要**：本项目约定 — 主 Claude **不主动**进 worktree。除非用户明确说 "worktree"，或 CLAUDE.md / memory 指示，否则保持当前 cwd。

### 退出

```
exit worktree                    # 用户指令；保留分支 + 文件
remove worktree                  # 用户指令；删 worktree 目录 + 分支
```

或者直接关 Claude，再用 `git worktree remove` 手动清理。

## 3. 跨 worktree 状态如何处理

### 自动聚合（已实现）

| 状态                     | 跨 worktree 行为                                                                                          |
| ------------------------ | --------------------------------------------------------------------------------------------------------- |
| `.claude/.audit.log`     | **自动聚合到主仓库**：`policy-dispatch.py` 用 `git rev-parse --git-common-dir` 检测，子 worktree 写主仓库 |
| `.claude/.session.state` | **不聚合**：每 worktree 独立任务状态（一个会话一个任务）                                                  |
| `.claude/.session.hints` | **不聚合**：per-session 提示去重，子 worktree 独立                                                        |
| `.audit.log` summary     | `audit-log-summary.py` 同样 worktree-aware；任意 worktree 跑都看到主仓库 baseline                         |

### 自动复制（已配置）

`.worktreeinclude` 列出新建 worktree 时从主仓库自动复制的 untracked + gitignored 文件：

- `.env` / `.env.local` / `.env.*.local`：MCP 与外部连接配置
- `.claude/settings.local.json`：个人偏好

**注意**：tracked 文件（`pom.xml` / `.mcp.json` / `CLAUDE.md` ...）随分支 checkout 自动出现，无须列入。

### 覆盖路径

如果想强制写到自定义位置（例如多仓库共享）：

```bash
export HARNESS_AUDIT_LOG_PATH=~/.claude/audit/myharness.log
```

`audit-log-summary.py` 也支持 `--log-path <path>` 临时读其他位置。

## 4. 反模式

- ❌ **nested worktree**（worktree 内再开 worktree）：git 不支持，Claude 也不知所措
- ❌ **改主仓库 .gitignore 不同步到 worktree**：worktree 共享同一 .gitignore，不会漂
- ❌ **依赖 `.claude/.audit.log` 在 worktree 内本地写入**：子 worktree 写的是主仓库的 log，主仓库的 `bypass 阈值告警 / 上周 audit summary` 会包含所有 worktree 的活动
- ❌ **在 worktree 内跑 `mvn clean install` 期望走主仓库 `target/`**：每 worktree 独立编译，独立 `target/`，磁盘占用乘 N
- ❌ **主 Claude 自作主张进 worktree**：本项目 CLAUDE.md 约定要用户明确请求

## 5. 已知限制

- **Maven `target/` 磁盘占用**：M8 实例化后每 worktree 独立编译。`mvn clean` 仅清当前 worktree
- **MCP 连接共享 `.env`**：靠 `.worktreeinclude` 复制初始版本；如改了 `.env`，需手动复制到各 worktree
- **Windows 路径长度**：`.claude/worktrees/<name>/src/main/java/...` 可能超 260 字符，建议 worktree 名短（< 20 字符）
- **subagent 内 `isolation: worktree` 与本项目 `.session.state` 冲突**：sub-agent 自己的 worktree 内 `.session.state` 是空的；M8 后如果用，需主对话显式同步状态。当前**不推荐**给本项目 agents 加这个 frontmatter，等真有并行编辑需求再开

## 6. 与现有约束的协同

| 机制                                        | 在 worktree 内的行为                                                               |
| ------------------------------------------- | ---------------------------------------------------------------------------------- |
| PreToolUse 黑+灰名单 (`policy-dispatch.py`) | ✅ 正常工作；规则用 basename / 子路径匹配，worktree cwd 切换不影响命中             |
| `HARNESS_BYPASS=1`                          | ✅ 与 worktree 正交；bypass 写入主仓库 audit log（聚合后阈值告警跨 worktree 共享） |
| Auto mode（Claude Code permission mode）    | ✅ 与 worktree 正交；audit log 自动记 `permission_mode` 字段，跨 worktree 可见     |
| `statusline.py`                             | ✅ 自动适配；`git rev-parse --abbrev-ref HEAD` 返回当前 worktree 的分支            |
| `/commit` 命令                              | ✅ 在 worktree 内提交即提到对应分支；主 worktree 不受影响                          |
| Maven 编译                                  | 各 worktree 独立 `target/`；不冲突但占用磁盘                                       |

## 7. 修订记录

| 版本 | 日期       | 变更                                                                                            |
| ---- | ---------- | ----------------------------------------------------------------------------------------------- |
| v0.1 | 2026-05-19 | 初稿（D6 落地）：audit log 自动聚合 + `.worktreeinclude` + `.gitignore` 加 `.claude/worktrees/` |
