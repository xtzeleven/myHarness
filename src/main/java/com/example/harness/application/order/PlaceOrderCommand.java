package com.example.harness.application.order;

import java.util.List;
import java.util.Objects;

import com.example.harness.domain.order.OrderItem;

/**
 * 下单用例输入。
 *
 * 设计：application 层 Command 直接复用 domain VO `OrderItem`：
 * - 依赖方向合法（application → domain，单向）
 * - 避免在 application 层再造一个等价 DTO 形成"无差别映射层"
 * - HTTP DTO ↔ OrderItem 的转换由 interfaces 层（P2.5 OrderController / Assembler）承担
 *
 * record 自动给 final 字段 + equals/hashCode，符合 Command 不可变意图。
 */
public record PlaceOrderCommand(String customerId, List<OrderItem> items) {

    public PlaceOrderCommand {
        Objects.requireNonNull(customerId, "customerId must not be null");
        Objects.requireNonNull(items, "items must not be null");
        items = List.copyOf(items);
    }
}
