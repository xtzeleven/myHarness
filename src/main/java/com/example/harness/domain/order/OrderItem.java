package com.example.harness.domain.order;

import java.math.BigDecimal;

import lombok.Value;

/**
 * 订单行（值对象）。
 *
 * 严格不可变：@Value 生成 final 字段 + 全字段 equals/hashCode，无 setter。
 * 满足 engineering-practices §13 "VO 不可变 + equals/hashCode 全字段"。
 *
 * Money 暂用裸 BigDecimal，不引入 Money VO（amount + currency）—— P2.1 最小化，
 * Money VO 留到出现"多币种"或"金额运算集中"诉求时再抽。
 */
@Value
public class OrderItem {

    String sku;
    int quantity;
    BigDecimal unitPrice;
}
