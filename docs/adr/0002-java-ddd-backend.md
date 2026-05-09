# ADR 0002 — Java + DDD 作为后端实战载体

**Status**: Accepted
**Date**: 2026-05-09

## 背景

三层 Harness 需要在真实工程场景验证。"真实"意味着：有领域复杂度、有架构纪律、有数据边界。

## 决定

后端实战载体选 **Java 17+ / Spring Boot / Maven / DDD 四层架构**。

DDD 分层依赖方向严格单向：
```
interfaces → application → domain ← infrastructure
```

`domain/` 层 0 框架污染（无 Spring/JPA/MyBatis import）。

## 替代方案

| 候选 | 否决原因 |
|------|---------|
| Python + FastAPI + 贫血模型 | 缺架构纪律样本，DDD 在 Python 里不典型 |
| Go + clean architecture | 生态对 DDD 战术工具支持弱（无 JPA / Spring 这种"反模式温床"） |
| Node + NestJS | 类 DDD 但 TypeScript 类型系统对领域不变量约束弱 |

选 Java 是因为它**最容易踩坑**：Lombok 滥用、`@Transactional` 边界、N+1、循环依赖。Harness 在最容易出错的栈上验证才有说服力。

## 后果

- 引入 5 个 Java/DDD 专项 agent：`ddd-architect` `spring-boot-reviewer` `maven-build-doctor` `schema-analyst` `migration-author`
- engineering-practices.md 加 §12（DDD 分层）§13（Java/Spring 风格）
- PreToolUse 灰名单加："改 `domain/` 下聚合根 / Repository 接口 / DomainEvent" + "改 pom.xml 主依赖版本"
- M4 阶段需实例化 `pom.xml` + `src/main/java/<base>/{interfaces,application,domain,infrastructure}/`

## 相关

- 后端 agent 索引：[../AGENTS.backend.md](../AGENTS.backend.md)
- DDD 规则：[../../.claude/rules/engineering-practices.md](../../.claude/rules/engineering-practices.md) §12-§13
