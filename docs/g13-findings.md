# G13 — Plugin 外部项目端到端验证结果

**Date**: 2026-05-12
**Runner**: 主对话（非交互部分） + 待用户跑（交互部分）
**Plugin commit**: HEAD（含 S2/S3/S4/M1-M5/H1-H5 全部修复）

---

## 总览

| 节             | 类型              | 自动   | 手工   | 状态         |
| -------------- | ----------------- | ------ | ------ | ------------ |
| §1 空仓库基线  | hook 行为         | 5/5 ✅ | 1/1 待 | 自动部分全过 |
| §2 Java 项目   | PreToolUse 灰名单 | 3/3 ✅ | 1/1 待 | 自动部分全过 |
| §3 Python 项目 | 静默无副作用      | 5/5 ✅ | 4/5 待 | 自动部分全过 |
| §4 Bypass      | env 兼容          | 3/3 ✅ | 1/1 待 | 自动部分全过 |
| §5 审计日志    | 路径隔离          | 2/2 ✅ | —      | 全过         |

**自动验证**：18/18 ✅
**手工待跑**：7 项（详见末节）

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

## 待用户手工跑（需真 Claude CLI 加载 plugin）

下列项必须在外部项目跑 `claude --plugin-dir D:/myGithub/myHarness/plugin` 后交互验证。我（主对话）无法用 bash 直接模拟"主 Claude 解析 command markdown 并路由 agent"。

| #   | 节/步骤 | 验证内容                                                                      | 提示                                                                                                                        |
| --- | ------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| H1  | §1.6    | 在空仓库说 "实现一个简单的 add 函数" 看 `harness-guidelines` SKILL 是否被召唤 | SKILL 是 model-invoked；在 `/help` 看是否列出，或在 Claude 思考输出中看是否提及"思考优先 / 简单优先"                        |
| H2  | §2.1    | 在 Java 项目说"设计一个 Order 聚合" 看是否路由 `ddd-architect`                | 看 `/agents` 列表；输出顶部应出现 `ddd-architect:` 前缀或类似                                                               |
| H3  | §3.1    | 在 Python 项目跑 `/harness:onboard`                                           | 输出应识别 Python（不提 JDK/Maven）；按"模式 A 默认"格式                                                                    |
| H4  | §3.2    | 在 Python 项目说"review 这段 Python 代码"                                     | 路由 `code-reviewer`（通用），**不**路由 `spring-boot-reviewer`                                                             |
| H5  | §3.4    | 在 Python 项目说"这个项目的 BC 怎么分？"                                      | 关键测：`ddd-architect` description 标"适用：Java/JVM"；主 Claude 理想情况应拒绝路由或先确认。若仍误路由 → 加强 description |
| H6  | §3.5    | 在 Python 项目跑 `/harness:audit-practices`                                   | §12-§13（DDD/Java）维度应标 `N/A`，非"❌ 缺失"                                                                              |
| H7  | §4.3    | 创建带 `BYPASS:` 前缀的 commit + push                                         | CI `bypass-guard` job 应 fail                                                                                               |

**完成后**：每项打 ✅/❌/部分，失败的按 F<n> 格式补到本文末，由我后续修。

---

## 推荐外部跑法（最少代价）

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
