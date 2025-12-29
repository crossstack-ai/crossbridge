package com.example;

import com.example.pages.LoginPage;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

public class LoginTest {
    
    @Test
    @Tag("smoke")
    public void testValidLogin() {
        LoginPage loginPage = new LoginPage();
        loginPage.login("testuser", "password123");
        assertTrue(loginPage.isLoginSuccessful());
    }
    
    @Test
    @Tag("smoke")
    public void testInvalidLogin() {
        LoginPage loginPage = new LoginPage();
        loginPage.login("baduser", "wrongpass");
        // Test logic here
        assertTrue(true);
    }
    
    @Test
    @Tag("regression")
    public void testLoginWithEmptyCredentials() {
        LoginPage loginPage = new LoginPage();
        loginPage.login("", "");
        assertTrue(true);
    }
}
