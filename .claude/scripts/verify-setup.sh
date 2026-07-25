#!/usr/bin/env bash
# 环境预检 — 一眼看清"我这台机器能不能让 myHarness 的三层 Harness 真正生效"。
#
# 为什么需要它：本项目所有 hook 是 bash 调 python。非 Git Bash / WSL 环境
# （PowerShell / cmd）下 hook **静默失败**——Harness 塌掉两层却无任何报错。
# 新人克隆下来若不知道这点，会以为门禁在保护自己，实则没有。本脚本把这类
# 隐性前置显式化：逐条 ✅/⚠️/❌ + 一句话修法。
#
# 用法：
#   bash .claude/scripts/verify-setup.sh          # 全量预检
#   bash .claude/scripts/verify-setup.sh --quiet   # 只输出 ❌/⚠️ 项（CI / 快查用）
#
# 退出码：0 = 无 ❌（可能有 ⚠️）；1 = 有 ❌（关键前置缺失）。
# 失败项不阻断后续检查（逐条独立），最后汇总。

set -uo pipefail

cd "$(dirname "$0")/../.." 2>/dev/null || exit 0

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

# ---- 颜色（非 tty 或 NO_COLOR 时关闭）----
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_RED=$'\033[31m'; C_YEL=$'\033[33m'; C_GRN=$'\033[32m'; C_RST=$'\033[0m'
else
  C_RED=''; C_YEL=''; C_GRN=''; C_RST=''
fi

fail_count=0
warn_count=0
ok_count=0

# 收集非 ✅ 的行，末尾统一给修法
declare -a problems=()

# report <status> <label> <detail> [fix]
#   status: ok | warn | fail
report() {
  local status="$1" label="$2" detail="$3" fix="${4:-}"
  local icon
  case "$status" in
    ok)   icon="${C_GRN}✅${C_RST}"; ok_count=$((ok_count + 1)) ;;
    warn) icon="${C_YEL}⚠️${C_RST}";  warn_count=$((warn_count + 1)) ;;
    fail) icon="${C_RED}❌${C_RST}"; fail_count=$((fail_count + 1)) ;;
  esac
  # --quiet 只打印非 ok
  if [ "$QUIET" -eq 0 ] || [ "$status" != "ok" ]; then
    printf '  %s %-22s %s\n' "$icon" "$label" "$detail"
  fi
  if [ "$status" != "ok" ] && [ -n "$fix" ]; then
    problems+=("$label: $fix")
  fi
}

# 读 .tool-versions 里某工具的锁定版本（第 2 列）
locked_version() {
  local tool="$1"
  [ -f .tool-versions ] || return 0
  grep -E "^${tool}\b" .tool-versions 2>/dev/null | awk '{print $2}' | head -1
}

echo ""
echo "═══════════════════════════════════════════"
echo " myHarness 环境预检 (verify-setup)"
echo "═══════════════════════════════════════════"

# ============================================================
# 0. Shell —— 最关键的前置：hook 只在 bash 下触发
# ============================================================
echo ""
echo "▶ Shell（hook 生效的前提）"
# $BASH_VERSION 存在即说明当前解释器是 bash
if [ -n "${BASH_VERSION:-}" ]; then
  # 进一步区分 Git Bash / WSL / 原生 Linux（仅信息，不影响判定）
  uname_s="$(uname -s 2>/dev/null || echo unknown)"
  report ok "bash" "BASH_VERSION=${BASH_VERSION%%(*} · $uname_s"
else
  report fail "bash" "当前不是 bash" \
    "本项目 hook 只在 bash 下触发。Windows 用 Git Bash 或 WSL 跑 Claude Code；PowerShell / cmd 下 hook 会静默失效。"
fi

# ============================================================
# 1. 核心工具就绪 + 版本对照 .tool-versions
# ============================================================
echo ""
echo "▶ 核心工具（对照 .tool-versions 锁定版本）"

# --- git ---
if command -v git >/dev/null 2>&1; then
  report ok "git" "$(git --version 2>/dev/null | head -1)"
else
  report fail "git" "未安装" "装 git；本项目是 git 仓库，hook / CI 全依赖它。"
fi

# --- python（hook 解析 JSON / 写 audit log 用）---
py_bin=""
for c in python python3; do command -v "$c" >/dev/null 2>&1 && { py_bin="$c"; break; }; done
if [ -n "$py_bin" ]; then
  py_ver="$("$py_bin" -c 'import sys;print(".".join(map(str,sys.version_info[:3])))' 2>/dev/null || echo '?')"
  py_lock="$(locked_version python)"
  # 只比对 major.minor（patch 漂移不告警）
  if [ -n "$py_lock" ] && [ "${py_ver%.*}" != "${py_lock%.*}" ]; then
    report warn "python" "$py_bin $py_ver（锁定 $py_lock）" \
      "版本 minor 与 .tool-versions 不一致；hook 用得到 python，一般能跑，但 CI 用 ${py_lock%.*}。"
  else
    report ok "python" "$py_bin $py_ver"
  fi
else
  report fail "python" "未安装" "hook 全靠 python 解析 stdin JSON + 写审计日志；无 python 则整个反馈层失效。"
fi

# --- java（M8 实战载体，跑 mvn 前必须 17）---
if command -v java >/dev/null 2>&1; then
  # java -version 输出到 stderr
  jv_raw="$(java -version 2>&1 | head -1)"
  jv_major="$(printf '%s' "$jv_raw" | grep -oE '"[0-9]+' | tr -d '"' | head -1)"
  jlock="$(locked_version java)"   # temurin-17.0.13+11
  jlock_major="$(printf '%s' "$jlock" | grep -oE '[0-9]+' | head -1)"
  if [ -n "$jv_major" ] && [ -n "$jlock_major" ] && [ "$jv_major" != "$jlock_major" ]; then
    report warn "java" "Java $jv_major（锁定 $jlock_major）· $jv_raw" \
      "mvn verify 需 JDK ${jlock_major}。JAVA_HOME 若指向旧版本：export JAVA_HOME=<jdk17 路径>（见 memory pitfall_java_home_points_to_jdk8）。"
  else
    report ok "java" "Java $jv_major · $jv_raw"
  fi
else
  report warn "java" "未安装" "M8 Java 代码 / mvn verify 需要 JDK 17；只做 Harness 文档层可暂缓。"
fi

# --- maven（优先看 mvnw wrapper）---
if [ -f ./mvnw ]; then
  report ok "maven" "用项目 ./mvnw wrapper（无需全局 mvn）"
elif command -v mvn >/dev/null 2>&1; then
  mvn_ver="$(mvn -v 2>/dev/null | head -1)"
  report ok "maven" "$mvn_ver"
else
  report warn "maven" "无 mvnw 也无 mvn" "项目应带 ./mvnw；若缺失，装 Maven 3.9+ 或恢复 wrapper。"
fi

# --- node / npx（本地 prettier + CI）---
if command -v node >/dev/null 2>&1; then
  node_ver="$(node -v 2>/dev/null | tr -d 'v')"
  node_lock="$(locked_version nodejs)"
  if [ -n "$node_lock" ] && [ "${node_ver%%.*}" != "${node_lock%%.*}" ]; then
    report warn "node" "v$node_ver（锁定 $node_lock）" \
      "major 与锁定不一致；prettier 格式化一般不受影响，但 CI 用 ${node_lock%%.*}.x。"
  else
    report ok "node" "v$node_ver"
  fi
else
  report warn "node" "未安装" "PostToolUse 格式化 hook 走 npx prettier；无 node 则格式化静默跳过（不阻断）。"
fi

# ============================================================
# 2. 可选工具（缺失只降级，不阻断）
# ============================================================
echo ""
echo "▶ 可选工具（缺失仅降级）"

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    report ok "docker" "已装且 daemon 在跑"
  else
    report warn "docker" "已装但 daemon 未运行" "Testcontainers 集成测（*IT）需 docker daemon；启动 Docker Desktop 后重试。"
  fi
else
  report warn "docker" "未安装" "仅 Testcontainers 集成测需要；单测 + 编译不受影响。"
fi

if command -v npx >/dev/null 2>&1; then
  report ok "npx" "prettier 格式化可用"
else
  report warn "npx" "未安装" "PostToolUse 格式化会跳过（输出标 '未格式化'）；不阻断提交。"
fi

# ============================================================
# 3. 项目本地配置
# ============================================================
echo ""
echo "▶ 项目配置"

if [ -f .env ]; then
  report ok ".env" "存在（MySQL 只读 MCP 可用）"
else
  report warn ".env" "缺失" "MCP schema 分析不可用。cp .env.example .env 并填只读账号（见 docs/mcp-onboarding.md）。"
fi

# hook 可执行位（git 记录的 mode 应为 755）
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  bad_mode=0
  while IFS= read -r h; do
    mode="$(git ls-files -s "$h" 2>/dev/null | awk '{print $1}')"
    [ -n "$mode" ] && [ "$mode" != "100755" ] && bad_mode=$((bad_mode + 1))
  done < <(find .claude/hooks -maxdepth 1 -type f -name '*.sh' 2>/dev/null)
  if [ "$bad_mode" -eq 0 ]; then
    report ok "hook 可执行位" "全部 .sh git mode 100755"
  else
    report warn "hook 可执行位" "$bad_mode 个 hook 非 755" \
      "chmod +x .claude/hooks/*.sh 后 commit；否则 CI structure-check 会 fail。"
  fi
fi

# ============================================================
# 汇总
# ============================================================
echo ""
echo "═══════════════════════════════════════════"
printf ' 结果：%s%d ✅%s  %s%d ⚠️%s  %s%d ❌%s\n' \
  "$C_GRN" "$ok_count" "$C_RST" "$C_YEL" "$warn_count" "$C_RST" "$C_RED" "$fail_count" "$C_RST"

if [ "${#problems[@]}" -gt 0 ]; then
  echo ""
  echo " 待处理（按出现顺序）："
  for p in "${problems[@]}"; do
    printf '  • %s\n' "$p"
  done
fi
echo "═══════════════════════════════════════════"
echo ""

# 有 ❌ 才非 0 退出；⚠️ 不算失败（降级可用）
[ "$fail_count" -eq 0 ] || exit 1
exit 0
