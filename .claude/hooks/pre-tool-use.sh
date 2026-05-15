#!/usr/bin/env bash
# PreToolUse hook — 薄壳，转发给 python dispatcher
#
# P1-A 后规则数据全部在 .claude/rules/policies/*.yaml；本脚本只负责调用 dispatcher。
# dispatcher 失败默认放行（exit 0）以避免 hook bug 拖死会话。
#
# 改规则：编辑 yaml，无需碰本文件或 dispatcher。

exec python "$(dirname "$0")/../scripts/policy-dispatch.py"
