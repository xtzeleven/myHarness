---
name: harness-guidelines
description: 工程化通用行为准则 — 思考优先 / 简单优先 / 外科手术 / 目标驱动。Use when starting any non-trivial coding task (implementing new features, fixing bugs, refactoring, reviewing code), planning multi-step implementations, or when uncertain about scope. Helps reduce common LLM mistakes like overcomplicating, hidden assumptions, scope creep, and weak success criteria. 触发关键词：实现 / 重构 / 修 bug / 评审 / 加功能 / 简化 / 怎么改 / plan / implement / refactor / review。
---

# Harness 工程化通用准则

> 这是一组**行为准则**，不是技术清单。在写代码、改代码、评审代码前过一遍，能避开 LLM 最常见的几类错误：过度设计、隐藏假设、跑题、目标模糊。
>
> **Tradeoff**：这些准则偏保守、偏沟通。对一次性的 trivial 任务（typo、单行修复）可酌情跳过。

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:

- Remove imports / variables / functions that **your** changes made unused.
- Don't remove pre-existing dead code unless asked.

**The test**: every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## 与 plugin 其他组件的关系

- **`/harness:audit-practices`** 是工程实践 15 维度的**结构化自检**清单（CI / 测试 / git 卫生等），关注"项目是否就位"；本 SKILL 关注"动手时的行为方式"。两者互补：自检前先按本 SKILL 思考，自检后按结果改进。
- **`ddd-architect` / `spring-boot-reviewer` 等专项 agent** 都假设主对话已经按本 SKILL 思考过（明确范围、不擅自扩大改动）。如果主对话没遵循，agent 收到的请求会过宽。
- **PreToolUse 灰名单**（DDD 边界 / 主依赖升级）是"硬约束"；本 SKILL 是"软约束"。灰名单触发时，按本 SKILL §1"surface tradeoffs"先和用户对齐。
