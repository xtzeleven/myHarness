#!/usr/bin/env python3
"""run-auto.sh 的尝试记录：一次写入、不覆盖。不调模型，只读写本地文件。

用法：
  python3 bench/attempt-record.py write <目标文件> [key=字符串 | key:=JSON 值] ...
  python3 bench/attempt-record.py batch <批次目录> <任务-配置-序号> ...

write：先把内容完整写进同目录的临时文件，再用硬链接（link(2)，目标已存在就失败）落到目标名。
  目标已存在、目录不可写、值不是合法 JSON → 非零退出，目标文件不被创建也不被改动。
  并发写同一个目标只有一个成功。退出码：0 成功 / 3 目标已存在 / 1 其他失败 / 2 用法错误。
  `key:=` 后面是 JSON 值（数字、true/false、null）；空串记为 null。`key=` 后面一律当字符串，空串记为 null。

batch：读批次目录里各子运行的结束记录（<任务-配置-序号>.json），打印汇总并写 batch.json（同样不覆盖）。
  这里只报**子脚本执行状态**：跑完 / 失败（停在哪一步）/ 被信号中断 / 没有结束记录。
  **样本有效性不在这里判**：跑完的脚本也可能是超时或 API 错误的作废样本，由 analyze.py 按原口径判。
  有子脚本不是"跑完"，或 batch.json 写不出来 → 退出码 1。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile


def write_once(dest: str, text: str) -> int:
    d = os.path.dirname(os.path.abspath(dest))
    try:
        fd, tmp = tempfile.mkstemp(prefix=".tmp-" + os.path.basename(dest) + "-", dir=d)
    except OSError as e:
        print(f"attempt-record: 写不了 {dest}：{e}", file=sys.stderr)
        return 1
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tmp, dest)  # 目标已存在 → FileExistsError；不会替换已有文件
        except FileExistsError:
            print(f"attempt-record: {dest} 已存在，不覆盖", file=sys.stderr)
            return 3
        except OSError as e:
            print(f"attempt-record: 写不了 {dest}：{e}", file=sys.stderr)
            return 1
        return 0
    finally:
        try:
            os.unlink(tmp)  # 只删本次自己建的临时文件
        except OSError:
            pass


def parse_pairs(pairs: list[str]) -> dict:
    rec = {}
    for p in pairs:
        key, sep, value = p.partition("=")
        if not sep or not key:
            raise ValueError(f"不是 key=value：{p}")
        if key.endswith(":"):  # key:=JSON
            try:
                rec[key[:-1]] = json.loads(value) if value.strip() else None
            except ValueError:
                raise ValueError(f"{key[:-1]} 的值不是合法 JSON：{value!r}") from None
        else:
            rec[key] = value if value != "" else None
    return rec


STATUS_TEXT = {"completed": "跑完", "failed": "失败", "interrupted": "被信号中断", "no-end-record": "没有结束记录"}


def batch(batch_dir: str, expected: list[str]) -> int:
    children = []
    for name in expected:
        try:
            with open(os.path.join(batch_dir, name + ".json"), encoding="utf-8") as f:
                rec = json.load(f)
        except (OSError, ValueError):
            rec = {"script_status": "no-end-record"}  # 子脚本被强制终止，或没能写出记录
        rec["name"] = name
        children.append(rec)
    counts = {k: sum(1 for c in children if c.get("script_status") == k) for k in STATUS_TEXT}
    print(f"批次 {os.path.basename(batch_dir)}：子脚本 {len(children)} 个 — "
          + " / ".join(f"{STATUS_TEXT[k]} {counts[k]}" for k in STATUS_TEXT))
    for c in children:
        st = c.get("script_status")
        script = STATUS_TEXT.get(st, str(st))
        if st != "no-end-record":
            script += f"（停在 {c.get('stage')}，exit {c.get('exit_code')}" + (f"，信号 {c['signal']}" if c.get("signal") else "") + "）"
        if c.get("out_dir"):
            known = [f"{k}={c.get(k)}" for k in ("timed_out", "model_exit") if c.get(k) is not None]
            sample = "待 analyze.py 判定" + (f"（已知：{'，'.join(known)}）" if known else "")
        elif st == "no-end-record":
            sample = "未知（看输出目录里有没有 attempt-start.json）"
        else:
            sample = "无（没有占到输出目录）"
        print(f"  {c['name']}  脚本：{script}  样本：{sample}")
    outs = [c["out_dir"] for c in children if c.get("out_dir")]
    print("样本有效性不在这里判。" + (f"用：python3 bench/analyze.py --table {' '.join(outs)}" if outs else ""))
    rc = write_once(os.path.join(batch_dir, "batch.json"),
                    json.dumps({"schema": 1, "batch_id": os.path.basename(batch_dir), "script_status_counts": counts,
                                "children": children}, ensure_ascii=False, indent=1) + "\n")
    if rc != 0:
        return 1
    return 0 if counts["completed"] == len(children) else 1


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "write":
        try:
            rec = parse_pairs(argv[2:])
        except ValueError as e:
            print(f"attempt-record: {e}", file=sys.stderr)
            return 2
        return write_once(argv[1], json.dumps(rec, ensure_ascii=False, indent=1) + "\n")
    if len(argv) >= 2 and argv[0] == "batch":
        return batch(argv[1], argv[2:])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
