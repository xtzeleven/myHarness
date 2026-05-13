#!/usr/bin/env bash
# scripts/g13-setup.sh — 一键起 H1-H7 验证用的 3 个 demo 仓库
#
# 用法：
#   bash scripts/g13-setup.sh         # 创建/重置 D:/tmp/g13/{empty,java,py}
#   bash scripts/g13-setup.sh clean   # 仅清理
#
# 之后逐个进 demo 跑 `claude --plugin-dir D:/myGithub/myHarness/plugin`

set -uo pipefail

ROOT="D:/tmp/g13"
PLUGIN="D:/myGithub/myHarness/plugin"

cmd="${1:-create}"

clean() {
  for k in empty java py; do
    rm -rf "$ROOT/$k" 2>/dev/null
  done
  echo "[clean] removed $ROOT/{empty,java,py}"
}

mk_git() {
  cd "$1" || exit 1
  git init -q
  git -c user.name=g13 -c user.email=g13@t commit --allow-empty -qm init
}

create() {
  mkdir -p "$ROOT" || { echo "ERROR: cannot mkdir $ROOT"; exit 1; }

  # ---------- empty demo ----------
  mkdir -p "$ROOT/empty"
  cd "$ROOT/empty"
  echo "# g13-empty — 空仓库基线 (H1)" > README.md
  git init -q
  git add README.md
  git -c user.name=g13 -c user.email=g13@t commit -qm init
  echo "[create] $ROOT/empty (H1)"

  # ---------- java demo ----------
  mkdir -p "$ROOT/java/src/main/java/com/example/domain"
  mkdir -p "$ROOT/java/src/main/java/com/example/application"
  cd "$ROOT/java"
  cat > pom.xml <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>g13-java-demo</artifactId>
  <version>0.1.0</version>
  <packaging>jar</packaging>
</project>
XML
  echo "# g13-java — Java/Maven demo (H2)" > README.md
  git init -q
  git add .
  git -c user.name=g13 -c user.email=g13@t commit -qm java-stub
  echo "[create] $ROOT/java (H2)"

  # ---------- py demo ----------
  mkdir -p "$ROOT/py/src/demo"
  cd "$ROOT/py"
  cat > pyproject.toml <<'TOML'
[project]
name = "g13-demo"
version = "0.1.0"
TOML
  cat > src/demo/__init__.py <<'PY'
def add(a, b):
    return a + b
PY
  echo "# g13-py — Python demo (H3-H6)" > README.md
  git init -q
  git add .
  git -c user.name=g13 -c user.email=g13@t commit -qm py-stub
  echo "[create] $ROOT/py (H3-H6)"

  echo
  echo "============================================================"
  echo "demo 已就绪。逐项跑："
  echo "  cd $ROOT/empty && claude --plugin-dir $PLUGIN   # H1"
  echo "  cd $ROOT/java  && claude --plugin-dir $PLUGIN   # H2"
  echo "  cd $ROOT/py    && claude --plugin-dir $PLUGIN   # H3-H6"
  echo "  H7 在 myHarness 仓库本身做 (BYPASS: prefix commit)"
  echo "============================================================"
}

case "$cmd" in
  create) create ;;
  clean)  clean  ;;
  *)      echo "usage: $0 [create|clean]"; exit 2 ;;
esac
