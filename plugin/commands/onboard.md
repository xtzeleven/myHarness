---
description: 项目快速入职助手 — 5 分钟摘要 + 可选产出 CLAUDE.md 模板让用户贴
argument-hint: "[summary | init | role(backend/frontend/qa/pm)]"
---

# /harness:onboard

两种模式：

- **默认 / `summary`**：给当前项目做 5 分钟摘要（不假设语言栈）
- **`init`**：产出一段"建议贴到本项目 CLAUDE.md 的内容"模板。**不**直接 Edit 用户的 CLAUDE.md —— 输出文本由用户审阅后**手动**复制。

按 `$ARGUMENTS` 选择分支。空 `$ARGUMENTS` = `summary`。

---

## 模式 A：项目摘要（默认）

帮新人在 5 分钟内回答四个问题：**这是什么？跑起来怎么做？现在做到哪？我下一步该做啥？**

### 1. 采集（并行跑，缺失文件兜底 `2>/dev/null`）

```bash
# 项目身份
ls README.md CLAUDE.md AGENTS.md 2>/dev/null
head -40 README.md 2>/dev/null

# 技术栈线索（不假设是哪一种）
ls package.json pom.xml build.gradle Cargo.toml pyproject.toml go.mod requirements.txt 2>/dev/null
ls src/ app/ lib/ cmd/ 2>/dev/null | head -10

# 当前阶段
git log --oneline -10 2>/dev/null
git branch --show-current 2>/dev/null
git status --porcelain 2>/dev/null | head -20

# plugin / MCP 就绪？
ls .mcp.json 2>/dev/null
ls .env 2>/dev/null || echo ".env 缺失（如需 MCP 须先配）"
```

### 2. 综合判断

读上面输出，**只**回答能从证据支撑的：

- **它是什么**：从 README + 构建文件推断领域 / 主要语言 / 框架
- **跑起来需要**：从存在的构建文件给标准命令（npm / mvn / cargo / pip / go），**不要猜版本**
- **现在到哪**：最近一周 commit 摘要、未合并分支
- **下一步**：按 `$ARGUMENTS` 角色（`backend` / `frontend` / `qa` / `pm`，默认 `backend`）给建议

### 3. 输出格式

````
# 👋 项目入职摘要 — <project basename>

## 这是什么
<1 句话> + <技术栈一行> + <架构一行（如能推断）>

## 现在做到哪
**最近一周**：
- <commit 1 — 一句话意图>
- <commit 2 — ...>
**进行中**：<未合并分支 / 未提交变更>

## 跑起来怎么做
1. **环境**：<根据构建文件推断>
2. **配置**：复制 `.env.example` → `.env`（如存在）
3. **构建**：
   ```bash
   <根据构建文件给命令>
````

## 第一周建议（角色：<role>）

1. 读 `README.md` 全部 + `CLAUDE.md`（如存在）
2. 探索 src/ 主入口（main / index / app）
3. ... 按角色定制

## 出问题先看（按 plugin 提供的 agent）

- Maven 构建报错 → maven-build-doctor（仅 Maven 项目）
- Spring 反模式 → spring-boot-reviewer（仅 Spring 项目）
- 通用 code review → code-reviewer
- 文档漂移 → docs-keeper
  ```

  ```

### 模式 A 硬性规则

- **基于事实**：每段陈述都来自 step 1 的真实采集，不要瞎编
- **不要假设语言栈**：没看到 pom.xml 就不要说 Maven；没看到 src/main/java 就不要谈 DDD
- 不要超过一页

---

## 模式 B：产 CLAUDE.md 模板（`init`）

> ⚠️ **本 plugin 不直接写用户的 CLAUDE.md**。下面是建议**手动复制贴到项目根 `CLAUDE.md`** 的模板。请基于项目实际情况修改 `<...>` 占位符。

### 1. 采集项目事实

```bash
ls README.md CLAUDE.md 2>/dev/null
[ -f CLAUDE.md ] && echo "⚠️ CLAUDE.md 已存在，请审阅后选择性合并下方模板，勿覆盖" || echo "无 CLAUDE.md，可直接贴"
git remote -v 2>/dev/null
git log --oneline -3 2>/dev/null
ls package.json pom.xml build.gradle Cargo.toml pyproject.toml go.mod 2>/dev/null
```

### 2. 产出模板（喂给用户复制）

````markdown
# CLAUDE.md

> 本项目使用 [harness plugin](https://github.com/<user>/myHarness)。通用行为准则由 plugin 的 `harness-guidelines` SKILL 提供，本文件只写项目专属上下文。

## 项目上下文

**项目性质**：<一句话，例如"<X> 系统的后端服务"或"<Y> 工具的 CLI">
**当前阶段**：<例如"v1.0 待发布" / "重构中" / "初始原型">

## 技术栈

- 语言：<从构建文件读>
- 主要框架：<如 Spring Boot / Next.js / Django / ...>
- 构建：<mvn / npm / cargo / go / ...>
- 数据：<MySQL / Postgres / 无 / ...>

## 目录结构

```
.
├── README.md
├── CLAUDE.md
├── <主源码目录>
├── <测试目录>
└── ...
```
````

## 禁忌事项

- 不要提交 `.env*` / 密钥文件（plugin 已通过 PreToolUse 拦截，但仍要警惕）
- <项目自己的硬规则，例如"不修改 schema 不写迁移脚本">
- <例如"不引入未在 README 声明的依赖">

## 测试 / 校验命令

```bash
<构建命令>     # 例如 mvn clean compile / npm run build
<测试命令>     # 例如 mvn test / npm test / pytest
<lint 命令>    # 例如 npx prettier --check . / ruff check .
```

## plugin 提供能力

- `/harness:audit-practices` — 15 维度工程化自检
- `/harness:commit` — 标准化提交流程
- `/harness:sync-docs` — 文档同步检查
- `harness-guidelines` SKILL — 通用行为准则（思考优先 / 简单优先 / 外科手术 / 目标驱动）
- `code-reviewer` / `docs-keeper` 等通用 agent；Java/Spring 项目额外有 ddd-architect / spring-boot-reviewer / maven-build-doctor

## 项目专属约定

<例如"所有 API 必须有 OpenAPI 注解" / "DB 迁移走 Flyway，命名 V<n>\_\_<desc>.sql">

````

### 3. 末尾给用户的指引

```
✅ 模板已产出。请：
1. 复制上面的代码块（不含末尾说明）
2. 项目根新建 / 合并 CLAUDE.md
3. 把所有 <占位符> 改为实际值
4. 删掉不适用的段（例如非 Java 项目删 ddd-architect 那条）
````

### 模式 B 硬性规则

- **绝对不能**用 Edit / Write 直接动用户的 CLAUDE.md —— 只产文本，让用户审阅后手动贴
- 模板末尾必须列"占位符待替换"清单
- 已存在 CLAUDE.md 时必须警告"勿覆盖，选择性合并"
