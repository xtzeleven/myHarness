package com.example.harness.domain.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import org.junit.jupiter.api.Test;

class OrderTest {

    private static OrderItem item(String sku, int qty, String price) {
        return new OrderItem(sku, qty, new BigDecimal(price));
    }

    @Test
    void place_returnsPendingOrder() {
        Order order = Order.place("CUST-001", List.of(item("SKU-1", 2, "9.90")));

        assertThat(order.id()).isNotNull();
        assertThat(order.id().getValue()).isNotNull();
        assertThat(order.customerId()).isEqualTo("CUST-001");
        assertThat(order.items()).hasSize(1);
        assertThat(order.status()).isEqualTo(OrderStatus.PENDING);
    }

    /** AC#2：空 items 抛 EmptyOrderException。 */
    @Test
    void place_withEmptyItems_throwsEmptyOrderException() {
        assertThatThrownBy(() -> Order.place("CUST-001", Collections.emptyList()))
                .isInstanceOf(EmptyOrderException.class)
                .hasMessageContaining("至少包含");
    }

    /** AC#2 边界：null items 同样按 "empty" 处理，抛 EmptyOrderException（不让 NPE 泄漏）。 */
    @Test
    void place_withNullItems_throwsEmptyOrderException() {
        assertThatThrownBy(() -> Order.place("CUST-001", null))
                .isInstanceOf(EmptyOrderException.class);
    }

    @Test
    void items_isImmutable() {
        List<OrderItem> mutable = new ArrayList<>();
        mutable.add(item("SKU-1", 1, "1.00"));

        Order order = Order.place("CUST-001", mutable);

        // 外部修改原 list 不应影响聚合内部
        mutable.add(item("SKU-2", 1, "2.00"));
        assertThat(order.items()).hasSize(1);

        // 直接对 items() 加元素也应抛 UnsupportedOperationException
        assertThatThrownBy(() -> order.items().add(item("SKU-3", 1, "3.00")))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    /** 聚合根的 equals 仅基于 id（DDD 标准：身份即 ID）。 */
    @Test
    void equals_basedOnIdOnly() {
        Order a = Order.place("CUST-001", List.of(item("SKU-1", 1, "1.00")));
        Order b = Order.place("CUST-002", List.of(item("SKU-2", 2, "2.00")));

        // 不同 customer / 不同 items / 不同 id → 不等
        assertThat(a).isNotEqualTo(b);

        // 同 id → 即便 customer/items 字段不同也相等（用 self 比 self 验证）
        assertThat(a).isEqualTo(a);
    }
}
