package com.example.harness.architecture;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

/**
 * 对生产代码跑 DDD 架构规则（规则定义见 {@link DddRules}）。由 {@code mvn verify} → CI java-build 不可绕过地执行。
 */
@AnalyzeClasses(packages = "com.example.harness", importOptions = ImportOption.DoNotIncludeTests.class)
class DddArchitectureTest {

    @ArchTest
    static final ArchRule layer_direction = DddRules.LAYER_DIRECTION;

    @ArchTest
    static final ArchRule domain_framework_free = DddRules.DOMAIN_FRAMEWORK_FREE;

    @ArchTest
    static final ArchRule interfaces_no_repository = DddRules.INTERFACES_NO_REPOSITORY;

    @ArchTest
    static final ArchRule application_no_business_rule_throw = DddRules.APPLICATION_NO_BUSINESS_RULE_THROW;

    @ArchTest
    static final ArchRule domain_no_setters = DddRules.DOMAIN_NO_SETTERS;

    @ArchTest
    static final ArchRule no_cross_aggregate_reference = DddRules.NO_CROSS_AGGREGATE_REFERENCE;
}
