---
description: 跑 token 审计 — 估算上下文注入成本，找最大消费者，给减重建议
argument-hint: "[--top N | --auto | --json]"
---

# /audit-context

跑 `${CLAUDE_PLUGIN_ROOT}/scripts/audit-context-cost.py` 估算项目内上下文文件的 token 成本。

## 用法

```bash
# 全部文件按 token 排序
python "${CLAUDE_PLUGIN_ROOT}/scripts/audit-context-cost.py"

# 只看每会话自动注入部分
python "${CLAUDE_PLUGIN_ROOT}/scripts/audit-context-cost.py" --auto

# Top 15
python "${CLAUDE_PLUGIN_ROOT}/scripts/audit-context-cost.py" --top 15

# JSON 机器可读（接入 CI / dashboard）
python "${CLAUDE_PLUGIN_ROOT}/scripts/audit-context-cost.py" --json
```

## 步骤

1. 跑 `python "${CLAUDE_PLUGIN_ROOT}/scripts/audit-context-cost.py" $ARGUMENTS`
2. 看 **自动注入** 是否 ≤ 8K（每会话付费的预算上限）
3. 看 Top 5 token 消费者，判断哪些可以拆 / 精简
4. 把基线数字记到项目自己的 context 管理文档（如有）的"当前估算"列

## 何时跑

- 完成一个里程碑（M4/M5/M6...）后跑一次记 baseline
- 怀疑会话变慢 / 注入超预算时跑
- M7 后的每周自动通过 `scheduled.yml` 跑

## 输出预期

```
Tokenizer: tiktoken-cl100k_base 或 char/4 approx
=== 文件级 ===   按 token 排序
=== 汇总 ===     按 6 大类
=== 预算检查 === 自动注入 vs 8K 目标
=== 减重建议 === 仅在超预算时输出
```

## 减重原则（如超预算）

通用减重原则：

- CLAUDE.md > 4K → 拆出"参考材料"性段落到按需文档
- MEMORY.md 索引 > 1K → 检查每行 ≤ 150 字符
- AGENTS.md > 3K → 把自反馈表 / 升级链拆出去
- 不动 rules / docs / agents 正文（按需加载，不计预算）

## 反模式

- ❌ 看到大文件就删（按需文档大没事，关键看自动注入）
- ❌ 把内容塞进根 CLAUDE.md 想让模型一定能看到（增加每会话成本，绕过按需机制）
- ❌ 用本命令优化按需文档（按需的不算预算）
