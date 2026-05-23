package com.example.harness.application.order;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.example.harness.domain.order.Order;
import com.example.harness.domain.order.OrderId;
import com.example.harness.domain.order.event.OrderPlaced;
import com.example.harness.domain.order.repository.OrderRepository;

/**
 * 下单用例编排器。
 *
 * 按 engineering-practices §12 / P2.4 AC#1：
 * - 类位于 application 层，事务边界由本层承担（domain / infrastructure 不准带 @Transactional）
 * - `handle` 严格四步：接命令 → 调 domain → 调 repo → 发事件，无 if/else 业务规则
 *   （业务规则在 `Order.place` 内表达，本层不做条件分支）
 * - 失败路径：`Order.place` 抛 `EmptyOrderException` 时直接冒泡，由 interfaces 层翻译为 HTTP
 *
 * 事件发布用 Spring 内置 ApplicationEventPublisher（应用内同步广播）。
 * 跨进程 / 异步 / MQ 发布是 P2.5+ 或后续 BC 的扩展点，本批次不引入。
 */
@Service
public class PlaceOrderHandler {

    private final OrderRepository repository;
    private final ApplicationEventPublisher publisher;

    public PlaceOrderHandler(OrderRepository repository, ApplicationEventPublisher publisher) {
        this.repository = repository;
        this.publisher = publisher;
    }

    @Transactional
    public OrderId handle(PlaceOrderCommand cmd) {
        Order order = Order.place(cmd.customerId(), cmd.items());
        Order saved = repository.save(order);
        publisher.publishEvent(OrderPlaced.of(saved.id(), saved.customerId()));
        return saved.id();
    }
}
