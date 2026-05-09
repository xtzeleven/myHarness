---
description: 工程实践自检清单，逐维度打勾报告项目当前落地状态
argument-hint: "[focus] 可选：聚焦某一维度名"
---

# /audit-practices

对当前项目工程化实践做一次自检，按以下 11 维度逐项打 ✅ / ⚠️ / ❌ 并给一句话依据 + 改进建议。

如果项目根有 `.claude/rules/engineering-practices.md`，**优先**对照该文件 11 节执行。否则使用下方通用 11 维度。

## 通用 11 维度自检

1. **CLAUDE.md 完备性** — 是否覆盖技术栈 / 目录 / 禁忌 / 测试命令 / 行为准则
2. **Hook 配置** — PostToolUse 格式化、Stop 提醒、PreToolUse 校验是否合理
3. **权限治理** — `.claude/settings.local.json` 是否用通配符收敛、有无危险通配
4. **自定义 Agent** — `.claude/agents/` 是否有专项 agent 覆盖高频场景
5. **自定义 Command** — `.claude/commands/` 是否有项目专属 slash 命令
6. **Skill 资产** — `skills/` 或可调用的 plugin skill 是否到位
7. **测试基础设施** — 测试框架、运行命令、覆盖率门禁是否齐备
8. **Git 卫生** — `.gitignore` 是否覆盖 `.idea/` / build 产物 / 临时文件；是否有泄露风险
9. **CI / 质量门禁** — 是否有 lint / format / test 的自动检查（GitHub Actions / pre-commit）
10. **文档同步** — README / docs 是否与代码现状一致；有无 WIP/占位声明
11. **可观测性** — 日志 / 错误处理 / 关键路径监控是否有规划

## 执行步骤

1. **采集**：读 `CLAUDE.md`、`.claude/settings*.json`、`.claude/hooks/`、`.claude/agents/`、`.claude/commands/`、`README.md`、`.gitignore`、CI 目录（`.github/workflows/`）。如可能，跑 `git status --porcelain` 看脏度。
2. **打分**：逐维度判定，**用证据说话**（引用文件路径或具体行）。
3. **汇总**：按下表格式输出，最后给"前 3 个最值得动手的改进"。

## 输出模板

```
# 工程实践自检报告 — <YYYY-MM-DD>

| # | 维度 | 状态 | 依据 | 建议 |
|---|------|------|------|------|
| 1 | CLAUDE.md 完备性 | ✅ | CLAUDE.md:1-90 含 7 节 | 补充 lint 命令 |
| 2 | Hook 配置 | ⚠️ | 仅 PostToolUse | 加 PreToolUse 校验 |
| ... | ... | ... | ... | ... |

## 优先改进（Top 3）
1. <最值得做的> — 预估成本 X 分钟
2. ...
3. ...

## 已达标维度
- ✅ <列表>
```

## 评分尺度

- ✅ **达标**：核心要素齐全，可直接生产使用
- ⚠️ **部分**：基础在但有缺口，未阻塞但建议补齐
- ❌ **缺失**：未实施或严重不足

## 参数

- `$ARGUMENTS` 为空：跑全量 11 维度
- `$ARGUMENTS` 指定维度名（如 `hooks`）：仅对该维度做深度审查并给修复样例
