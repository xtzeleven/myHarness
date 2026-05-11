# Memory Conventions — Memory / ADR / CLAUDE.md 分工

**Status**: Accepted (M4)
**Date**: 2026-05-09

> **本文回答**：项目里有三种"知识载体"——CLAUDE.md / ADR / Claude Code Memory。新事实出现时该写到哪里？

## 三类载体的差异

| 载体          | 位置                              | 入 git? | 注入时机                                          | 适合写什么                                        |
| ------------- | --------------------------------- | ------- | ------------------------------------------------- | ------------------------------------------------- |
| **CLAUDE.md** | 项目根 / 子目录                   | ✅ 是   | 每会话**全量**自动注入                            | 项目稳定准则、技术栈、目录、禁忌、必读清单        |
| **ADR**       | `docs/adr/NNNN-*.md`              | ✅ 是   | 主对话**主动 Read**                               | 公开决策追溯：决定 X、考虑过 Y、否决 Z 的理由     |
| **Memory**    | `~/.claude/projects/<id>/memory/` | ❌ 否   | 主对话**自然引用**（看到 MEMORY.md 索引按需加载） | Claude 协作上下文：用户偏好、踩坑、未公开决策细节 |

## 分工矩阵

```
新事实
  │
  ├─ 影响每次代码生成的硬性约束？  ──→ CLAUDE.md
  │  (例: domain 层不许 import Spring)
  │
  ├─ 是不可逆的架构 / 技术决策？    ──→ ADR
  │  (例: 选 Java DDD 而非 Python)
  │
  ├─ 是协作偏好 / 踩坑 / 决策细节？ ──→ Memory
     (例: 用户喜欢分级 P0/P1；jq 不可用要用 python)
```

## 关键判别问题

### 写 CLAUDE.md 当且仅当：

- 它是**每次会话都要遵守**的项目级规则
- 漏了它，主 Claude 写出的代码就会违反项目惯例
- 它**不会因协作经验积累而频繁变化**

> **反例**：「上次会话用户要求分级 P0/P1」——这是用户偏好，写 Memory；不写 CLAUDE.md（那是给所有协作者看的硬规则）

### 写 ADR 当且仅当：

- 它是**已做出**的、**不可逆**或**改之昂贵**的决策
- 未来某天可能要重审，那时需要还原"当时为什么这么决定"
- **公开**——团队所有人应该看得到

> **反例**：「调试 hook 时 jq 不可用，改用 python」——这是技术取舍但**可逆**，不写 ADR；写 Memory 提醒未来 Claude 别再走 jq 路径

### 写 Memory 当且仅当：

- 它对**Claude 协作有帮助**，但不构成项目对外承诺
- 写在 git 里反而会污染（如个人偏好、临时事实）
- **未来 Claude 看到它能改变行为**

> **反例**：「项目用 Java 17」——这是技术栈事实，应在 CLAUDE.md（每次注入），不写 Memory（按需加载会漏）

## Memory 子分类与命名前缀

按 system prompt 的 auto memory 类型（user / feedback / project / reference）实例化为本项目的命名约定：

| 前缀         | 类型      | 内容                                      | 示例                                      |
| ------------ | --------- | ----------------------------------------- | ----------------------------------------- |
| `decision_*` | project   | 决策原因 / 否决条件 / 何时重审            | `decision_java_ddd_choice.md`             |
| `pitfall_*`  | project   | 踩过的坑 + 修法 + 预防                    | `pitfall_jq_not_in_path.md`               |
| `pref_*`     | feedback  | 用户协作偏好（按需启用，暂未推进）        | `pref_use_priority_levels.md`（参考命名） |
| `session_*`  | project   | 会话事实 / 中间状态（按需启用，暂未推进） | `session_2026_05_09_audit.md`（参考命名） |
| `ref_*`      | reference | 外部系统指针（如 Linear / Grafana）       | （暂无）                                  |

文件命名：**全小写、下划线分隔、动名结构、≤ 50 字符**。

## ADR 与 Memory 的指针关系

ADR 和 Memory 谈同一件事时，**ADR 是根**，Memory 用指针引用：

```markdown
# decision_java_ddd_choice.md

---

## type: project

补充 ADR-0002：选 Java DDD 的核心原因是它"最容易踩坑"（Lombok / @Transactional / 循环依赖），
Harness 在最容易出错的栈上验证才有说服力。详见 docs/adr/0002-java-ddd-backend.md。

ADR 不便写、但 Claude 应当记住的：

- 否决 Python 时考虑过用 typed-dict 强约束，但用户表态"在 Python 里 DDD 不典型"，决策稳定
- 何时重审：如果引入第二个项目（M5）发现 Python/Go 项目也想接入本框架
```

## 不该进任何一处的事

以下内容**不应出现**在三处任何一处：

- 临时调试输出、单次会话的状态
- 可由 `git log` / `git blame` / 当前代码状态直接推出的事实
- 用户私密信息（密码 / token / 个人身份）
- 跨项目的通用知识（属于 Claude Code 全局而非本项目）

## 维护

- **CLAUDE.md / ADR**：随代码一起 review 与 commit
- **Memory**：协作过程中由 Claude 主动写入；用户也可显式说"记下这点"；过期 / 被推翻时 Claude 应主动删除或更新
- **跨载体冲突**：以最近的为准；发现矛盾立即同步

## 相关

- ADR 索引：[adr/README.md](adr/README.md)
- 注入约束：[../CLAUDE.md](../CLAUDE.md)
- M4 路线图：[roadmap.md §3](roadmap.md)
