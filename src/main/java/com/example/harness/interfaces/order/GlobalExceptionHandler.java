package com.example.harness.interfaces.order;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import com.example.harness.domain.order.EmptyOrderException;

/**
 * Order BC 边界的异常翻译器。
 *
 * 按 engineering-practices §13："domain 层抛 domain exception，interfaces 层翻译为 HTTP"。
 *
 * 不暴露 stacktrace（满足 P2.5 AC#3）；错误体含字段名 + 简要原因。
 * 当前仅注册 Order BC 涉及的两类异常；其他 BC 出现时各自补 advice，不堆在本类。
 */
@RestControllerAdvice(basePackageClasses = OrderController.class)
public class GlobalExceptionHandler {

    @ExceptionHandler(EmptyOrderException.class)
    public ResponseEntity<Map<String, Object>> handleEmptyOrder(EmptyOrderException ex) {
        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(errorBody("EMPTY_ORDER", ex.getMessage(), List.of()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(MethodArgumentNotValidException ex) {
        List<Map<String, String>> fieldErrors = ex.getBindingResult().getFieldErrors().stream()
                .map(fe -> Map.of(
                        "field", fe.getField(),
                        "message", fe.getDefaultMessage() == null ? "invalid" : fe.getDefaultMessage()))
                .toList();
        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(errorBody("VALIDATION_FAILED", "请求体校验失败", fieldErrors));
    }

    private static Map<String, Object> errorBody(String code, String message, List<Map<String, String>> fields) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", Instant.now().toString());
        body.put("code", code);
        body.put("message", message);
        body.put("fields", fields);
        return body;
    }
}
