package com.crossbridge.tests;

import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledOnOs;
import org.junit.jupiter.api.condition.OS;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Sample JUnit 5 test class for checkout functionality.
 */
@DisplayName("Checkout Process Tests")
@Tag("integration")
public class CheckoutTest {

    @BeforeAll
    static void initAll() {
        System.out.println("Initializing checkout test suite...");
    }

    @BeforeEach
    void init() {
        System.out.println("Setting up individual test...");
    }

    @Test
    @DisplayName("Complete checkout with valid items")
    @Tag("smoke")
    void testCompleteCheckout() {
        // Arrange
        String[] items = {"Item1", "Item2", "Item3"};
        double expectedTotal = 150.0;
        
        // Act
        double actualTotal = calculateTotal(items);
        
        // Assert
        assertEquals(expectedTotal, actualTotal, 0.01,
                    "Total should match expected value");
    }

    @Test
    @DisplayName("Checkout with empty cart should fail")
    @Tag("regression")
    void testEmptyCartCheckout() {
        String[] items = {};
        
        assertThrows(IllegalArgumentException.class,
                    () -> processCheckout(items),
                    "Empty cart should throw exception");
    }

    @Test
    @DisplayName("Apply discount code")
    @Tag("smoke")
    void testDiscountCode() {
        double originalPrice = 100.0;
        String discountCode = "SAVE20";
        
        double discountedPrice = applyDiscount(originalPrice, discountCode);
        
        assertEquals(80.0, discountedPrice, 0.01,
                    "20% discount should be applied");
    }

    @Test
    @DisplayName("Invalid discount code")
    @Tag("regression")
    void testInvalidDiscountCode() {
        double originalPrice = 100.0;
        String discountCode = "INVALID";
        
        double discountedPrice = applyDiscount(originalPrice, discountCode);
        
        assertEquals(originalPrice, discountedPrice, 0.01,
                    "Invalid code should not apply discount");
    }

    @Test
    @EnabledOnOs(OS.WINDOWS)
    @DisplayName("Windows-specific payment processing")
    void testWindowsPayment() {
        assertTrue(processPayment("credit_card"));
    }

    @Disabled("Payment gateway integration pending")
    @Test
    void testPayPalIntegration() {
        // TODO: Implement PayPal integration
    }

    @AfterEach
    void tearDown() {
        System.out.println("Cleaning up individual test...");
    }

    @AfterAll
    static void tearDownAll() {
        System.out.println("Checkout test suite complete.");
    }

    // Helper methods
    private double calculateTotal(String[] items) {
        return items.length * 50.0;
    }

    private void processCheckout(String[] items) {
        if (items.length == 0) {
            throw new IllegalArgumentException("Cart cannot be empty");
        }
    }

    private double applyDiscount(double price, String code) {
        if ("SAVE20".equals(code)) {
            return price * 0.8;
        }
        return price;
    }

    private boolean processPayment(String method) {
        return "credit_card".equals(method);
    }
}
