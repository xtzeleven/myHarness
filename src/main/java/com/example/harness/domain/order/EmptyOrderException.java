package com.example.harness.domain.order;

/**
 * 创建订单时 items 为空 / null 触发的 domain 异常。
 *
 * 按 engineering-practices §13 "domain 层抛 domain exception"：
 * interfaces 层负责翻译为 HTTP 4xx，本类不直接暴露给外部协议。
 */
public class EmptyOrderException extends RuntimeException {

    public EmptyOrderException(String message) {
        super(message);
    }
}
