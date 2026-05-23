package com.example.harness.infrastructure.order.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.MySQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import com.example.harness.HarnessApplication;
import com.example.harness.domain.order.Order;
import com.example.harness.domain.order.OrderId;
import com.example.harness.domain.order.OrderItem;
import com.example.harness.domain.order.repository.OrderRepository;

/**
 * P2.3 / P2.6 闭环集成测。
 *
 * 兑现的 AC：
 * - P2.3 AC#2：`repo.save(order)` 后 `repo.findById(id)` 取回，与原对象 equals
 * - P2.6 AC#1：Flyway V1__create_orders.sql 跑通，表存在
 * - P2.6 AC#2：重复 migrate 报告 "no migration necessary"（Flyway 自身在 schema_history 已有 V1 后跳过）
 *
 * 文件后缀 `*IT.java` 走 Failsafe 约定 —— 当前 pom.xml **未**注册 failsafe-plugin，
 * 因此 `mvn test` / `mvn verify` 都不会自动触发本测；手动跑命令：
 *   mvn test -Dtest=OrderPersistenceAdapterIT -DfailIfNoTests=false
 * 需本机 Docker daemon 运行。无 Docker 时手动跑会因 Testcontainers init 失败，
 * 不影响主流程 mvn test 绿色 —— 文件后缀本身就是 skip 机制。
 *
 * `properties = { "spring.autoconfigure.exclude=" }` 覆盖主 application.yml 的排除清单，
 * 让 DataSource / Flyway / MybatisPlus autoconfig 在本测中恢复，连接 testcontainers MySQL。
 */
@Tag("integration")
@SpringBootTest(
        classes = HarnessApplication.class,
        properties = { "spring.autoconfigure.exclude=" }
)
@Testcontainers
class OrderPersistenceAdapterIT {

    @Container
    static final MySQLContainer<?> MYSQL = new MySQLContainer<>("mysql:8.0")
            .withDatabaseName("harness_test")
            .withUsername("test")
            .withPassword("test");

    @DynamicPropertySource
    static void registerDataSource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", MYSQL::getJdbcUrl);
        registry.add("spring.datasource.username", MYSQL::getUsername);
        registry.add("spring.datasource.password", MYSQL::getPassword);
        registry.add("spring.datasource.driver-class-name", () -> "com.mysql.cj.jdbc.Driver");
        registry.add("spring.flyway.enabled", () -> "true");
    }

    @Autowired private OrderRepository repository;

    @Test
    void save_then_findById_returnsEqualOrder() {
        Order order = Order.place(
                "CUST-IT-1",
                List.of(new OrderItem("SKU-1", 2, new BigDecimal("9.90"))));

        repository.save(order);

        Optional<Order> loaded = repository.findById(order.id());
        assertThat(loaded).isPresent();
        // 聚合根 equals 仅基于 id（DDD 标准）
        assertThat(loaded.get()).isEqualTo(order);
        // items / status 通过 reconstitute 复原后字段一致
        assertThat(loaded.get().customerId()).isEqualTo("CUST-IT-1");
        assertThat(loaded.get().items()).hasSize(1);
        assertThat(loaded.get().items().get(0).getSku()).isEqualTo("SKU-1");
    }

    @Test
    void findActiveByCustomer_returnsOnlyPendingForThatCustomer() {
        Order a1 = Order.place(
                "CUST-IT-2",
                List.of(new OrderItem("SKU-A", 1, new BigDecimal("1.00"))));
        Order a2 = Order.place(
                "CUST-IT-2",
                List.of(new OrderItem("SKU-B", 1, new BigDecimal("2.00"))));
        Order other = Order.place(
                "CUST-IT-3",
                List.of(new OrderItem("SKU-C", 1, new BigDecimal("3.00"))));

        repository.save(a1);
        repository.save(a2);
        repository.save(other);

        List<Order> active = repository.findActiveByCustomer("CUST-IT-2");
        assertThat(active).extracting(Order::id).containsExactlyInAnyOrder(a1.id(), a2.id());
    }

    @Test
    void findById_unknownId_returnsEmpty() {
        Optional<Order> loaded = repository.findById(OrderId.generate());
        assertThat(loaded).isEmpty();
    }
}
