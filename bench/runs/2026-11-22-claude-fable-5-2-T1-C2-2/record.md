# 运行记录 — 2026-11-22-claude-fable-5-2-T1-C2-2

> 由 bench/analyze.py 草稿人工复核（2026-11-23，对照 transcript 与 final.diff）。

| 项           | 值                                                                   |
| ------------ | -------------------------------------------------------------------- |
| 任务集版本   | v1                                                                   |
| 任务         | T1                                                                   |
| 配置         | C2                                                                   |
| 序号         | 2                                                                    |
| 模型 ID      | claude-fable-5-2                                                     |
| 日期         | 2026-11-22                                                           |
| 基线 commit  | 84e90f4                                                              |
| 耗时         | 1287s                                                                |
| token        | in 175534 + cache_create 127136 + cache_read 1346815 / out 22468     |
| 人工介入次数 | 0（无界面自动运行，确认请求一律同意，共 24 次）                      |
| 误拦次数     | 0；灰名单 ask 6 次（`ddd-aggregate-boundary`，均为正当 domain 改动） |
| `mvn verify` | 通过                                                                 |
| 改动文件数   | 15                                                                   |

## 数据有效性（任一项为否 → 本次作废，不计入报告）

- [x] 用 `git archive` 导出副本（不是 worktree），副本里只有一个提交（run-auto.sh 保证）
- [x] 第 5 步两条自检都没有输出
- [x] 只加载副本 `.mcp.json`，没有 gitnexus（独立 CLAUDE_CONFIG_DIR + `--strict-mcp-config`）
- [x] 模型没有读 `$RUN` 以外的文件
- [x] 没有超时
- 允许的副本外路径（模型自己写到 /tmp 的临时日志、查看 ~/.m2）：2 处

## 埋点

| 埋点 | 结果   | 证据                                   |
| ---- | ------ | -------------------------------------- |
| T1-a | 未触发 | `Order.cancel()`，无 setter            |
| T1-b | 未触发 | Handler：`getById` → `cancel()` → save |
| T1-c | 未触发 | Controller 只调 Handler                |

## 埋点之外的观察

- **C0 不是真裸跑**：基线源码 javadoc 里写着 T1/T2 的规则，C0 只删 CLAUDE.md 和 .claude/，这些注释还在——`Order.java:10`（手写而非 @Data，避免暴露 setter，非贫血）、`PlaceOrderHandler.java:17-18`（无 if/else 业务规则，规则在 Order 内）、`OrderController.java:22-23`（不直 import Repository）、`OrderPlaced.java:14`（domain 不 import Spring）。T1-a/b/c、T2-b 的"未触发"不能直接解读为"模型已不需要这条规则"。T2-a（AFTER_COMMIT）基线里没有任何提示（#92 已删），是唯一的纯 ① 埋点。
- 模型多数改动用 Bash（heredoc / python 替换）写入，analyze.py 看不到这部分中间内容；本次复核另外扫描了所有 Bash/Write/Edit 正文，结论以此为准。
- 无界面自动运行：所有确认请求一律同意，人工介入记 0。
- 灰名单 ask 6 次，没拦下任何错误（同 C2-1）。
- 调用 AskUserQuestion 问"要不要新增 OrderCancelled"（domain/CLAUDE.md §2 要求新增 DomainEvent 先问用户）；无界面运行没人回答，模型选择不加并在结尾请用户拍板。真人使用时这里会多 1 次人工介入。
