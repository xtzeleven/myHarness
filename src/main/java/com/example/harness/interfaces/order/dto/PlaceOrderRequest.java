package com.example.harness.interfaces.order.dto;

import java.math.BigDecimal;
import java.util.List;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/**
 * POST /orders 请求体。
 *
 * 作为 interfaces 层 DTO，与 domain VO `OrderItem` 解耦：
 * 协议演进（如未来加 currency、加 customerName）不应影响 domain。
 *
 * 校验在 Controller 入口处由 @Valid 触发，失败由 GlobalExceptionHandler 翻译为 400。
 */
public record PlaceOrderRequest(

        @NotNull(message = "customerId 不能为空")
        @Size(min = 1, max = 64, message = "customerId 长度需在 1..64")
        String customerId,

        @NotNull(message = "items 不能为空")
        @NotEmpty(message = "订单至少包含 1 个 item")
        @Valid
        List<OrderItemRequest> items
) {

    /**
     * 行项目 DTO。字段语义与 domain VO `OrderItem` 一致，但裸 record + 校验注解。
     */
    public record OrderItemRequest(

            @NotNull(message = "sku 不能为空")
            @Size(min = 1, max = 64)
            String sku,

            @NotNull(message = "quantity 不能为空")
            Integer quantity,

            @NotNull(message = "unitPrice 不能为空")
            BigDecimal unitPrice
    ) {}
}
