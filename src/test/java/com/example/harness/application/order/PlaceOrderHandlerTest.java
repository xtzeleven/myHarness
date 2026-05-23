package com.example.harness.application.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.util.Collections;
import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.context.ApplicationEventPublisher;

import com.example.harness.domain.order.EmptyOrderException;
import com.example.harness.domain.order.Order;
import com.example.harness.domain.order.OrderId;
import com.example.harness.domain.order.OrderItem;
import com.example.harness.domain.order.event.OrderPlaced;
import com.example.harness.domain.order.repository.OrderRepository;

/**
 * PlaceOrderHandler 单测。
 *
 * 用 Mockito mock OrderRepository + ApplicationEventPublisher，验证 P2.4 AC#1：
 * 正常路径 → repo.save + publisher.publishEvent 各被调一次，返回 OrderId 即 saved.id()
 * 失败路径 → EmptyOrderException 直接冒泡，repo/publisher 均**不**被调（事务不脏写）
 */
class PlaceOrderHandlerTest {

    private OrderRepository repository;
    private ApplicationEventPublisher publisher;
    private PlaceOrderHandler handler;

    @BeforeEach
    void setUp() {
        repository = org.mockito.Mockito.mock(OrderRepository.class);
        publisher = org.mockito.Mockito.mock(ApplicationEventPublisher.class);
        handler = new PlaceOrderHandler(repository, publisher);
    }

    private static OrderItem item(String sku, int qty, String price) {
        return new OrderItem(sku, qty, new BigDecimal(price));
    }

    @Test
    void handle_savesOrderAndPublishesEvent() {
        PlaceOrderCommand cmd = new PlaceOrderCommand(
                "CUST-001",
                List.of(item("SKU-1", 2, "9.90")));
        when(repository.save(any(Order.class))).thenAnswer(inv -> inv.getArgument(0));

        OrderId resultId = handler.handle(cmd);

        // repo.save 调用 1 次，入参聚合 customerId 正确
        ArgumentCaptor<Order> savedCaptor = ArgumentCaptor.forClass(Order.class);
        verify(repository).save(savedCaptor.capture());
        assertThat(savedCaptor.getValue().customerId()).isEqualTo("CUST-001");
        assertThat(savedCaptor.getValue().items()).hasSize(1);

        // 事件发布 1 次，事件字段对得上聚合
        ArgumentCaptor<OrderPlaced> eventCaptor = ArgumentCaptor.forClass(OrderPlaced.class);
        verify(publisher).publishEvent(eventCaptor.capture());
        OrderPlaced event = eventCaptor.getValue();
        assertThat(event.orderId()).isEqualTo(resultId);
        assertThat(event.customerId()).isEqualTo("CUST-001");
        assertThat(event.occurredAt()).isNotNull();

        // 返回的 id 即 saved.id()（因 save 直返参数）
        assertThat(resultId).isEqualTo(savedCaptor.getValue().id());
    }

    /** 空 items：domain 层抛 EmptyOrderException，application 不 catch；repo/publisher 不被触达。 */
    @Test
    void handle_withEmptyItems_propagatesEmptyOrderException() {
        PlaceOrderCommand cmd = new PlaceOrderCommand("CUST-001", Collections.emptyList());

        assertThatThrownBy(() -> handler.handle(cmd))
                .isInstanceOf(EmptyOrderException.class);

        verify(repository, never()).save(any());
        verify(publisher, never()).publishEvent(any());
    }
}
