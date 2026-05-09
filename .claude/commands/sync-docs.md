---
description: 检查最近改动是否需要同步文档 — 调 docs-keeper agent，给改文档清单
argument-hint: "[range] 可选：HEAD~N（默认 HEAD~10）"
---

# /sync-docs

手动触发文档漂移检查。**不直接改文档**，只产清单。

## 执行步骤

### 1. 采集

```bash
RANGE="${ARGUMENTS:-HEAD~10}"
git log --oneline ${RANGE}..HEAD
git diff ${RANGE}...HEAD --stat
git diff ${RANGE}...HEAD -- '*.java' '*.yml' 'pom.xml' '.mcp.json' '.env.example'
```

### 2. 调 docs-keeper agent

把上面采集结果作为上下文，调 `docs-keeper` agent 跑增量模式：

> 比对范围 `<RANGE>..HEAD`，检查 README / CLAUDE.md / docs/ 是否与代码现状漂移。给改文档清单。

### 3. 汇总输出

把 docs-keeper 的报告原样贴出，并在末尾追加：

```
## 下一步
- 选择性接受清单 → 我可以按清单帮你改（再说"接受 #1 #3"）
- 需要重新评估 → 调整 range（如 `/sync-docs HEAD~30`）后重跑
- 要更新 AGENTS.md / agent 描述 → 手动改，本流程不动
```

## 硬性规则

- **不调 ddd-architect / spring-boot-reviewer / 其他 agent**，避免越权。
- **不直接改任何 .md 文件**。改动只能在用户明确"接受 #N"后由主对话执行。
- 检测到 `${RANGE}` 中没有任何代码改动（只动了文档）→ 直接报"无需检查"，不调 agent。
- 检测到 docs-keeper 找到 0 项漂移 → 输出"✅ 文档与代码同步"。
