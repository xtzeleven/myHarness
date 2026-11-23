# 规则清单 — 成分 / 强制力 / 处置 / 退役条件（M9-P2 · backlog G5）

**Status**: 初版 2026-11-22。四个字段已全部填写；**还没有 bench 数据**，所以退役条件写好了但没有一条已满足。按数据拆规则是 G7 的事。
**依据**: [improvement-plan.md](improvement-plan.md) §2（五种成分）、§4 P2；[ADR-0010](adr/0010-measurable-harness-positioning.md)
**一致性**: `test_rule_inventory.py`（CI `python-unit-test`）校验 policies 规则 id、CI job、hook、agent、command、ArchUnit 规则都在本清单里，且每行四个字段齐全、①② 行有退役条件。新增规则不登记，CI 就 fail。

## 字段与取值

- **成分**：① 能力补偿 · ② 编排补偿 · ③ 信息补偿 · ④ 验证 · ⑤ 权责。有多个成分时主成分写在前面。
- **强制力**：**机制** = 代码 / CI / 原生权限强制，模型不配合也生效；**信号** = 自动触发，但只提示或记录、不拦；**文档** = 写给模型或人读的文字，靠自觉。
- **处置**：保留 · 加强 · 冻结（不再扩写）· 改指针 · 下沉（P3 分层）· 退役候选。
- **退役条件**（简写）：
  - **两代未犯(X)**：[`bench/generations.md`](../bench/generations.md) 连续两代模型在 C0（裸跑）下埋点 X 都是「未触发」→ 删除；删完用同一任务集复跑 C2，确认不退化（plan §4 P2）。
  - **无埋点**：任务集 v1 没有能测它的埋点。先在任务集 v2 补埋点，补之前不删。
  - **原生替代(Y)**：Claude Code 原生功能 Y 能覆盖时，迁过去再删。
  - **—**：不设退役条件。⑤ 不随模型能力退役，只在原生权限能表达时迁移；③ ④ 不贬值。

埋点见 [bench/README.md](../bench/README.md)：T1-a setter · T1-b application 写业务规则 · T1-c Controller 直调 Repository · T2-a 事务内同步发事件 · T2-b 监听器进 domain · T3-a 改已有 V1 迁移 · T3-b 顺手升级依赖 · T3-c 违反"Customer 用 String"的项目决策。

---

## 1. 黑名单（`deny.yaml` · PreToolUse exit 2 · 规则加载失败时 fail-closed）

| 规则                                                                                              | 成分 | 强制力 | 处置                                                                                      | 退役条件 |
| ------------------------------------------------------------------------------------------------- | ---- | ------ | ----------------------------------------------------------------------------------------- | -------- |
| `bash-rm-rf-root` `bash-rm-rf-home` `bash-rm-rf-git`                                              | ⑤    | 机制   | 保留；`rm -rf /`、`rm -rf ~` 另有原生 deny 双层                                           | —        |
| `bash-find-delete-root`                                                                           | ⑤    | 机制   | 保留（原生前缀规则写不出 find 变体）                                                      | —        |
| `bash-force-push-protected` `bash-force-push-refspec-protected`                                   | ⑤    | 机制   | 保留；`--force` / `-f` 推 main、master 另有原生 deny；`+refspec` 与 `prod` 只有 hook 一层 | —        |
| `bash-chmod-777-broad` `bash-curl-pipe-sh`                                                        | ⑤    | 机制   | 保留                                                                                      | —        |
| `write-env-file` `write-key-cert` `write-ssh-key` `write-credential-file` `write-credentials-dir` | ⑤    | 机制   | 保留；原生 `Edit(**/.env)` 等双层（原生层待 G2 实测）                                     | —        |

## 2. 灰名单（`ask-user.yaml` · 原生确认弹窗，ADR-0009；6 个 permission mode 实测都弹窗，G1）

| 规则                                                                     | 成分 | 强制力 | 处置                                                                                                                                            | 退役条件                                                                                                         |
| ------------------------------------------------------------------------ | ---- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `bash-mysql-ddl-dml` `bash-sql-file-pipe`                                | ⑤    | 机制   | 保留                                                                                                                                            | —                                                                                                                |
| `bash-git-rewrite-history` `bash-git-rm-recursive` `bash-git-reset-hard` | ⑤    | 机制   | 保留                                                                                                                                            | —                                                                                                                |
| `bash-mvn-deploy`                                                        | ⑤    | 机制   | 保留                                                                                                                                            | —                                                                                                                |
| `pom-major-deps` `pom-blank-rewrite` `bash-pom-write`                    | ⑤    | 机制   | 保留（埋点 T3-b）                                                                                                                               | —                                                                                                                |
| `ddd-aggregate-boundary` `bash-domain-boundary-write`                    | ⑤ ①  | 机制   | 保留，bench 记录误拦次数。⚠️ 实际匹配 `domain/` 下**全部** `.java`，CLAUDE.md §9 曾写成"聚合根 / Repository 接口 / DomainEvent"，已改指针（K3） | 只收窄不删：C2 运行记录误拦占比高，且 ArchUnit 已兜住 T1-a、T2-b → 收窄到聚合根 / Repository 接口 / 领域事件文件 |

## 3. 提示（`hints.yaml` · stderr 提示 · 每会话去重）

| 规则                                                        | 成分 | 强制力 | 处置                                                                                         | 退役条件                                                                           |
| ----------------------------------------------------------- | ---- | ------ | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `hint-domain-layer`                                         | ① ②  | 信号   | 冻结                                                                                         | 两代未犯(T1-a, T2-b)                                                               |
| `hint-application-layer`                                    | ① ②  | 信号   | 冻结                                                                                         | 两代未犯(T1-b)                                                                     |
| `hint-migration-files`                                      | ① ②  | 信号   | 冻结；T3-a 目前只有这一层和 migration-author（见 §13 K1）                                    | 两代未犯(T3-a)（K1 的迁移 CI 检查已落地，G11）                                     |
| `hint-infrastructure-layer` `hint-spring-config`            | ① ②  | 信号   | 冻结，与 `spring-boot-reviewer` 同去留                                                       | 无埋点（任务集 v2 补适配器 / 配置类埋点）                                          |
| `hint-pom-xml` `hint-mvn-cmd`                               | ② ③  | 信号   | 冻结                                                                                         | 原生替代(agent description 自动路由)：G7 抽查 C2 记录，没有提示也能调对 agent → 删 |
| `hint-mysql-select` `hint-grep-find` `hint-git-commit-push` | ②    | 信号   | 冻结                                                                                         | 原生替代(skill / agent description 自动路由)，抽查同上                             |
| `hint-claude-md`                                            | ②    | 信号   | 冻结                                                                                         | 原生替代(`/context` 显示注入 token)                                                |
| `hint-agent-md`                                             | ③    | 信号   | 保留：`agents-manifest-check` 只校验 AGENTS.md 的 agent 表，路由速查表与升级链表仍靠这条提示 | —                                                                                  |
| `hint-mcp-json` `hint-env-example`                          | ③ ⑤  | 信号   | 保留，作为 CI `structure-check`（`.env.example` ↔ `.mcp.json` 对齐）的前置提示              | —                                                                                  |
| `hint-gitignore`                                            | ③    | 信号   | 保留（项目踩坑 `pitfall_settings_local_already_tracked`）                                    | —                                                                                  |

## 4. 原生权限（`settings.json`）

| 规则                                                                               | 成分 | 强制力                                                                                              | 处置                                                                 | 退役条件 |
| ---------------------------------------------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | -------- |
| `permissions.deny`（23 条）                                                        | ⑤    | 机制                                                                                                | 保留，硬边界；hook 正则只算"防手滑"。hook 失效时是否仍拦，待 G2 实测 | —        |
| gitnexus MCP 只读：`GITNEXUS_MCP_READ_ONLY=1`（用户级 `~/.claude.json`，不在仓库） | ⑤    | 机制（gitnexus 自己拒绝 `rename` / `cypher` / `group_*`）；仓库管不到别的机器，靠 mcp-onboarding §3 | 保留（G15）                                                          | —        |

## 5. CLAUDE.md（每会话注入）

| 规则                                                                                   | 成分 | 强制力                                               | 处置                                                                                                                                   | 退役条件                                                                                                                                                                  |
| -------------------------------------------------------------------------------------- | ---- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| §1–4 行为准则（先想后写 / 简单优先 / 改动最小 / 目标驱动）                             | ①    | 文档                                                 | 保留 + 退役条件                                                                                                                        | 两代未犯(全部 ① 埋点)，且 C1（第二批）与 C0 无差异 → 删 §1–4                                                                                                              |
| §5 项目上下文                                                                          | ③    | 文档                                                 | 保留（进度快照已外移 README）                                                                                                          | —                                                                                                                                                                         |
| §6 DDD 禁忌前 5 条                                                                     | ① ④  | 机制（ArchUnit 6 条 + `ddd-layer-purity`）+ 文档     | 机制保留；文字下沉到 `src/` 子目录 CLAUDE.md（P3）                                                                                     | 文字：两代未犯(T1-a, T1-b, T1-c, T2-b) → 删文字，只留 ArchUnit                                                                                                            |
| §6 其余条（hook 先 `command -v`、不提交 IDE / 构建产物、生产库只读、不引入未声明依赖） | ③ ⑤  | 机制（`.gitignore`、MCP 只读账号、pom 灰名单）+ 文档 | 保留                                                                                                                                   | —                                                                                                                                                                         |
| §7 测试 / 校验命令                                                                     | ③    | 文档                                                 | 保留                                                                                                                                   | —                                                                                                                                                                         |
| §8 gitnexus 路由表                                                                     | ②    | 文档                                                 | 冻结                                                                                                                                   | 原生替代(skill description 自动触发) → 删路由表，只留"首次先建索引"                                                                                                       |
| gitnexus 注入块（Always / Never Do：改任何符号前必须跑 impact analysis）               | ②    | 文档                                                 | 冻结。⚠️ "MUST… before editing any symbol" 与 §2 简单优先、§3 改动最小冲突，且每会话付费注入；由 `gitnexus analyze` 生成，手改会被覆盖 | 无埋点；MCP 调用已进审计（G13，`mcp-observe.sh`）。bench 不加载 gitnexus（防答案泄漏），改看日常会话审计里 `mcp__gitnexus__*` 的调用量：长期为 0 → 关掉注入（观察期待定） |
| §9 人工决策清单                                                                        | ⑤    | 文档（镜像 policies yaml）                           | 已改指针（G12）：只留黑 / 灰名单语义与大类，清单以 `policies/*.yaml` 为准                                                              | —                                                                                                                                                                         |
| §10 子目录指引 · §11 Memory                                                            | ③    | 文档                                                 | 保留，按需查询                                                                                                                         | —                                                                                                                                                                         |
| §12 会话状态（`session-state.py`，主对话自觉调用）                                     | ②    | 文档 + 工具                                          | 冻结                                                                                                                                   | 原生替代(原生任务列表 / 会话恢复显示上次未完事项)                                                                                                                         |

## 6. engineering-practices.md

| 规则                                                                                | 成分 | 强制力                                                          | 处置                                         | 退役条件                                          |
| ----------------------------------------------------------------------------------- | ---- | --------------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------- |
| §0–2 阅读顺序 / CLAUDE.md 完备性 / rules 文档                                       | ②    | 文档（`/audit-practices` 评分依据）                             | 冻结                                         | P4 并入一页总览后删                               |
| §3 PreToolUse 防御 · §11 可观测 / 审计 · §15 Bypass / Permission Mode / 审计 policy | ⑤    | 机制（文字是对机制的说明）                                      | 保留；Permission Mode 实测表已填（G1）       | —                                                 |
| §4 Hooks · §5 Agents · §6 Commands                                                  | ②    | 文档                                                            | 冻结                                         | P4 并入一页总览后删                               |
| §7 CI / 质量门禁 · §9 测试 / 校验                                                   | ④    | 机制（`lint.yml`）                                              | 加强                                         | —                                                 |
| §8 Git 卫生                                                                         | ① ④  | 机制（`commit-lint`）+ 文档                                     | 保留                                         | 文字部分：无埋点                                  |
| §10 文档同步                                                                        | ③    | 文档 + 手动命令                                                 | 保留                                         | —                                                 |
| §12 DDD 分层                                                                        | ① ④  | 机制（ArchUnit）+ 文档                                          | 文字下沉 `java-ddd` 配置（P3）               | 两代未犯(T1-a, T1-b, T1-c, T2-b)                  |
| §13 Java / Spring 风格                                                              | ①    | 文档                                                            | 下沉 `java-ddd` 配置（P3）                   | 两代未犯(T2-a)                                    |
| §14 MCP 治理                                                                        | ⑤ ③  | 机制（只读账号 + 版本锁）+ 文档                                 | 保留                                         | —                                                 |
| §15 模型选择 / 降级 / 拒绝继续 / 升级链                                             | ②    | 文档（"model 选择须带注释"已由 `agents-manifest-check` 机制化） | 冻结；降级 / fallback 没有机制执行，标"参考" | 原生替代(子 agent `model` 字段 + 平台侧 fallback) |

## 7. Hooks

| 规则                                               | 成分 | 强制力                         | 处置                                  | 退役条件                                                    |
| -------------------------------------------------- | ---- | ------------------------------ | ------------------------------------- | ----------------------------------------------------------- |
| `pre-tool-use.sh`（→ `policy-dispatch.py`）        | ⑤    | 机制                           | 保留                                  | —                                                           |
| `format.sh` 格式化                                 | ④    | 机制                           | 保留                                  | —                                                           |
| `format.sh` 事后秘钥检测                           | ⑤    | 信号（只警告）                 | 保留                                  | —                                                           |
| `session-start.sh`                                 | ⑤ ③  | 信号                           | 保留门禁自检；注入内容按 ③ 改按需查询 | —                                                           |
| `user-prompt-submit.sh`                            | ⑤    | 信号（只警告，exit 0）         | 保留                                  | —                                                           |
| `stop-check.sh`                                    | ②    | 信号                           | 冻结，与 CLAUDE.md §12 同去留         | 原生替代(会话恢复)                                          |
| `subagent-stop.sh`                                 | ②    | 信号（靠 agent 自报 status）   | 冻结                                  | 原生替代(子 agent 结构化输出)                               |
| `pre-compact.sh`                                   | ②    | 信号                           | 冻结                                  | 原生替代(自动压缩摘要)：抽查 3 次压缩都保留了 4 类内容 → 删 |
| `prepare-commit-msg`（`.githooks/`）               | ⑤    | 机制                           | 保留（ADR-0012）                      | —                                                           |
| `mcp-observe.sh` MCP 调用审计（matcher `mcp__.*`） | ⑤    | 信号（只记录，任何失败都放行） | 保留                                  | —                                                           |

## 8. Agents（10 个，都是模型读的 prompt）

| 规则                                   | 成分 | 强制力          | 处置                                             | 退役条件                               |
| -------------------------------------- | ---- | --------------- | ------------------------------------------------ | -------------------------------------- |
| `code-reviewer`                        | ①    | 文档            | 只留项目特有部分                                 | 两代未犯(全部 ① 埋点) → 删通用部分     |
| `tdd-cycle-driver`                     | ①    | 文档            | 冻结                                             | 无埋点                                 |
| `spring-boot-reviewer`                 | ① ③  | 文档            | 只留项目特有部分                                 | 两代未犯(T2-a)；③ 部分保留             |
| `ddd-architect`                        | ① ③  | 文档            | 只留项目特有部分（typed ID、items JSON 列、C23） | 两代未犯(T1-a, T1-b, T1-c)；③ 部分保留 |
| `migration-author`                     | ① ③  | 文档            | 只留项目特有部分                                 | 两代未犯(T3-a)；③ 部分保留             |
| `maven-build-doctor`                   | ③ ①  | 文档            | 保留本机踩坑（JAVA_HOME 等）                     | 通用部分：无埋点                       |
| `schema-analyst`                       | ③    | 文档 + MCP 只读 | 保留                                             | —                                      |
| `docs-keeper`                          | ②    | 文档            | 冻结                                             | P4 文档预算落地后重审                  |
| `requirement-decomposer` `event-storm` | ①    | 文档            | 冻结（ADR-0008 Tier 2–4 冻结，D4）               | 无埋点（bench 只覆盖代码侧）           |

## 9. Commands / Skills

| 规则                                                                             | 成分 | 强制力             | 处置                            | 退役条件                         |
| -------------------------------------------------------------------------------- | ---- | ------------------ | ------------------------------- | -------------------------------- |
| `/commit`                                                                        | ② ①  | 文档               | 冻结                            | 无埋点                           |
| `/review`                                                                        | ①    | 文档               | 冻结，与 `code-reviewer` 同去留 | 两代未犯(全部 ① 埋点)            |
| `/verify-setup` `/doctor`                                                        | ④ ⑤  | 信号（手动跑脚本） | 保留                            | —                                |
| `/audit-practices` `/audit-context` `/cross-stage-check` `/sync-docs` `/onboard` | ②    | 文档（手动触发）   | 冻结                            | P4 并入一页总览 / 文档预算后重审 |
| skill `audit-practices` · `cross-stage-check`                                    | ②    | 文档               | 冻结，与同名 command 同去留     | 同对应 command                   |
| skill `gitnexus`（外部七件套）                                                   | ②    | 文档               | 冻结，与 CLAUDE.md §8 同去留    | 同 CLAUDE.md §8                  |

## 10. CI（`lint.yml` / `scheduled.yml`）

| 规则                                                                | 成分 | 强制力           | 处置                                              | 退役条件             |
| ------------------------------------------------------------------- | ---- | ---------------- | ------------------------------------------------- | -------------------- |
| `format-check` `structure-check` `hook-test` `python-unit-test`     | ④    | 机制             | 保留                                              | —                    |
| `java-build`（`mvn verify` + ArchUnit + IT 跳过即 fail）            | ④    | 机制             | 加强                                              | —                    |
| `ddd-layer-purity`（`git grep`）                                    | ④    | 机制             | 保留，作为不需要 JDK 的快速前置（ADR-0011）       | —                    |
| `agents-manifest-check`                                             | ④ ②  | 机制             | 保留；守护的 agent 体系本身是 ②，与 agents 同去留 | agents 全部退役后删  |
| `commit-lint`                                                       | ④    | 机制             | 保留                                              | —                    |
| `migration-immutability`（G11）                                     | ④    | 机制             | 保留；bench 第 7 步用工作区模式本地跑             | —                    |
| `bypass-guard`                                                      | ⑤    | 机制             | 保留（含 G6 尾注检查，ADR-0012）                  | —                    |
| `daily-structure-audit` `weekly-stale-check` `weekly-tool-versions` | ④ ③  | 信号（开 issue） | 保留                                              | —                    |
| `weekly-audit-reminder`                                             | ⑤    | 信号             | 保留                                              | —                    |
| `weekly-context-audit`                                              | ②    | 信号             | 冻结                                              | 原生替代(`/context`) |

## 11. ArchUnit（`DddRules`，跑在 `java-build`）

| 规则                                                                                                                    | 成分 | 强制力 | 处置                                                                                     | 退役条件 |
| ----------------------------------------------------------------------------------------------------------------------- | ---- | ------ | ---------------------------------------------------------------------------------------- | -------- |
| `LAYER_DIRECTION` `DOMAIN_FRAMEWORK_FREE` `INTERFACES_NO_REPOSITORY` `DOMAIN_NO_SETTERS` `NO_CROSS_AGGREGATE_REFERENCE` | ④    | 机制   | 加强                                                                                     | —        |
| `APPLICATION_NO_BUSINESS_RULE_THROW`                                                                                    | ④    | 机制   | 加强；只是 §6-3"application 不写业务规则"的可判定代理（ADR-0011），T1-b 能否抓到看 bench | —        |

## 12. 文档（`docs/`）

| 规则                                                                                                          | 成分 | 强制力                                                           | 处置                                  | 退役条件                                              |
| ------------------------------------------------------------------------------------------------------------- | ---- | ---------------------------------------------------------------- | ------------------------------------- | ----------------------------------------------------- |
| `loop-architecture.md`（含 E36 loop 硬上限）                                                                  | ②    | 文档                                                             | 冻结；"硬上限"没有机制执行，标"参考"  | 原生替代(平台子 agent / 计划模式自带的步数与重试控制) |
| `policy-model-selection.md`（含 E44 fallback）                                                                | ②    | 文档                                                             | 冻结；fallback 没有机制执行，标"参考" | 原生替代(子 agent `model` 字段 + 平台侧 fallback)     |
| `context-management.md` `prompt-caching-notes.md` `tools-fallback.md` `periodic-tasks.md` `worktree-usage.md` | ②    | 文档                                                             | 冻结                                  | P4 文档预算：超预算时先删这一组                       |
| `agent-output-schema.md`                                                                                      | ②    | 机制（`subagent-stop.sh` 解析 + `agents-manifest-check` 查标记） | 冻结                                  | 与 `subagent-stop.sh` 同去留                          |
| `memory-conventions.md` `mcp-onboarding.md` `m8-*.md`、ADR                                                    | ③    | 文档                                                             | 保留，按需查询                        | —                                                     |
| `harness-methodology.md`                                                                                      | ③    | 文档                                                             | P4 增"五种成分与演化终局"一节         | —                                                     |

---

## 13. 缺口：盘点时发现的问题（本次只登记、不改动）

| #   | 问题                                                                                                                                                                                                                                                                                                                                                       | 建议                                                                      |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| K1  | ✅ 已处理（G11 → E59，CI `migration-immutability`）。原问题：**T3-a 没有机制**：改已有 `V1__*.sql` 只有 hint + `migration-author`；IT 每次用全新库，改 V1 也不会失败                                                                                                                                                                                       | ④：CI 检查 PR 是否修改了 base 上已存在的 `V*__*.sql`，改了即 fail         |
| K2  | ✅ 已处理（G10 → E57，写进 `domain/CLAUDE.md`）。原问题：**T3-c 的项目决策没有载体**："Customer BC 落地前用 String"只写在 backlog C23 和 plan 里，模型默认读不到（`domain/CLAUDE.md` 没写）                                                                                                                                                                | ③：写进 `domain/CLAUDE.md`。要在首批 bench 之前定：先写再跑，基线才一致   |
| K3  | ✅ 已处理（G12 → E60）。原问题：**CLAUDE.md §9 与灰名单范围不一致**：§9 写"聚合根 / Repository 接口 / DomainEvent"，`ddd-aggregate-boundary` 实际拦 domain 全部 `.java`                                                                                                                                                                                    | §9 改成指向 `policies/*.yaml` 的指针（见 §5）                             |
| K4  | ✅ 已处理（G13 → E61，`mcp-observe.sh`）。原问题：**MCP 工具调用不进审计**：PreToolUse matcher 不含 `mcp__*`，gitnexus / mysql 用了多少无从统计，§5 的 gitnexus 退役条件没法观测。P0-6 遗留评估：mysql 已由 `ALLOW_*=false` 锁只读；gitnexus `rename` 在 `dry_run:false` 时直接改源码，绕过 Edit/Write 门禁 → G15：用户级配置开 `GITNEXUS_MCP_READ_ONLY=1` | 加只记日志、不拦截的 matcher（与 P0-6 遗留的"评估 MCP 写类工具"一并处理） |
| K5  | **② 类"硬上限 / fallback"只是文字**：E36、E44 在归档里记为完成，实际没有机制                                                                                                                                                                                                                                                                               | 归档已补"类型"列标 📄（本次）；文档内标"参考"随 P4 处理                   |
