package com.example;

import org.testng.annotations.Test;
import org.testng.annotations.BeforeMethod;
import static org.testng.Assert.*;

/**
 * Sample TestNG test for fixture testing.
 * Tests checkout functionality with smoke and regression groups.
 */
public class CheckoutTest {

    private WebDriver driver;

    @BeforeMethod
    public void setUp() {
        driver = new ChromeDriver();
    }

    @Test(groups = {"smoke", "critical"})
    public void testAddToCart() {
        ProductPage productPage = new ProductPage(driver);
        productPage.selectProduct("Laptop");
        productPage.clickAddToCart();
        
        CartPage cartPage = new CartPage(driver);
        assertTrue(cartPage.hasItems());
    }

    @Test(groups = {"smoke"})
    public void testCheckoutFlow() {
        CartPage cartPage = new CartPage(driver);
        cartPage.proceedToCheckout();
        
        CheckoutPage checkoutPage = new CheckoutPage(driver);
        checkoutPage.enterShippingInfo("123 Main St", "New York", "10001");
        checkoutPage.enterPaymentInfo("4111111111111111", "12/25", "123");
        checkoutPage.placeOrder();
        
        ConfirmationPage confirmationPage = new ConfirmationPage(driver);
        assertTrue(confirmationPage.isOrderSuccessful());
    }

    @Test(groups = {"regression"})
    public void testEmptyCartCheckout() {
        CartPage cartPage = new CartPage(driver);
        cartPage.proceedToCheckout();
        
        assertTrue(cartPage.showsEmptyCartMessage());
    }
}
