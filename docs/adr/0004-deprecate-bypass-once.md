# ADR 0004 — 废弃 `.bypass-once` 单次授权机制

**Status**: Accepted
**Date**: 2026-05-11
**Stage**: M7 后置整理（M8 启动前清账）

## 背景

`.claude/.audit.log` 第 3–5 行残留 3 条历史记录：

```
{"ts":"2026-05-09T11:14:51+00:00", "action":"bypass", "reason":"one-shot via .bypass-once: M8 pom.xml 写入（用户已授权 #1）", ...}
{"ts":"2026-05-09T11:18:46+00:00", "action":"bypass", "reason":"one-shot via .bypass-once: M8 OrderRepository.java（用户已授权 #3）", ...}
{"ts":"2026-05-09T11:18:52+00:00", "action":"bypass", "reason":"one-shot via .bypass-once: M8 OrderPlacedEvent.java（用户已授权 #4）", ...}
```

5/9 当天 M8 第一次尝试启动时（参见 [docs/roadmap.md §7](../roadmap.md)），曾设计/实验过一个 **`.bypass-once` 文件机制**：在仓库根放一个 `.bypass-once` 文件，文件内含"用户已授权的一次性事由"，`pre-tool-use.sh` 检测到该文件存在时放行当前 Edit/Write 并消费（删除文件），相比 `HARNESS_BYPASS=1` 全局 env 变量更细粒度。

**问题**：

1. M8 折返后该机制未保留进当前代码：`pre-tool-use.sh` 现行版本（2026-05-11）只有 `HARNESS_BYPASS=1` 检测，没有 `.bypass-once` 处理逻辑。
2. 任何文档（`engineering-practices.md §15` / `loop-architecture.md` / `tools-fallback.md` / `CHANGELOG.md` / `AGENTS.md`）都未提及该机制。
3. audit.log 残留让"机制是否存在"读起来矛盾。

## 决定

**废弃 `.bypass-once`**，统一只用 `HARNESS_BYPASS=1` env 变量 + commit message `BYPASS:` marker + CI `bypass-guard` job 三道。

- `.bypass-once` 历史 audit 记录**不清理**（作为踩坑/追溯证据保留）
- `pre-tool-use.sh` 不需要改（本来就没该逻辑）
- 后续任何"想要细粒度一次性授权"的需求 → 用 `HARNESS_BYPASS=1 <command>` 单行作用域 + 在 audit log 的 `reason` 字段写明事由（功能等价）

## 替代方案与权衡

### A. 重新实现 `.bypass-once`（消费即过期 token）

- 👍 比 env 变量安全：忘 unset 不会持续 bypass，文件被消费就失效
- 👍 能携带 `reason` 与 `编号` 进 audit log（自带审计语义）
- 👎 hook 复杂度增加：新增"读 → 验证 → 消费 → 写审计"四步，且文件存在与否的竞态需要考虑
- 👎 与 `HARNESS_BYPASS=1` 并存 = 两套 bypass 机制，使用者要记住何时用哪个
- 👎 5/9 实验过但折返时未保留 → 实际工程价值未验证
- ❌ 弃用

### B. 废弃 `.bypass-once`，纯用 `HARNESS_BYPASS=1`（当前方案）

- 👍 机制少一个 → 维护点少一个
- 👍 `HARNESS_BYPASS=1 <command>` 作为 shell 前缀的作用域天然就是"单次"
- 👍 audit log 的 `reason` 字段可承载任意事由文本，等价于 `.bypass-once` 中的事由
- 👎 失去"事前承诺的一次性 token"语义
- 👎 用户若 `export HARNESS_BYPASS=1` 而非前缀使用，会持续 bypass — 但这是 shell 使用者责任，hook 已 stderr 红色警告
- ✅ 采纳

### C. 把 `.bypass-once` 改名为更明确的 `.harness-onetime-bypass`，重新实现

- 同 A，命名差异不解决核心 trade-off
- ❌ 弃用

## 后果

- engineering-practices.md §15 Bypass policy 章末加一段废弃声明，引本 ADR
- 5/9 audit.log 残留保留，作为本 ADR 的证据；不在 CI 验证里 grep `.bypass-once`
- 未来若 M8 实例化时仍想要细粒度一次性授权 → 走"用户对话授权 + 主 Claude 输出 `HARNESS_BYPASS=1 <command>` 给用户复制粘贴"的协作模式，hook 不动
- 若三个月内（2026-08）有 ≥ 2 次"事前确认的 bypass"场景再次出现 → 重审本 ADR，可能重新实现

## 相关

- 残留证据：[`.claude/.audit.log`](../../.claude/.audit.log) 第 3-5 行（已 .gitignore，仅本地）
- 现行 bypass：[`.claude/hooks/pre-tool-use.sh`](../../.claude/hooks/pre-tool-use.sh) L76-82
- Bypass policy：[`.claude/rules/engineering-practices.md` §15 "Bypass policy"](../../.claude/rules/engineering-practices.md)
- CI 拒合：[`.github/workflows/lint.yml`](../../.github/workflows/lint.yml) `bypass-guard` job
