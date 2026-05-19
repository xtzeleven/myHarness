---
description: 项目健康一键看板 — 串联 context / audit log / memory / git status 五路探针，给一张诊断卡
argument-hint: "[--full] 可选：附带跑 audit-practices 全量评分（耗时较长）"
---

# /doctor

一次性出 myHarness 项目的健康看板。把已有的 5 个分散 audit 入口串成一张卡，方便每周扫一眼定位异常。

## 探针清单（按顺序跑）

1. **Git 工作树状态**：未提交改动数 + 当前 HEAD
2. **Context 注入成本**：自动注入 token + 预算占比
3. **审计日志最近信号**：按 action 分类 + 失败 / bypass / secret_suspect 计数
4. **Memory 增长**：按类型条目数 + 索引漂移检查
5. **CI 必需文件**：`.github/required-files.txt` 全部存在

## 执行步骤（主对话照此跑）

并行跑以下命令（互相独立）：

```bash
# 1. Git
git status --porcelain | wc -l
git log -1 --oneline

# 2. Context 成本
python .claude/scripts/audit-context-cost.py --auto

# 3. Audit log 多维度摘要
python .claude/scripts/audit-log-summary.py --by-action
python .claude/scripts/audit-log-summary.py --failures
python .claude/scripts/audit-log-summary.py --bypass

# 4. Memory
python .claude/scripts/memory-growth-summary.py

# 5. 必需文件抽查（CI 已每次跑，这里只做存在性快查）
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in \#*) continue ;; esac
  [ -e "$f" ] || echo "MISSING: $f"
done < .github/required-files.txt
```

如果传了 `--full` 参数，再跑：

```bash
# 6. 工程实践 15 维度（耗时 30s+）
# 直接告诉用户：请显式调 /audit-practices —— slash command 不能嵌套
```

## 输出模板

```
# /doctor — <YYYY-MM-DD HH:MM>

## 总览
**整体**：🟢 健康 / 🟡 关注 / 🔴 异常
**变更**：未提交 N 个 / HEAD <hash> <msg>

## 五路探针

| 探针 | 结果 | 阈值 | 状态 |
|------|------|------|------|
| Git 工作树 | N 个未提交 | < 20 | 🟢/🟡/🔴 |
| Context auto-inject | X tokens | ≤ 8K (50%) | 🟢/🟡 |
| Audit log 失败信号 | M 条 dispatcher error | 0（历史可累计） | 🟢/🟡 |
| Audit log bypass 7d | K 次 | < 3（HARNESS_BYPASS_WARN_AT） | 🟢/🟡/🔴 |
| Audit log secret_suspect 30d | S 条 | 无硬阈值，>0 需人工扫 | 🟢/🟡 |
| Memory 增长 30d | +D decision / +P pitfall | 不漂移即可 | 🟢 |
| MEMORY.md 索引一致 | OK / 漂移 N 条 | 必须 OK | 🟢/🔴 |
| 必需文件 | 全在 / 缺 N 个 | 全在 | 🟢/🔴 |

## 红灯项
（按严重性列出每个🔴的诊断 + 修法指针）

## 黄灯项
（关注但不紧急）

## 下一步
- 若 audit-practices 距上次 > 1 周：建议跑 `/audit-practices`
- 若 backlog 中 P1 项有遗留：列出
```

## 硬性规则

- **只读不改**：所有探针都是 query，不动文件
- **失败容忍**：某探针失败不阻塞其他（探针之间互相独立）
- **数据导向**：每个状态判断必须有数字支撑，不写"看着还行"
- **指针化建议**：红灯给具体修法文件路径（如"见 docs/improvement-backlog.md §C3"），不重复粘贴长解释

## 与已有命令的区别

| 命令               | 焦点                     | 何时用                |
| ------------------ | ------------------------ | --------------------- |
| `/audit-practices` | 15 维度逐项评分          | 季度自检 / 重大变更后 |
| `/audit-context`   | token 注入审计           | 怀疑上下文膨胀时      |
| `/sync-docs`       | 文档与代码漂移           | PR 前                 |
| `/doctor`          | **状态快照**（5 路探针） | **每周 / 会话开头**   |
| `/onboard`         | 新人 5 分钟上手          | 协作者首日            |

`/doctor` 是高频低成本的"体温计"，`/audit-practices` 是低频高成本的"年检"。两者互补。
