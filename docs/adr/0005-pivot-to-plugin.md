# ADR 0005 — 项目重定位：M8 Java DDD 实例化 → Plugin 化

**Status**: Accepted
**Date**: 2026-05-11
**Stage**: M7 完成后战略转向

## 背景

[ADR-0002](0002-java-ddd-backend.md) 选 Java + Spring Boot + Maven + DDD 作为 Harness 的"后端实战载体"，理由是 Java/DDD 栈最容易踩坑（Lombok / `@Transactional` / N+1 / 循环依赖），在最容易出错的栈上验证 Harness 有效性最具说服力。

M7（Tools + Policy 机制化）完成后，进入 M8（Java DDD 实例化）前重新评估：

1. 当前 Harness 框架（11 节 CLAUDE.md / 15 节 engineering-practices / 6 类 hook / 8 个 agent / 5 个命令 / 2 脚本 / MCP）已**自身完整**，价值不只在"验证 Java DDD 工程"
2. 框架的可复用性远高于单一后端实战项目：一旦封装为 Claude Code plugin，其他项目（任何语言栈）可直接安装使用
3. M8 实例化 Java DDD 骨架的边际价值（"再多一个工程样本"）小于 plugin 化的边际价值（"任何 Claude Code 用户都能用"）
4. 官方 [Claude Code plugin 机制](https://docs.anthropic.com/en/docs/claude-code/plugins)已稳定，本项目绝大多数资产可直接平移

## 决定

**废弃 M8 路线（实例化 Java DDD 骨架）**，重新定位项目目标为：**把 Harness 框架封装为 Claude Code plugin**。

新路线 **M8'（Plugin 化）**：

- **同仓库子目录**：在 myHarness 仓库下新建 `plugin/`，原 `.claude/` 在迁移期间共存
- **单一 plugin**：通用 Harness + Java/DDD 扩展打包在一起，非 Java 项目路径检查不匹配静默跳过
- **资产迁移**：agents / commands / scripts / MCP 直接平移；hook 重写路径 + `hooks/hooks.json`；CLAUDE.md 拆分到 skill + onboard 命令
- **验证方式**：通过 `claude --plugin-dir ./plugin` 本地验证；后续视情况发到私有或公开 marketplace

## 替代方案与权衡

### A. 维持 M8 路线（先实例化 Java DDD，plugin 化推迟）

- 👍 ADR-0002 完整兑现；六维度框架在真代码上回归测试
- 👎 实例化代码后再 plugin 化的转换成本更高（更多内嵌的 Java 依赖要拆）
- 👎 plugin 化的紧迫性来自"框架已经稳定 + 可复用窗口期"，等 M8 完成再做可能错过最佳时机
- ❌ 弃用

### B. 同时做 M8 + Plugin 化（双线推进）

- 👍 不抛弃任何路线
- 👎 双线分散注意力；Java 代码与 plugin 抽象互相牵扯，决策点变复杂
- 👎 单人项目同时维护两条线易半途而废
- ❌ 弃用

### C. 完全废弃 M8，专注 Plugin 化（当前方案）

- 👍 焦点单一，路线清晰
- 👍 复用性最大化：框架不绑死 Java
- 👍 已就位的 Java/DDD 资产仍保留在 plugin 中（不浪费 ADR-0002 投入）
- 👎 ADR-0002 的"在真实 Java 代码上验证"承诺未兑现 — 但 plugin 用户带自己项目的代码即可验证，间接达成
- 👎 后端 agent 的真实场景测试推迟到"plugin 用户首次跑通"
- ✅ 采纳

### D. 拆"core + java-ddd"两个 plugin

- 👍 语义干净，非 Java 用户只装 core
- 👎 配置成本翻倍；单人项目维护两个 release 节奏不现实
- 👎 当前 Java 路径检查在非 Java 项目中本就静默无伤，"干净"是伪需求
- ❌ 弃用（评估时考虑过，三个月内若反馈强烈再重审）

## 后果

- **ADR-0002 状态** 改为 `Superseded by ADR-0005`，但**内容保留**作为决策追溯
- **ADR-0001（三层 Harness）继续有效**：plugin 化不改变三层架构本质，只改变载体
- **ADR-0003（MCP + gitnexus）继续有效**：plugin 内含 `.mcp.json`
- **ADR-0004（废弃 .bypass-once）继续有效**：bypass 机制随 hook 一同迁入 plugin
- **roadmap §7** M8 段改写为 M8' Plugin 化；原 M8 内容保留为子节"历史"
- **improvement-backlog** 加 §G「Plugin 化任务清单」（G1–G15 细化），M4–M7 的所有 follow-up 仍有效
- **后端 agent**（`ddd-architect` / `spring-boot-reviewer` / `maven-build-doctor` / `schema-analyst` / `migration-author`）作为 plugin 的"Java/DDD 扩展套件"保留
- **engineering-practices.md §12–§14**（DDD 分层 / Java&Spring / MCP）作为 plugin rules 资源保留，用户跑 `/harness:audit-practices` 时被 Read
- **CLAUDE.md / README.md / AGENTS.md** 中"项目性质 = Java + DDD 后端实战"措辞将在 M8'-G14 同步修订为"plugin 仓库"视角

## 关键挑战（M8' 落地时要解决）

1. **CLAUDE.md 硬注入丢失**：plugin 没有项目级硬注入机制 → 拆为 skill（通用准则 §1–4）+ `/harness:onboard` 命令（项目模板 §5–10）
2. **hook 路径硬编码**：`pre-tool-use.sh` 等引用 `.claude/scripts/audit-log-summary.py` 等绝对路径 → 改 `${CLAUDE_PLUGIN_ROOT}/scripts/...`
3. **DDD/Java 上下文耦合**：pre-tool-use 灰名单含 `src/main/java/*/domain/*` 与 `pom.xml` 路径模式 → 对非 Java 项目自动静默（不匹配即跳过，无副作用）
4. **审计日志位置**：plugin 私有 vs 用户项目根，待 M8'-G7 决策
5. **MCP 凭据**：`.env` 仍在用户项目侧维护，plugin README 提供 `.env.example` 模板

## 何时重审

- 三个月内（2026-08）若 plugin 化进度 < 50% 或本地端到端验证持续失败 → 重审是否回到 M8 实战载体路线
- 若 plugin 安装用户 < 5 且无内部团队使用 → 重审是否价值兑现
- 若 Java/DDD 部分被发现严重耦合无法解耦 → 重审是否拆 "core + java-ddd" 两 plugin（方案 D 复活）

## 相关

- 被替代：[ADR-0002](0002-java-ddd-backend.md)（Java + DDD 后端实战载体）
- 仍有效：[ADR-0001](0001-three-layer-harness.md)（三层 Harness 架构）/ [ADR-0003](0003-mcp-and-gitnexus.md)（MCP + gitnexus）/ [ADR-0004](0004-deprecate-bypass-once.md)（废弃 .bypass-once）
- 路线变更：[../roadmap.md](../roadmap.md) §7 M8 → M8' Plugin 化
- 落地清单：[../improvement-backlog.md](../improvement-backlog.md) §G「Plugin 化任务清单」（G1–G15）
- 官方文档：[Claude Code Plugins](https://docs.anthropic.com/en/docs/claude-code/plugins) / [Plugin Marketplaces](https://docs.anthropic.com/en/docs/claude-code/plugin-marketplaces)
