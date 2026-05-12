---
name: harness-guidelines
description: Behavioral guardrails for ANY coding, refactoring, debugging, or code-review task. Invoke BEFORE writing code, explaining a change, or starting any multi-step implementation — even when the task looks small or obvious. Enforces four checks every time: (1) assumption-check (state assumptions, ask if unclear); (2) simplicity-first (minimum viable code, no speculative abstractions); (3) surgical changes (touch only what's necessary, don't refactor adjacent code); (4) goal-driven (define verifiable success criteria before coding). Use for tasks like "implement X", "add a function", "fix this bug", "refactor Y", "review this code", "how should I do Z?", "实现 X", "加个函数", "修 bug", "重构", "评审", "review", "plan", "explain how". When in doubt about whether to invoke, ALWAYS invoke — the cost is one short check, the benefit is avoiding scope creep / wrong assumptions / overcomplication. Skip only for pure-conversation / non-code questions.
---

# Harness 工程化通用准则

> **使用方法**：这是一组**前置检查**，每次开始 coding 任务前先过一遍，再动手。
>
> **第一件事永远是 §1**（Think Before Coding）。哪怕用户说"加个 add 函数"这种看似 trivial 的，也先做 §1 的 4 个确认（语言 / 签名 / 边界 / 测试），再动手。
>
> 跳过的唯一情形：纯文本问答、解释概念、查找文件等不涉及"写或改代码"的请求。

## 1. Think Before Coding（先做这步）

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

**实操：开口前先告诉用户**：

> "我打算这样做：<一句话方案> + 假设 <X>。需要确认吗？"
>
> 然后等用户回应或自己继续（看任务清晰度）。

即使任务是"加个 add 函数"，也至少声明 1-2 行假设：语言 / 是否要测试 / 边界 case 处理，让用户有机会纠正。

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
