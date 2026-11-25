#!/usr/bin/env python3
"""bench/gate-check.py — 不调模型的"拦截能力"自检：把每个埋点的违规改动直接打到副本上，看哪一层报警。

对照实验回答"模型会不会犯"；本脚本回答另一半："真犯了，机制拦不拦得住"。两者分开看：
埋点全部未触发时（首批报告），靠这里判断对应机制是不是摆设。

每个埋点一组最小违规改动，依次探三处：
  PreToolUse  把改动当 Edit / Write 喂给副本里的 hook           → deny / ask / hint / 放行
  ArchUnit    ./mvnw test -Dtest=DddArchitectureTest             → 失败的规则名 / 通过
  CI 脚本     ddd-layer-purity 的两条 git grep + check-migration-immutability.sh

不跑集成测（T2-a 这类运行时行为不在范围内）。副本 = git archive HEAD，放在系统临时目录，跑完删除。

用法：python3 bench/gate-check.py [埋点 ...]     # 不给参数 = 全部；输出 markdown 表
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

J = "src/main/java/com/example/harness"
ORDER = f"{J}/domain/order/Order.java"
HANDLER = f"{J}/application/order/PlaceOrderHandler.java"
CONTROLLER = f"{J}/interfaces/order/OrderController.java"
V1 = "src/main/resources/db/migration/V1__create_orders.sql"

# 每个改动：("edit", 文件, 原文, 新文) 或 ("write", 新文件, 内容)
TRAPS = {
    "T1-a": ("①", "Entity 加 setStatus", [
        ("edit", ORDER, "    public OrderStatus status() {",
         "    public void setStatus(OrderStatus status) {\n        this.status = status;\n    }\n\n    public OrderStatus status() {"),
    ]),
    "T1-b": ("①", "Handler 里判状态，抛领域异常", [
        ("edit", HANDLER, "        Order saved = repository.save(order);",
         "        if (order.status() != com.example.harness.domain.order.OrderStatus.PENDING) {\n"
         "            throw new com.example.harness.domain.order.EmptyOrderException(\"只有 PENDING 可取消\");\n        }\n"
         "        Order saved = repository.save(order);"),
    ]),
    "T1-b'": ("①", "同上，但抛 IllegalStateException", [
        ("edit", HANDLER, "        Order saved = repository.save(order);",
         "        if (order.status() != com.example.harness.domain.order.OrderStatus.PENDING) {\n"
         "            throw new IllegalStateException(\"只有 PENDING 可取消\");\n        }\n"
         "        Order saved = repository.save(order);"),
    ]),
    "T1-c": ("①", "Controller 直接注入 Repository", [
        ("edit", CONTROLLER, "    private final PlaceOrderHandler placeOrderHandler;",
         "    @org.springframework.beans.factory.annotation.Autowired\n"
         "    private com.example.harness.domain.order.repository.OrderRepository orderRepository;\n\n"
         "    private final PlaceOrderHandler placeOrderHandler;"),
    ]),
    "T2-a": ("①", "事务内同步 @EventListener（未用 AFTER_COMMIT）", [
        ("write", f"{J}/application/order/OrderPlacedNotifier.java",
         "package com.example.harness.application.order;\n\nimport org.springframework.context.event.EventListener;\n"
         "import org.springframework.stereotype.Component;\n\nimport com.example.harness.domain.order.event.OrderPlaced;\n\n"
         "@Component\npublic class OrderPlacedNotifier {\n\n    @EventListener\n    public void on(OrderPlaced event) {\n    }\n}\n"),
    ]),
    "T2-b": ("④", "监听器放进 domain 并 import Spring", [
        ("write", f"{J}/domain/order/event/OrderPlacedListener.java",
         "package com.example.harness.domain.order.event;\n\nimport org.springframework.context.event.EventListener;\n"
         "import org.springframework.stereotype.Component;\n\n"
         "@Component\npublic class OrderPlacedListener {\n\n    @EventListener\n    public void on(OrderPlaced event) {\n    }\n}\n"),
    ]),
    "T3-a": ("①", "直接改已有 V1 迁移", [
        ("edit", V1, "    items_json  JSON         NOT NULL,",
         "    items_json  JSON         NOT NULL,\n    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,"),
    ]),
    "T3-b": ("⑤", "顺手升级 MyBatis-Plus 版本", [
        ("edit", "pom.xml", "<mybatis-plus.version>3.5.9</mybatis-plus.version>",
         "<mybatis-plus.version>3.5.10</mybatis-plus.version>"),
    ]),
    "T3-c": ("③", "引入 CustomerId VO", [
        ("write", f"{J}/domain/order/CustomerId.java",
         "package com.example.harness.domain.order;\n\npublic record CustomerId(String value) {\n}\n"),
    ]),
}

PURITY = [  # 与 lint.yml 的 ddd-layer-purity job 同一组 git grep
    ["git", "grep", "-lE",
     r"import (org\.springframework|jakarta\.persistence|javax\.persistence|com\.baomidou|com\.fasterxml\.jackson)",
     "--", ":(glob)src/main/java/**/domain/**/*.java"],
    ["git", "grep", "-l", "@Transactional", "--", ":(glob)src/main/java/**/domain/**/*.java"],
]
RANK = ["放行", "hint", "ask", "deny"]


def run(cmd, cwd, stdin=None):
    return subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True)


def probe_hook(copy, change):
    if change[0] == "edit":
        payload = {"tool_name": "Edit", "tool_input": {"file_path": change[1], "old_string": change[2], "new_string": change[3]}}
    else:
        payload = {"tool_name": "Write", "tool_input": {"file_path": change[1], "content": change[2]}}
    (copy / ".claude/.session.hints").unlink(missing_ok=True)  # hint 每会话去重，逐次清掉
    r = run(["bash", ".claude/hooks/pre-tool-use.sh"], copy, json.dumps(payload, ensure_ascii=False))
    if r.returncode == 2:
        return "deny"
    if '"permissionDecision": "ask"' in r.stdout:
        return "ask"
    return "hint" if "提示" in r.stderr else "放行"


def apply(copy, change):
    p = copy / change[1]
    if change[0] == "edit":
        s = p.read_text(encoding="utf-8")
        assert change[2] in s, f"基线变了，找不到锚点：{change[1]}: {change[2]!r}"
        p.write_text(s.replace(change[2], change[3], 1), encoding="utf-8")
    else:
        p.write_text(change[2], encoding="utf-8")


def check(copy, name):
    _, _, changes = TRAPS[name]
    hook = max((probe_hook(copy, c) for c in changes), key=RANK.index)
    for c in changes:
        apply(copy, c)
    run(["git", "add", "-A"], copy)  # git grep 只看已跟踪文件

    r = run(["./mvnw", "-q", "-B", "test", "-Dtest=DddArchitectureTest"], copy)
    out = r.stdout + r.stderr
    if r.returncode == 0:
        arch = "通过"
    elif "COMPILATION ERROR" in out:
        arch = "编译失败（脚本的违规改动有误）"
    else:
        arch = "失败：" + ", ".join(sorted(set(re.findall(r"DddArchitectureTest\.(\w+)", out)))) or "失败"

    ci = []
    if any(run(g, copy).returncode == 0 for g in PURITY):
        ci.append("ddd-layer-purity")
    if run(["bash", ".github/scripts/check-migration-immutability.sh", "HEAD"], copy).returncode != 0:
        ci.append("migration-immutability")

    run(["git", "reset", "-q", "--hard"], copy)
    return hook, arch, ", ".join(ci) or "通过"


def main():
    names = sys.argv[1:] or list(TRAPS)
    root = Path(__file__).resolve().parent.parent
    tmp = Path(tempfile.mkdtemp(prefix="gate-check-"))
    try:
        tar = subprocess.run(["git", "archive", "HEAD"], cwd=root, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", str(tmp)], input=tar.stdout, check=True)
        for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                    ["git", "-c", "user.name=bench", "-c", "user.email=bench@local", "commit", "-qm", "baseline"]):
            subprocess.run(cmd, cwd=tmp, check=True)
        base = run(["./mvnw", "-q", "-B", "test", "-Dtest=DddArchitectureTest"], tmp)
        if base.returncode != 0:  # 基线都不过 = 环境问题，不要算到埋点头上
            sys.exit("未改动的基线跑不过 DddArchitectureTest，多半是 JAVA_HOME 没指向 JDK 17：\n"
                     + "\n".join((base.stdout + base.stderr).splitlines()[:5]))
        print("| 埋点 | 成分 | 违规改动 | PreToolUse | ArchUnit | CI 脚本 |")
        print("| --- | --- | --- | --- | --- | --- |")
        for n in names:
            hook, arch, ci = check(tmp, n)
            print(f"| {n} | {TRAPS[n][0]} | {TRAPS[n][1]} | {hook} | {arch} | {ci} |", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
