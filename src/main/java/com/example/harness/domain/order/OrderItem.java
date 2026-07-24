package com.example.harness.domain.order;

import java.math.BigDecimal;
import java.util.Objects;

import lombok.Value;

/**
 * 订单行（值对象）。
 *
 * 严格不可变：@Value 生成 final 字段 + 全字段 equals/hashCode，无 setter。
 * 满足 engineering-practices §13 "VO 不可变 + equals/hashCode 全字段"。
 *
 * 不变量在构造器内强制（§13 "公共方法参数校验"）：sku 非空白、quantity 为正、
 * unitPrice 非负。@Value 在已存在构造器时不再生成 all-args 构造器，故本手写构造器
 * 是唯一入口，杜绝"数量为负 / 单价为负"的非法订单行被静默创建。
 * 构造器参数名与字段同名同序，Jackson 仍可经参数名反序列化（Spring Boot 默认开 -parameters），
 * 无需在 domain 层 import Jackson（保持分层纯净）。
 *
 * Money 暂用裸 BigDecimal，不引入 Money VO（amount + currency）—— P2.1 最小化，
 * Money VO 留到出现"多币种"或"金额运算集中"诉求时再抽。
 */
@Value
public class OrderItem {

    String sku;
    int quantity;
    BigDecimal unitPrice;

    public OrderItem(String sku, int quantity, BigDecimal unitPrice) {
        Objects.requireNonNull(sku, "sku must not be null");
        if (sku.isBlank()) {
            throw new IllegalArgumentException("sku must not be blank");
        }
        if (quantity <= 0) {
            throw new IllegalArgumentException("quantity must be positive, got " + quantity);
        }
        Objects.requireNonNull(unitPrice, "unitPrice must not be null");
        if (unitPrice.signum() < 0) {
            throw new IllegalArgumentException("unitPrice must not be negative, got " + unitPrice);
        }
        this.sku = sku;
        this.quantity = quantity;
        this.unitPrice = unitPrice;
    }
}
