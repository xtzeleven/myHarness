# Policy — Model Selection（单点真源）

**Status**: Accepted
**Date**: 2026-05-15
**Audience**: 主对话（Driver）+ 所有 sub-agent 路由判断

> 本文是模型选择策略的**单点真源**。AGENTS.md / engineering-practices.md §15 / 各 agent frontmatter 中如有"模型选择"叙述，应是本文的指针或 1 行注释，不再复述表格。

## 1. 优先级（硬规则）

按顺序生效，先匹配先用：

1. **用户显式指定**：`/model opus` 或对话明示
2. **agent frontmatter `model:`**：单 agent 内的默认
3. **本文场景表**：跨 agent 的通用回退
4. **Driver 当前模型**：以上都未命中时沿用主对话设置

## 2. Agent 默认模型表

| Agent                  | 默认模型 | 选这个的原因                         | 升级路径                                         |
| ---------------------- | -------- | ------------------------------------ | ------------------------------------------------ |
| `tdd-cycle-driver`     | sonnet   | 红绿循环路径明确，sonnet 够用        | sonnet → opus（连续 2 次 GREEN 失败时）          |
| `code-reviewer`        | sonnet   | 通用评审，sonnet 性价比高            | sonnet → opus（涉敏感 / 安全审查时）             |
| `ddd-architect`        | **opus** | 战略设计 / 跨 BC 决策需要长链路推理  | 已最高，下一步是用户决策                         |
| `spring-boot-reviewer` | sonnet   | Spring 反模式有清单可对照，sonnet 够 | sonnet → opus（涉事务边界 / 复杂 Bean 生命周期） |
| `maven-build-doctor`   | sonnet   | 构建错误有套路                       | sonnet → opus（依赖冲突涉多版本传递时）          |
| `schema-analyst`       | sonnet   | EXPLAIN / 索引分析有套路             | sonnet → opus（跨表 join / 分库分表设计）        |
| `migration-author`     | sonnet   | 模板化产出                           | sonnet → opus（向后兼容性涉应用层双写时）        |
| `docs-keeper`          | sonnet   | 漂移检测是模式匹配                   | sonnet → opus（罕见，文档结构剧变时）            |

## 3. 通用场景表（agent 未指定时）

| 场景                               | 默认模型                | 升级触发               |
| ---------------------------------- | ----------------------- | ---------------------- |
| 主对话（Driver）                   | 沿用用户当前会话设置    | —                      |
| 简单 review / 格式调整 / 小重构    | sonnet                  | 卡住 / 用户不满意      |
| 长链路战略设计（DDD 边界 / 跨 BC） | **opus**                | 已最高，无可升         |
| 安全 / 合规审查                    | sonnet                  | 涉敏感数据 → opus      |
| 调试 / 修 bug                      | sonnet                  | 复现失败/根因深 → opus |
| 大量文件批改 / 文档批改            | haiku（如可用）/ sonnet | 出错 → sonnet          |
| 路径明确的 TDD 红绿循环            | sonnet                  | —                      |

## 4. 升级与重试规则

- **同模型 retry 上限 2 次**，超即换模型或换 agent
- **升级前先 retry 当前模型 1 次**（瞬时失败可能并非模型能力问题）
- **永不向下升级**（用户决策后回到原层级）
- **跨 agent 转交时保留当前会话上下文**，不让接手 agent 从零开始
- **三次以内必升到用户**（agent ≤ 2 次 / model 升 1 次 / 都失败 → 用户）

## 5. Fallback（向下降级）规则

**升级 = 能力不足换更强；fallback = 模型不可用换可替代**。两个方向，触发条件不同。

| 触发                                  | 当前模型 | Fallback 到     | 必须做的事                                                   |
| ------------------------------------- | -------- | --------------- | ------------------------------------------------------------ |
| opus API 报错（如下线 / 配额 / 网络） | opus     | sonnet          | 输出顶部声明 "**已降级**: opus 不可用 → sonnet"              |
| sonnet API 报错                       | sonnet   | haiku（如可用） | 同上                                                         |
| 所有 Claude 模型不可用                | 任意     | 转用户决策      | 不静默继续；问用户改本地操作或等服务恢复                     |
| sub-agent 启动报 "模型已下线"         | opus-4-6 | opus-4-7        | 看实测案例：本仓库历史曾踩 4-6 → 4-7，处理方式见 `pitfall_*` |
| 任务要求长链路推理但仅有 sonnet 可用  | sonnet   | sonnet + 拆任务 | 把单次大请求拆 2-3 个小请求，每个 < 30 步                    |

**fallback 不可掩盖能力不足**：

- 如果原任务要求 opus 的长链路推理（如 DDD 跨 BC 设计），fallback 到 sonnet 后**必须**先告知用户"已降级，结果可能保守"，再问是否继续
- 不允许"opus 不可用 → 默默 sonnet → 输出降质方案" 不让用户知道
- 对应 `loop-architecture.md §3 Degradation` 的具体执行；本节是**模型维度**的细化

**实测踩坑**：

- 2026-05-19 本会话尝试 spawn `claude-code-guide` sub-agent 返回 `claude-opus-4-6 已下线`。处理：主对话改用 WebSearch / WebFetch 直接查官方文档（degradation 一级），结果作 OK。说明 agent 选模型固定的话需要文档触发条件（见 §2 升级路径）。

## 6. 维护

- 新增 agent 时，在第 2 节 + agent frontmatter 加 1 行 `# model 选择: <reason>` 注释；其他位置不复述
- 改动默认模型时只改本文，AGENTS.md / engineering-practices §15 自动随之生效
- `/audit-practices` 抽样校验 agent frontmatter 的 `model:` 与本文第 2 节是否一致
