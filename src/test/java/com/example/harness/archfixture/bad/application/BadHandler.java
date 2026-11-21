package com.example.harness.archfixture.bad.application;

import com.example.harness.archfixture.bad.domain.order.BadOrderException;

/** 违规：application 自己判业务规则并抛领域异常（禁忌 3 代理）。 */
public class BadHandler {

    public void handle() {
        throw new BadOrderException();
    }
}
