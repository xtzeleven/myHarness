# myHarness

> 自用Harness工程级实践
> _Real-world coding benchmark for AI assistants_

![Status](https://img.shields.io/badge/status-WIP%20M2-orange)
![License](https://img.shields.io/badge/license-MIT-blue)
![Models](https://img.shields.io/badge/models-8%2B-green)

## 🎯 项目简介

从Harness原理开始，构建持续迭代框架，期待工程级表现

## 🛠️ 技术路线

### 三层 Harness 架构

- **Layer 1：约束层（Constraint Harness）**
  在 LLM 行动**之前**注入规则与禁忌，让"错误的代码写不出来"。
  - `CLAUDE.md`：每次会话自动注入的行为准则（思考优先 / 简单优先 / 外科手术 / 目标驱动）
  - `.claude/rules/engineering-practices.md`：11 节工程化规则（带"为什么 / 怎么做 / 什么算达标"）
  - `.claude/hooks/pre-tool-use.sh`：事前防御（拦 `rm -rf /`、强推主分支、写敏感文件）

- **Layer 2：反馈循环层（Feedback Loop）**
  在 LLM 行动**期间与之后**给出即时信号，让"错的能立刻被纠"。
  - PostToolUse hook：编辑后自动按后缀分发格式化（prettier / ruff）
  - Stop hook：会话结束前 `git status` 摘要 + 变动量警告
  - Sub-agents：`tdd-cycle-driver`（红绿重构）、`code-reviewer`（独立评审）
  - Slash commands：`/audit-practices`（11 维度自检）、`/commit`（标准化提交）

- **Layer 3：质量门禁层（Quality Gates）**
  在 LLM **不可绕过**的位置兜底，让"绕过了也合不进 main"。
  - `.gitignore` 覆盖 IDE / OS / 语言 / 密钥四类
  - GitHub Actions `lint.yml`：prettier --check + 必需文件存在性 + settings.json JSON 校验
  - 提交规范：Conventional Commits

## 📊 阶段性路线

| 阶段   | 目标                                           | 状态      |
| ------ | ---------------------------------------------- | --------- |
| **M0** | 项目立项，写下三层架构假设                     | ✅ 完成   |
| **M1** | Layer 1 落地（CLAUDE.md + rules + PreToolUse） | ✅ 完成   |
| **M2** | Layer 2 落地（hooks + agents + commands）      | ✅ 完成   |
| **M3** | Layer 3 落地（CI + 提交规范 + 必需文件门禁）   | 🟢 当前   |
| **M4** | 接入第二个真实项目，对照本框架做差异分析       | ⏳ 待启动 |
| **M5** | 总结 8+ 模型在本框架下的表现差异               | ⏳ 待启动 |

## 🚀 快速上手

```bash
git clone <repo> && cd myHarness
# 1. 看准则
cat CLAUDE.md
# 2. 看工程化清单
cat .claude/rules/engineering-practices.md
# 3. 跑自检
/audit-practices
```

## 📁 目录速览

```
CLAUDE.md                       行为准则（每会话自动注入）
AGENTS.md                       agent 索引
.claude/
  settings.json                 共享配置（hooks 注册）
  rules/engineering-practices.md  11 节工程化规则
  hooks/                        format / stop-check / pre-tool-use
  agents/                       tdd-cycle-driver / code-reviewer
  commands/                     audit-practices / commit
.github/workflows/lint.yml      CI 质量门禁
docs/                           设计文档
```
