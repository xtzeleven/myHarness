#!/usr/bin/env python
# coding: utf-8
"""bypass-trailer.py — 让 bypass 记录随提交进入 CI 视野（backlog G6 / improvement-plan F7）。

真实 bypass 只记在本地 `.claude/.audit.log`（gitignored），CI 看不到。本脚本两种用法：

1. 写尾注（由 `.githooks/prepare-commit-msg` 调用；启用：`git config core.hooksPath .githooks`）
     bypass-trailer.py <msg-file> [source] [sha]      # 即 prepare-commit-msg 的参数
   - 取 audit log 里 bypass=true 且晚于「上一个提交」的记录（amend 时以 HEAD^ 为界）
   - 当前进程带 HARNESS_BYPASS=1（在 bypass 会话里提交）也算
   - 命中则写尾注：`Harness-Bypass: <n> tool calls <first>..<last> (Bash=3, Edit=1)`
   - prepare-commit-msg 不受 `git commit --no-verify` 影响
   - 出错不阻断提交，但在 stderr 告警（失败要响）

2. CI 检查（lint.yml bypass-guard 调用）
     bypass-trailer.py --check <rev-range>
   - 带 `Harness-Bypass` 尾注、且同一提交没有非空 `Bypass-Reviewed: <理由>` 尾注 → exit 1
   - 带理由的照常放行，但列入 warning 与 job summary，记录永久留在历史里

补理由：`git commit --amend --trailer "Bypass-Reviewed: <为什么必须 bypass、事后核对了什么>"`

定位是「防手滑 + 留痕」，不防蓄意绕过（`git -c core.hooksPath=` 或改写提交都能去掉尾注）。
只用标准库。
"""
from __future__ import annotations

import collections
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

TRAILER_KEY = "Harness-Bypass"
REVIEW_KEY = "Bypass-Reviewed"
UTC = datetime.timezone.utc


def _git(*args: str, check: bool = False) -> str:
    out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10, check=False)
    if out.returncode != 0:
        if check:
            raise RuntimeError(f"git {' '.join(args)} 失败：{(out.stderr or '').strip()}")
        return ""
    return (out.stdout or "").strip()


# ---------- 写尾注 ----------


def resolve_audit_log() -> Path:
    """与 policy-dispatch.py `_resolve_audit_log_path` 同一规则：env 覆盖 > 子 worktree 写主仓库 > 仓库根。"""
    env_p = os.environ.get("HARNESS_AUDIT_LOG_PATH")
    if env_p:
        return Path(env_p).expanduser()
    common = _git("rev-parse", "--git-common-dir")
    if common and Path(common).is_absolute():
        return Path(common).resolve().parent / ".claude" / ".audit.log"
    top = _git("rev-parse", "--show-toplevel")
    return (Path(top) if top else Path(".")) / ".claude" / ".audit.log"


def _parse_ts(s: str) -> datetime.datetime:
    ts = datetime.datetime.fromisoformat(s)
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def since_time(source: str, sha: str) -> Optional[datetime.datetime]:
    """本次提交覆盖的起点 = 上一个提交的 committer 时间；无提交 → None（全部算）。"""
    head = _git("rev-parse", "--verify", "-q", "HEAD")
    if not head:
        return None
    ref = "HEAD"
    # --amend 时 source=commit、sha=HEAD：新提交取代 HEAD，界线退到 HEAD^
    if source == "commit" and sha and _git("rev-parse", "--verify", "-q", sha) == head:
        if not _git("rev-parse", "--verify", "-q", "HEAD^"):
            return None
        ref = "HEAD^"
    iso = _git("log", "-1", "--format=%cI", ref)
    return _parse_ts(iso) if iso else None


def collect_bypass(log: Path, since: Optional[datetime.datetime]) -> List[Tuple[datetime.datetime, str]]:
    hits: List[Tuple[datetime.datetime, str]] = []
    if not log.exists():
        return hits
    with open(log, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                rec = json.loads(line)
                if not isinstance(rec, dict) or rec.get("bypass") is not True:
                    continue
                ts = _parse_ts(str(rec["ts"]))
            except Exception:
                continue
            if since is not None and ts <= since:
                continue
            hits.append((ts, str(rec.get("tool") or "?")))
    return hits


def trailer_value(hits: List[Tuple[datetime.datetime, str]], env_active: bool) -> str:
    parts = []
    if hits:
        tools = ", ".join(f"{k}={v}" for k, v in sorted(collections.Counter(t for _, t in hits).items()))
        first = min(ts for ts, _ in hits).astimezone(UTC).isoformat()
        last = max(ts for ts, _ in hits).astimezone(UTC).isoformat()
        parts.append(f"{len(hits)} tool calls {first}..{last} ({tools})")
    if env_active:
        parts.append("committed with bypass env active")
    return "; ".join(parts)


def write_trailer(msg_file: str, source: str = "", sha: str = "") -> int:
    try:
        hits = collect_bypass(resolve_audit_log(), since_time(source, sha))
        env_active = os.environ.get("HARNESS_BYPASS") == "1"
        if not hits and not env_active:
            return 0
        value = trailer_value(hits, env_active)
        path = Path(msg_file)
        text = path.read_text(encoding="utf-8")
        if not any(ln.strip() and not ln.startswith("#") for ln in text.splitlines()):
            # 编辑器模板（还没有正文）：interpret-trailers 会把尾注放在第 2 行，
            # 用户在第 1 行写标题后尾注和标题同段，git 不认 → 自己排好「标题 / 空行 / 尾注」
            comments = "\n".join(ln for ln in text.splitlines() if ln.startswith("#"))
            path.write_text(
                f"\n\n{TRAILER_KEY}: {value}\n"
                f"# ↑ {TRAILER_KEY} 由 bypass-trailer 自动加入（backlog G6）。在第 1 行写标题；放弃提交请清空全部内容。\n"
                f"{comments}\n",
                encoding="utf-8",
            )
        else:
            _git("interpret-trailers", "--in-place", "--if-exists", "replace",
                 "--trailer", f"{TRAILER_KEY}: {value}", msg_file, check=True)
        print(
            f"[bypass-trailer] ⚠️ 本次提交包含 bypass 期间的改动，已加尾注 {TRAILER_KEY}: {value}\n"
            f"[bypass-trailer]    合入前补理由：git commit --amend --trailer \"{REVIEW_KEY}: <理由>\"，"
            "否则 CI bypass-guard 拒合。",
            file=sys.stderr,
        )
    except Exception as e:  # 不阻断提交，但要响
        print(f"[bypass-trailer] ❌ 检查 bypass 记录失败（提交未阻断，尾注可能缺失）：{e}", file=sys.stderr)
    return 0


# ---------- CI 检查 ----------


def _trailer(sha: str, key: str) -> str:
    return _git("log", "-1", f"--format=%(trailers:key={key},valueonly)", sha, check=True).strip()


def check_range(rev_range: str) -> int:
    shas = _git("rev-list", rev_range, check=True).split()
    unreviewed, reviewed = [], []
    for sha in shas:
        bp = _trailer(sha, TRAILER_KEY)
        if not bp:
            continue
        row = (_git("log", "-1", "--format=%h %s", sha), bp.replace("\n", "; "), _trailer(sha, REVIEW_KEY).replace("\n", "; "))
        (reviewed if row[2] else unreviewed).append(row)

    for subj, bp, _ in unreviewed:
        print(f"::error::{subj} 带 {TRAILER_KEY}（{bp}）但没有 {REVIEW_KEY} 理由")
    for subj, bp, rv in reviewed:
        print(f"::warning::{subj} 含 bypass 改动（{bp}），理由：{rv}")
    if unreviewed:
        print(f"补理由：git commit --amend --trailer \"{REVIEW_KEY}: <为什么必须 bypass、事后核对了什么>\"")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary and (unreviewed or reviewed):
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"### Bypass 记录（{rev_range}）\n\n| 提交 | {TRAILER_KEY} | {REVIEW_KEY} |\n| --- | --- | --- |\n")
            for subj, bp, rv in unreviewed + reviewed:
                f.write(f"| {subj} | {bp} | {rv or '❌ 缺理由'} |\n")
    print(f"{len(shas)} commits checked: {len(reviewed)} bypass reviewed, {len(unreviewed)} unreviewed.")
    return 1 if unreviewed else 0


def main(argv: List[str]) -> int:
    if len(argv) >= 3 and argv[1] == "--check":
        try:
            return check_range(argv[2])
        except Exception as e:
            print(f"::error::bypass 尾注检查出错：{e}")
            return 1
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    return write_trailer(argv[1], argv[2] if len(argv) > 2 else "", argv[3] if len(argv) > 3 else "")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
