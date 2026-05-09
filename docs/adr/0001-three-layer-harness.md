# ADR 0001 — 三层 Harness 架构

**Status**: Accepted
**Date**: 2026-05-08
**Stage**: M0–M3 总结追溯

## 背景

让 LLM 写出工程级代码，光靠"提示词 + 良好习惯"不可靠。需要一套**结构化的 Harness**，从行动前/中/后三个阶段约束 LLM 输出。

## 决定

采用三层 Harness 架构：

1. **Layer 1 约束层** — 行动**之前**注入规则与禁忌
2. **Layer 2 反馈循环层** — 行动**期间与之后**给即时信号
3. **Layer 3 质量门禁层** — 不可绕过的最后兜底

## 各层组件映射

| 层 | 组件 | 文件 |
|----|------|------|
| L1 | 行为准则 | `CLAUDE.md`（10 节，自动注入） |
| L1 | 工程化规则 | `.claude/rules/engineering-practices.md`（14 节） |
| L1 | 事前防御 | `.claude/hooks/pre-tool-use.sh`（黑+灰双层） |
| L2 | 事后格式化 | `.claude/hooks/format.sh`（PostToolUse） |
| L2 | 会话结束摘要 | `.claude/hooks/stop-check.sh`（Stop） |
| L2 | 子工作流 | `.claude/agents/*.md`（8 个，含 ddd-architect 等） |
| L2 | 流程命令 | `.claude/commands/*.md`（4 个） |
| L3 | 仓库卫生 | `.gitignore` |
| L3 | 不可绕兜底 | `.github/workflows/lint.yml`（CI） |
| L3 | 提交规范 | Conventional Commits（由 `/commit` 强制） |

## 替代方案与权衡

### A. 只用 CLAUDE.md（无 hook、无 CI）
- 👍 简单，零基础设施
- 👎 LLM 仍然能犯所有低级错误（写 .env、强推 main、改 domain 边界），无强制力
- ❌ 弃用

### B. 只用 hook（无 CLAUDE.md、无 CI）
- 👍 强制力强
- 👎 hook 是黑名单，无法穷尽。新人没准则会一直触发拦截
- ❌ 弃用

### C. 三层都做（当前方案）
- 👍 三层各司其职，叠加防御
- 👎 维护成本高（14 节规则 + 8 agent + 3 hook + CI）
- ✅ 采纳，因为本项目目标就是探索"工程级"边界

## 后果

- 任何新加的规则要决定属于哪一层
- 三层之间索引必须一致（CLAUDE.md / engineering-practices / lint.yml / AGENTS.md）— 这是**主要维护成本**，靠 `/audit-practices` 自检兜底
- 跑 `/audit-practices` 是验证三层完整性的入口，**不可降级**

## 相关

- 整体说明：[../../README.md](../../README.md)
- 行为准则：[../../CLAUDE.md](../../CLAUDE.md)
- 工程化规则：[../../.claude/rules/engineering-practices.md](../../.claude/rules/engineering-practices.md)
