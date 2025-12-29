package com.example;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.BeforeEach;

/**
 * Sample JUnit 5 test for fixture testing.
 * Tests login functionality with smoke and regression tags.
 */
public class LoginTest {

    private WebDriver driver;

    @BeforeEach
    void setUp() {
        driver = new ChromeDriver();
    }

    @Test
    @Tag("smoke")
    void testValidLogin() {
        LoginPage loginPage = new LoginPage(driver);
        loginPage.enterUsername("user@example.com");
        loginPage.enterPassword("password123");
        loginPage.clickLogin();
        
        DashboardPage dashboard = new DashboardPage(driver);
        assertTrue(dashboard.isDisplayed());
    }

    @Test
    @Tag("regression")
    void testInvalidLogin() {
        LoginPage loginPage = new LoginPage(driver);
        loginPage.enterUsername("invalid@example.com");
        loginPage.enterPassword("wrongpass");
        loginPage.clickLogin();
        
        assertTrue(loginPage.isErrorMessageDisplayed());
    }

    @Test
    @Tag("smoke")
    @Tag("security")
    void testEmptyCredentials() {
        LoginPage loginPage = new LoginPage(driver);
        loginPage.clickLogin();
        
        assertTrue(loginPage.isValidationErrorDisplayed());
    }
}
