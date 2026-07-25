---
description: 评审编排入口 — 显式声明三 reviewer（code-reviewer / spring-boot-reviewer / ddd-architect）的串并行调度，避免主对话每次即兴分派
argument-hint: "[target] 可选：分支 / 文件 / 路径（默认当前分支 vs main 的 diff）；加 --quick 只跑 code-reviewer"
---

# /review

**评审编排**：把一次改动的评审**显式分派**给合适的 reviewer 组合，而不是让主对话每次即兴决定该调谁。

## 为什么需要编排入口

一个 PR 往往同时涉及三类关注点，靠主对话读 description 关键词临时分派容易**漏**（只想到 code-reviewer）或**重叠**（三个都 spawn 却各说各话）。本命令固化"何时并行、何时串行、谁审谁"的调度，与 [AGENTS.md 自反馈环 / 升级链](../../AGENTS.md) 保持同一套约定，不另起一套。

## 三 reviewer 分工（不重叠）

| Reviewer               | 关注                                                           | 模型   |
| ---------------------- | -------------------------------------------------------------- | ------ |
| `code-reviewer`        | 通用质量：命名 / 复杂度 / 重复 / 异常 / 安全 / 测试覆盖        | sonnet |
| `spring-boot-reviewer` | Spring 反模式：@Transactional / 循环依赖 / N+1 / Bean / Lombok | sonnet |
| `ddd-architect`        | DDD 边界：聚合 / Entity vs VO / 领域事件 / 分层依赖方向        | opus   |

## 调度决策树

先看改动**触碰哪些层**（用 `git diff --name-only` 判定），再决定调谁：

```
改动文件路径
├── 含 src/main/java/**/domain/         → ddd-architect 必上（边界判断）
├── 含 @Transactional / @Bean / @Autowired / Lombok 注解 → spring-boot-reviewer 上
└── 任何代码改动                        → code-reviewer 兜底（永远上）
```

### 并行 vs 串行

- **并行阶段**（三者互不依赖，同时 spawn）：`code-reviewer` + `spring-boot-reviewer` + `ddd-architect` 各自独立审同一份 diff，**不互相等**。
- **串行/自反馈阶段**（仅当并行阶段有命中时触发，遵循 [AGENTS.md 自反馈环](../../AGENTS.md)）：
  - `ddd-architect` 报"边界改动" → 若该改动经 PreToolUse 灰名单，二次确认分层准入
  - 三者输出**汇总去重**由主对话（Driver）做，不让 reviewer 互相改对方结论

> 硬上限（[loop-architecture §3](../../docs/loop-architecture.md)）：并行 ≤ 5、串行链 ≤ 4、单 reviewer retry ≤ 2。

## 执行步骤

### 1. 采集 diff 范围

```bash
# 默认：当前分支 vs main
target="${ARGUMENTS:-}"
if [ -z "$target" ]; then
  git diff --name-only main...HEAD
  git diff main...HEAD --stat
else
  # target 是分支/文件/路径
  git diff --name-only "$target" 2>/dev/null || git diff --name-only -- "$target"
fi
```

### 2. 按调度决策树选 reviewer

- 扫改动文件路径 + 内容，判定命中哪些层
- `--quick` 参数：跳过判定，只跑 `code-reviewer`
- 无代码改动（纯文档 / 配置）：只跑 `code-reviewer`，并提示"未触及 Java 代码，Spring/DDD reviewer 已跳过"

### 3. 并行 spawn 命中的 reviewer

同一 `git diff` 范围喂给每个 reviewer，各自独立产出。**保留各 reviewer 原始输出**（升级/自反馈时反馈 agent 要看得到）。

### 4. 汇总（Driver 做）

按下方模板合并三者结论，**去重**（同一问题多个 reviewer 提到 → 合并成一条，标注哪几个 reviewer 命中），按严重度排序。

## 输出模板

```
# 评审报告 — <target> — <YYYY-MM-DD>

## 范围
- diff：<N> 文件 / +<X> -<Y> 行
- 触及层：<domain / application / interfaces / infrastructure / 非代码>
- 已调 reviewer：<code-reviewer [+ spring-boot-reviewer] [+ ddd-architect]>
- 已跳过：<原因，如"未触及 Java 代码，Spring/DDD 跳过">

## 阻断项（合并前必修）
- [B1] <问题> — 命中：<code-reviewer / spring / ddd>，证据：<file:line>，改法：<一句话>

## 建议项（可择机）
- [S1] <问题> — 命中：<...>，证据：<file:line>

## 各 reviewer 原始结论（保留追溯）
### code-reviewer
<摘要 + status>
### spring-boot-reviewer
<摘要 + status，或"未触发">
### ddd-architect
<摘要 + status，或"未触发">

## 待用户决策
- <reviewer 间冲突或需业务拍板的点>
```

## 参数

- `$ARGUMENTS` 为空：评审当前分支 vs main 的 diff，按决策树自动选 reviewer
- `$ARGUMENTS` = 分支 / 文件 / 路径：评审指定范围
- `$ARGUMENTS` 含 `--quick`：只跑 code-reviewer（轻量场景，如小 typo 批改）

## 硬性规则

- **code-reviewer 永远上**（兜底通用质量），其余按决策树条件触发
- **不重复 spawn 同一 reviewer**；一个 reviewer 一次改动只跑一遍（retry 除外）
- **汇总去重由 Driver 做**，reviewer 之间不互相改结论（保留独立视角）
- **阻断/建议分级**：阻断项必须给可执行改法，不写"建议提升质量"空话
- **保留各 reviewer 原始输出**：符合 [AGENTS.md 升级链"跨 agent 升级保留原 Worker 输出"](../../AGENTS.md)
- **不动文件**：只产报告；修复由用户确认后主对话执行

## 与其他命令 / skill 的边界

| 场景                        | 用                                               |
| --------------------------- | ------------------------------------------------ |
| 评审代码改动（本命令）      | `/review`                                        |
| 工程化机制自检              | skill `audit-practices` / `/audit-practices`     |
| 文档间漂移                  | skill `cross-stage-check` / `/cross-stage-check` |
| 代码 ↔ 文档漂移            | `/sync-docs`（调 docs-keeper）                   |
| 影响面 / 调用链（改前分析） | skill `gitnexus-impact-analysis`                 |

## 末步：写入 audit log

```bash
python .claude/scripts/audit-log-append.py \
  --hook ReviewOrchestration \
  --action reviewed \
  --target "$(git rev-parse --abbrev-ref HEAD)-$(date -u +%Y%m%d)" \
  --reason "/review run" \
  --extra reviewers='["code-reviewer","spring-boot-reviewer","ddd-architect"]' \
  --extra blockers='<阻断项数>'
```
