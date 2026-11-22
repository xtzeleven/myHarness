#!/usr/bin/env bash
# 已入库的 Flyway 版本化迁移不可改（backlog G11 / 规则清单 K1 / bench 埋点 T3-a）
#
# Usage: check-migration-immutability.sh <base> [<head>]
#   给 head：比较 merge-base(base, head) → head（CI PR 用）
#   不给 head：比较 base → 工作区（bench / 本地自查用，含未提交改动）
#
# 改动 / 删除 / 改名 base 上已有的 V*__*.sql → exit 1。R__（可重复迁移）和新增文件不管。
# 例外：给 head 时，范围内任一提交带非空 `Migration-Rewrite-Reviewed: <理由>` 尾注 → 放行并告警。
# 只需 git + bash（兼容 macOS bash 3.2），不依赖 .claude/（bench C0 也能跑）。
set -euo pipefail

base="${1:?usage: $0 <base> [<head>]}"
head="${2:-}"
dir="${MIGRATION_DIR:-src/main/resources/db/migration}"

if [ -n "$head" ]; then
  changes="$(git diff --name-status -M "$base...$head" -- "$dir")"
else
  changes="$(git diff --name-status -M "$base" -- "$dir")"
fi

bad=""
while IFS=$'\t' read -r status p1 p2; do
  [ -n "$status" ] || continue
  case "$status" in
    M* | D* | T* | R*) ;;
    *) continue ;;
  esac
  if [[ "$(basename "$p1")" =~ ^V[0-9][0-9._]*__.+\.sql$ ]]; then
    bad="${bad}${status} ${p1}${p2:+ -> $p2}"$'\n'
  fi
done <<< "$changes"

if [ -z "$bad" ]; then
  echo "✅ 没有改动已有的版本化迁移（${dir}）"
  exit 0
fi

reason=""
if [ -n "$head" ]; then
  reason="$(git log --format='%(trailers:key=Migration-Rewrite-Reviewed,valueonly)' "$base..$head" | sed '/^[[:space:]]*$/d' | head -1)"
fi

while IFS= read -r line; do
  [ -n "$line" ] || continue
  if [ -n "$reason" ]; then
    echo "::warning::已有迁移被改写：${line}（理由：${reason}）"
  else
    echo "::error::已有迁移被改写：${line}"
  fi
done <<< "$bad"

if [ -n "$reason" ]; then
  echo "⚠️ 已有提交写了 Migration-Rewrite-Reviewed 理由，放行。所有已执行过它的环境都要 flyway repair。"
  exit 0
fi
echo "已入库的 V*__*.sql 不能改、删、改名：Flyway 校验和会失败。请新增下一个版本（如 V2__xxx.sql）。"
echo "确需改写（例如从未部署过）：git commit --amend --trailer \"Migration-Rewrite-Reviewed: <理由>\""
exit 1
