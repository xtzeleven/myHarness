#!/usr/bin/env bash
# 占用一次运行的两个目录：副本 <RUN> 和输出 <OUT>。run-auto.sh 在开跑前调用；单独成文件是为了能离线测。
#
# 用法：bash bench/claim-run-dirs.sh <RUN> <OUT>
# 退出码：0 = 两个目录都是本次新建的空目录；1 = 有冲突或建不了；2 = 用法错误
#
# 规则：
# - 用不带 -p 的 mkdir 占用。目录已存在时 mkdir 失败，这一步是原子的：同名的重复运行、并发运行只有一个能成功。
# - 任一目录已存在（哪怕是空的，或是个文件）→ 报错退出，已有的东西原样保留。没有覆盖开关，要重跑就换序号。
# - 先占 RUN 再占 OUT。OUT 占不到时，只用 rmdir 撤回本次刚建的 RUN（rmdir 只删空目录），不删别的。
set -u
[ $# -eq 2 ] || { echo "用法：bash $0 <RUN> <OUT>" >&2; exit 2; }
RUN=$1; OUT=$2

conflict() { # $1 = 占不到的路径
  if [ -e "$1" ] || [ -L "$1" ]; then
    echo "ABORT: $1 已存在，不覆盖。同日同任务同配置同序号的结果已经在了（或另一个进程正在跑），换一个序号重跑。" >&2
  else
    echo "ABORT: 建不了 $1（上级目录不存在或没有写权限？）" >&2
  fi
}

mkdir -p "$(dirname "$RUN")" "$(dirname "$OUT")" 2>/dev/null
if ! mkdir "$RUN" 2>/dev/null; then
  conflict "$RUN"; exit 1
fi
if ! mkdir "$OUT" 2>/dev/null; then
  rmdir "$RUN" 2>/dev/null
  conflict "$OUT"; exit 1
fi
