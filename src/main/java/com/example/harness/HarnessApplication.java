package com.example.harness;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * myHarness 主入口。
 *
 * 放在包根 com.example.harness，不进 interfaces / application / domain / infrastructure 任一子包，
 * 既触发 Spring 包扫描覆盖四层，又避免主类自身污染领域分层。
 */
@SpringBootApplication
public class HarnessApplication {

    public static void main(String[] args) {
        SpringApplication.run(HarnessApplication.class, args);
    }
}
