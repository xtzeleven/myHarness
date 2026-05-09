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
  echo "[pre-tool-use] BLOCKED: $1" >&2
  echo "[pre-tool-use] 如确需执行，请用户在终端手动跑，或调整规则后重试" >&2
  exit 2
}

# 灰名单：阻止 + 提示主对话向用户索要授权
# 主对话看到 "⚠️ 待人工授权:" 前缀应当停下，把待执行操作描述给用户，由用户口头确认后才继续。
ask_user() {
  echo "[pre-tool-use] ⚠️ 待人工授权: $1" >&2
  echo "[pre-tool-use] 主 Claude：请向用户描述将执行的动作并等待明确授权后再重试，不可绕过。" >&2
  exit 2
}

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

  # 6. 灰名单 — 数据库写操作（即便 MCP 是只读，禁止主对话拼写操作 SQL）
  if echo "$cmd" | grep -Eiq '(^|[[:space:]"'\''])(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE)[[:space:]]+(INTO|FROM|TABLE|DATABASE|SCHEMA|VIEW|INDEX|ON)?'; then
    case "$cmd" in
      *"mysql "*|*"mysqldump "*|*"psql "*|*".sql"*)
        ask_user "包含 DDL/DML（INSERT/UPDATE/DELETE/DROP/ALTER/...）的数据库命令"
        ;;
    esac
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

exit 0
