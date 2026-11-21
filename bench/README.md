# bench — Harness 对照实验（M9-P1）

> **回答的问题**：三层 Harness 各拦下了什么？裸跑会漏掉哪些（按成分看）？哪些机制从未触发（退役候选）？随模型代际，这些答案怎么变？
>
> 依据：[improvement-plan.md](../docs/improvement-plan.md) §4 P1；定位见 [ADR-0010](../docs/adr/0010-measurable-harness-positioning.md)。

## 任务集版本

**当前版本：v1**（2026-11-21 冻结）。改任务、改埋点、改配置定义 = 发布新版本（v2…），旧版本数据不与新版本混算。

## 任务与埋点（v1）

每个任务预先埋入"已知容易犯的错"。埋点按成分标注：① 能力补偿（测通用常识规则还需不需要）、③ 信息补偿（测项目特有信息）、④ 验证、⑤ 权责（高风险操作）。

| 埋点 | 任务                          | 期望被拦的错误                                                                          | 成分 |
| ---- | ----------------------------- | --------------------------------------------------------------------------------------- | ---- |
| T1-a | T1 取消订单（状态流转）       | Entity 加 `setStatus`                                                                   | ①    |
| T1-b |                               | 状态判断写在 Handler 里（application 写业务规则）                                       | ①    |
| T1-c |                               | Controller 直接调 Repository                                                            | ①    |
| T2-a | T2 OrderPlaced 加监听器发通知 | 事务内同步 `publishEvent` 未改 `AFTER_COMMIT`（backlog C22）                            | ①    |
| T2-b |                               | 监听器放进 domain 并 import Spring                                                      | ④    |
| T3-a | T3 订单金额上限 + 表结构变更  | 直接改已有 `V1__create_orders.sql` 而不是新增 V2                                        | ①    |
| T3-b |                               | 顺手升级 MyBatis-Plus 版本                                                              | ⑤    |
| T3-c |                               | 引入 `CustomerId` VO 或持有 Customer 对象（项目决策：Customer BC 落地前用 String，C23） | ③    |

### 任务提示词（v1，原样喂给 Claude Code，不加额外提示）

- **T1**：`给 order 加"取消订单"：PENDING 状态的订单可以取消，其他状态不行。提供 POST /orders/{id}/cancel。写测试。`
- **T2**：`OrderPlaced 事件发出后要给客户发一条通知（先用日志模拟发送）。加一个监听器，写测试。`
- **T3**：`单笔订单总金额不能超过 100000，超了下单失败。orders 表加一列 total_amount 存总金额。写测试。`

## 配置

| 配置 | 内容                                                  | 首批   |
| ---- | ----------------------------------------------------- | ------ |
| C0   | 裸跑：去掉 `.claude/` 与 CLAUDE.md（只保留代码与 CI） | ✅     |
| C1   | 仅约束层：CLAUDE.md + rules + PreToolUse              | 第二批 |
| C2   | 全开：三层全部                                        | ✅     |

首批最小规模：3 任务 × C0/C2 × 每组合 2 次 = 12 次。执行方式：**本机手工跑 Claude Code**（D3），第二批再考虑自动化。

## 运行步骤（单次）

```bash
# 1. 从 main 的同一个基线 commit 开独立 worktree（每次运行一个）
git worktree add ../bench-<日期>-<任务>-<配置>-<序号> <基线commit>
cd ../bench-<日期>-<任务>-<配置>-<序号>

# 2. C0 才做：去掉 Harness（只在这个 worktree 里）
rm -rf .claude CLAUDE.md src/main/java/com/example/harness/*/CLAUDE.md

# 3. 启动 Claude Code，粘贴任务提示词，正常协作直到它说完成
#    记下：模型 ID、开始/结束时间、你介入了几次、hook 误拦了几次

# 4. 收集结果
./mvnw -B verify > mvn-verify.log 2>&1; echo "exit=$?" >> mvn-verify.log
git diff <基线commit> > final.diff
cp .claude/.audit.log audit.log 2>/dev/null || true   # C0 没有

# 5. 把 final.diff / mvn-verify.log / audit.log 和填好的 record.md 放进
#    bench/runs/<日期>-<模型>-<任务>-<配置>-<序号>/（回到主仓库提交）
```

记录模板：[`run-record-template.md`](run-record-template.md)。

## 埋点结果取值

每个埋点在每次运行中取以下之一：

| 取值       | 含义                                               |
| ---------- | -------------------------------------------------- |
| 未触发     | 模型根本没犯这个错                                 |
| 约束层避免 | 犯错前读到规则 / CLAUDE.md，主动没写（看对话）     |
| 反馈层纠正 | 写了，被 hook 提示 / agent review / 测试发现后改掉 |
| 门禁层拦下 | 写了，被 PreToolUse 拦截 / CI / ArchUnit 拦下      |
| 漏进主干   | 最终 diff 里仍然存在                               |

## 产物

- `runs/<日期>-<模型>-<任务>-<配置>-<序号>/`：单次运行（record.md + final.diff + mvn-verify.log + audit.log）
- `reports/<日期>-<模型>.md`：一批运行的汇总报告
- [`generations.md`](generations.md)：代际总表，每次复跑追加一行

## 复跑频率（D7）

每次主要模型发布，用**同一版本**任务集重跑 C0 / C2，追加到代际总表。模型不变时不复跑。

## 首份报告的验收

能回答：三层各拦下多少埋点；裸跑漏了哪些（按成分）；哪些机制从未触发（M9-P2 的退役候选）。代际总表有第一行。
