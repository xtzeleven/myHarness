package com.example.harness.infrastructure.order.persistence;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import org.apache.ibatis.annotations.Mapper;

/**
 * OrderPO 的 MyBatis-Plus Mapper。
 *
 * 不写自定义 SQL：save/findById/findActiveByCustomer 全走 BaseMapper 提供的
 * {@code insert} / {@code selectById} / {@code selectList(LambdaQueryWrapper)}。
 *
 * 标 {@code @Mapper}（而非主类 {@code @MapperScan}）注册为 bean：@MapperScan 会递归扫描
 * 包内所有接口，会误把 domain 层的 {@code OrderRepository} 接口注册成 mapper；逐接口标注更精确、无副作用。
 */
@Mapper
public interface OrderMapper extends BaseMapper<OrderPO> {
}
