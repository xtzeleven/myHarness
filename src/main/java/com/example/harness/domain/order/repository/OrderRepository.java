package com.example.harness.domain.order.repository;

import java.util.List;
import java.util.Optional;

import com.example.harness.domain.order.Order;
import com.example.harness.domain.order.OrderId;

/**
 * Order 聚合根的持久化端口（domain 层接口）。
 *
 * 按 engineering-practices §12：Repository 接口属 domain 层，实现属 infrastructure。
 * 本接口纯 POJO 语义，不带任何 Spring / JPA / MyBatis 注解，实现由 P2.3 在
 * `infrastructure/order/persistence/` 提供。
 *
 * 方法命名遵循 DDD "表达业务意图" 原则，而非 ORM CRUD 风格。
 */
public interface OrderRepository {

    /**
     * 保存聚合根（新建或更新由实现自行判断；外部不区分）。
     *
     * @return 保存后的 Order（实现可能返回输入实例，也可能重建；上层不应假设引用相等）
     */
    Order save(Order order);

    /**
     * 按 typed ID 查询单个聚合。
     */
    Optional<Order> findById(OrderId id);

    /**
     * 查询某 customer 当前处于"活跃"状态的订单。
     *
     * <p>"active" 当前定义为 {@code status == PENDING}（订单已下单但未进入终态）。
     * 终态（CONFIRMED / REJECTED / EXPIRED）不在此列。后续若引入更细分的过程状态，
     * 此处语义需同步更新（且需评估是否拆出 {@code findByCustomerAndStatus}）。
     */
    List<Order> findActiveByCustomer(String customerId);
}
