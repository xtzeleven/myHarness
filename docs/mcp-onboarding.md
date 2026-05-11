# MCP Onboarding — 新增 MCP 接入清单

**Status**: Accepted (M7 后置 / M8 启动前)
**Date**: 2026-05-11

> **本文回答**：要接一个新 MCP（如 Linear / Slack / GitHub / 其他 DB），要改哪些文件？怎么保证不违反 [engineering-practices §14 MCP 治理](../.claude/rules/engineering-practices.md)？

## 1. 什么时候用本清单

- 新加 MCP server（数据库 / API client / 文件系统 / 外部 SaaS）
- 升级已有 MCP 凭据或换 provider
- 替换 MCP 引用的环境变量名

## 2. 5 步标准流程

```
①  设计权限边界    →  ②  改 .mcp.json    →  ③  改 .env.example
                                                       ↓
                          ⑤  文档登记    ←  ④  CI 校验确认
```

### ① 设计权限边界（最重要，先想清楚再动）

回答四个问题：

| 问题                                              | 必答                                      |
| ------------------------------------------------- | ----------------------------------------- |
| 这个 MCP 能读什么？写什么？                       | 列清单                                    |
| 失败时降级路径是什么？                            | 见 [tools-fallback.md](tools-fallback.md) |
| 凭据敏感度（dev / prod / readonly / readwrite）？ | 永远先 dev + readonly                     |
| 谁该 / 不该用它？哪个 agent 关联？                | 在 agent frontmatter 显式                 |

**硬规则**：

- 数据库类 MCP **必须** readonly（账号层 + MCP 配置层双层）
- 凭据**绝不**硬编码进 `.mcp.json`（走 `${ENV_VAR}` 引用）
- prod 凭据**不入** `.env`（只放 dev）

### ② 改 `.mcp.json`

参考 `mysql-readonly` 范本：

```json
{
  "$schema": "https://json.schemastore.org/mcp.json",
  "mcpServers": {
    "<name>-readonly": {
      "_comment": "<一句话说明用途与权限边界>",
      "command": "npx",
      "args": ["-y", "<package>"],
      "env": {
        "<KEY>": "${<ENV_VAR>}",
        "ALLOW_INSERT_OPERATION": "false",
        "ALLOW_UPDATE_OPERATION": "false",
        "ALLOW_DELETE_OPERATION": "false",
        "ALLOW_DDL_OPERATION": "false"
      }
    }
  }
}
```

**注意**：

- 命名后缀 `-readonly` / `-readwrite` 显示权限边界
- `_comment` 字段写"用途 + 权限"一句话，便于审计
- env 引用用 `${VAR}` 而非 `${VAR:-default}`（避免悄悄走默认值进 prod）
- 若 MCP 不支持 `ALLOW_*=false` 控制，**必须**在账号层强制 readonly

### ③ 改 `.env.example`

为每个新 env var 加一行：

```bash
# <一句话用途，含权限说明>
<ENV_VAR>=
```

**注意**：

- 值留空（**绝不**填示例真实凭据，连 fake 都不要 — 防止误以为是真的）
- 注释写清"必须 readonly 账号"等限制
- 同一 MCP 的多个 var **写在一组**，便于复制粘贴配置

### ④ CI 校验自动覆盖（无需手动改 lint.yml）

`.github/workflows/lint.yml` 的 `structure-check` 已有：

```yaml
- name: .mcp.json variables are documented in .env.example
  run: |
    mcp_vars=$(grep -oE '\$\{[A-Z_]+' .mcp.json | sed 's/\${//' | sort -u)
    for v in $mcp_vars; do
      if ! grep -q "^${v}=" .env.example; then
        echo "::error file=.env.example::missing variable: $v"
        exit 1
      fi
    done
```

**该校验自动跑**，不需要为新 MCP 改 lint.yml。本地先跑：

```bash
mcp_vars=$(grep -oE '\$\{[A-Z_]+' .mcp.json | sed 's/\${//' | sort -u)
for v in $mcp_vars; do
  grep -q "^${v}=" .env.example || echo "MISSING: $v"
done
```

确认空输出再 push。

### ⑤ 文档登记

按重要性登记三处：

1. **`.claude/rules/engineering-practices.md §14 MCP 治理`** — 加一项"接入清单"条目：
   ```
   - <name>-readonly：用于 <场景>；凭据走 ${<ENV_VAR>}；权限：readonly only
   ```
2. **关联的 agent frontmatter** — 在 description 中提到该 MCP：
   ```
   description: ...用 <name>-readonly MCP 查 ...
   ```
3. **`AGENTS.md` 路由速查** — 如果是新场景，加一行；已覆盖则不必

**`README.md` / `CLAUDE.md` 暂不必动**（除非新 MCP 是项目核心能力，如本项目的 mysql-readonly）。

## 3. MCP 分类与默认设置

| 类别                        | 默认权限                                 | 关键 env                                | 关联 agent                 | 范例            |
| --------------------------- | ---------------------------------------- | --------------------------------------- | -------------------------- | --------------- |
| 数据库（只读）              | readonly + 账号层 SELECT only            | `*_HOST` `*_RO_USER` `*_RO_PASS` `*_DB` | schema-analyst             | mysql-readonly  |
| 数据库（读写）              | **禁用**；除非 migration-author 显式需要 | —                                       | —                          | —               |
| Issue 跟踪（Linear / Jira） | readonly 优先                            | `*_API_TOKEN`                           | （未启用）                 | linear-readonly |
| Chat（Slack / Teams）       | 只读取消息历史                           | `*_BOT_TOKEN`                           | （未启用）                 | slack-readonly  |
| 文件系统                    | 沙箱目录                                 | `<NAME>_ROOT`                           | —                          | filesystem      |
| 外部 API（GitHub / GitLab） | repo:read scope                          | `GH_TOKEN`                              | docs-keeper（如查 issues） | github-readonly |

**规则**：

- 不存在"读写都开"的默认；任何写权限必须单独 ADR 论证
- 一个 service 跑两套 MCP（如 `linear-readonly` + `linear-comment-only`）比"一套全权 MCP"更安全

## 4. 安全清单（接入前过一遍）

- [ ] 凭据走 env，`.mcp.json` 无明文
- [ ] `.env` 在 `.gitignore`（已有，复核不需要重加）
- [ ] `.env.example` 列出所有新 var，**值留空**
- [ ] 账号层强制 readonly（不只靠 MCP `ALLOW_*=false`）
- [ ] PreToolUse hook 灰名单覆盖（如 `mysql-readonly` 已被 §6 SQL 检测覆盖；新增 DB 类 MCP 时**检查 `pre-tool-use.sh` SQL 检测是否需扩展**）
- [ ] 不在日志输出凭据值（hook \_audit_log 已做了 `target` 截断 200 字符，但仍要复核 reason 字段）
- [ ] 关联 agent frontmatter 显式声明用该 MCP，便于追溯

## 5. 反模式

- ❌ `.mcp.json` 直接写明文 token（"反正本地 gitignored 了" — `.mcp.json` 入仓库）
- ❌ 用同一个账号既给 MCP 又给应用（应用挂了 MCP 也挂）
- ❌ 给 MCP 配 `ALLOW_UPDATE=true` "暂时方便"（暂时会变永久）
- ❌ 加 MCP 但不更新 `.env.example`（CI 会拦但你下次切机器自己也忘了）
- ❌ 加 MCP 但没说哪个 agent 用（其他 agent 也会用 → 失去隔离）
- ❌ prod 凭据进入开发者本地 `.env`（误 push 风险）

## 6. 范例：mysql-readonly 完整接入

参考实现路径：

```
.mcp.json:                          mysql-readonly server 定义（已有）
.env.example:                       MYSQL_HOST / MYSQL_PORT / MYSQL_RO_USER / MYSQL_RO_PASS / MYSQL_DB（已有）
.gitignore:                         .env / .env.* 已忽略（已有）
.github/workflows/lint.yml:         mcp_vars 校验（已有，通用，新 MCP 不需改）
.claude/agents/schema-analyst.md:   description 提到 mysql-readonly（已有）
.claude/rules/engineering-practices.md §14:  MCP 治理章（已有）
.claude/hooks/pre-tool-use.sh L126: 拦截 mysql/psql 起头 + DDL/DML 灰名单（已有）
```

照这套结构接入下一个 MCP。

## 7. 与其他文档的关系

- [engineering-practices §14 MCP 治理](../.claude/rules/engineering-practices.md)：硬性约束
- [tools-fallback.md](tools-fallback.md)：MCP 不可用时的降级链
- [.mcp.json](../.mcp.json)：当前实例配置
- [.env.example](../.env.example)：变量模板
- [ADR-0003 MCP 与 gitnexus](adr/0003-mcp-and-gitnexus.md)：选型决策

## 8. 接入后的复核

接入完成后，跑以下命令复核：

```bash
# 1. mcp_vars 一致性
mcp_vars=$(grep -oE '\$\{[A-Z_]+' .mcp.json | sed 's/\${//' | sort -u)
for v in $mcp_vars; do grep -q "^${v}=" .env.example && echo "OK: $v" || echo "MISSING: $v"; done

# 2. 凭据未提交
git ls-files | grep -E '\.env$' && echo "❌ .env tracked!" || echo "✅ .env not tracked"

# 3. 关联 agent 已说明
grep -l "mysql-readonly\|<新MCP名>" .claude/agents/*.md

# 4. 跑一遍 audit-practices §14
/audit-practices mcp
```
