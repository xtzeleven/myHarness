# G13 — Plugin 外部项目端到端验证结果

**Date**: 2026-05-12 / 更新 2026-05-13（H1-H7 手工验证完成）
**Runner**: 主对话（非交互部分） + 用户（交互部分 H1-H7）
**Plugin commit**: HEAD（含 S2/S3/S4/M1-M5/H1-H5 全部修复 + F1 + **F8**）

---

## 总览

| 节             | 类型              | 自动   | 手工   | 状态        |
| -------------- | ----------------- | ------ | ------ | ----------- |
| §1 空仓库基线  | hook 行为         | 5/5 ✅ | 1/1 ✅ | 全过        |
| §2 Java 项目   | PreToolUse 灰名单 | 3/3 ✅ | 1/1 ✅ | 全过（F8） |
| §3 Python 项目 | 静默无副作用      | 5/5 ✅ | 4/4 ✅ | 全过        |
| §4 Bypass      | env 兼容          | 3/3 ✅ | 1/1 ✅ | 全过        |
| §5 审计日志    | 路径隔离          | 2/2 ✅ | —      | 全过        |

**自动验证**：18/18 ✅
**手工 H1-H7**：7/7 ✅（H2 暴露 F8，已修复并加 5 case 回归测试）

---

## §1 空仓库基线（自动）

```
$ CLAUDE_PROJECT_DIR=/tmp/g13-empty CLAUDE_PLUGIN_ROOT=<plugin> bash session-start.sh
```

- ✅ Git 段正确显示当前态（branch=master / head=init）
- ✅ 工具就绪段显示 git/python/npx/mvn/java 全 ✅
- ✅ memory 索引段**正确静默**（无匹配 `~/.claude/projects/*empty*` → 不输出该段）
- ✅ `.env 缺失`警告触发
- ✅ `.gitignore 未排除 .claude/.audit.log`警告触发

---

## §2 Java 项目（自动）

骨架：`pom.xml` + `src/main/java/com/example/{domain,application}/`

- ✅ §2.2 写 `domain/OrderAggregate.java` → 灰名单 `待人工授权: DDD 边界`（exit=2）
- ✅ §2.3 改 `pom.xml` 含 `<artifactId>spring-boot-starter</artifactId>` → `待人工授权: 主要依赖升级`（exit=2）
- ✅ §2.4 写 `application/PlaceOrderUseCase.java` → **不**触发灰名单（exit=0）；正确给出 application 层提示

---

## §3 Python 项目（自动核心）

骨架：`pyproject.toml` + `src/demo/` + `tests/`

- ✅ §3.3 写 `src/demo/orders.py` → 不触发任何 Java 灰名单
- ✅ §3.3 改 Python 文件 → 不触发 ddd-architect/DDD 分层 hint
- ✅ §3 SessionStart 在 Python 项目：不出现 "Java"、"DDD" 字样；通用工具段照常显示

**结论**：plugin 装到非 Java 项目，hook 层完全静默，**无副作用**。

---

## §4 Bypass 行为（自动）

- ✅ §4.1 `CLAUDE_PLUGIN_HARNESS_BYPASS=1`（新 namespace）→ `BYPASS ACTIVE` / exit=0
- ✅ §4.2 `HARNESS_BYPASS=1`（旧名 fallback）→ `BYPASS ACTIVE` / exit=0
- ✅ §4 audit log 写到 `$CLAUDE_PROJECT_DIR/.claude/.audit.log`，两条记录 `"bypass": true`

---

## §5 审计日志位置（自动）

- ✅ 灰名单触发 → audit log 写到 `$CLAUDE_PROJECT_DIR/.claude/.audit.log`
- ✅ plugin 目录**无** `.claude/` 子目录被创建（plugin 不污染）

---

## 发现项（Findings）

### F1 — bypass audit log reason 固定字符串（已修复 ✅）

- **场景**：§4.2，用旧名 `HARNESS_BYPASS=1` 触发 bypass
- **预期**：audit log 的 `reason` 字段反映实际触发的 env 名字
- **实际**（修复前）：固定写 `"reason": "CLAUDE_PLUGIN_HARNESS_BYPASS=1 in env"`（即使是旧名触发）
- **影响等级**：🟢 体验问题（不影响 bypass 功能；只在审计追溯时模糊）
- **修复**：`plugin/hooks/pre-tool-use.sh:80-86` 改为先检测 `CLAUDE_PLUGIN_HARNESS_BYPASS` 再 fallback 到 `HARNESS_BYPASS`，把实际触发的 env 名字写进 reason
- **回归测试**：`plugin/hooks/tests/test_pre_tool_use.sh` 新增 2 case (`audit-reason-new-name` / `audit-reason-old-name`) 验证 audit log 内容
- **验证**：69 case smoke 全过

---

### F8 — Windows 反斜杠路径让 PreToolUse 灰名单全失效（已修复 ✅）

- **场景**：H2 在 Windows 上让 Claude 写 `src\main\java\com\example\domain\OrderAggregate.java`
- **预期**：PreToolUse 灰名单触发 `⚠️ 待人工授权: DDD 边界改动`
- **实际**（修复前）：Write 直接放行 102 行写入，**没有任何拦截**
- **根因**：Windows Claude Code 透传给 hook 的 `file_path` 用反斜杠，但 `pre-tool-use.sh` 的 `case` glob 用正斜杠 → 所有路径模式（DDD 灰名单 / secrets / .aws / .ssh / 所有 M6 hint）在 Windows 一律失配
- **验证根因**：
  - 反斜杠 payload 喂 hook → exit=0（误放行）
  - 正斜杠 payload 喂 hook → exit=2 + "DDD 边界改动" 提示
- **影响等级**：🔴 **黑+灰防御层在 Windows 上部分失效**（致命漏洞，跨平台 plugin 必修）
- **修复**：`plugin/hooks/pre-tool-use.sh:34-35` 提取 `file_path` 后立即 `${file_path//\\//}` 规范化反斜杠 → 正斜杠
- **回归测试**：`plugin/hooks/tests/test_pre_tool_use.sh` 新增 5 case (`ask-domain-aggregate-backslash` / `ask-domain-repository-backslash` / `ask-domain-aggregate-mixed-drive` / `deny-secrets-path-backslash` / `allow-application-handler-backslash`) → 74/74 全过（旧 69 + 新 5）
- **commit**: `ce6ff49 fix(hooks): F8 — Windows 反斜杠路径让 PreToolUse 灰名单全失效`

---

## 已知环境限制（非 plugin 缺陷）

### E1 — API 代理（new-api / one-api 网关）panic on sub-agent invocations

- **场景**：H2 ddd-architect 调用 / H4 code-reviewer 强触发
- **症状**：`harness:<agent>(...)` 委派块出现 ✅（plugin 路由正确），但 `Done (0 tool uses · 0 tokens · 3m)` + Claude 内置错误信息 "上游 new-api panic / nil pointer"
- **结论**：用户使用 OpenAI-compatible 代理网关（如 new-api / one-api）转发 Anthropic 调用；该网关在处理 plugin sub-agent 委派调用时上游 panic，**不是 plugin 缺陷**
- **plugin 职责边界**：在"正确路由 + 委派"这步 PASS；sub-agent 实际执行依赖底层 API 链路
- **缓解**：用户直连 Anthropic API 或换稳定代理时该问题消失

---

## H1-H7 手工验证结果（2026-05-13）

外部项目交互验证：`D:\tmp\g13\{empty,java,py}` + myHarness 仓库本身（H7）。

| #   | 节/步骤 | 验证内容 | 结果 | 证据 |
| --- | ------- | -------- | ---- | ---- |
| H1  | §1.6    | 空仓库说"实现工程化方案" → `harness-guidelines` SKILL 召唤 | ✅ | 显式 `Skill(harness:harness-guidelines)` + "Successfully loaded skill" + 引用 SKILL.md §1 "先 surface 状态" + 主动 AskUserQuestion 验证假设 |
| H2  | §2.1    | Java 项目说"设计 Order 聚合" → 路由 `ddd-architect` + 写文件触发 DDD 灰名单 | ✅ | `harness:ddd-architect(Design Order aggregate with DDD)` 委派块出现；但首次写 `OrderAggregate.java` 因 **F8** 未拦截 → hook 层已修，回归 5 case 全过 |
| H3  | §3.1    | Python 项目跑 `/harness:onboard` | ✅ | 识别为 Python 项目；建议 pip/ruff/pytest/uv；末尾主动声明 "maven-build-doctor / spring-boot-reviewer / ddd-architect 不适用"（超预期）|
| H4  | §3.2    | Python 项目说"review 代码" → 路由 `code-reviewer`，**不**路由 `spring-boot-reviewer` | ✅ | 显式触发后出现 `harness:code-reviewer(...)` 委派块 2 次；sub-agent 执行被 **E1**（API 代理 500）挡住，路由层 PASS |
| H5  | §3.4    | Python 项目说"BC 怎么分？" → DDD agent 应拒绝路由 | ✅ | 第一句即"这个问题在当前项目上不成立"；显式引 agent description "适用：Java/JVM 项目"；无委派块；引 Eric Evans 反驳"为分层而分层"（教科书级别）|
| H6  | §3.5    | Python 项目跑 `/harness:audit-practices` → §12/§13 标 N/A | ✅ | §12 DDD 标 N/A + "非 JVM 项目"；§13 Java/Spring 标 N/A + "纯 Python"；bonus §14 MCP 标 "N/A（暂）"；备注"维度 12、13 永久 N/A" |
| H7  | §4.3    | 带 `BYPASS:` 前缀 commit + PR → CI `bypass-guard` fail | ✅ | "Found commit with BYPASS marker in ce6ff49..9812446" + "9812446 BYPASS: testing CI guard (H7 verification)" + exit code 1 |

**操作细节**：
- H1-H6 用 `claude --plugin-dir D:\myGithub\myHarness\plugin` 在 3 个 demo 仓库交互
- H7 走 PR（`h7-test-bypass-guard` → `plugin-branch`），lint.yml 触发 bypass-guard job
- workflow trigger 仅在 `[main, plugin-branch]` 上 fire；feature branch push 不触发 CI，必须经 PR

**清理**：H7 测试 PR + 分支已删除（本地 + 远程）。

---

## 推荐外部跑法（保留作历史参考）

```bash
# 一次性建三个 demo 仓库
for kind in empty java py; do
  rm -rf /tmp/g13-$kind
  mkdir -p /tmp/g13-$kind
  cd /tmp/g13-$kind
  git init -q && echo "# $kind" > README.md && git add . \
    && git -c user.name=t -c user.email=t@t commit -qm init
done

# 各跑一次 claude --plugin-dir
cd /tmp/g13-empty && claude --plugin-dir D:/myGithub/myHarness/plugin
# 试：/harness:audit-practices / "实现 add 函数"
# /exit

cd /tmp/g13-java
mkdir -p src/main/java/com/example/domain
echo '<project></project>' > pom.xml
git add . && git -c user.name=t -c user.email=t@t commit -qm java-stub
claude --plugin-dir D:/myGithub/myHarness/plugin
# 试："设计一个 Order 聚合" / 让它写 OrderAggregate.java（看是否要求授权）

cd /tmp/g13-py
echo '[project]' > pyproject.toml
echo 'name="d"' >> pyproject.toml
mkdir -p src/d && echo 'def add(a,b):return a+b' > src/d/__init__.py
git add . && git -c user.name=t -c user.email=t@t commit -qm py-stub
claude --plugin-dir D:/myGithub/myHarness/plugin
# 试：/harness:onboard / "review 这段代码" / "BC 怎么分？"
```

每个 demo ~5 分钟，全套 ~15 分钟。
