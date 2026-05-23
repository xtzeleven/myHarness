package com.example.harness.domain.order.event;

import java.time.Instant;
import java.util.Objects;

import com.example.harness.domain.order.OrderId;

/**
 * 订单已下单领域事件。
 *
 * 按 engineering-practices §12 / §13：
 * - 不可变 record（field final、自动 equals/hashCode）
 * - 事件名过去式（OrderPlaced）
 * - 不 import 任何 Spring / persistence / jackson —— domain 层纯净
 *
 * 当前 P2.4 阶段无消费者；本类先就位，等 P2.5+ 或后续 BC 出现 listener 时直接订阅。
 * 不引入 marker `DomainEvent` 接口 —— 先一个事件就抽象会形成空抽象，等出现第二个再抽。
 */
public record OrderPlaced(OrderId orderId, String customerId, Instant occurredAt) {

    public OrderPlaced {
        Objects.requireNonNull(orderId, "orderId must not be null");
        Objects.requireNonNull(customerId, "customerId must not be null");
        Objects.requireNonNull(occurredAt, "occurredAt must not be null");
    }

    public static OrderPlaced of(OrderId orderId, String customerId) {
        return new OrderPlaced(orderId, customerId, Instant.now());
    }
}
