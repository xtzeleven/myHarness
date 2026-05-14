# ADR Index

记录本项目的关键架构与流程决策。新决策按编号递增（`NNNN-<topic>.md`）。

## 阅读顺序

| #                                     | 主题                                 | 状态                                              |
| ------------------------------------- | ------------------------------------ | ------------------------------------------------- |
| [0001](0001-three-layer-harness.md)   | 三层 Harness 架构                    | Accepted                                          |
| [0002](0002-java-ddd-backend.md)      | Java + DDD 作为后端实战载体          | Accepted（曾被 0005 超越，0007 恢复）             |
| [0003](0003-mcp-and-gitnexus.md)      | MySQL 只读 MCP + gitnexus skill 接入 | Accepted                                          |
| [0004](0004-deprecate-bypass-once.md) | 废弃 `.bypass-once` 单次授权机制     | Accepted                                          |
| [0005](0005-pivot-to-plugin.md)       | 项目重定位：M8 → Plugin 化           | Superseded by [0007](0007-revoke-plugin-pivot.md) |
| [0006](0006-cleanup-claude-dir.md)    | 共存期收尾：清空 `.claude/`          | Superseded by [0007](0007-revoke-plugin-pivot.md) |
| [0007](0007-revoke-plugin-pivot.md)   | 撤销 plugin 化转向，回归 M8 原计划   | Accepted                                          |

## 何时写 ADR

- 选择架构 / 技术栈 / 重大依赖
- 决定项目阶段或路线图重大调整
- 新增或删除一层防御机制
- 与已有约定冲突时的破例

## 何时不写 ADR

- 普通 bug 修复、单点优化（写 commit message 即可）
- 文档措辞调整
- agent / command 微调（除非新增类别）

## 模板

```markdown
# ADR NNNN — <一句话主题>

**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-XXXX
**Date**: YYYY-MM-DD

## 背景

（决策为什么必要）

## 决定

（具体做什么）

## 替代方案

| 候选 | 否决原因 |

## 后果

（带来的好处与维护成本）

## 相关

（链向相关代码/文档）
```
