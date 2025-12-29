package com.crossbridge.tests;

import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

/**
 * JUnit 5 test without build file - relies on source code detection.
 */
@DisplayName("Calculator Tests (No Build File)")
public class CalculatorTest {

    @Test
    @DisplayName("Addition test")
    void testAddition() {
        int result = add(5, 3);
        assertEquals(8, result, "5 + 3 should equal 8");
    }

    @Test
    @DisplayName("Subtraction test")
    void testSubtraction() {
        int result = subtract(10, 4);
        assertEquals(6, result, "10 - 4 should equal 6");
    }

    @Test
    @DisplayName("Division by zero")
    void testDivisionByZero() {
        assertThrows(ArithmeticException.class,
                    () -> divide(10, 0),
                    "Division by zero should throw exception");
    }

    private int add(int a, int b) {
        return a + b;
    }

    private int subtract(int a, int b) {
        return a - b;
    }

    private int divide(int a, int b) {
        if (b == 0) {
            throw new ArithmeticException("Cannot divide by zero");
        }
        return a / b;
    }
}
