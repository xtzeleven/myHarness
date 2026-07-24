package com.example.harness.infrastructure.order.persistence;

import java.util.List;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import com.example.harness.domain.order.OrderItem;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Order 聚合的持久化对象（PO）。
 *
 * 方案 B（单表 + JSON 列）：items 序列化为 `items_json` 列。
 * domain 层 {@code Order} 与本 PO 的双向转换发生在 {@link OrderPersistenceAdapter}。
 *
 * 字段命名 camelCase；DB 列由 mybatis-plus 全局 map-underscore-to-camel-case=true 自动映射 snake_case。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName(value = "orders", autoResultMap = true)
public class OrderPO {

    /** UUID 以 CHAR(36) 字符串存储；domain OrderId(UUID) ↔ String 转换在 OrderPersistenceAdapter 完成。 */
    @TableId(type = IdType.INPUT)
    private String id;

    private String customerId;

    /** Domain {@code OrderStatus.name()}；用 String 而非 enum 避免 MyBatis-Plus enum handler 配置。 */
    private String status;

    /** items 经 Jackson 序列化为 JSON 存入列 `items_json`。 */
    @TableField(value = "items_json", typeHandler = JacksonTypeHandler.class)
    private List<OrderItem> items;
}
