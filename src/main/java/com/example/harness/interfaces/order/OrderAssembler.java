package com.example.harness.interfaces.order;

import java.util.List;

import com.example.harness.application.order.PlaceOrderCommand;
import com.example.harness.domain.order.OrderItem;
import com.example.harness.interfaces.order.dto.PlaceOrderRequest;

/**
 * HTTP DTO ↔ 应用层 Command 的转换器。
 *
 * 与 Controller 解耦让转换逻辑可独立单测，未来若引入 ModelMapper / MapStruct 也无需改 Controller。
 * 全 static —— 无状态，不需要 Spring 容器管理。
 *
 * 注意：domain VO `OrderItem` 在 application 层 Command 内直接出现，是允许的（依赖方向 application → domain）。
 * interfaces 层在此构造 domain VO，也是分层约定允许的（interfaces → domain 经 application 的"传送带"，VO 不可变即不会破坏聚合）。
 */
public final class OrderAssembler {

    private OrderAssembler() {}

    public static PlaceOrderCommand toCommand(PlaceOrderRequest request) {
        List<OrderItem> items = request.items().stream()
                .map(i -> new OrderItem(i.sku(), i.quantity(), i.unitPrice()))
                .toList();
        return new PlaceOrderCommand(request.customerId(), items);
    }
}
