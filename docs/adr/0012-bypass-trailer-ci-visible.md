# ADR 0012 — bypass 留痕：提交尾注 + CI 要求补理由

**Status**: Accepted
**Date**: 2026-11-22
**Stage**: M9-P2（backlog G6）
**Relates to**: [ADR-0009](0009-native-ask-and-fail-closed.md), [improvement-plan.md](../improvement-plan.md) §1.2 F7

## 背景

F7：`HARNESS_BYPASS=1` 会话里的放行只记在本地 `.claude/.audit.log`（gitignored）。CI `bypass-guard` 只认人工写进提交信息的 `BYPASS:` 标记——没人写就看不到，bypass 期间产生的改动可以无痕合入。按 ADR-0010，⑤ 权责类应机制化，且 CI 能看到。

## 决策

1. **`.githooks/prepare-commit-msg`** 调用 `.claude/scripts/bypass-trailer.py`：读 audit log（worktree-aware，同 policy-dispatch），把**上一个提交之后**的 `bypass=true` 记录（amend 时以 `HEAD^` 为界）和"当前进程带 bypass 环境变量"写成尾注：
   `Harness-Bypass: <n> tool calls <first>..<last> (Bash=3, Edit=1)`
   选 prepare-commit-msg 是因为 `git commit --no-verify` 跳不过它。脚本出错不阻断提交，但在 stderr 告警。
2. **启用**：`git config core.hooksPath .githooks`。`/verify-setup` 未启用时报 ⚠️；SessionStart 未启用时首屏提醒。不自动改用户的 git 配置。
3. **CI**（2026-11-22 用户拍板"补理由后可合"）：`bypass-guard` 跑 `bypass-trailer.py --check <range>`。带 `Harness-Bypass` 尾注的提交，同一提交须有非空 `Bypass-Reviewed: <理由>` 尾注，否则 fail；带理由的放行，但打 warning 并列进 job summary。
   补理由：`git commit --amend --trailer "Bypass-Reviewed: <为什么必须 bypass、事后核对了什么>"`
4. 人工 `BYPASS:` 标记仍一律拒合（不变）。

## 备选

| 方案                               | 否决原因                                                        |
| ---------------------------------- | --------------------------------------------------------------- |
| 带尾注一律拒合（同 `BYPASS:`）     | 最省事的过关办法是删掉尾注，等于逼人销毁记录                    |
| 只告警不拦                         | warning 容易被忽略，没有"事后核对"这一步                        |
| bypass 时写入一个入库的台账文件    | 要靠人记得 `git add`；漏提交 CI 照样看不到                      |
| commit-msg hook                    | `--no-verify` 会跳过                                            |
| SessionStart 自动设 core.hooksPath | 静默改用户 git 配置；与"原生优先、不替用户做配置决定"的原则冲突 |

## 后果

- bypass 期间的改动在 PR 上可见，且需要一句理由才能合入；记录永久留在 git 历史。
- **定位是防手滑 + 留痕，不防蓄意绕过**：`git -c core.hooksPath= commit`、改写提交信息、未启用 hooksPath 的克隆都能不带尾注。蓄意绕过属于组织信任问题，不在本项目范围。
- 编辑器提交时脚本会预先排好"标题 / 空行 / 尾注"模板（否则尾注与标题同段，git 不认）；在 bypass 期间放弃提交需清空全部内容。
- 以上一个提交的 committer 时间为界：rebase 会刷新 committer 时间，之后的 bypass 计数可能偏少；可接受。

## 相关

- [`.claude/scripts/bypass-trailer.py`](../../.claude/scripts/bypass-trailer.py)、[`.githooks/prepare-commit-msg`](../../.githooks/prepare-commit-msg)
- [`.claude/scripts/tests/test_bypass_trailer.py`](../../.claude/scripts/tests/test_bypass_trailer.py)（临时仓库端到端：尾注 / 界线 / amend / `--no-verify` / 编辑器模板 / `--check`）
- [`.github/workflows/lint.yml`](../../.github/workflows/lint.yml) `bypass-guard`
- [engineering-practices §15 Bypass policy](../../.claude/rules/engineering-practices.md#bypass-policym7-t5-引入)
