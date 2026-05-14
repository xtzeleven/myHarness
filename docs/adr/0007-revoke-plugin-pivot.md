# ADR 0007 — 撤销 plugin 化转向，回归 M8 原计划

**Status**: Accepted
**Date**: 2026-05-14
**Stage**: 战略回滚
**Supersedes**: [ADR-0005](0005-pivot-to-plugin.md), [ADR-0006](0006-cleanup-claude-dir.md)
**Restores**: [ADR-0002](0002-java-ddd-backend.md)

## 背景

[ADR-0005](0005-pivot-to-plugin.md)（2026-05-11）把项目战略从"M8 实例化 Java DDD"转为"M8' Plugin 化"，并落地 `plugin/` 目录、8 agents / 5 commands / 6 hooks / SKILL / .mcp.json / rules 等完整资产。[ADR-0006](0006-cleanup-claude-dir.md) 进一步提出 M8' 完成后清空 `.claude/`、仓库根 = pure plugin。

经实际推进与权衡后，项目主导者决定**撤销该战略转向**，回归 [ADR-0002](0002-java-ddd-backend.md) 原计划：以 Java + Spring Boot + Maven + DDD 作为 Harness 的后端实战载体，继续推进 M8（实例化 Java DDD 骨架）。

## 决定

1. **撤销 M8'**：放弃"封装为 Claude Code Plugin"的方向。
2. **物理移除 plugin 产物**：`git rm -r plugin/`，避免与 `.claude/` 双源带来的歧义和漂移。
3. **恢复 `.claude/` 唯一权威源地位**：本仓库自身的 Harness 资产（hooks / agents / commands / rules）以 `.claude/` 为准；`settings.json` 已基于 `.claude/` 路径，工作流不需调整。
4. **状态切换**：
   - [ADR-0002](0002-java-ddd-backend.md)：恢复为 **Accepted**（解除 0005 的 Superseded 标注）
   - [ADR-0005](0005-pivot-to-plugin.md)：**Superseded by ADR-0007**
   - [ADR-0006](0006-cleanup-claude-dir.md)：**Superseded by ADR-0007**（其依赖 0005，0005 失效后 0006 自然失效）
5. **文档清理**：CLAUDE.md / README.md / CHANGELOG.md / docs/roadmap.md / docs/improvement-backlog.md 中所有 plugin 化叙事改回 M8 原计划口径；plugin 阶段产出的 `docs/g13-findings.md`、`docs/g13-external-validation.md` 删除（内容 100% 属于 plugin 外部验证，无法迁移到 M8 口径）。

## 替代方案与权衡

| 候选                                  | 否决原因                                                                         |
| ------------------------------------- | -------------------------------------------------------------------------------- |
| 保留 plugin/ 不动但停止维护           | 产生孤儿目录与双源歧义，将来引用 plugin 路径的脚本/文档会持续混淆                |
| 把 plugin/ 移到 archive/ 子目录       | 仍保留 plugin 叙事的引力，且与"全部清理为 M8 原计划口径"的总方向矛盾             |
| 同时维护 plugin + Java DDD 实战两条线 | 双线维护成本超过 plugin 化的边际收益，且分散注意力于核心目标（Java DDD 验证）    |
| 直接 `rm` 不写 ADR                    | 违反 ADR 不可变原则；公开决策追溯链断裂；后人无法理解 0005/0006 与代码状态的偏差 |

## 后果

**回归 M8 原计划后：**

- `.claude/` 完整保留（8 agents / 5 commands / 6 hooks / engineering-practices.md），可直接用于 M8 Java DDD 骨架实例化
- `settings.json` 已绑定 `.claude/hooks/*.sh`，hook 链路无需调整
- 路线图回到 [ADR-0002](0002-java-ddd-backend.md) + [roadmap.md](../roadmap.md) M4-M8 原计划：M8 = 实例化 Java DDD 骨架（六维度回归测试场）
- `pom.xml` 仍未实例化（参见 CLAUDE.md §7 注），M8 启动后落地

**信息丢失：**

- plugin/ 阶段的外部验证结果（G13 共 18+ 自动 case + 多项手工验证通过）随删除而消失；如未来再次评估 plugin 化方向，需要重新建立验证
- ADR-0005 文中"任何语言栈可直接安装使用"的潜在收益放弃

**历史可追溯：**

- ADR-0005 / 0006 保留全文不动（仅 Status 行变更），plugin 化阶段的决策与权衡仍可被未来 reader 完整阅读
- git 历史保留 plugin-branch 与所有 plugin 提交（如 `6b8f0fd`、`eb69bfd`、`ce6ff49` 等），需要时可通过 git 回溯

## 相关

- [ADR-0002](0002-java-ddd-backend.md) — 恢复为 Accepted
- [ADR-0005](0005-pivot-to-plugin.md) — 被本 ADR 超越
- [ADR-0006](0006-cleanup-claude-dir.md) — 被本 ADR 超越（其依赖 0005）
- [roadmap.md §7](../roadmap.md) — M8 章节回归"实例化 Java DDD 骨架"
- CLAUDE.md §5 / §7 — 项目性质与命令清单同步更新
