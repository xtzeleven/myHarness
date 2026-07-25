---
description: 环境预检 — 一次列清 shell / 五件套 / 版本 / Docker / .env / hook 可执行位是否就绪，每项给 ✅/⚠️/❌ + 修法
argument-hint: 无参数
---

# /verify-setup

跑本机环境预检，回答新人第一个问题：**我装对了吗？** 尤其针对本项目最隐蔽的坑——**非 Git Bash / WSL 环境下 hook 会静默失败**，Harness 三层塌掉两层却毫无报错。

## 为什么需要

- `/onboard` 讲"该怎么装"，`/doctor` 是装好后的日常巡检；两者都**假设环境已就绪**。
- 唯独没有一个入口回答"我现在装的对不对"。非 bash 用户克隆下来，PreToolUse / PostToolUse / SessionStart 全部不触发，且**没有任何报错**——他们以为 Harness 在保护自己，其实没有。
- 本命令补这个缺口：一次性把前置逐条核到位。

## 执行

```bash
bash .claude/scripts/verify-setup.sh
```

脚本是**只读诊断**，不改任何文件，`exit 0` 不阻断（预检是体温计，不是门禁）。

## 检查项

| 分组     | 项                          | 判定                                                            |
| -------- | --------------------------- | --------------------------------------------------------------- |
| Shell    | 是否在 bash 下              | 非 bash → ❌（hook 全静默失败，最致命）                         |
| 核心工具 | git / python / java / maven | 缺 → ❌；版本与 `.tool-versions` 不符 → ⚠️（一般能跑，CI 对齐） |
| 核心工具 | node                        | 同上（prettier 格式化用）                                       |
| 可选工具 | docker                      | 缺 / daemon 未起 → ⚠️（仅 Testcontainers 集成测需要）           |
| 可选工具 | npx                         | 缺 → ⚠️（prettier 降级为跳过）                                  |
| 项目配置 | .env                        | 缺 → ⚠️（MCP schema 分析不可用）                                |
| 项目配置 | hook 可执行位               | 非 100755 → ⚠️（CI 会 fail，本地 chmod +x 后 commit）           |

## 何时跑

- **协作者首日**：`/onboard` 之前先跑本命令，环境不对先修。
- **hook 感觉没生效时**：怀疑 PreToolUse 没拦、格式化没跑 → 先跑本命令看 shell / 可执行位。
- **换机器 / 重装后**：确认新环境与 `.tool-versions` 对齐。

## 与其他命令的边界

| 命令               | 焦点                   | 何时用          |
| ------------------ | ---------------------- | --------------- |
| `/verify-setup`    | **环境就绪**（装对没） | **首日 / 换机** |
| `/onboard`         | 项目上手（这是什么）   | 协作者首日      |
| `/doctor`          | 运行时健康（5 路探针） | 每周 / 会话开头 |
| `/audit-practices` | 工程化机制 15 维度评分 | 季度 / 重大变更 |
