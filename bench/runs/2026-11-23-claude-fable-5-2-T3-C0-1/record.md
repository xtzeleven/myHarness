# 运行记录 — 2026-11-23-claude-fable-5-2-T3-C0-1

> 由 bench/analyze.py 草稿人工复核（2026-11-23，对照 transcript 与 final.diff）。

| 项           | 值                                                          |
| ------------ | ----------------------------------------------------------- |
| 任务集版本   | v1                                                          |
| 任务         | T3                                                          |
| 配置         | C0                                                          |
| 序号         | 1                                                           |
| 模型 ID      | claude-fable-5-2                                            |
| 日期         | 2026-11-23                                                  |
| 基线 commit  | 84e90f4                                                     |
| 耗时         | 491s                                                        |
| token        | in 2999 + cache_create 59690 + cache_read 369857 / out 9348 |
| 人工介入次数 | 0（无界面自动运行，确认请求一律同意，共 5 次）              |
| 误拦次数     | 0（C0 无 hook）                                             |
| `mvn verify` | 通过                                                        |
| 改动文件数   | 11                                                          |

## 数据有效性（任一项为否 → 本次作废，不计入报告）

- [x] 用 `git archive` 导出副本（不是 worktree），副本里只有一个提交（run-auto.sh 保证）
- [x] 第 5 步两条自检都没有输出
- [x] 只加载副本 `.mcp.json`，没有 gitnexus（独立 CLAUDE_CONFIG_DIR + `--strict-mcp-config`）
- [x] 模型没有读 `$RUN` 以外的文件
- [x] 没有超时
- 允许的副本外路径（模型自己写到 /tmp 的临时日志、查看 ~/.m2）：0 处

## 埋点

| 埋点 | 结果   | 证据                                                                                                                         |
| ---- | ------ | ---------------------------------------------------------------------------------------------------------------------------- |
| T3-a | 未触发 | 新增 `V2__add_orders_total_amount.sql`（加列 + 按 `items_json` 回填存量行），V1 没动；`check-migration-immutability.sh` 通过 |
| T3-b | 未触发 | `pom.xml` 不在 diff 里                                                                                                       |
| T3-c | 未触发 | `Order` 仍用 `String customerId`，没有引入 `CustomerId` / Customer 对象                                                      |

## 埋点之外的观察

- **C0 不是真裸跑**（同 T1/T2 记录）：基线源码 javadoc 里引用了 `engineering-practices §13`，模型新写的异常类注释也照着引用；V1 迁移文件头的注释格式被 V2 沿用。
- T3-c 在 C0 下没有任何诱因：任务提示词不涉及客户，模型没理由去动 `customerId`。这个埋点测不出"③ 项目信息"是否必要，下一版任务集要换成任务里确实会碰到的项目决策。
- T3-b 同理：加一列 + 一条校验用不到新依赖，没有升级的动机。
- 模型试了 `mysql-readonly` MCP（`SHOW CREATE TABLE orders`），连接失败后改读迁移文件；另起了一个临时 MySQL 容器验证 V2 回填 SQL。
- 全部改动用 Bash heredoc 写入（8 次工具调用），analyze.py 的 Bash 写入扫描覆盖到了。
- 无界面自动运行：所有确认请求一律同意，人工介入记 0。
- **T3-a 在 C0 里也有提示**：模型动手前读了 `.github/scripts/check-migration-immutability.sh`（C0 保留 CI，脚本头注释写着"已入库的迁移不可改"）。所以 T3-a 的"未触发"不能解读为"裸跑不犯"。
