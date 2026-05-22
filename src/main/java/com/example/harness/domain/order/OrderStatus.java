package com.example.harness.domain.order;

/**
 * Order 聚合根的状态机（与 docs/m8-event-storm.md 时间线一致）。
 *
 * P2.1 只用 PENDING（place 入口）；CONFIRMED / REJECTED / EXPIRED 留待
 * P2.4 PlaceOrderHandler 引入 confirm/reject/expire 状态转移方法时使用。
 */
public enum OrderStatus {
    PENDING,
    CONFIRMED,
    REJECTED,
    EXPIRED;
}
