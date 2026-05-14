# ADR 0006 — 共存期收尾：清空 `.claude/`，仓库根 = pure plugin

**Status**: Superseded by [ADR-0007](0007-revoke-plugin-pivot.md)（2026-05-14 plugin 化方向已撤销，本 ADR 失去前提）
**Date**: 2026-05-12
**Driver**: improvement-backlog G15
**Depends on**: [ADR-0005](0005-pivot-to-plugin.md)（已被 ADR-0007 撤销）

> ⚠️ **状态变更**：本 ADR 依赖 ADR-0005 的 plugin 化决定。ADR-0005 已被 [ADR-0007](0007-revoke-plugin-pivot.md) 撤销，"清空 `.claude/`、仓库根 = pure plugin"的前提不再成立。`.claude/` 恢复为本仓库唯一权威源，本 ADR 内容作为决策追溯保留。

## 背景

ADR-0005 把项目战略从"M8 实例化 Java DDD"转为"M8' Plugin 化"。M8' 推进期间，`.claude/`（原 standalone Harness 资产）与 `plugin/`（plugin 化产物）**并行共存**，作为风险对冲：plugin 验证未通过前，`.claude/` 是 myHarness 仓库自身的"权威源"。

本次会话推完了 G8 / G9 / G11 / G13（自动部分） + 一批 F1-F4 修复后，plugin 已基本可用（67 case smoke test 全过，外部空仓库 / Java / Python 项目模拟跑通）。**G15 决策点**到了。

## 现状量化

`diff -rq .claude plugin` 显示：

| 资产       | 总数  | 不同     | 说明                                                                                      |
| ---------- | ----- | -------- | ----------------------------------------------------------------------------------------- |
| agents     | 8     | 4        | plugin 版加了"适用：Java/JVM 项目"等限定 + `${CLAUDE_PLUGIN_ROOT}` 引用                   |
| commands   | 5     | 3        | plugin 版改了 `.claude/scripts/` → `${CLAUDE_PLUGIN_ROOT}/scripts/`、加 §0 运行模式判定   |
| hooks      | 6     | 6 (全部) | plugin 版用 `CLAUDE_PROJECT_DIR` 取代 cwd 假设、bypass env 加 namespace、F1 reason 动态化 |
| rules      | 1     | 1        | plugin 版加了"双重身份"注解                                                               |
| scripts    | 2     | 2        | plugin 版 PROJECT_ROOT 改用 `CLAUDE_PROJECT_DIR` env                                      |
| skills     | 0 / 1 | —        | plugin 独有 `harness-guidelines/SKILL.md`                                                 |
| hooks.json | 0 / 1 | —        | plugin 独有                                                                               |

**结论**：两套已**实质性分叉**，不再是简单的复制关系。plugin 用 plugin-runtime 语义（`${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_PROJECT_DIR}`）；`.claude/` 用 standalone 语义（相对 cwd、硬编码 `~/.claude/projects/D--myGithub-myHarness/...`）。"同步两边"不仅成本高，**语义上根本不等价**。

## 决定（拟）

**选项 B：清空 `.claude/`，让 myHarness 仓库根成为 pure plugin 仓库。仓库自身使用通过自举模式（`claude --plugin-dir ./plugin`）。**

## 替代方案分析

### A. 永久双轨保留

- 👍 myHarness 自己开发期不受影响（仓库根 `.claude/` 仍生效，无需自举）
- 👎 **维护成本**：每次改 hook / agent 都要思考"plugin 改了，要不要同步到 .claude/？"——但因为语义不等价，多数情况答案是"不能简单同步"
- 👎 漂移会越来越大，未来 plugin 加 skill / monitor / LSP 时 `.claude/` 永远滞后
- 👎 CI 双份（`lint.yml` 检查 `.claude/` + `plugin-validate.yml` 检查 `plugin/`）
- 👎 对外说明成本：README / CLAUDE.md 要解释"两套并存"
- ❌ 不推荐

### B. 清空 `.claude/`，自举模式（推荐）

- 👍 单一权威源 = 零漂移成本
- 👍 myHarness 仓库自身的 Claude Code 会话用 `claude --plugin-dir ./plugin` 启动，每次都验证 plugin 在"作者环境"下的可用性 = 持续的回归测试场
- 👍 CI 简化：`lint.yml` 减负（只校验 README / CLAUDE.md 等"项目外壳"），`plugin-validate.yml` 是真正的质量门
- 👍 单一目录结构对外更清晰：`plugin/` 是产物，仓库根是产物的开发工程
- 👎 myHarness 自身开发期要养成"启动加 `--plugin-dir ./plugin`"的习惯（或写个 launch 脚本/Makefile 简化）
- 👎 仓库根 CLAUDE.md 仍存在 → plugin 用户拿到的"标准 plugin-dir"不会自动注入这个 CLAUDE.md，但这本来就是 plugin 化目标（CLAUDE.md 项目模板已经通过 `/harness:onboard init` 命令产文本让用户手贴）
- ✅ 推荐

### C. 拆仓库（myHarness-plugin + myHarness-docs）

- 👍 plugin 仓库纯粹（无 docs / ADR / improvement-backlog 干扰）
- 👎 高成本：拆 issue / PR / git history / star / CI 配置
- 👎 单人项目过度工程化；plugin 还在 v0.1.0 没必要做大动作
- 👎 docs 仓库脱离 plugin 后，ADR 与代码的追溯链断裂
- ❌ 不推荐（除非未来 plugin 走向公开 marketplace + 多人协作）

## 后果（选项 B 实施后）

### 立即变化

1. **删除目录**（一次性）：
   - `.claude/agents/` `.claude/commands/` `.claude/hooks/` `.claude/rules/` `.claude/scripts/`
   - 保留：`.claude/settings.json`（仍是项目级配置）、`.claude/settings.local.json`（个人 / .gitignore）、`.claude/.audit.log`（运行时产物）、`.claude/.session.state`（运行时产物）
2. **`.claude/settings.json` 改写**：移除 hooks 注册段（hooks 由 plugin 提供），保留权限白名单等通用配置
3. **`.github/required-files.txt`**：移除 `.claude/{hooks,agents,commands,rules,scripts}/*` 条目
4. **`.github/workflows/lint.yml`**：移除"`.claude/agents` 必需文件"、"hook shebang + +x 检查"等 job（已由 `plugin-validate.yml` 覆盖）；保留 prettier + 顶层必需文件 + bypass-guard
5. **README / CLAUDE.md**：去掉"`.claude/` 是权威源"的描述；改为"开发期用 `claude --plugin-dir ./plugin` 自举"
6. **加 launch 脚本**（可选）：`scripts/dev.sh` 一行 `claude --plugin-dir ./plugin "$@"`，免每次手敲

### 持续变化

- 所有 hook / agent / command 改动**只改一处**（`plugin/`）
- myHarness 自身 Claude Code 会话**强制走 plugin**，等同于持续 dogfooding
- plugin 出现 bug 时作者第一时间感知（因为自己也是 plugin 用户）

### 风险

| #   | 风险                                                                        | 缓解                                                                         |
| --- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| R1  | 自己忘记加 `--plugin-dir ./plugin` 启动                                     | `.tool-versions` / `Makefile` / `scripts/dev.sh` 标准化；README 头部红字提醒 |
| R2  | plugin 出 bug 时自己也用不了（鸡生蛋）                                      | 临时回退 `git checkout HEAD~1 plugin/` 或用 `--bare` 模式                    |
| R3  | 已合并的 git history 中有 `.claude/hooks/` 等引用 → 旧 commit 文档失效      | 不动 history；CHANGELOG 标注 "M8'-T9 起 `.claude/` 资产清空，参见 ADR-0006"  |
| R4  | `improvement-backlog.md` / 老 ADR 引用 `.claude/...` 路径会变 dangling link | grep 一次性修订；不修订的纳入"历史快照"（ADR 通常不改）                      |

## 实施步骤（拍板后另起一批 commit）

```
1. (新分支) git checkout -b m8prime-cleanup-claude-dir
2. 删 .claude/{agents,commands,hooks,rules,scripts}（不删 settings*.json / 运行时产物）
3. 改 .claude/settings.json 去 hooks 段
4. 改 .github/required-files.txt 去 .claude/ 资产行
5. 改 .github/workflows/lint.yml 去 .claude/ 相关 job
6. 改 README.md / CLAUDE.md 去"权威源"描述 + 加"自举模式"段
7. 加 scripts/dev.sh（一行启动 plugin）
8. 改 docs/improvement-backlog.md：G15 标 ✅
9. 跑全套 plugin smoke test 确认无回归
10. PR + 自检 + merge
```

预估工作量：1.5 - 2 小时。

## 何时该重审本决定

- 如果未来 plugin 成熟到要发到公开 marketplace 且有 > 1 contributor → 重新考虑选项 C（拆仓库）
- 如果自举模式踩坑频繁 / R2 真实发生 → 回 A（双轨）

---

## 等待用户拍板

- ✅ 同意走选项 B → 创建实施 PR
- ❌ 改走 A / C → 写明理由，更新本 ADR Status
- ⏸️ 暂缓 → 维持现状（双轨），下次会话再评
