package com.example.harness.archfixture.bad.interfaces;

import com.example.harness.archfixture.bad.domain.order.repository.BadOrderRepository;

/** 违规：interfaces 直接持有 Repository（禁忌 2）。 */
public class BadController {

    private BadOrderRepository repository;
}
