package com.example.harness.infrastructure.config;

import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.module.paramnames.ParameterNamesModule;

import jakarta.annotation.PostConstruct;

import org.springframework.context.annotation.Configuration;

/**
 * 让 MyBatis-Plus 的 {@link JacksonTypeHandler}（items_json 列走它）用一个注册了
 * {@link ParameterNamesModule} 的 ObjectMapper。
 *
 * <p>为什么需要：{@code OrderItem} 是 domain 层 VO，只有一个带校验的 all-args 构造器、
 * 无默认构造器、且**不允许** import Jackson（分层门禁：domain 不得依赖 Jackson）。
 * Jackson 要靠构造器**参数名**反序列化（编译已开 {@code -parameters}），
 * 但 JacksonTypeHandler 默认用的是自己 new 的裸 ObjectMapper，没注册 ParameterNamesModule
 * → 读回 items_json 时报 "no Creators"。这里全局替换它的 ObjectMapper 修复往返。
 *
 * <p>本类在 infrastructure 层，import Jackson 合规（分层门禁只约束 domain）。
 */
@Configuration
public class MyBatisJacksonConfig {

    @PostConstruct
    void configureJacksonTypeHandler() {
        ObjectMapper mapper = new ObjectMapper().registerModule(new ParameterNamesModule());
        JacksonTypeHandler.setObjectMapper(mapper);
    }
}
