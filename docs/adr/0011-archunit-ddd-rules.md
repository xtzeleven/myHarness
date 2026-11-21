# ADR 0011 — 引入 ArchUnit（test scope），把 DDD 禁忌跑进 mvn verify

**Status**: Accepted
**Date**: 2026-11-21
**Stage**: M9-P2（提前落地）
**Relates to**: [ADR-0002](0002-java-ddd-backend.md), [improvement-plan.md](../improvement-plan.md) §1.1、§4 P2、§7 D2

## 背景

CLAUDE.md §6 列了 5 条 DDD 禁忌，但 CI `ddd-layer-purity` 只用 `git grep` 覆盖第 1 条（domain 无框架 import / 无 `@Transactional`）。其余 4 条（interfaces 不直调 Repository、application 不写业务规则、Entity 无 setter、不跨聚合持引用）只是写给模型读的文字。按 ADR-0010 的"按成分投资"，④ 验证类应机制化。`git grep` 做不了依赖分析与字段类型判断。

CLAUDE.md §6 要求新依赖经用户确认：2026-11-21 用户确认 D2 = 引入。

## 决定

- `pom.xml` 增加 `com.tngtech.archunit:archunit-junit5:1.3.0`，**test scope**，不进运行时。
- `src/test/java/com/example/harness/architecture/`：
  - `DddRules`：规则定义，按包名段（`..domain..` 等）识别分层，不绑定根包。
  - `DddArchitectureTest`：对生产代码（不含测试类）跑全部规则，随 `mvn verify` → CI `java-build` 执行。
  - `DddRulesSelfTest`：对故意写错的夹具 `archfixture.bad` 逐条求值，**必须报违规**，证明规则不是永远绿。
- 覆盖：

| 规则                                 | 对应                       | 判定                                                |
| ------------------------------------ | -------------------------- | --------------------------------------------------- |
| `LAYER_DIRECTION`                    | §5 依赖方向                | layeredArchitecture：domain 不依赖任何外层等        |
| `DOMAIN_FRAMEWORK_FREE`              | §6-1                       | domain 不依赖 Spring / JPA / MyBatis / Jackson      |
| `INTERFACES_NO_REPOSITORY`           | §6-2                       | interfaces 不依赖 `..repository..` 或 `*Repository` |
| `APPLICATION_NO_BUSINESS_RULE_THROW` | §6-3（**代理**，部分覆盖） | application 不 `new` 领域异常                       |
| `DOMAIN_NO_SETTERS`                  | §6-4                       | domain 无 public `setXxx`                           |
| `NO_CROSS_AGGREGATE_REFERENCE`       | §6-5                       | domain 字段不持有其他聚合的类型，`*Id` 除外         |

- `ddd-layer-purity`（`git grep`）保留：不需要 JDK，几秒出结果，作快速前置；ArchUnit 是完整判定。

## 替代方案

| 候选                   | 否决原因                                             |
| ---------------------- | ---------------------------------------------------- |
| 继续扩 `git grep` 规则 | 只能做文本匹配，判不了依赖方向、字段类型、构造调用   |
| jMolecules / 自写注解  | 要给现有代码加注解，侵入载体；规模小时不值得         |
| Spring Modulith        | 面向模块边界，不覆盖 setter / 跨聚合引用；引入面更大 |

## 后果

- 👍 5 条禁忌中 4 条完整机制化，1 条（§6-3）机制化可判定部分，剩余靠 review —— 在规则注释与本表里写明，不把代理当完整落地。
- 👍 自测夹具让"规则失效"本身会让 CI 变红。
- 👎 多一个 test 依赖；夹具类放在 `src/test`，包名含 `domain` / `application`，只供自测引用。
- 新增聚合时 `NO_CROSS_AGGREGATE_REFERENCE` 自动生效；若出现共享内核（直接放在 `domain` 包下的类）不受该规则约束。

## 相关

- [`src/test/java/com/example/harness/architecture/DddRules.java`](../../src/test/java/com/example/harness/architecture/DddRules.java)
- [`CLAUDE.md` §6](../../CLAUDE.md)
- [`.github/workflows/lint.yml`](../../.github/workflows/lint.yml) `java-build` / `ddd-layer-purity`
