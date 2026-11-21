package com.example.harness.architecture;

import static com.tngtech.archunit.core.domain.JavaClass.Predicates.resideInAPackage;
import static com.tngtech.archunit.core.domain.JavaClass.Predicates.simpleNameEndingWith;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noMethods;
import static com.tngtech.archunit.library.Architectures.layeredArchitecture;

import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaConstructorCall;
import com.tngtech.archunit.core.domain.JavaField;
import com.tngtech.archunit.lang.ArchCondition;
import com.tngtech.archunit.lang.ArchRule;
import com.tngtech.archunit.lang.ConditionEvents;
import com.tngtech.archunit.lang.SimpleConditionEvent;

/**
 * CLAUDE.md §5 依赖方向 + §6 DDD 禁忌 5 条的机制化版本（D2 / ADR-0011）。
 *
 * <p>规则按包名段识别分层（{@code ..domain..} / {@code ..application..} / ...），不绑定根包，
 * 因此同一套规则既跑真实代码（{@link DddArchitectureTest}），也跑故意写错的夹具（{@link DddRulesSelfTest}），
 * 后者证明"规则确实会拦"，避免出现永远绿的空规则。
 *
 * <p>禁忌 3「application 不写业务规则」无法从字节码完整判定，这里只机制化其可判定的代理：
 * application 层不得自己 new 领域异常（业务规则违例应由 domain 抛出）。其余部分仍靠 review。
 */
final class DddRules {

    private DddRules() {}

    /** 依赖方向：interfaces → application → domain ← infrastructure；domain 不依赖任何外层。 */
    static final ArchRule LAYER_DIRECTION = layeredArchitecture()
            .consideringOnlyDependenciesInLayers()
            .layer("Interfaces").definedBy("..interfaces..")
            .layer("Application").definedBy("..application..")
            .layer("Domain").definedBy("..domain..")
            .layer("Infrastructure").definedBy("..infrastructure..")
            .whereLayer("Interfaces").mayNotBeAccessedByAnyLayer()
            .whereLayer("Application").mayOnlyBeAccessedByLayers("Interfaces")
            .whereLayer("Domain").mayOnlyBeAccessedByLayers("Interfaces", "Application", "Infrastructure")
            .whereLayer("Infrastructure").mayNotBeAccessedByAnyLayer()
            .because("CLAUDE.md §5：DDD 依赖方向严格单向");

    /** 禁忌 1：domain 不 import Spring / JPA / MyBatis / Jackson（含 @Transactional）。 */
    static final ArchRule DOMAIN_FRAMEWORK_FREE = noClasses()
            .that().resideInAPackage("..domain..")
            .should().dependOnClassesThat().resideInAnyPackage(
                    "org.springframework..",
                    "jakarta.persistence..",
                    "javax.persistence..",
                    "com.baomidou..",
                    "org.apache.ibatis..",
                    "com.fasterxml.jackson..")
            .because("CLAUDE.md §6-1：domain 层不依赖任何基础设施框架");

    /** 禁忌 2：interfaces 不直接调 Repository（必须经 application）。 */
    static final ArchRule INTERFACES_NO_REPOSITORY = noClasses()
            .that().resideInAPackage("..interfaces..")
            .should().dependOnClassesThat(
                    resideInAPackage("..repository..").or(simpleNameEndingWith("Repository")))
            .because("CLAUDE.md §6-2：interfaces 层必须经 application 层访问 Repository");

    /** 禁忌 3（代理）：application 不自己构造领域异常 —— 业务规则违例由 domain 判定并抛出。 */
    static final ArchRule APPLICATION_NO_BUSINESS_RULE_THROW = classes()
            .that().resideInAPackage("..application..")
            .should(new ArchCondition<JavaClass>("not construct domain exceptions") {
                @Override
                public void check(JavaClass clazz, ConditionEvents events) {
                    for (JavaConstructorCall call : clazz.getConstructorCallsFromSelf()) {
                        JavaClass target = call.getTargetOwner();
                        if (isDomain(target) && target.isAssignableTo(Throwable.class)) {
                            events.add(SimpleConditionEvent.violated(call, call.getDescription()));
                        }
                    }
                }
            })
            .because("CLAUDE.md §6-3：业务规则属于 domain，application 只编排");

    /** 禁忌 4：domain 不暴露 setter（业务方法表达意图，非贫血模型）。 */
    static final ArchRule DOMAIN_NO_SETTERS = noMethods()
            .that().areDeclaredInClassesThat().resideInAPackage("..domain..")
            .and().arePublic()
            .should().haveNameMatching("set[A-Z].*")
            .because("CLAUDE.md §6-4：Entity 不暴露 setter");

    /** 禁忌 5：不跨聚合直接持有引用，只能持有对方的 ID（类名以 Id 结尾）。 */
    static final ArchRule NO_CROSS_AGGREGATE_REFERENCE = classes()
            .that().resideInAPackage("..domain..")
            .should(new ArchCondition<JavaClass>("reference other aggregates by ID only") {
                @Override
                public void check(JavaClass clazz, ConditionEvents events) {
                    String own = aggregateOf(clazz);
                    if (own == null) {
                        return;
                    }
                    for (JavaField field : clazz.getFields()) {
                        for (JavaClass type : field.getType().getAllInvolvedRawTypes()) {
                            String other = aggregateOf(type);
                            if (other != null && !other.equals(own) && !type.getSimpleName().endsWith("Id")) {
                                events.add(SimpleConditionEvent.violated(field,
                                        field.getFullName() + " 持有聚合 '" + other + "' 的 "
                                                + type.getSimpleName() + "，应改为持有其 ID"));
                            }
                        }
                    }
                }
            })
            .because("CLAUDE.md §6-5：跨聚合用 ID 引用 + Repository 查询");

    static boolean isDomain(JavaClass c) {
        return ("." + c.getPackageName() + ".").contains(".domain.");
    }

    /** 包名中 domain 后的第一段即聚合名（..domain.order.event → order）；直接位于 domain 包的返回 null。 */
    static String aggregateOf(JavaClass c) {
        String[] parts = c.getPackageName().split("\\.");
        for (int i = 0; i < parts.length - 1; i++) {
            if (parts[i].equals("domain")) {
                return parts[i + 1];
            }
        }
        return null;
    }
}
