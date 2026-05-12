# G13 — Plugin 外部项目端到端验证 Runbook

> **目的**：在 myHarness 仓库**之外**、用真实 Claude Code CLI 加载 plugin，验证所有组件（SKILL / agents / commands / hooks / MCP）在非作者环境正常工作。本地 smoke test 通过 ≠ 装到别人项目能用。

**前置**：已安装 Claude Code 最新版（含 `--plugin-dir` 支持）。

---

## 一、空仓库基线验证

**目标**：plugin 加载本身不破坏空项目。

```bash
# 1. 创建空仓库
tmp=$(mktemp -d /tmp/harness-empty-XXXX)
cd "$tmp"
git init -q
echo "# scratch" > README.md
echo "node_modules/" > .gitignore
git add . && git -c user.name=test -c user.email=t@t -c commit.gpgsign=false commit -qm init

# 2. 加载 plugin
claude --plugin-dir D:/myGithub/myHarness/plugin
```

### 验证清单

| #   | 步骤                                    | 预期                                                                                                                                                                 |
| --- | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 启动即看 SessionStart 注入              | 显示 Git 当前态 + 工具就绪段；`memory 索引` 段**应不出现**（无匹配的 ~/.claude/projects 项目）；`.env 缺失`警告出现；`.gitignore 未排除 .claude/.audit.log` 警告出现 |
| 2   | 跑 `/harness:audit-practices`           | 命令被识别；产出 15 维度自检报告；`engineering-practices.md` 路径解析为 plugin 内绝对路径（不再 file-not-found）                                                     |
| 3   | 跑 `/harness:audit-context`             | `audit-context-cost.py` 真的被找到并执行（不报 No such file or directory）                                                                                           |
| 4   | 跑 `/harness:onboard`                   | 模式 A 默认；输出"项目入职摘要"，不假设是 Java 项目                                                                                                                  |
| 5   | 跑 `/harness:onboard init`              | 模式 B；输出"建议贴到 CLAUDE.md 的模板"文本；**不**直接 Edit 用户 CLAUDE.md                                                                                          |
| 6   | 触发 SKILL：说"实现一个简单的 add 函数" | `harness-guidelines` SKILL 被主 Claude 召唤（或在 SKILL 列表里能看到）                                                                                               |

---

## 二、Java 项目验证

**目标**：Java 专属 agent + 灰名单生效。

```bash
tmp=$(mktemp -d /tmp/harness-java-XXXX)
cd "$tmp"
git init -q

# 造 Java DDD 骨架
mkdir -p src/main/java/com/example/{domain,application,infrastructure,interfaces}
cat > pom.xml <<'EOF'
<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>demo</artifactId>
  <version>0.1.0</version>
</project>
EOF
echo "node_modules/" > .gitignore
git add . && git -c user.name=t -c user.email=t@t commit -qm init

claude --plugin-dir D:/myGithub/myHarness/plugin
```

### 验证清单

| #   | 步骤                                                                            | 预期                                                                           |
| --- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 1   | 问"设计一个 Order 聚合，要怎么分聚合根和 entity？"                              | 主 Claude 路由到 `ddd-architect` agent（description 含 "Java/JVM 项目"，命中） |
| 2   | 让 Claude 写文件 `src/main/java/com/example/domain/OrderAggregate.java`         | PreToolUse 灰名单触发 `⚠️ 待人工授权:DDD 边界改动`                             |
| 3   | 让 Claude 改 `pom.xml` 加 spring-boot 依赖                                      | PreToolUse 灰名单触发 `⚠️ 待人工授权:主要依赖升级`                             |
| 4   | 让 Claude 写文件 `src/main/java/com/example/application/PlaceOrderUseCase.java` | **不**触发灰名单（application 层非灰名单），但 hint 提示"事务边界仅在此层"     |

---

## 三、非 Java 项目验证（关键！）

**目标**：plugin 在 Python/JS/Go 等项目静默无副作用，不误路由 Java agent。

```bash
tmp=$(mktemp -d /tmp/harness-py-XXXX)
cd "$tmp"
git init -q
cat > pyproject.toml <<'EOF'
[project]
name = "demo"
version = "0.1.0"
EOF
mkdir -p src/demo tests
echo "def add(a, b): return a + b" > src/demo/__init__.py
echo "from demo import add" > tests/test_demo.py
echo "node_modules/" > .gitignore
git add . && git -c user.name=t -c user.email=t@t commit -qm init

claude --plugin-dir D:/myGithub/myHarness/plugin
```

### 验证清单

| #   | 步骤                                              | 预期                                                                                                                                                  |
| --- | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 跑 `/harness:onboard`                             | 摘要正确识别 Python（不会说"JDK / Maven"）                                                                                                            |
| 2   | 问"review 这段 Python 代码"                       | 主 Claude 路由到 `code-reviewer`（通用），**不**路由 `spring-boot-reviewer`（已声明"非 Spring 项目用 code-reviewer"）                                 |
| 3   | 让 Claude 写一个 Python 文件 `src/demo/orders.py` | PreToolUse 不触发任何 Java 灰名单（路径不匹配）                                                                                                       |
| 4   | 问"这个项目的 BC 怎么分？"                        | `ddd-architect` description 标注 "适用：Java/JVM 项目"；理想情况下主 Claude 应拒绝路由或先确认上下文。**若仍路由**记下来 — agent description 还需加强 |
| 5   | 跑 `/harness:audit-practices`                     | 输出报告应在 §12-§13（DDD / Java）维度标 `N/A`，非"❌ 缺失"                                                                                           |

---

## 四、bypass 行为验证

**目标**：`CLAUDE_PLUGIN_HARNESS_BYPASS=1` 新名字生效；旧名兼容；CI 拒合机制不可绕过。

```bash
# 4.1 新名字 bypass
CLAUDE_PLUGIN_HARNESS_BYPASS=1 echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' \
  | bash D:/myGithub/myHarness/plugin/hooks/pre-tool-use.sh
# 预期 stderr 含 "BYPASS ACTIVE"；exit 0

# 4.2 旧名字兼容
HARNESS_BYPASS=1 echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' \
  | bash D:/myGithub/myHarness/plugin/hooks/pre-tool-use.sh
# 预期同上（fallback 生效）

# 4.3 commit message marker → CI 应拒合（GitHub Actions 上验证）
git commit --allow-empty -m "BYPASS: emergency fix"
git push  # CI bypass-guard job 应 fail
```

---

## 五、审计日志位置验证

**目标**：audit log 写到用户项目根 `.claude/.audit.log`，不污染 plugin 目录。

```bash
tmp=$(mktemp -d)
cd "$tmp"
git init -q

# 触发 1 次灰名单（不命中黑名单字面量）
CLAUDE_PROJECT_DIR="$tmp" echo '{"tool_name":"Bash","tool_input":{"command":"mvn deploy"}}' \
  | bash D:/myGithub/myHarness/plugin/hooks/pre-tool-use.sh

# 验证
ls -la "$tmp/.claude/.audit.log"          # 应存在
ls -la D:/myGithub/myHarness/plugin/.claude/  # 应不存在（plugin 目录干净）
cat "$tmp/.claude/.audit.log"             # 应含 mvn deploy 那条 JSONL
```

---

## 六、问题报告格式

发现失败项时，按下面格式记录到 `docs/g13-findings.md`（可后续补）：

```markdown
### F<n> — <简短标题>

- **场景**：第 X 节 / 步骤 Y
- **预期**：<预期行为>
- **实际**：<实际表现>
- **复现**：<最小复现步骤>
- **影响等级**：🔴 阻塞 / 🟡 退化 / 🟢 体验问题
- **修复点**：<猜测的代码位置>
```

---

## 七、通过标准

- 第一节：6/6 ✅（plugin 加载基线）
- 第二节：3/4 ✅（PreToolUse 灰名单 3 项必中）
- 第三节：4/5 ✅（非 Java 项目无副作用）— 第 4 项 `ddd-architect` 路由行为是改进点，不阻塞
- 第四节：3/3 ✅（bypass 行为）
- 第五节：1/1 ✅（审计日志位置）

**最低线**：第二、三、五节必须全过。第一节中"SKILL 主动召唤"（步骤 6）属于 best-effort，若不触发可以观察一段时间再调 description。
