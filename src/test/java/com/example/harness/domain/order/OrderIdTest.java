package com.example.harness.domain.order;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.UUID;

import org.junit.jupiter.api.Test;

class OrderIdTest {

    @Test
    void equality_basedOnUuid() {
        UUID uuid = UUID.randomUUID();
        OrderId a = new OrderId(uuid);
        OrderId b = new OrderId(uuid);

        assertThat(a).isEqualTo(b);
        assertThat(a.hashCode()).isEqualTo(b.hashCode());
    }

    @Test
    void generate_returnsUniqueId() {
        OrderId a = OrderId.generate();
        OrderId b = OrderId.generate();

        assertThat(a).isNotEqualTo(b);
        assertThat(a.getValue()).isNotNull();
    }
}
