#!/usr/bin/env bash
# PreToolUse hook：事前拦截危险操作
# 退出码 2 = 阻止该工具调用；0 = 通过
# 在 stderr 输出原因，会显示给主对话

set -uo pipefail

payload="$(cat)"

# --- 工具与入参提取（python 解析 JSON，比 sed 兜底更鲁棒）---
_extract() {
  # $1=key (eg 'tool_input.command')；从 stdin 读 payload
  python -c '
import json, sys
data = json.load(sys.stdin)
keys = sys.argv[1].split(".")
cur = data
for k in keys:
    if isinstance(cur, dict):
        cur = cur.get(k)
    else:
        cur = None
        break
sys.stdout.write("" if cur is None else str(cur))
' "$1" 2>/dev/null
}

tool_name="$(printf '%s' "$payload" | _extract tool_name)"
cmd="$(printf '%s' "$payload" | _extract tool_input.command)"
file_path="$(printf '%s' "$payload" | _extract tool_input.file_path)"
new_content="$(printf '%s' "$payload" | _extract tool_input.new_string)"
[ -z "$new_content" ] && new_content="$(printf '%s' "$payload" | _extract tool_input.content)"

deny() {
  _audit_log "deny" "$1" false
  echo "[pre-tool-use] BLOCKED: $1" >&2
  echo "[pre-tool-use] 如确需执行，请用户在终端手动跑，或调整规则后重试" >&2
  exit 2
}

# 灰名单：阻止 + 提示主对话向用户索要授权
# 主对话看到 "⚠️ 待人工授权:" 前缀应当停下，把待执行操作描述给用户，由用户口头确认后才继续。
ask_user() {
  _audit_log "ask_user" "$1" false
  echo "[pre-tool-use] ⚠️ 待人工授权: $1" >&2
  echo "[pre-tool-use] 主 Claude：请向用户描述将执行的动作并等待明确授权后再重试，不可绕过。" >&2
  exit 2
}

# 写 JSONL 到 .claude/.audit.log（M7-T4 引入；已 .gitignore）
# 用法：_audit_log <action: deny|ask_user|bypass|hint> <reason> <bypass: true|false>
_audit_log() {
  local action="$1" reason="$2" bypass="${3:-false}"
  local target="${file_path:-${cmd:-}}"
  # 截断 target 到 200 字符，避免 log 爆炸
  target="${target:0:200}"
  python - "$action" "$reason" "$bypass" "${tool_name:-}" "$target" "${CLAUDE_PROJECT_DIR:-}" <<'PY' 2>/dev/null || true
import json, sys, os, datetime
action, reason, bypass, tool, target, project_dir = sys.argv[1:7]
# 优先用 Claude Code 注入的项目根；fallback 到 cwd
log_dir = os.path.join(project_dir, ".claude") if project_dir else ".claude"
os.makedirs(log_dir, exist_ok=True)
entry = {
    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "hook": "PreToolUse",
    "tool": tool,
    "target": target,
    "action": action,
    "reason": reason,
    "bypass": bypass == "true",
}
with open(os.path.join(log_dir, ".audit.log"), "a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
PY
}

# Bypass 检查（M7-T5）：CLAUDE_PLUGIN_HARNESS_BYPASS=1 绕过黑+灰名单，仍记录审计
# 兼容旧名 HARNESS_BYPASS（无 namespace 易跨 plugin 冲突，推荐用新名）
_bypass_flag="${CLAUDE_PLUGIN_HARNESS_BYPASS:-${HARNESS_BYPASS:-}}"
if [ "$_bypass_flag" = "1" ]; then
  if [ "${CLAUDE_PLUGIN_HARNESS_BYPASS:-}" = "1" ]; then
    _bypass_source="CLAUDE_PLUGIN_HARNESS_BYPASS"
  else
    _bypass_source="HARNESS_BYPASS"
  fi
  _audit_log "bypass" "${_bypass_source}=1 in env" true
  echo "[pre-tool-use] ⚠️⚠️⚠️ BYPASS ACTIVE — 黑+灰名单全部放行，仅记录审计 ⚠️⚠️⚠️" >&2
  echo "[pre-tool-use] 这不应是常态。CI 检测到 commit message 含 'BYPASS:' 会拒合。" >&2
  exit 0
fi

# === Bash 命令防御 ===
if [ "$tool_name" = "Bash" ] && [ -n "${cmd:-}" ]; then

  # 1. 致命删除
  case "$cmd" in
    *"rm -rf /"*|*"rm -rf /*"*|*"rm -fr /"*) deny "rm -rf 根目录" ;;
    *"rm -rf ~"*|*"rm -rf \$HOME"*|*"rm -rf /root"*) deny "rm -rf 家目录" ;;
    *"rm -rf .git"*) deny "rm -rf .git（仓库元数据）" ;;
  esac

  # 2. 强推主分支
  if echo "$cmd" | grep -Eq 'git[[:space:]]+push.*--force([[:space:]]|$).*\b(main|master|prod|production)\b'; then
    deny "git push --force 到保护分支（main/master/prod）"
  fi
  if echo "$cmd" | grep -Eq 'git[[:space:]]+push.*\+.*\b(main|master|prod|production)\b'; then
    deny "git push +refspec 到保护分支"
  fi

  # 3. 危险权限
  case "$cmd" in
    *"chmod -R 777"*|*"chmod 777 /"*) deny "chmod 777 大范围或根" ;;
  esac

  # 4. 远程脚本直接执行
  if echo "$cmd" | grep -Eq '(curl|wget)[^|]*\|[[:space:]]*(sh|bash|zsh)([[:space:]]|$)'; then
    deny "curl|wget | sh（未审计的远程脚本直接执行）"
  fi

  # 5. 重置工作树
  case "$cmd" in
    *"git reset --hard"*)
      # 允许指向具体 commit/HEAD~N，但不允许 origin/main
      if echo "$cmd" | grep -Eq 'reset[[:space:]]+--hard[[:space:]]+(origin/(main|master)|HEAD~[0-9]+)'; then
        : # 允许常见用法
      else
        echo "[pre-tool-use] WARN: git reset --hard 会丢失未提交工作，已放行但请确认" >&2
      fi
      ;;
  esac

  # 6. 灰名单 — 数据库写操作（只在命令本身就是 mysql/psql 客户端调用时检查，
  #    避免误伤 grep / cat / echo 等含 SQL 关键字字面量的普通命令）
  if echo "$cmd" | grep -Eq '^[[:space:]]*(mysql|mysqldump|psql)([[:space:]]|$)'; then
    if echo "$cmd" | grep -Eiq '\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE)[[:space:]]+(INTO|FROM|TABLE|DATABASE|SCHEMA|VIEW|INDEX|ON|USER)?\b'; then
      ask_user "包含 DDL/DML（INSERT/UPDATE/DELETE/DROP/ALTER/...）的数据库命令"
    fi
  fi
  # 同时拦截 .sql 文件管道喂入 mysql/psql
  if echo "$cmd" | grep -Eq '(mysql|psql)([[:space:]][^&|;]*)?[[:space:]]*<[[:space:]]*[^[:space:]]+\.sql'; then
    ask_user "通过 .sql 文件喂给 mysql/psql 执行"
  fi

  # 7. 灰名单 — 高影响 git 操作
  if echo "$cmd" | grep -Eq 'git[[:space:]]+(rebase[[:space:]]+-i|filter-branch|filter-repo)'; then
    ask_user "git rebase -i / filter-branch / filter-repo（重写历史）"
  fi
  if echo "$cmd" | grep -Eq 'git[[:space:]]+rm[[:space:]]+-rf?[[:space:]]'; then
    ask_user "git rm -r 批量删除"
  fi

  # 8. 灰名单 — Maven 发布 / 部署
  if echo "$cmd" | grep -Eq 'mvn[[:space:]]+([^&|;]*[[:space:]])?(deploy|release:|gpg:sign)'; then
    ask_user "mvn deploy / release（发布到仓库）"
  fi
fi

# === 文件写入防御（Edit / Write / MultiEdit）===
if [ "$tool_name" = "Edit" ] || [ "$tool_name" = "Write" ] || [ "$tool_name" = "MultiEdit" ]; then
  if [ -n "${file_path:-}" ]; then
    base="$(basename "$file_path")"
    case "$base" in
      .env|.env.*)
        # 允许 .env.example
        case "$base" in
          .env.example|.env.sample|.env.template) : ;;
          *) deny "写入 .env 文件（敏感）" ;;
        esac
        ;;
      *.key|*.pem|*.p12|*.pfx) deny "写入密钥/证书文件 ($base)" ;;
      id_rsa|id_rsa.pub|id_ed25519|id_ed25519.pub) deny "写入 SSH 密钥 ($base)" ;;
      .npmrc|.pypirc|.netrc) deny "写入凭据文件 ($base)" ;;
    esac

    # 路径中含 secrets / credentials
    case "$file_path" in
      *secrets/*|*credentials/*|*/.aws/*|*/.ssh/id_*) deny "写入凭据目录路径 ($file_path)" ;;
    esac

    # 灰名单：DDD 边界改动 — domain 层下聚合根 / Repository 接口 / 领域事件
    case "$file_path" in
      *src/main/java/*/domain/*)
        # 仅对"高影响子类型"问授权：聚合根、Repository 接口、领域事件
        if echo "$base" | grep -Eq '(Aggregate|AggregateRoot|Repository|Event|DomainEvent)\.java$'; then
          ask_user "DDD 边界改动：$file_path（聚合根 / Repository 接口 / 领域事件）"
        fi
        ;;
    esac

    # 灰名单：主要依赖升级 — pom.xml 中 spring-boot / 主 ORM / mysql 驱动
    if [ "$base" = "pom.xml" ]; then
      if [ -n "${new_content:-}" ]; then
        if echo "$new_content" | grep -Eiq '<(artifactId|groupId)>(spring-boot|mybatis|hibernate|mysql-connector|mysql)\b'; then
          ask_user "主要依赖升级：pom.xml 涉及 spring-boot / MyBatis / Hibernate / MySQL 驱动"
        fi
      else
        ask_user "pom.xml 整文件改写（请确认未变更主要依赖版本）"
      fi
    fi
  fi
fi

# === M6 按需注入 hint（建议性，不阻塞）===
# 主 Claude 看到 stderr 的 "💡 提示:" 前缀应当主动 prefetch 对应文档/agent
hint() {
  echo "💡 提示: $1" >&2
}

# 基于 file_path 的 hint
if [ -n "${file_path:-}" ]; then
  case "$file_path" in
    */pom.xml|pom.xml)
      hint "改 pom.xml 前建议调 maven-build-doctor agent + 看 rules §13"
      ;;
    *src/main/java/*/domain/*)
      hint "改 domain 层前建议调 ddd-architect agent + 看 rules §12（DDD 分层）"
      ;;
    *src/main/java/*/infrastructure/*)
      hint "改 infrastructure 层前建议调 spring-boot-reviewer agent（Repository 实现 / 适配器）"
      ;;
    *src/main/java/*/application/*)
      hint "改 application 层前看 rules §12（事务边界仅在此层）+ 调 spring-boot-reviewer agent"
      ;;
    *db/migration/*|*db/changelog/*)
      hint "写 migration 前建议调 migration-author agent（向后兼容性 / 回滚预案）"
      ;;
    */application*.yml|*/application*.yaml|*/application*.properties)
      hint "改 application 配置前建议调 spring-boot-reviewer agent（配置 / Profile）"
      ;;
    */.mcp.json|.mcp.json)
      hint "改 .mcp.json 前必读 engineering-practices.md §14（MCP 治理 — 凭据走 .env、强制只读）"
      ;;
    */.env.example|.env.example)
      hint "改 .env.example 后须同步 .mcp.json 引用变量；CI lint.yml 会校验对齐"
      ;;
    */CLAUDE.md|CLAUDE.md)
      hint "改 CLAUDE.md 后跑 /audit-context 看 token 数（每会话付费）"
      ;;
    */agents/*.md)
      hint "改 agent 文件后须同步项目 AGENTS.md 路由速查表 + 升级链表（如有）"
      ;;
    */.gitignore|.gitignore)
      hint "加 ignore 条目后跑 git ls-files 检查是否需要 git rm --cached（参考 memory: pitfall_settings_local_already_tracked）"
      ;;
  esac
fi

# 基于 cmd 的 hint
if [ -n "${cmd:-}" ]; then
  if echo "$cmd" | grep -Eq '^[[:space:]]*mvn[[:space:]]+(test|verify|compile|clean|package)'; then
    hint "跑 mvn 前可看 maven-build-doctor agent；若失败常见根因见 §速查表"
  fi
  if echo "$cmd" | grep -Eq '^[[:space:]]*(mysql|psql)[[:space:]].*\b(SELECT|EXPLAIN)\b'; then
    hint "查 DB schema / SQL 性能可走 schema-analyst agent（已配 mysql-readonly MCP）"
  fi
  if echo "$cmd" | grep -Eq '^[[:space:]]*git[[:space:]]+(commit|push)'; then
    hint "提交前考虑跑 /commit 命令（标准化 + 灰名单交互检查）；推送前 /audit-practices 自检"
  fi
  if echo "$cmd" | grep -Eq 'grep|find.*-name'; then
    hint "代码探索可优先用 gitnexus-exploring（结构化检索） / gitnexus-impact-analysis（影响面）"
  fi
fi

exit 0
