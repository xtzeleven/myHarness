# bench — Harness 对照实验（M9-P1）

> **回答的问题**：三层 Harness 各拦下了什么？裸跑会漏掉哪些（按成分看）？哪些机制从未触发（退役候选）？随模型代际，这些答案怎么变？
>
> 依据：[improvement-plan.md](../docs/improvement-plan.md) §4 P1；定位见 [ADR-0010](../docs/adr/0010-measurable-harness-positioning.md)。

## 任务集版本

**当前版本：v1**（2026-11-21 冻结）。改任务、改埋点、改配置定义 = 发布新版本（v2…），旧版本数据不与新版本混算。

**v1 的固定基线**：`84e90f4537d713e7af6b10d16abe28f8c0fb3430`（首批数据全部在它上面跑）。

- 用 v1 复跑（换模型代际）一律用这个基线，不用 HEAD。提示词由 `run-auto.sh` 从基线 commit 的本文件里取，所以改 HEAD 上的本文件不影响 v1 的口径。
- 基线之后 Harness 本身改过（灰名单 `ask-user.yaml`、`policy-dispatch.py`、`CLAUDE.md` 等；业务代码、`pom.xml`、`.github/scripts` 没变），所以 HEAD 上的 C2 不是代际总表里那个 C2。要测新的 Harness：同一个模型在新旧两个基线上各跑一遍再比，或者发 v2。两种做法的数据都不和 `84e90f4` 的数据写进同一格。

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

首批最小规模：3 任务 × C0/C2 × 每组合 2 次 = 12 次。执行方式原定**本机手工跑 Claude Code**（D3）；2026-11-23 首批改为**无界面自动跑**（[`run-auto.sh`](run-auto.sh)），与手工跑的差别：

- 确认请求（含灰名单）由一个自动同意的 permission prompt tool 回答，人工介入记 0；该工具在 C0 / C2 都出现在模型的工具列表里
- 单次上限 60 分钟，超时作废；首批 T3 三次超时后，补跑放宽到 90 分钟（报告里注明）
- 中转站整段不通时 claude 仍以 `subtype=success` 退出（`is_error=true`、0 次工具调用），这种运行作废
- 自动数据不和手工数据混算；报告里注明执行方式
- 输出目录不覆盖（2026-11-26 起）：副本目录或 `.out` 目录任一个已存在，`run-auto.sh` 报错退出并原样保留已有内容；同日同任务同配置重跑要换序号，作废的也占号。`all` 模式下有子运行没跑起来时整体以非零退出

## 运行步骤（单次）

> **防答案泄漏**（2026-11-22 修订，修订前没有任何运行数据，仍算 v1）：仓库里有文件把埋点写得清清楚楚（本文、improvement-plan、rule-inventory、backlog、CHANGELOG），git 历史里也有。所以每次运行都**导出一份不带历史的副本**，所有配置都先删掉这些文件，再按配置决定去不去 Harness。副本放在 `~/bench-runs/` 下，不放在任何项目目录里（Claude Code 会逐级加载上级目录的 CLAUDE.md）。
>
> **用户级配置也会混进来**（2026-11-23 首批作废后加）：`~/.claude/` 下的 skills / hooks / MCP / 记忆在 C0、C2 都会加载。首批里用户级 gitnexus skill 把模型引出副本（读 `~/.gitnexus/registry.json`、试 `npx gitnexus analyze`），7 次运行全部作废。所以 claude 要用**独立的配置目录**（`CLAUDE_CONFIG_DIR`），里面只放连接所需的 `env` 与 `model`；跑 bench 期间还要删掉主仓库的 gitnexus 索引（C2 的项目级 gitnexus skill 可能引模型用命令行查它），跑完再重建：
>
> ```bash
> CFG=~/bench-runs/.claude-config; mkdir -p "$CFG" && chmod 700 "$CFG"
> (umask 077; python3 -c "import json,os; d=json.load(open(os.path.expanduser('~/.claude/settings.json'))); json.dump({k:d[k] for k in ('env','model') if k in d}, open('$CFG/settings.json','w'))")
> gitnexus remove myHarness --force      # 跑完：在主仓库 gitnexus analyze --index-only
> ```
>
> **MCP 也会泄漏**（2026-11-23 再修订，同样没有运行数据，仍算 v1）：gitnexus 是用户级 MCP，C0 / C2 都会加载；它按名字能查任何已索引的仓库，主仓库的索引里就有本文、improvement-plan、rule-inventory 等答案文件。所以第 6 步用 `--strict-mcp-config` 启动，只加载副本自己的 `.mcp.json`。用户级 gitnexus hook（Grep / Glob 时注入图谱上下文）按 cwd 找索引，副本里没有 `.gitnexus/`，不会触发。

```bash
# 1. 从基线 commit 导出干净副本（不带 git 历史）；v1 的基线见「任务集版本」
B=84e90f4537d713e7af6b10d16abe28f8c0fb3430; RUN=~/bench-runs/<日期>-<任务>-<配置>-<序号>
mkdir -p "$RUN" && git archive "$B" | tar -x -C "$RUN" && cd "$RUN"

# 2. 所有配置都做：删掉写有埋点答案的文件
rm -rf bench docs/improvement-plan.md docs/rule-inventory.md \
  docs/improvement-backlog.md docs/improvement-backlog-archive.md CHANGELOG.md
#    基线 84e90f4 的 G11 测试拿 T3-a 的列名当示例：副本里换成中性名字（之后的基线已改，这步是空操作）
f=.claude/scripts/tests/test_check_migration_immutability.py; [ -f "$f" ] && perl -pi -e 's/total_amount/remark/g' "$f"

# 3. C0 才做：去掉 Harness
rm -rf .claude .githooks CLAUDE.md src/main/java/com/example/harness/*/CLAUDE.md

# 4. 建一个只有一个提交的新仓库当基线（模型需要 git，但看不到历史）
git init -q && git add -A && git commit -qm "bench baseline"
[ -d .githooks ] && git config core.hooksPath .githooks   # C2

# 5. 自检：两条都应该没有输出，有输出就别跑
git grep -l -w -E 'setStatus|CustomerId|AFTER_COMMIT|total_amount' -- ':!src'
git grep -l -E '埋点|期望被拦' -- .

# 6. 在 $RUN 里启动 Claude Code：只加载副本的 .mcp.json，不加载用户级 MCP（gitnexus 索引含答案）
CLAUDE_CONFIG_DIR=~/bench-runs/.claude-config claude --strict-mcp-config --mcp-config .mcp.json
#    进会话先跑 /mcp：只应有 mysql-readonly，出现 gitnexus → 退出重来；/skills 里不应有用户级 skill
#    然后粘贴任务提示词，正常协作直到它说完成
#    记下：模型 ID、开始/结束时间、你介入了几次、hook 误拦了几次；
#    模型读了 $RUN 以外的文件（如 cd 回主仓库、用 gitnexus 查 myHarness）→ 本次作废；
#    模型把自己的命令输出写到 /tmp 再读回、查看 ~/.m2 不算；读 ~/.gitnexus 注册表、npx gitnexus 不算
#    （C2 的 §8 本来就让模型先用 gitnexus；开跑前已确认注册表里没有 myHarness，只记入观察）

# 7. 收集结果（写到副本外的 $RUN.out/，不污染 diff；B0 = 副本的初始提交，模型自己提交过也能比全）
OUT="$RUN.out"; mkdir -p "$OUT"; B0=$(git rev-list --max-parents=0 HEAD)
./mvnw -B verify > "$OUT/mvn-verify.log" 2>&1; echo "exit=$?" >> "$OUT/mvn-verify.log"
bash .github/scripts/check-migration-immutability.sh "$B0" > "$OUT/ci-local.log" 2>&1; echo "exit=$?" >> "$OUT/ci-local.log"
git add -A && git diff --cached "$B0" > "$OUT/final.diff"
cp .claude/.audit.log "$OUT/audit.log" 2>/dev/null || true   # C0 没有

# 8. 把 $OUT 里的文件和填好的 record.md 放进主仓库的
#    bench/runs/<日期>-<模型>-<任务>-<配置>-<序号>/ 并提交
```

记录模板：[`run-record-template.md`](run-record-template.md)。自动运行的结果用 [`analyze.py`](analyze.py) 生成记录草稿（`python3 bench/analyze.py ~/bench-runs/<RUN>.out`）和汇总表（`--table`）：埋点按"最终 diff 里有 → 漏进主干 / 中途写过后来没了 → 反馈层纠正或门禁层拦下 / 没写过 → 未触发（C2 提到规则 → 约束层避免）"**初判**，带"待复核"的要对照 transcript 人工确认。有效性和复核怎么记见「统计口径」。

## 埋点结果取值

每个埋点在每次运行中取以下之一：

| 取值       | 含义                                               |
| ---------- | -------------------------------------------------- |
| 未触发     | 模型根本没犯这个错                                 |
| 约束层避免 | 犯错前读到规则 / CLAUDE.md，主动没写（看对话）     |
| 反馈层纠正 | 写了，被 hook 提示 / agent review / 测试发现后改掉 |
| 门禁层拦下 | 写了，被 PreToolUse 拦截 / CI / ArchUnit 拦下      |
| 漏进主干   | 最终 diff 里仍然存在                               |

## 统计口径

2026-11-26 补。只约束今后的记录、报告和代际总表怎么写；首批的报告和运行记录保持原样，它们与本节的出入记在 [`generations.md`](generations.md) 的首批说明里。

**一次运行的有效性有三种，分开计数**

| 状态     | 条件                                                                                                                                                                | 计入报告 |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| 有效     | 记录模板「数据有效性」各项都判得了，且都通过                                                                                                                        | 是       |
| 作废     | 至少一项确定不通过：超时、API 错误退出或 0 次工具调用、读了副本外的文件、加载了 gitnexus MCP、自检有输出；没走到收集阶段（没有 `summary.json`，"未完成"）也按作废计 | 否       |
| 无法判定 | 没有确定不通过的项，但缺原始材料判不全                                                                                                                              | 否       |

- 入库的 `runs/*` 没有 `runner.log`、`selfcheck.txt`、`transcript.jsonl`。`analyze.py` 读这些目录时：
  - 埋点一律标"无法复核"；只有"漏进主干"能从 `final.diff` 单独确定，仍会判出。
  - `summary.json` 带 `meta` 的（2026-11-26 之后的运行）有效性判得出。
  - 不带 `meta` 的看同目录 `record.md` 的有效性清单：有未勾项 → 作废，原因注明来自 `record.md`；全勾 → 仍是"无法判定"，那是人工复核的结论，不是工具复算出来的。
- 要复算首批的有效数，得用仓库外的原始输出：`python3 bench/analyze.py --table ~/bench-runs/*.out`。表格在 stdout，统计和每个非有效运行的原因在 stderr。原始输出不入库，丢了就只剩 `record.md` 的人工结论。

**样本数**

- 每格写清三个数：目标次数、尝试次数、有效次数。尝试次数包含所有作废的。
- 代际总表的单元格只列有效运行，一次一个结果，不补位；有效次数不是目标次数时，在 [`generations.md`](generations.md) 该批的「样本数」节里写出实际数（首批见[「样本数」](generations.md#样本数claude-fable-5-22026-11-23)）。
- 结论里提到"N 次都没犯"时，N 是有效次数。

**超时上限**

- 上限是运行条件的一部分，记在每次运行的 `meta.timeout_limit_s` 里，报告里按批次写明。
- 只在某个上限下才有效的运行要标出来（"在 90 分钟上限下有效，60 分钟下会作废"）。
- 不同上限下跑出来的耗时可以并列，写倍数时要同时写出各自的上限。
- 一格里有超时作废的运行时，耗时只来自跑完的那几次。倍数旁边要写这一格"尝试几次、超时几次"，并注明它是观测比值，不能据此推断这一格的典型耗时或偏差方向。
- 首批的例子：T3 的"约 7–8 倍"是一条有效的 C2 运行（4030 秒）对两条有效的 C0 运行（491、577 秒）的观测比值。T3-C2 有目录记录的 8 次尝试里 3 次超时作废（首批有目录记录的尝试共 23 次）。有超时、样本少、上限记录又不完整，无法据此推断典型耗时或偏差方向。

**ask 与误拦**

- 误拦 = hook `deny` 拦了正当操作。
- 灰名单 `ask` 不算误拦，单独计数；无界面自动运行里 ask 一律被同意，所以它只能当成本数据，不能说明拦截效果。
- ask 次数按有效运行统计，作废运行里的另列。

**初判与复核**

- `analyze.py` 的结论是初判。记录的埋点表保留三列：初判、复核后、依据。
- 复核改写初判时，依据里写明为什么改（对话位置、diff 位置），初判一列不删。
- 报告里写出"改写了几处、各是哪一格"，读者能从记录里逐条找到依据。
- `analyze.py` 的判定规则改过之后，同一份原始输出重算的初判可能和入库记录里的不一样。以记录为准，差异要重新复核后才能改记录。

## 运行元数据（`summary.json` 的 `meta`）

`run-auto.sh` 从 2026-11-26 起在 `summary.json` 里多写一个 `meta` 块，记这次运行是在什么条件下跑的。之前的运行没有这个块，`analyze.py` 两种都能读。

| 字段                  | 含义                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------- |
| `schema`              | `meta` 的格式版本，现在是 1                                                             |
| `task_set`            | 任务集版本，从基线 commit 的本文件读（和提示词同源）                                    |
| `task` `conf` `seq`   | 任务、配置、序号                                                                        |
| `day`                 | 输出目录名里的日期（本机时区）                                                          |
| `base_commit`         | 基线的完整 SHA                                                                          |
| `runner_commit`       | 跑的时候主仓库的 HEAD，即 `run-auto.sh` 自己的版本                                      |
| `exec_mode`           | 执行方式，现在只有 `headless-auto-approve`（确认请求一律同意）                          |
| `model_arg`           | 传给 `--model` 的原值（可能是别名）；真实模型 ID 在顶层的 `model`                       |
| `claude_code_version` | 会话 init 消息里的 Claude Code 版本，取不到时用 `claude --version` 的输出               |
| `timeout_limit_s`     | 本次的超时上限（秒）                                                                    |
| `elapsed_s`           | 模型会话的耗时（秒）；按 5 秒轮询，超时的还多出终止进程的几秒                           |
| `timed_out`           | 是否因超时被终止                                                                        |
| `started_at`          | 会话开始时间（UTC）                                                                     |
| `selfcheck_clean`     | 第 5 步自检是否没有输出。自检有输出时脚本直接中止、不写 `summary.json`，所以正常是 true |

取不到的字段写 `null`，不填默认值。

## 尝试记录（`attempt-start.json` / `attempt-end.json`）

2026-11-27 起，`run-auto.sh` 每次尝试另写两个小文件到 `.out` 目录，都只写一次、不覆盖（[`attempt-record.py`](attempt-record.py)）。它们记的是**脚本怎么跑的**，不是样本有没有效；有效性仍由 `analyze.py` 按「统计口径」判，`analyze.py` 不读这两个文件。

- `attempt-start.json`：占到目录后立刻写。任务、配置、序号、任务集版本、基线完整 SHA、`--model` 传值、超时上限、所属批次。脚本之后被强杀、没有任何收尾时，靠它知道这次尝试是在什么条件下开始的。
- `attempt-end.json`：脚本结束时写。`script_status` 取 `completed`（跑完）、`failed`（中止，`stage` 是停在哪一步）、`interrupted`（收到 INT / TERM）；另记脚本退出码、会话进程退出码 `model_exit`、是否超时。没有这个文件 = 脚本被强杀或机器掉电。
- `stage` 的取值按顺序是：`base`、`prompt`、`claim`、`start-record`、`export`、`strip`、`git-init`、`selfcheck`、`model`、`collect`、`summary`、`done`。
- **基线只解析一次**：传给 `run-auto.sh` 的可以是 `HEAD`、分支名或短 SHA，脚本一开始就解析成完整 commit SHA，之后读提示词、读任务集版本、导出副本、写记录都用它；运行途中引用被移动不影响本次尝试。`all` 模式由父脚本解析一次再传给子脚本。`base_arg` 记原始输入，`base_commit` 记解析结果。解析不出来就报错退出，不占目录。
- **收集出错不发布结果**：`git add` / `git diff` 失败时，结束记录是 `failed`、`stage` 为 `collect`，不留 `final.diff`，也不写 `summary.json`，这次尝试在 `analyze.py` 里算"未完成"。`mvn verify` 或 CI 脚本失败不属于这种情况，那是样本自己的结果，照常记录。
- **脚本跑完不等于样本有效**：超时、API 错误的运行，脚本照样是 `completed`。反过来，`failed` / `interrupted` / 没有结束记录的尝试没有 `summary.json`，`analyze.py` 记为"未完成"。
- `all` 模式在 `~/bench-runs/.batches/<批次>/` 下留 `plan.txt`、每个子运行的结束记录和汇总 `batch.json`，结束时打印"跑完 / 失败 / 被信号中断 / 没有结束记录"各几个。有子脚本不是跑完，整体以非零退出。
- 记录写不出来（目标已存在、目录不可写）时不覆盖已有内容，本来以 0 结束的运行改为非零退出。

v2 的实验方案草案见 [`v2-plan.md`](v2-plan.md)（未定稿，当前版本仍是 v1）。

## 拦截能力自检（不调模型）

对照实验回答"模型会不会犯"，[`gate-check.py`](gate-check.py) 回答另一半："真犯了，哪一层报警"。它在 `git archive HEAD` 的临时副本里把每个埋点的最小违规改动直接打上去，依次探 PreToolUse hook、ArchUnit、CI 脚本。要 JDK 17，约 1 分钟，不花模型费用：

```bash
JAVA_HOME=<jdk17 路径> python3 bench/gate-check.py          # 全部埋点；也可只给 T1-a T3-b
```

2026-11-25 在 `5b05a7f` 上的结果（ask = 灰名单确认，hint = 只提示不拦）：

| 埋点  | 违规改动                               | PreToolUse | ArchUnit                             | CI 脚本                  | 有没有硬拦                |
| ----- | -------------------------------------- | ---------- | ------------------------------------ | ------------------------ | ------------------------- |
| T1-a  | Entity 加 `setStatus`                  | ask        | `domain_no_setters`                  | —                        | 有                        |
| T1-b  | Handler 里判状态，抛领域异常           | hint       | `application_no_business_rule_throw` | —                        | 有                        |
| T1-b' | 同上，改抛 `IllegalStateException`     | hint       | —                                    | —                        | **没有**（ADR-0011 已知） |
| T1-c  | Controller 直接注入 Repository         | 放行       | `interfaces_no_repository`           | —                        | 有                        |
| T2-a  | 事务内同步 `@EventListener`            | hint       | —                                    | —                        | **没有**                  |
| T2-b  | 监听器放进 domain 并 import Spring     | hint       | `domain_framework_free`              | `ddd-layer-purity`       | 有                        |
| T3-a  | 改已入库的 V1 迁移                     | hint       | —                                    | `migration-immutability` | 有                        |
| T3-b  | 改 `<mybatis-plus.version>` 属性升版本 | ask        | —                                    | —                        | 只有 ask                  |
| T3-c  | 新建 `CustomerId` VO                   | hint       | —                                    | —                        | **没有**                  |

- **T3-b 只有 ask，没有第二层**：本脚本只探"改整行属性"这一种改法（G16 起问，在 `028e735` 上这一格是 hint）。只换版本号数字、只改 `<parent>` 的 `<version>` 行、MultiEdit 三种改法由 G17 的 `pom-version-lines` 补上，证据在 `test_pre_tool_use.sh` 的 `ask-pom-*` 用例，不在这张表里。ArchUnit 和 CI 都不检查依赖版本，用户在弹窗里点了同意就没有别的拦截。
- **T2-a 没有任何硬机制**：`PlaceOrderHandler` 里原有的提醒注释已在 `04767ea` 删除（它等于把答案写在代码里），现在只剩 backlog C22 的记录。集成测不在本脚本范围内。
- **T3-c 没有任何硬机制**：灰名单 `ddd-aggregate-boundary` 收窄到"只问已有文件"后，新建 VO 不再问（在 `63889ab` 上这一格是 ask，但那是"改 `domain/` 就问"带出来的，不是针对这个埋点）。"Customer BC 落地前用 String"是项目决策（C23），只写在文档里。T2-b 的 PreToolUse 同样由 ask 变为 hint，仍被 ArchUnit 和 CI 拦下。

## 产物

- `runs/<日期>-<模型>-<任务>-<配置>-<序号>/`：单次运行（record.md + summary.json + final.diff + mvn-verify.log + audit.log；C0 没有 audit.log，没走到收集阶段的作废运行没有 final.diff 和 mvn-verify.log）
- `~/bench-runs/<日期>-<任务>-<配置>-<序号>.out/`：原始输出，不入库（transcript、runner.log、selfcheck.txt、debug 日志等）。重算初判和有效数要用它
- `reports/<日期>-<模型>.md`：一批运行的汇总报告
- [`generations.md`](generations.md)：代际总表，每次复跑追加一行

## 复跑频率（D7）

每次主要模型发布，用**同一版本**任务集、**同一个固定基线**重跑 C0 / C2，追加到代际总表。模型不变时不复跑。

## 首份报告的验收

能回答：三层各拦下多少埋点；裸跑漏了哪些（按成分）；哪些机制从未触发（M9-P2 的退役候选）。代际总表有第一行。
