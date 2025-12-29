package com.crossbridge.tests.junit;

import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

/**
 * JUnit 5 test in a mixed framework project.
 */
@DisplayName("Payment Tests (JUnit)")
@Tag("payment")
public class PaymentJUnitTest {

    @Test
    @DisplayName("Process credit card payment")
    @Tag("smoke")
    void testCreditCardPayment() {
        String cardNumber = "4111111111111111";
        double amount = 99.99;
        
        boolean result = processPayment(cardNumber, amount);
        
        assertTrue(result, "Credit card payment should succeed");
    }

    @Test
    @DisplayName("Reject invalid card")
    @Tag("regression")
    void testInvalidCard() {
        String cardNumber = "0000000000000000";
        double amount = 99.99;
        
        assertThrows(IllegalArgumentException.class,
                    () -> processPayment(cardNumber, amount),
                    "Invalid card should throw exception");
    }

    @Test
    @DisplayName("Process refund")
    void testRefund() {
        String transactionId = "TXN123";
        double amount = 50.00;
        
        boolean result = processRefund(transactionId, amount);
        
        assertTrue(result, "Refund should be processed successfully");
    }

    private boolean processPayment(String cardNumber, double amount) {
        if (cardNumber.startsWith("0000")) {
            throw new IllegalArgumentException("Invalid card number");
        }
        return cardNumber.startsWith("4") && amount > 0;
    }

    private boolean processRefund(String transactionId, double amount) {
        return transactionId != null && amount > 0;
    }
}
