---
description: 标准化提交流程 — 复核变更、按 logical change 分组 stage、写 Conventional Commit、不擅自 push
argument-hint: "[scope] 可选：本次提交主题词（如 hooks / agents / docs）"
---

# /commit

帮用户做一次干净的提交。**不许直接 push**，除非用户明确说"push"。

## 执行步骤

### 1. 采集现状（并行）

```bash
git status --porcelain
git diff --stat
git diff --cached --stat
git log --oneline -5
```

读 4 项产出，回答自己 3 个问题：

- 本地有几组**逻辑独立**的变更？（应该拆成几个 commit？）
- 是否混入不该提的文件（`.env`、`*.key`、`.idea/`、生成产物）？若有，**先警告用户**。
- 仓库 commit 风格是什么？（看最近 5 条 → 决定 type 用 `feat`/`fix`/`docs`/`chore`/`refactor`/`test`/`build`/`ci`）

### 2. 复核 diff

对每组逻辑变更各跑一次 `git diff -- <files>`，确认：

- 没有调试残留（`console.log` / `print(` / `TODO: remove`）
- 没有秘钥（`AKIA*`、`-----BEGIN`、`password=` 字面量）
- 改动确实只做了一件事

发现可疑 → **停下来问用户**，不要自动 amend / 删改。

### 3. 分组 stage

按逻辑分组：

```bash
git add <group1-files>
```

**禁止** `git add -A` / `git add .`（容易卷入未审 file）。

### 4. 写 commit message

格式：

```
<type>(<scope>): <subject 50 字内>

<body — 解释 WHY，不解释 WHAT，可空>

<footer — 关闭 issue 等，可空>
```

`<type>` 必须从仓库现有风格里挑（看 step 1 的 `git log`），常见：

- `feat` 新功能 / `fix` bug 修复 / `docs` 文档 / `chore` 杂项
- `refactor` 重构（无行为变更） / `test` 测试 / `build` 构建 / `ci` CI 配置

`<scope>` 用 `$ARGUMENTS` 或自动从改动路径推断（如 `hooks` / `agents` / `readme`）。

### 5. 提交

```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): <subject>

<body>
EOF
)"
```

**多个逻辑分组 → 多次重复 step 3-5**，绝不合并提交。

### 6. 复核

```bash
git log --oneline -3
git status
```

确认：

- commit 数量等于逻辑组数
- working tree 干净（如有意保留未 stage，明确告诉用户）
- **不要 `git push`**，除非用户说了 push

## 遇到 PreToolUse 灰名单提示

如果 `git add` / `git commit` 过程中看到 stderr 含 `⚠️ 待人工授权: <动作>`：

1. **停下**。不要重试，不要换形式绕过
2. 把动作描述给用户：「我正要 X（如：改 pom.xml 中 spring-boot 版本 / 删除 domain 下 Repository 接口），hook 拦下需授权」
3. 等用户明确说"授权"或"继续"后，再重试同一动作
4. 用户拒绝 → 调整改动范围（如把 pom.xml 主依赖变更拆出去单独提，或暂不动 domain 边界）

**禁止**：以"绕过测试"为由跳过 hook（`--no-verify`）；以"快速完成"为由不向用户报告。

## 硬性规则

- 永不 `--amend` 已 push 的 commit（除非用户显式要）
- 永不 `--no-verify`（绕 hook = 绕质量门禁）
- 永不 `git add -A` / `git add .`（精确 stage）
- 永不在 main/master 分支做实验性提交（多人协作 / 进入 M8 后**强烈建议先建分支**；当前单人 + 工程化方法论阶段可在 main 上提交小改动，但任何 ≥ 2 文件 / 涉及 hook / agent / CI 的提交都应分支化）
- 任何 `.env` / `*.key` / `id_rsa` 出现在 staging 区 → **拒绝提交并报警**
- 灰名单触发 → **必须**让用户明确授权，不可绕过

## 输出汇报

```
📦 提交完成
- <hash> <type>(<scope>): <subject>
- <hash> <type>(<scope>): <subject>

剩余未提交：<count> 文件
下一步建议：<push? 拆 PR? 继续工作?>
```
