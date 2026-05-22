package com.example.harness.infrastructure.order.persistence;

import java.util.List;
import java.util.Optional;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.example.harness.domain.order.Order;
import com.example.harness.domain.order.OrderId;
import com.example.harness.domain.order.OrderStatus;
import com.example.harness.domain.order.repository.OrderRepository;

import org.springframework.stereotype.Repository;

/**
 * OrderRepository 的 MyBatis-Plus 实现（方案 B：单表 + items JSON 列）。
 *
 * 按 engineering-practices §12：domain 层定义 Repository 接口，实现放 infrastructure 层。
 * 本类是**唯一**能 import MyBatis-Plus 的 BC 内类型 —— domain/ 下保持纯净。
 *
 * 不标 @Transactional：事务边界由 application 层（PlaceOrderHandler 等）控制。
 */
@Repository
public class OrderPersistenceAdapter implements OrderRepository {

    private final OrderMapper mapper;

    public OrderPersistenceAdapter(OrderMapper mapper) {
        this.mapper = mapper;
    }

    @Override
    public Order save(Order order) {
        OrderPO po = toPO(order);
        if (mapper.selectById(po.getId()) == null) {
            mapper.insert(po);
        } else {
            mapper.updateById(po);
        }
        return order;
    }

    @Override
    public Optional<Order> findById(OrderId id) {
        OrderPO po = mapper.selectById(id.getValue());
        return Optional.ofNullable(po).map(OrderPersistenceAdapter::toDomain);
    }

    @Override
    public List<Order> findActiveByCustomer(String customerId) {
        LambdaQueryWrapper<OrderPO> w = new LambdaQueryWrapper<OrderPO>()
                .eq(OrderPO::getCustomerId, customerId)
                .eq(OrderPO::getStatus, OrderStatus.PENDING.name());
        return mapper.selectList(w).stream()
                .map(OrderPersistenceAdapter::toDomain)
                .toList();
    }

    private static OrderPO toPO(Order o) {
        return new OrderPO(
                o.id().getValue(),
                o.customerId(),
                o.status().name(),
                o.items());
    }

    private static Order toDomain(OrderPO po) {
        return Order.reconstitute(
                new OrderId(po.getId()),
                po.getCustomerId(),
                po.getItems(),
                OrderStatus.valueOf(po.getStatus()));
    }
}
