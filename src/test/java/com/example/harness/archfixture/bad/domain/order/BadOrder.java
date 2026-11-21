package com.example.harness.archfixture.bad.domain.order;

import com.example.harness.archfixture.bad.application.BadHandler;
import com.example.harness.archfixture.bad.domain.customer.Customer;

/** 违规：@Transactional（禁忌 1，故意不用 @Component 以免被 Spring 扫描成 bean）、setter（禁忌 4）、持有另一聚合对象（禁忌 5）、domain 依赖 application（依赖方向）。 */
public class BadOrder {

    private Customer customer;
    private String status;

    @org.springframework.transaction.annotation.Transactional
    public void setStatus(String status) {
        this.status = status;
    }

    public void callBack(BadHandler handler) {
        handler.handle();
    }
}
