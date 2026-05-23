-- V1__create_orders.sql
-- 第一个 BC（order）的初始 schema。
--
-- 字段映射（OrderPO ↔ DB 列，依赖 mybatis-plus map-underscore-to-camel-case=true）：
--   OrderPO.id          UUID            → id            CHAR(36)     PRIMARY KEY
--   OrderPO.customerId  String          → customer_id   VARCHAR(64)
--   OrderPO.status      String          → status        VARCHAR(16)
--   OrderPO.items       List<OrderItem> → items_json    JSON         （Jackson 序列化）
--
-- 设计选择：
-- 1. UUID 存 CHAR(36) 而非 BINARY(16)：可读 / 调试友好；订单量级远低于需 BINARY 压缩的场景。
--    后续若 hot path 出现 ID 比较瓶颈，再走 ADR 评估迁移。
-- 2. items_json 存 JSON 而非拆 order_items 子表：方案 B（详见 OrderPO 注释），
--    单聚合一次写入 / 一次读出，原子性由 JSON 列保证；当前无"按 SKU 跨订单聚合"查询需求。
-- 3. 单索引 customer_id：findActiveByCustomer 的主查询路径；不在 status 单独建索引
--    （活跃订单查询走 customer_id 过滤后再 status 二级过滤，selectivity 主要来自 customer_id）。

CREATE TABLE IF NOT EXISTS orders (
    id          CHAR(36)     NOT NULL,
    customer_id VARCHAR(64)  NOT NULL,
    status      VARCHAR(16)  NOT NULL,
    items_json  JSON         NOT NULL,
    PRIMARY KEY (id),
    INDEX idx_orders_customer_id (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
