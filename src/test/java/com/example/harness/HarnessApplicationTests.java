package com.example.harness;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * Phase 1 冒烟测试：Spring 上下文能加载就 OK。
 *
 * 真正业务测试随 M8-T3+ 各聚合落地后逐步加。
 */
@SpringBootTest
class HarnessApplicationTests {

    @Test
    void contextLoads() {
        // 仅验证 ApplicationContext 启动通过；契约由 @SpringBootTest 隐式断言。
    }
}
