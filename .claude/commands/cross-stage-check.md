---
description: 产研全链路文档间漂移检查 — 扫 roadmap / ADR / CHANGELOG / MEMORY.md / AGENTS.md / m8-*.md / improvement-backlog 之间的不一致
argument-hint: "[focus] 可选：维度（existence / status / scope / reference / timeline）或文档（adr / roadmap / changelog / memory / agents / m8 / backlog）"
---

# /cross-stage-check

**跨阶段一致性检查**：扫产研全链路**文档之间**的漂移。元能力，不动文件，**只产清单**。

承担 [ADR-0008](../../docs/adr/0008-process-capability-expansion.md) 能力 H。

## 与 /sync-docs 的边界（互补，不重叠）

| 命令                 | 检测对象                                                                       | 调用                       | 范围        |
| -------------------- | ------------------------------------------------------------------------------ | -------------------------- | ----------- |
| `/sync-docs`         | **代码 ↔ 文档**                                                               | 调 docs-keeper agent       | git diff 内 |
| `/cross-stage-check` | **文档 ↔ 文档**（roadmap/ADR/CHANGELOG/MEMORY.md/AGENTS.md/m8-\*.md/backlog） | 主对话直接执行，不调 agent | 全仓        |

本命令**绝不扫代码**、**绝不调 agent**、**绝不直接改文件**。

## 5 个检测维度

### D1 — 产物存在性

ADR / roadmap 声明的资产是否真落地。

- 例：ADR-0008 §决定·3 声明 Tier 1 落地 3 资产 → 找 3 个文件
- 例：roadmap M-X 子任务列表 → 找对应产物
- 例：AGENTS.md 路由表登记的 agent / command → 找 `.claude/agents/<name>.md` / `.claude/commands/<name>.md`

### D2 — 状态一致性

同一里程碑 / 任务在不同文档的状态是否同口径。

- 例：roadmap §X 写 "M7 完成" ↔ CHANGELOG `[Unreleased]` 仍标 "M7 后置 / M8 启动前清账"
- 例：ADR Status（Proposed / Accepted / Superseded / Deprecated）↔ 实际是否仍被引用
- 例：improvement-backlog 条目状态（⏳ / ✅）↔ CHANGELOG 是否入账

### D3 — 范围漂移

ADR / roadmap 承诺的范围 ↔ 实际落地的范围。

- 例：ADR-0008 §决定·3 承诺 Tier 1 = 3 资产 → 实际落地几个？
- 例：roadmap M8-T0 列 6 个子任务 → 文件系统对应几个？
- 例：ADR §"后续会话落地"列表 ↔ CHANGELOG 是否全入账

### D4 — 引用链断裂

文档间互相引用的锚点 / 章节号 / ID / ADR 编号是否仍有效。

- 例：ADR 写 "详见 roadmap §7" → §7 是否仍存在 / 是否还在那一节
- 例：旧 ADR 引用旧编号（如 "见 ADR-0005"）→ ADR-0005 是否已被 ADR-0007 撤回
- 例：m8-event-storm.md 引用 m8-decomposition.md 的 P2.x → P2.x 是否还在那个位置
- 例：MEMORY.md 索引指向的 memory 文件 → 文件是否存在

### D5 — 时间线漂移

声明的"何时落地" ↔ 实际落地时点。

- 例：ADR Date 字段 ↔ 真实落地日期差距过大（如 ADR 写 2026-05-09，至今未落地）
- 例：ADR §"后续会话落地"列表 ↔ 实际入账时机（堆积多会话）
- 例：roadmap "M8 待启动" ↔ 实际已开始 M8-T0a/b/c/d

## 执行步骤

### 1. 采集

```bash
ls docs/adr/*.md docs/roadmap.md docs/m8-*.md docs/improvement-backlog.md
ls AGENTS.md CHANGELOG.md MEMORY.md 2>/dev/null    # MEMORY.md 注入在 system context
ls .claude/agents/ .claude/commands/
git log --oneline -20
```

**读关键锚点章节**（按需，不全文）：

- `docs/roadmap.md` §1.1 维度评分 + §7 M8 章节 + §10 修订记录
- 每个 ADR 头部 Status / Date / Relates to
- ADR-0008 §决定·3（Tier 1 资产清单）+ §决定·6（与 M8 主线关系）
- `AGENTS.md` 路由速查表 + 自定义 Agents 表
- `CHANGELOG.md` `[Unreleased]` + 最近 3 个日期段
- `docs/improvement-backlog.md` ⏳ / ✅ 标记的条目
- `MEMORY.md` 索引（system context 注入版）

### 2. 5 维度逐个扫

对每个维度，列出**命中**的漂移项；无命中 → 标 "✅ 无漂移"。

### 3. 输出格式

```
# 跨阶段一致性检查 — <YYYY-MM-DD>

## 总览
- 扫描对象：<N> 个文档
- 命中漂移：<N> 项
- 状态：🟢 全闭环 / 🟡 <N> 项需修 / 🔴 <N> 项阻塞下一步

## D1 产物存在性
- [P1.<n>] <文档:章节> 声明 "<资产>" → <✅ 存在 / ❌ 缺失>，证据：<file[:line]>

## D2 状态一致性
- [P2.<n>] <文档A:位置> "<状态甲>" ↔ <文档B:位置> "<状态乙>"，差异：<一句话>

## D3 范围漂移
- [P3.<n>] <ADR / roadmap 声明范围> ↔ <CHANGELOG / FS 实际>，差异：<一句话>

## D4 引用链断裂
- [P4.<n>] <文档:位置> 引用 "<目标>" → <✅ 有效 / ❌ 失效>，证据：<file[:line]>

## D5 时间线漂移
- [P5.<n>] <文档:位置> 声明 "<时机>" ↔ 实际 "<观察>"，差异：<天数 / 会话数>

## 待澄清（升级用户）
- <漂移项编号>: <需用户拍板的问题>

## 已闭环
- ✅ <无漂移的维度 / 文档对>

## 修复建议（按优先级，最多 5 条）
1. <最该修的> — 改 <文件> <简述>
2. ...
```

### 4. 末步：写入 audit log

```bash
python .claude/scripts/audit-log-append.py \
  --hook CrossStageCheck \
  --action scanned \
  --target "all-stages-$(date -u +%Y%m%d)" \
  --reason "/cross-stage-check run" \
  --extra hits='{"D1":<n>,"D2":<n>,"D3":<n>,"D4":<n>,"D5":<n>}' \
  --extra scope='<focus 参数或 "all">'
```

## 参数

- `$ARGUMENTS` 为空：全 5 维度 × 全文档矩阵扫
- 维度名（`existence` / `status` / `scope` / `reference` / `timeline`）：聚焦该维度
- 文档名（`adr` / `roadmap` / `changelog` / `memory` / `agents` / `m8` / `backlog`）：聚焦该文档与其他文档的漂移

## 硬性规则

- **不动文件**：只产报告；修复需用户明确"接受 #N" 后由主对话执行（与 /sync-docs 同协议）
- **不调 agent**：本命令是元能力，避免与 docs-keeper / 其他 agent 重叠
- **不扫代码**：代码 ↔ 文档漂移走 `/sync-docs`
- **以证据说话**：每条漂移必须给 `file[:line]` 或具体引用；无证据 → 标"待澄清"
- **不报谣**：找不到证据的怀疑列入"待澄清"，不作为命中
- **不报"内容未更新"当漂移**：CHANGELOG 还没写今天的、PR 待合并 等不算漂移
- **修复建议上限 5 条**：超过说明扫得太散，应聚焦 focus 参数重跑

## 反模式（识别到点名）

- ❌ 把"工作正常推进中未入账"当漂移（如 当天 commit 未写 CHANGELOG）
- ❌ 把"措辞细节差异"当漂移（如 "已完成" / "完成" / "ok"）
- ❌ 把 ADR `Status: Superseded` / `Deprecated` 当漂移 — 是正常生命周期
- ❌ 把 roadmap "估时 40min" ↔ 实际 "35min" 当漂移 — 估时差不算
- ❌ 扫得太散：5 维度 × 7+ 文档 = 35 个组合全报 → 应聚焦真正高价值的 5 条

## 与其他命令的协作

- **上游**：无（独立元能力）
- **下游**：
  - 漂移项要改代码 → 走 `/sync-docs` 而不是本命令
  - 漂移项要改文档 → 主对话改后 `/commit` 入账
  - 漂移项要新决策 → 用户新建 ADR
  - 漂移项需治理机制重构 → 触发 ADR-0008 §"何时重审"

## 何时跑

- 每次会话末，作为收尾自检（与 `/audit-practices` 互补：本命令查文档间一致性，audit-practices 查工程化机制）
- 大段文档批量改动（如新增 ADR / roadmap 修订）后
- 跨多会话堆积"下次会话落地"事项时
- 怀疑某个里程碑状态不清晰时（如 "M8 到底启动了没"）
