---
description: 新人 5 分钟全局上手 — 自动生成项目摘要、当前阶段、第一周建议
argument-hint: "[role] 可选：backend | frontend | qa | pm（决定侧重点）"
---

# /onboard

帮新人在 5 分钟内回答四个问题：**这是什么？跑起来怎么做？现在做到哪？我下一步该做啥？**

## 执行步骤

### 1. 采集（并行跑）

```bash
# 项目身份
cat README.md | head -40
cat CLAUDE.md | sed -n '/## 5/,/## 6/p'   # 项目上下文节
cat AGENTS.md | head -40

# 技术栈与构建
cat pom.xml 2>/dev/null | head -40 || echo "no pom.xml"
ls src/main/java/ 2>/dev/null
ls src/main/resources/ 2>/dev/null

# 当前阶段
git log --oneline -10
git branch --show-current
git status --porcelain | head -20

# 仓库 / 索引就绪？
ls .mcp.json 2>/dev/null && echo "mcp 配置存在"
ls .env 2>/dev/null && echo ".env 存在（连接已配）" || echo ".env 缺失，需要复制 .env.example"

# 跑得起来吗？
mvn -v 2>&1 | head -3
java -version 2>&1
```

### 2. 综合判断

读上面输出，回答：

- **它是什么**：领域 / 架构（DDD 四层）/ 关键 BC
- **跑起来需要**：JDK 版本、Maven、是否需要本地 MySQL、`.env` 必填变量
- **现在到哪**：当前阶段（M0-M8 哪个）、最近一周做了什么、未合并的工作
- **下一步**（按 `$ARGUMENTS` 角色调整）：
  - `backend`：先看哪个 BC、先读哪几个聚合根、先跑哪个 module
  - `frontend`：API 文档位置、本地 mock 方式、对接的 BC
  - `qa`：测试策略、集成测试入口、当前覆盖率
  - `pm`：路线图位置、阻塞项、未关 issue

### 3. 输出格式

````
# 👋 欢迎入职 myHarness

## 这是什么
<1 句话> + <技术栈一行> + <架构一行>

## 现在做到哪
**当前阶段**：<M7 完成 / M8 待启动或实例化中>
**最近一周**：
- <commit 1 — 一句话意图>
- <commit 2 — ...>
**进行中**：<未合并分支 / 未关 PR>

## 跑起来怎么做
1. **环境**：JDK 17+、Maven 3.8+、MySQL 8（dev）
2. **配置**：复制 `.env.example` → `.env`，填 MySQL 只读账号
3. **构建**：
   ```bash
   mvn clean compile
   mvn test
````

4. **入口**：（按代码现状指出 main / Application 类位置）

## 你的第一周建议（角色：<role>）

1. 读 `CLAUDE.md` 全部 + `.claude/rules/engineering-practices.md` 第 12 节（DDD 分层）
2. 用 gitnexus-exploring 浏览 `domain/<bc>/` —— 从聚合根开始
3. <根据角色定制>
4. 跑通一个完整流程（在哪发请求 → 进哪个 Controller → 走哪个用例）
5. 提一个 trivial PR（修个 typo / 加测试）熟悉 /commit 流程

## 出问题先看

- 编译报错 → maven-build-doctor agent
- 启动报错 → 查 application.yml 与 .env
- DDD 边界疑惑 → ddd-architect agent
- SQL 慢 / schema 疑问 → schema-analyst agent

## 阅读路径（按优先级）

1. `README.md`、`CLAUDE.md`
2. `.claude/rules/engineering-practices.md`
3. `AGENTS.md`、`docs/AGENTS.backend.md`
4. `src/main/java/<base>/domain/`（领域核心）
5. `src/main/java/<base>/application/`（用例编排）

```

## 硬性规则

- **基于事实**：每段陈述都来自 step 1 的真实采集，不要瞎编。
- 检测到 .env 不存在 / pom.xml 缺失 / java 不可用 → 显式提示新人先解决环境。
- 路线图阶段从 README 表格读，不是猜。
- 不要超过一页（屏幕能滚到底）。
- 角色未指定 → 默认 `backend`。
```
