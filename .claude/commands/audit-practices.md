---
description: 工程实践自检清单，对照 engineering-practices.md 15 节逐项打勾
argument-hint: "[focus] 可选：聚焦某一节名（如 ddd / java / mcp / hooks / policy）"
---

# /audit-practices

对当前项目工程化实践做一次自检，按 **15 维度** 逐项打 ✅ / ⚠️ / ❌ 并给一句话依据 + 改进建议。

**优先**对照 `.claude/rules/engineering-practices.md`（含 §1-§11 通用 + §12-§14 领域专项 + §15 Policy）；该文件不存在时退回下方通用清单。

## 15 维度自检清单

### Layer 1 约束层

1. **CLAUDE.md 完备性** — 行为准则 / 项目上下文 / 技术栈 / 目录 / 禁忌 / 测试命令 / 子目录指引
2. **Rules 文档** — `engineering-practices.md` 每节"为什么 / 怎么做 / 达标"三段齐全
3. **PreToolUse 防御** — 黑名单（直接拦）+ 灰名单（人工授权）

### Layer 2 反馈循环层

4. **Hooks** — PostToolUse 格式化 + Stop 提醒 + PreToolUse 防御 至少三件齐
5. **Agents** — `.claude/agents/` 覆盖项目高频场景；description 含触发关键词；最小权限
6. **Commands** — `.claude/commands/` 含日常重复动作（提交 / 评审 / 自检 / 上手 / 同步）

### Layer 3 质量门禁层

7. **CI / 质量门禁** — `.github/workflows/*.yml` 跑 lint + 必需文件 + 配置合法性
8. **Git 卫生** — `.gitignore` 完整、提交 Conventional 风格、`settings.local.json` 不在 tracking
9. **测试 / 校验** — 项目类型对应的测试命令；本项目至少跑 `/audit-practices` 当冒烟

### 支撑层

10. **文档同步** — README / CLAUDE.md / docs 与代码现状一致；ADR 记录关键决策；CHANGELOG 标记发布
11. **可观测 / 审计** — statusLine / Stop hook 摘要 / 决策入 git

### 领域专项（Java + DDD + MCP）

12. **DDD 分层** — 依赖方向单向、domain 层无 Spring/JPA import、`@Transactional` 仅 application 层
13. **Java / Spring 风格** — Lombok 不滥用、循环依赖、N+1、Optional 用法、SLF4J 参数化
14. **MCP 治理** — `.mcp.json` 不含明文凭据、`.env.example` 与 `.mcp.json` 变量对齐、DB 账号确认只读

### 元规则（M7 引入）

15. **Policy 机制化** — model selection / fallback chain / bypass / 升级链 / 审计日志

## 执行步骤

1. **采集**（用 Bash + Read 一次跑完）：

   ```bash
   ls -la CLAUDE.md README.md AGENTS.md docs/AGENTS.backend.md
   ls .claude/{settings.json,rules,hooks,agents,commands}
   ls .github/workflows/
   cat .gitignore | head -30
   git ls-files | grep -E 'settings.local|\.env$'  # 应为空
   git status --porcelain
   ls .mcp.json .env.example
   ```

2. **打分**：逐维度判定，**用证据说话**（引用文件路径或具体行）。

3. **汇总**：按下表输出，最后给"前 3 个最值得动手的改进"。

## 输出模板

```
# 工程实践自检报告 — <YYYY-MM-DD>

## 总览
**层次状态**：L1 ✅ / L2 ⚠️ / L3 ✅ / 支撑 ⚠️ / 领域 ✅

| # | 维度 | 状态 | 依据 | 建议 |
|---|------|------|------|------|
| 1 | CLAUDE.md 完备性 | ✅ | 含 11 节，覆盖 7 类 | 无 |
| 2 | Rules 文档 | ✅ | engineering-practices 15 节齐 | 无 |
| 3 | PreToolUse 防御 | ✅ | 黑+灰双层，python 解析 | 无 |
| 4 | Hooks | ✅ | 6 类齐（pre/post/stop/sessionstart/subagentstop/userpromptsubmit） | 无 |
| 5 | Agents | ✅ | 8 个 agent | description 路由清晰 |
| 6 | Commands | ✅ | audit-practices/audit-context/commit/onboard/sync-docs（5 个） | 可加 /review |
| 7 | CI 门禁 | ✅ | lint.yml + scheduled.yml + 必需文件单点真源 | 无 |
| 8 | Git 卫生 | ✅ | .gitignore 完整，settings.local 已 untracked | 无 |
| 9 | 测试 | ⚠️ | prettier --check + hook smoke test（26 case） | 项目无 src/，待 M8 |
| 10 | 文档同步 | ✅ | README/CLAUDE/ADR/CHANGELOG 一致 | 无 |
| 11 | 可观测 | ⚠️ | Stop hook 摘要 + audit log + summary 工具 | 缺 statusLine |
| 12 | DDD 分层 | N/A | 项目尚无 src/ | M8 实例化后启用 |
| 13 | Java/Spring | N/A | 同上 | 同上 |
| 14 | MCP 治理 | ✅ | .mcp.json 走 env、强制只读 | 无 |
| 15 | Policy 机制化 | ✅ | model selection / bypass / audit log | 无 |

## 优先改进（Top 3）
1. <最该动的> — 预估 X 分钟
2. ...
3. ...

## 已达标维度
- ✅ <列表>
```

## 评分尺度

- ✅ **达标**：本节"达标"条件全满足
- ⚠️ **部分**：基础在但缺一两项
- ❌ **缺失**：未实施或严重不足
- **N/A**：本项目阶段不适用（如 DDD 维度在 M8 实例化前为 N/A）

## 参数

- `$ARGUMENTS` 为空：跑全量 15 维度
- `$ARGUMENTS` 指定关键词（如 `ddd` / `mcp` / `hooks` / `ci` / `policy`）：仅对该维度做深度审查并给修复样例

## 硬性规则

- **以证据说话**，不允许"看着像 ✅ 就 ✅"。每条都引文件路径或行号
- **N/A 也要写明原因**（如"项目无 src/，本维度待 M4 启用"）
- **Top 3 改进必须可执行**，不写"建议提升质量"这种空话
- 不动文件，**只产报告**（写 audit log 是唯一例外，见下）

## 末步：把评分写入 audit log（让趋势可追）

产报告后**必须**追加一行到 `.claude/.audit.log`，方便后续追踪 ⚠️/❌ 数量随时间走势。
把 15 维度的 ✅/⚠️/❌/N/A 压成单个 dict 传给 `--extra scores=`：

```bash
python .claude/scripts/audit-log-append.py \
  --hook PracticesAudit \
  --action scored \
  --target "15-dim-$(date -u +%Y%m%d)" \
  --reason "/audit-practices run" \
  --extra scores='{"1":"✅","2":"✅","3":"✅","4":"✅","5":"✅","6":"✅","7":"✅","8":"✅","9":"⚠️","10":"✅","11":"⚠️","12":"N/A","13":"N/A","14":"✅","15":"✅"}' \
  --extra top3='["<top1-id>","<top2-id>","<top3-id>"]'
```

`scores` 键名对应 §1-§15 节号；`top3` 用 backlog ID（B1/C3/...）或一句话描述。
日后用 `python .claude/scripts/audit-log-summary.py --hook PracticesAudit` 即可看历史。
