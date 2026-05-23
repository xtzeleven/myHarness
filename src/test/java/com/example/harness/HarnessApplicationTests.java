package com.example.harness;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;

import com.example.harness.infrastructure.order.persistence.OrderMapper;

/**
 * Phase 1+2 冒烟测试：Spring 上下文能加载就 OK。
 *
 * 测试 application.yml 排除了 MybatisPlusAutoConfiguration（避免无 DataSource 时 contextLoads 失败），
 * 因此 OrderMapper bean 不会被自动建出 —— P2.3 引入的 OrderPersistenceAdapter 构造器依赖 OrderMapper，
 * 用 @MockBean 提供空实现让上下文能装配通过。
 *
 * 真正的持久化闭环验证由 P2.6 的 testcontainers 集成测覆盖。
 */
@SpringBootTest
class HarnessApplicationTests {

    @MockBean private OrderMapper orderMapper;

    @Test
    void contextLoads() {
        // 仅验证 ApplicationContext 启动通过；契约由 @SpringBootTest 隐式断言。
    }
}
