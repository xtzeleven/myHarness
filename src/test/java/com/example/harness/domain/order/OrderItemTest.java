package com.example.harness.domain.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.math.BigDecimal;

import org.junit.jupiter.api.Test;

class OrderItemTest {

    @Test
    void construct_withValidArgs_succeeds() {
        OrderItem item = new OrderItem("SKU-1", 1, new BigDecimal("0.00"));
        assertThat(item.getSku()).isEqualTo("SKU-1");
        assertThat(item.getQuantity()).isEqualTo(1);
        assertThat(item.getUnitPrice()).isEqualByComparingTo("0.00");
    }

    @Test
    void construct_withBlankSku_throws() {
        assertThatThrownBy(() -> new OrderItem("  ", 1, new BigDecimal("1.00")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("sku");
    }

    @Test
    void construct_withNullSku_throws() {
        assertThatThrownBy(() -> new OrderItem(null, 1, new BigDecimal("1.00")))
                .isInstanceOf(NullPointerException.class);
    }

    @Test
    void construct_withZeroOrNegativeQuantity_throws() {
        assertThatThrownBy(() -> new OrderItem("SKU-1", 0, new BigDecimal("1.00")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("quantity");
        assertThatThrownBy(() -> new OrderItem("SKU-1", -1, new BigDecimal("1.00")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("quantity");
    }

    @Test
    void construct_withNegativeUnitPrice_throws() {
        assertThatThrownBy(() -> new OrderItem("SKU-1", 1, new BigDecimal("-0.01")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("unitPrice");
    }

    @Test
    void construct_withNullUnitPrice_throws() {
        assertThatThrownBy(() -> new OrderItem("SKU-1", 1, null))
                .isInstanceOf(NullPointerException.class);
    }

    @Test
    void equalsHashCode_basedOnAllFields() {
        OrderItem a = new OrderItem("SKU-1", 2, new BigDecimal("9.90"));
        OrderItem b = new OrderItem("SKU-1", 2, new BigDecimal("9.90"));
        OrderItem differentSku = new OrderItem("SKU-2", 2, new BigDecimal("9.90"));
        OrderItem differentQty = new OrderItem("SKU-1", 3, new BigDecimal("9.90"));
        OrderItem differentPrice = new OrderItem("SKU-1", 2, new BigDecimal("19.90"));

        assertThat(a).isEqualTo(b);
        assertThat(a.hashCode()).isEqualTo(b.hashCode());
        assertThat(a).isNotEqualTo(differentSku);
        assertThat(a).isNotEqualTo(differentQty);
        assertThat(a).isNotEqualTo(differentPrice);
    }

    /** AC#3：字段全 final、无 setter（反射断言，避免后续 PR 引入 @Data 退化）。 */
    @Test
    void fieldsAreFinal_noSetter() {
        for (Field f : OrderItem.class.getDeclaredFields()) {
            if (f.isSynthetic()) {
                continue;
            }
            assertThat(Modifier.isFinal(f.getModifiers()))
                    .as("OrderItem 字段 %s 必须为 final（VO 不可变）", f.getName())
                    .isTrue();
        }
        for (Method m : OrderItem.class.getDeclaredMethods()) {
            assertThat(m.getName())
                    .as("OrderItem 不允许 setter 方法（VO 不可变）")
                    .doesNotStartWith("set");
        }
    }
}
