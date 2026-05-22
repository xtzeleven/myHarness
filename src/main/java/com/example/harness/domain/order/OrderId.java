package com.example.harness.domain.order;

import java.util.UUID;

import lombok.Value;

/**
 * Order 聚合根的 typed identifier（值对象）。
 *
 * 用 typed ID 而非裸 UUID/Long，是为了让聚合边界跨方法签名时类型安全
 * （DDD 标准：聚合 ID 不可被误传成其他聚合的 ID）。
 */
@Value
public class OrderId {

    UUID value;

    public static OrderId generate() {
        return new OrderId(UUID.randomUUID());
    }
}
