package com.example.harness.infrastructure.order.persistence;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

/**
 * OrderPO 的 MyBatis-Plus Mapper。
 *
 * 不写自定义 SQL：save/findById/findActiveByCustomer 全走 BaseMapper 提供的
 * {@code insert} / {@code selectById} / {@code selectList(LambdaQueryWrapper)}。
 */
public interface OrderMapper extends BaseMapper<OrderPO> {
}
