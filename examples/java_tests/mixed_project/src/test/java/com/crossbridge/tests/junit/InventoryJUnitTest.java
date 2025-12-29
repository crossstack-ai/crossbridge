package com.crossbridge.tests.junit;

import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import static org.junit.jupiter.api.Assertions.*;

/**
 * JUnit 5 inventory tests in mixed framework project.
 */
@DisplayName("Inventory Tests (JUnit)")
@Tag("inventory")
public class InventoryJUnitTest {

    @ParameterizedTest
    @DisplayName("Check stock levels")
    @CsvSource({
        "PROD001, 100, true",
        "PROD002, 0, false",
        "PROD003, 50, true"
    })
    void testStockLevels(String productId, int quantity, boolean inStock) {
        boolean result = checkStock(productId, quantity);
        assertEquals(inStock, result,
                    String.format("Product %s stock check failed", productId));
    }

    @Test
    @DisplayName("Add inventory")
    @Tag("smoke")
    void testAddInventory() {
        String productId = "PROD001";
        int quantity = 50;
        
        boolean result = addStock(productId, quantity);
        
        assertTrue(result, "Adding inventory should succeed");
    }

    private boolean checkStock(String productId, int quantity) {
        return quantity > 0;
    }

    private boolean addStock(String productId, int quantity) {
        return productId != null && quantity > 0;
    }
}
