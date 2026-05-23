package com.example.harness.interfaces.order;

import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import com.example.harness.application.order.PlaceOrderCommand;
import com.example.harness.application.order.PlaceOrderHandler;
import com.example.harness.domain.order.EmptyOrderException;
import com.example.harness.domain.order.OrderId;

/**
 * OrderController WebMvc 单测。
 *
 * 验证 P2.5 三条 AC：
 * - 合法请求 → 201 Created + Location 头含订单 ID
 * - 缺字段 → 400 + 错误体含字段名，不暴 stacktrace
 * - 空 items（domain 抛 EmptyOrderException）→ 400 + 业务错误码
 */
@WebMvcTest(controllers = {OrderController.class, GlobalExceptionHandler.class})
class OrderControllerTest {

    @Autowired private MockMvc mvc;

    @MockBean private PlaceOrderHandler placeOrderHandler;

    @Test
    void placeOrder_returns201AndLocation() throws Exception {
        UUID fixedId = UUID.fromString("11111111-1111-1111-1111-111111111111");
        when(placeOrderHandler.handle(any(PlaceOrderCommand.class))).thenReturn(new OrderId(fixedId));

        String body = """
                {
                  "customerId": "CUST-001",
                  "items": [
                    {"sku": "SKU-1", "quantity": 2, "unitPrice": 9.90}
                  ]
                }
                """;

        mvc.perform(post("/orders").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", containsString(fixedId.toString())));

        verify(placeOrderHandler).handle(any(PlaceOrderCommand.class));
    }

    /** AC#3：缺必填字段 → 400 + 错误体含字段名，不暴 stacktrace。 */
    @Test
    void placeOrder_missingCustomerId_returns400WithFieldName() throws Exception {
        String body = """
                {
                  "items": [
                    {"sku": "SKU-1", "quantity": 1, "unitPrice": 1.00}
                  ]
                }
                """;

        mvc.perform(post("/orders").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.fields[*].field").value(org.hamcrest.Matchers.hasItem("customerId")));

        verify(placeOrderHandler, never()).handle(any());
    }

    /** 空 items 数组 → @NotEmpty 触发 400。 */
    @Test
    void placeOrder_emptyItems_returns400() throws Exception {
        String body = """
                {
                  "customerId": "CUST-001",
                  "items": []
                }
                """;

        mvc.perform(post("/orders").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"));

        verify(placeOrderHandler, never()).handle(any());
    }

    /** domain 抛 EmptyOrderException → 400 + EMPTY_ORDER 业务错误码（与校验失败区分）。 */
    @Test
    void placeOrder_domainEmptyOrderException_returns400EmptyOrderCode() throws Exception {
        when(placeOrderHandler.handle(any(PlaceOrderCommand.class)))
                .thenThrow(new EmptyOrderException("订单至少包含 1 个 OrderItem"));

        String body = """
                {
                  "customerId": "CUST-001",
                  "items": [
                    {"sku": "SKU-1", "quantity": 1, "unitPrice": 1.00}
                  ]
                }
                """;

        mvc.perform(post("/orders").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("EMPTY_ORDER"));
    }
}
