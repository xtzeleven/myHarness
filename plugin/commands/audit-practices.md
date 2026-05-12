---
description: 工程实践自检清单，对照 engineering-practices.md 15 节逐项打勾
argument-hint: "[focus] 可选：聚焦某一节名（如 ddd / java / mcp / hooks / policy）"
---

# /audit-practices

对当前项目工程化实践做一次自检，按 **15 维度** 逐项打 ✅ / ⚠️ / ❌ 并给一句话依据 + 改进建议。

**优先**对照 `${CLAUDE_PLUGIN_ROOT}/rules/engineering-practices.md`（含 §1-§11 通用 + §12-§14 领域专项 + §15 Policy）；该文件不存在时退回下方通用清单。

## 0. 运行模式判定（必读，跑下面 15 维度前先做）

本命令服务两类项目：

- **A. Standalone 项目**：项目根有 `.claude/` 自带 hooks/agents/commands/rules
- **B. Plugin 用户项目**：项目自己**没有** `.claude/` 子目录或只有少量个人配置，所有 Harness 资产由 plugin 提供（通过 `--plugin-dir` 或 `/plugin install`）

**判定方法**：

```bash
# 项目自带 .claude/ 资产？
ls .claude/hooks/ .claude/agents/ .claude/commands/ 2>/dev/null | head -5
# plugin 已加载？（CLAUDE_PLUGIN_ROOT 由 Claude Code 注入）
echo "${CLAUDE_PLUGIN_ROOT:-not-loaded}"
```

- 项目无 `.claude/hooks/` 且 plugin 已加载 → 视为 **B 模式**
- 否则 → A 模式（继续按原 15 维度严格自检）

**B 模式下的评分调整**：维度 3 (PreToolUse 防御) / 4 (Hooks) / 5 (Agents) / 6 (Commands) / 14 (MCP) 由 plugin 提供，**判 `✅(via plugin)`** 等价 ✅，不打 ❌。只对项目**自身**该有的（CLAUDE.md / CI / Git 卫生 / 文档 / 测试 / DDD 实施情况）正常打分。

## 15 维度自检清单

### Layer 1 约束层

1. **CLAUDE.md 完备性** — 行为准则 / 项目上下文 / 技术栈 / 目录 / 禁忌 / 测试命令 / 子目录指引
2. **Rules 文档** — `engineering-practices.md` 每节"为什么 / 怎么做 / 达标"三段齐全
3. **PreToolUse 防御** — 黑名单（直接拦）+ 灰名单（人工授权）

### Layer 2 反馈循环层

4. **Hooks** — PostToolUse 格式化 + Stop 提醒 + PreToolUse 防御 至少三件齐
5. **Agents** — 项目 `.claude/agents/` 或安装 plugin 提供的 agents，覆盖高频场景；description 含触发关键词；最小权限
6. **Commands** — 项目 `.claude/commands/` 或 plugin 提供的 commands，含日常重复动作（提交 / 评审 / 自检 / 上手 / 同步）

### Layer 3 质量门禁层

7. **CI / 质量门禁** — `.github/workflows/*.yml` 跑 lint + 必需文件 + 配置合法性
8. **Git 卫生** — `.gitignore` 完整、提交 Conventional 风格、`settings.local.json` 不在 tracking
9. **测试 / 校验** — 项目类型对应的测试命令；至少跑 `/audit-practices` 当冒烟

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

1. **运行模式判定**（见 §0）：先跑判定命令，输出顶部声明 `运行模式：A standalone / B plugin-user`。

2. **采集**（用 Bash + Read 一次跑完）：

   ```bash
   ls -la CLAUDE.md README.md AGENTS.md 2>/dev/null
   ls .claude/ 2>/dev/null || echo "no project-local .claude/ (可能用 plugin 提供)"
   ls "${CLAUDE_PLUGIN_ROOT:-/nonexistent}" 2>/dev/null  # plugin 资产
   ls .github/workflows/ 2>/dev/null
   cat .gitignore 2>/dev/null | head -30
   git ls-files | grep -E 'settings.local|\.env$'  # 应为空
   git status --porcelain
   ls .mcp.json .env.example 2>/dev/null
   ```

3. **打分**：逐维度判定，**用证据说话**（引用文件路径或具体行）。B 模式按 §0 评分调整。

4. **汇总**：按下表输出，最后给"前 3 个最值得动手的改进"。

## 输出模板

```
# 工程实践自检报告 — <YYYY-MM-DD>

**运行模式**：A standalone / B plugin-user（说明判定依据）
**Plugin 信息**（B 模式）：plugin 名 + 来源（`${CLAUDE_PLUGIN_ROOT}`）

## 总览
**层次状态**：L1 ✅ / L2 ✅(via plugin) / L3 ⚠️ / 支撑 ⚠️ / 领域 N/A

| # | 维度 | 状态 | 依据 | 建议 |
|---|------|------|------|------|
| 1 | CLAUDE.md 完备性 | ⚠️ | 项目根有 CLAUDE.md 但仅 X 行 | 跑 `/harness:onboard init` 取模板补全 |
| ... | ... | ... | ... | ... |

## 优先改进（Top 3）
1. <最该动的> — 预估 X 分钟
2. ...
3. ...

## 已达标维度
- ✅ <列表>
```

## 评分尺度

- ✅ **达标**：本节"达标"条件全满足
- ✅(via plugin) **plugin 提供**：等价 ✅，但来源是 plugin 而非项目自身（仅 B 模式）
- ⚠️ **部分**：基础在但缺一两项
- ❌ **缺失**：未实施或严重不足
- **N/A**：当前项目阶段不适用（如 §12-§13 DDD/Java 维度对非 Java 项目永远 N/A）

## 参数

- `$ARGUMENTS` 为空：跑全量 15 维度
- `$ARGUMENTS` 指定关键词（如 `ddd` / `mcp` / `hooks` / `ci` / `policy`）：仅对该维度做深度审查并给修复样例

## 硬性规则

- **必先做 §0 运行模式判定**，再做 15 维度
- **以证据说话**，不允许"看着像 ✅ 就 ✅"。每条都引文件路径或行号
- **N/A 也要写明原因**（如"项目无 src/main/java，DDD 维度 N/A"）
- **B 模式下不要把 plugin 已提供的能力判为 ❌**（这会误导用户）
- **Top 3 改进必须可执行**，不写"建议提升质量"这种空话
- 不动文件，**只产报告**
