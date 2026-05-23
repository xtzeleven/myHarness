package com.example.harness.interfaces.order;

import java.net.URI;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.UriComponentsBuilder;

import com.example.harness.application.order.PlaceOrderHandler;
import com.example.harness.domain.order.OrderId;
import com.example.harness.interfaces.order.dto.PlaceOrderRequest;

import jakarta.validation.Valid;

/**
 * Order BC 的 HTTP 入口。
 *
 * 按 engineering-practices §12：
 * - 不直 import Repository（仅依赖 application 层的 PlaceOrderHandler）
 * - 不写业务规则；DTO → Command → Handler 三步直达
 * - 异常由 GlobalExceptionHandler 统一翻译，本类不 try/catch
 */
@RestController
@RequestMapping("/orders")
public class OrderController {

    private final PlaceOrderHandler placeOrderHandler;

    public OrderController(PlaceOrderHandler placeOrderHandler) {
        this.placeOrderHandler = placeOrderHandler;
    }

    @PostMapping
    public ResponseEntity<Void> placeOrder(@Valid @RequestBody PlaceOrderRequest request) {
        OrderId orderId = placeOrderHandler.handle(OrderAssembler.toCommand(request));
        URI location = UriComponentsBuilder.fromPath("/orders/{id}")
                .buildAndExpand(orderId.getValue())
                .toUri();
        return ResponseEntity.created(location).build();
    }
}
