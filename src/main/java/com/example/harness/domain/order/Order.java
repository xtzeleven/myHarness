package com.example.harness.domain.order;

import java.util.List;
import java.util.Objects;

/**
 * Order 聚合根。
 *
 * 设计要点（按 engineering-practices §12 / §13）：
 * - 手写而非 @Data：避免 Lombok 暴露 setter 破坏不变量（业务方法表达意图，非贫血模型）
 * - private 构造器 + static factory `place(...)`：所有创建路径强制走业务校验
 * - items 包 List.copyOf 不可变：阻断外部修改聚合内部集合
 * - equals/hashCode 仅基于 id：DDD 标准 —— 聚合根的身份就是 ID 本身
 * - 不 import 任何 spring / persistence / jackson：满足 P2.1 AC#1
 *
 * 状态转移（confirm/reject/expire）留待 P2.4 PlaceOrderHandler 按用例补，
 * 避免本批次提前抽象未验证的状态机。
 */
public class Order {

    private final OrderId id;
    private final String customerId;
    private final List<OrderItem> items;
    private OrderStatus status;

    private Order(OrderId id, String customerId, List<OrderItem> items, OrderStatus status) {
        this.id = id;
        this.customerId = customerId;
        this.items = items;
        this.status = status;
    }

    /**
     * 创建新订单（PENDING 状态）。
     *
     * @throws EmptyOrderException items 为 null 或空
     */
    public static Order place(String customerId, List<OrderItem> items) {
        Objects.requireNonNull(customerId, "customerId must not be null");
        if (items == null || items.isEmpty()) {
            throw new EmptyOrderException("订单至少包含 1 个 OrderItem");
        }
        return new Order(
                OrderId.generate(),
                customerId,
                List.copyOf(items),
                OrderStatus.PENDING);
    }

    public OrderId id() {
        return id;
    }

    public String customerId() {
        return customerId;
    }

    public List<OrderItem> items() {
        return items;
    }

    public OrderStatus status() {
        return status;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Order other)) return false;
        return Objects.equals(this.id, other.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
}
