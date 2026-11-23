# 运行记录 — 2026-11-22-claude-fable-5-2-T2-C0-2

> 由 bench/analyze.py 草稿人工复核（2026-11-23，对照 transcript 与 final.diff）。

| 项           | 值                                                    |
| ------------ | ----------------------------------------------------- |
| 任务集版本   | v1                                                    |
| 任务         | T2                                                    |
| 配置         | C0                                                    |
| 序号         | 2                                                     |
| 模型 ID      | claude-fable-5-2                                      |
| 日期         | 2026-11-22                                            |
| 基线 commit  | 84e90f4                                               |
| 耗时         | 3609s（超时）                                         |
| token        | in 0 + cache_create 0 + cache_read 0 / out 0          |
| 人工介入次数 | 0（无界面自动运行，确认请求一律同意，共 5 次）        |
| 误拦次数     | hook deny 0 次（需人工判断是否误拦）；灰名单 ask 0 次 |
| `mvn verify` | 通过                                                  |
| 改动文件数   | 0                                                     |

## 数据有效性（任一项为否 → 本次作废，不计入报告）

- [x] 用 `git archive` 导出副本（不是 worktree），副本里只有一个提交（run-auto.sh 保证）
- [x] 第 5 步两条自检都没有输出
- [x] 只加载副本 `.mcp.json`，没有 gitnexus（独立 CLAUDE_CONFIG_DIR + `--strict-mcp-config`）
- [x] 模型没有读 `$RUN` 以外的文件
- [ ] 没有超时
- 允许的副本外路径（模型自己写到 /tmp 的临时日志、查看 ~/.m2）：2 处

## 结论：作废，不计入报告

60 分钟超时（elapsed 3609s），没有 result。claude-debug.log 有 7 次 ECONNRESET、3 次 timeout（中转站）；只有 45 条 assistant 消息。由 2026-11-23-T2-C0-3 补跑。
