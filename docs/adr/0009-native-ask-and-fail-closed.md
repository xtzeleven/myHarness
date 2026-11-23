# ADR 0009 — 灰名单改用原生确认 + 黑名单 fail-closed + bypass 只认会话级环境变量

**Status**: Accepted
**Date**: 2026-11-21
**Stage**: M9-P0（止血：本机门禁真生效）
**Partially supersedes**: [ADR-0004](0004-deprecate-bypass-once.md) 中"`HARNESS_BYPASS=1 <command>` 单行作用域"的结论
**Relates to**: [improvement-plan.md](../improvement-plan.md) §1.2 F1–F6、§4 P0、§7 D1

## 背景

2026-11-20 在 macOS 本机实测发现，三层 Harness 中最硬的 PreToolUse 门禁实际不生效：

1. **F1 静默放行**：本机 `python` 无 PyYAML → `load_rules()` 返回空列表 → 所有规则放行。`rm -rf /` payload exit 0。CI 装了 pyyaml，所以一直绿。
2. **F3 灰名单 = 硬拦**：ask_user 命中时 `exit 2`。用户口头授权后 Claude 重试，仍被同一条规则拦下；"授权"只能靠 bypass 绕过，等于没有授权通道。
3. **F4 bypass 前缀无效**：ADR-0004 推荐的 `HARNESS_BYPASS=1 <command>` 只是命令字符串的一部分，hook 读的是 **hook 进程自身**环境变量，前缀根本到不了 hook。原测试把变量设给 hook 进程，掩盖了问题。
4. **F5 / F6**：`settings.json` 未用原生 `permissions`；PreToolUse matcher 不含 `NotebookEdit`。

## 决定

### 1. 黑名单 fail-closed（D1-A，保留 yaml）

- `deny.yaml` 读不出来（PyYAML 缺失 / 解析失败 / 文件缺失 / 顶层非列表）→ dispatcher **拦截所有**经过 PreToolUse 的调用（exit 2），stderr 给出原因与一行修复命令。
- 唯一放行项：整行精确匹配的 PyYAML 安装命令（`pip install pyyaml` / `python -m pip install --user --break-system-packages pyyaml` 等），让会话能自救；`pip install pyyaml && ...` 拼接不放行。
- `ask-user.yaml` / `hints.yaml` 读不出来：放行，但 stderr 提示。
- 找不到 `python` / `python3`：薄壳 `pre-tool-use.sh` 直接 exit 2。
- 前置检查：`verify-setup.sh` 缺 PyYAML 报 ❌；`session-start.sh` 在会话首屏最前面打印红字警告。

### 2. 灰名单改用 Claude Code 原生确认

命中 ask_user 规则时 hook 输出：

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "⚠️ 待人工授权: <reason>（规则 <id>）"
  }
}
```

并 exit 0，由客户端弹窗请用户确认。用户同意 = 放行这一次；拒绝 = 不执行。去掉"主 Claude 必须自觉停下问用户"的软依赖。audit log 照旧记 `action: ask_user`。

### 3. bypass 只认会话级环境变量

- 唯一用法：**启动 Claude Code 之前**设置，如 `HARNESS_BYPASS=1 claude`。hook 进程继承该环境，整个会话放开**全部**黑+灰名单（仍写审计、红字警告、7 天用量阈值告警）。
- `HARNESS_BYPASS=1 <command>` 命令前缀**不生效**，测试改为验证这一点（`bypass-prefix-not-effective-*`）。
- 单次授权的正规通道是第 2 条的原生确认弹窗，不再需要 bypass。

### 4. 原生 `permissions.deny` 作硬边界

`settings.json` 增加 `permissions.deny`：写 `.env` / 密钥证书 / SSH 密钥 / 凭据文件与目录、强推 main/master、`rm -rf /`、`rm -rf ~`。它不依赖 hook 与 PyYAML。定位：**原生规则 = 硬边界，hook 正则 = 防手滑 + 审计 + 项目特有规则**。

刻意不写的：`Bash(rm -rf /:*)` 这类前缀规则会误拦 `rm -rf /tmp/x`；`Edit(**/.env.*)` 会拦住 `.env.example`（deny 优先于 allow，无法豁免）。这些仍由 hook 精确匹配。

### 5. matcher 补 NotebookEdit

PreToolUse matcher 改为 `Bash|Edit|Write|MultiEdit|NotebookEdit`；dispatcher 读 `notebook_path` / `new_source`；deny.yaml 写文件类规则的 `tool` 列表加 `NotebookEdit`。MCP：当前唯一的 MySQL MCP 在服务端强制只读（`ALLOW_*=false` + 只读账号），暂不加 matcher；新增可写 MCP 时重审。

## 替代方案

| 候选                             | 否决原因                                                                 |
| -------------------------------- | ------------------------------------------------------------------------ |
| D1-B 规则改 JSON（标准库可读）   | 去掉依赖最彻底，但 validate / 测试 / 文档 / 规则写法全要改，改动面大     |
| D1-C 只加预检提示                | 仍是静默放行，违背"失败要响"                                             |
| 灰名单保留 exit 2                | 没有正规授权通道，用户授权后只能 bypass                                  |
| 恢复 `.bypass-once` 一次性令牌   | 原生 ask 已提供"一次性授权"，无需自研                                    |
| fail-closed 时内置一份最小黑名单 | 两份规则来源会漂移；原生 `permissions.deny` 已承担"不依赖 yaml 的硬边界" |

## 后果

- 👍 本机实测：无 PyYAML 时 `rm -rf /` 与 `ls` 都 exit 2（此前 exit 0）；装好后 48 个 hook 用例全绿。
- 👍 用户授权有了不可绕过的原生通道，CLAUDE.md §9 / engineering-practices §3、§15 同步改写。
- 👎 依赖缺失时整个会话的 Bash / 写操作都会被拦，直到装好 PyYAML —— 这是有意的；提示里给了修复命令，且安装命令本身被放行。
- ⚠️ **待手工验证**（无法在 CI 自动化）：原生 ask 在 `default` / `acceptEdits` / `plan` / `auto` / `bypassPermissions` 各 mode 下是否都弹窗；`permissions.deny` 在 hook 失效时是否仍拦。结果记入 engineering-practices §15。若某 mode 下 ask 被自动放行，退回该 mode 用 exit 2 作后备。（2026-11-23 更新：ask 部分已实测，6 个 mode 都生效，无需后备，见 §15 / backlog G1；`permissions.deny` 也已实测，hook 失效时 5 个 mode 下都拦，见 §3 / backlog G2）

## 相关

- [`.claude/scripts/policy-dispatch.py`](../../.claude/scripts/policy-dispatch.py)：`load_rules` 返回 `(rules, error)`、`PYYAML_INSTALL_RE`、`ask_decision`
- [`.claude/hooks/tests/test_pre_tool_use.sh`](../../.claude/hooks/tests/test_pre_tool_use.sh)：`## PyYAML 缺失（fail-closed）`、`## Bypass`、`## NotebookEdit`
- [`.claude/settings.json`](../../.claude/settings.json)：`permissions.deny`
- [`.claude/rules/engineering-practices.md` §15](../../.claude/rules/engineering-practices.md)
