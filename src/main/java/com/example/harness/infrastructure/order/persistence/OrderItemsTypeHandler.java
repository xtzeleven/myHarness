package com.example.harness.infrastructure.order.persistence;

import java.lang.reflect.Field;

import com.baomidou.mybatisplus.extension.handlers.AbstractJsonTypeHandler;
import com.fasterxml.jackson.databind.JavaType;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.module.paramnames.ParameterNamesModule;

/**
 * items_json 列的自定义 JSON TypeHandler。
 *
 * <p>为什么不直接用 MyBatis-Plus 的 {@code JacksonTypeHandler}：
 * {@code OrderItem} 是 domain 层 VO —— 只有一个带校验的 all-args 构造器、无默认构造器、
 * 且**不允许** import Jackson（分层门禁：domain 不得依赖 Jackson）。Jackson 要靠构造器
 * **参数名**反序列化（编译已开 {@code -parameters}），需注册 {@link ParameterNamesModule}。
 *
 * <p>{@code JacksonTypeHandler} 用的是一个**共享静态** ObjectMapper，改它要靠
 * {@code setObjectMapper} 且时机不可控（MyBatis-Plus autoconfig 可能在之后又覆盖回裸 mapper）。
 * 本 handler 改为继承 {@link AbstractJsonTypeHandler}，持有**自己实例的** ObjectMapper，
 * 与全局静态字段完全解耦 —— 一被实例化 mapper 就配好，不受初始化顺序影响。
 *
 * <p>本类在 infrastructure 层，import Jackson 合规（分层门禁只约束 domain）。
 */
public class OrderItemsTypeHandler extends AbstractJsonTypeHandler<Object> {

    private static final ObjectMapper MAPPER =
            new ObjectMapper().registerModule(new ParameterNamesModule());

    public OrderItemsTypeHandler(Class<?> type) {
        super(type);
    }

    public OrderItemsTypeHandler(Class<?> type, Field field) {
        super(type, field);
    }

    @Override
    public Object parse(String json) {
        try {
            JavaType javaType = MAPPER.getTypeFactory().constructType(getFieldType());
            return MAPPER.readValue(json, javaType);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public String toJson(Object obj) {
        try {
            return MAPPER.writeValueAsString(obj);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
