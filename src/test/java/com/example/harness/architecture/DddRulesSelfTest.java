package com.example.harness.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.stream.Stream;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.lang.ArchRule;

/**
 * 证明 {@link DddRules} 每条规则都真的会拦：对故意写错的夹具（archfixture.bad）逐条求值，必须报违规。
 * 规则改坏成"永远绿"时这里会先红。
 */
class DddRulesSelfTest {

    private static final JavaClasses BAD =
            new ClassFileImporter().importPackages("com.example.harness.archfixture.bad");

    static Stream<Arguments> rules() {
        return Stream.of(
                Arguments.of("layer_direction", DddRules.LAYER_DIRECTION),
                Arguments.of("domain_framework_free", DddRules.DOMAIN_FRAMEWORK_FREE),
                Arguments.of("interfaces_no_repository", DddRules.INTERFACES_NO_REPOSITORY),
                Arguments.of("application_no_business_rule_throw", DddRules.APPLICATION_NO_BUSINESS_RULE_THROW),
                Arguments.of("domain_no_setters", DddRules.DOMAIN_NO_SETTERS),
                Arguments.of("no_cross_aggregate_reference", DddRules.NO_CROSS_AGGREGATE_REFERENCE));
    }

    @ParameterizedTest(name = "{0} 能拦下夹具里的违规")
    @MethodSource("rules")
    void rule_detects_violation_in_bad_fixture(String name, ArchRule rule) {
        assertThat(rule.evaluate(BAD).hasViolation()).as(name).isTrue();
    }
}
