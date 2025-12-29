package com.example;

// JUnit 5 tests
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Tag;

// TestNG tests
import org.testng.annotations.Test as TestNGTest;

/**
 * Mixed framework sample - contains both JUnit 5 and TestNG tests.
 * This represents a real-world migration scenario.
 */
public class MixedTest {

    // JUnit 5 test
    @Test
    @Tag("smoke")
    void junitTestLogin() {
        LoginPage loginPage = new LoginPage(driver);
        loginPage.performLogin();
    }

    // TestNG test
    @TestNGTest(groups = {"smoke"})
    public void testngTestCheckout() {
        CheckoutPage checkoutPage = new CheckoutPage(driver);
        checkoutPage.completeCheckout();
    }

    // JUnit 5 test
    @Test
    @Tag("regression")
    void junitTestProfile() {
        ProfilePage profilePage = new ProfilePage(driver);
        DashboardPage dashboard = new DashboardPage(driver);
    }
}
