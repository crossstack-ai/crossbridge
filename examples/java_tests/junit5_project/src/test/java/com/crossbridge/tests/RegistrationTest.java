package com.crossbridge.tests;

import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.junit.jupiter.params.provider.CsvSource;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Sample JUnit 5 test class with parametrized tests.
 */
@DisplayName("User Registration Tests")
@Tag("functional")
public class RegistrationTest {

    @ParameterizedTest
    @DisplayName("Valid email formats")
    @ValueSource(strings = {
        "user@example.com",
        "test.user@example.com",
        "user+tag@example.co.uk"
    })
    void testValidEmailFormats(String email) {
        assertTrue(isValidEmail(email),
                  "Email should be valid: " + email);
    }

    @ParameterizedTest
    @DisplayName("Invalid email formats")
    @ValueSource(strings = {
        "invalid.email",
        "@example.com",
        "user@",
        "user @example.com"
    })
    void testInvalidEmailFormats(String email) {
        assertFalse(isValidEmail(email),
                   "Email should be invalid: " + email);
    }

    @ParameterizedTest
    @DisplayName("Password strength validation")
    @CsvSource({
        "Pass123!, true",
        "weakpass, false",
        "12345678, false",
        "StrongP@ss1, true"
    })
    void testPasswordStrength(String password, boolean expected) {
        boolean actual = isStrongPassword(password);
        assertEquals(expected, actual,
                    "Password strength check failed for: " + password);
    }

    @Test
    @DisplayName("Successful user registration")
    @Tag("smoke")
    void testSuccessfulRegistration() {
        String username = "newuser";
        String email = "newuser@example.com";
        String password = "SecurePass123!";
        
        boolean result = registerUser(username, email, password);
        
        assertTrue(result, "Registration should succeed with valid data");
    }

    @Test
    @DisplayName("Duplicate username registration fails")
    @Tag("regression")
    void testDuplicateUsername() {
        String username = "existinguser";
        String email = "different@example.com";
        String password = "SecurePass123!";
        
        assertThrows(IllegalStateException.class,
                    () -> registerUser(username, email, password),
                    "Duplicate username should throw exception");
    }

    // Helper methods
    private boolean isValidEmail(String email) {
        if (email == null || email.trim().isEmpty()) {
            return false;
        }
        return email.matches("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$");
    }

    private boolean isStrongPassword(String password) {
        if (password == null || password.length() < 8) {
            return false;
        }
        boolean hasUpper = password.matches(".*[A-Z].*");
        boolean hasLower = password.matches(".*[a-z].*");
        boolean hasDigit = password.matches(".*\\d.*");
        boolean hasSpecial = password.matches(".*[!@#$%^&*].*");
        
        return hasUpper && hasLower && hasDigit && hasSpecial;
    }

    private boolean registerUser(String username, String email, String password) {
        if ("existinguser".equals(username)) {
            throw new IllegalStateException("Username already exists");
        }
        return isValidEmail(email) && isStrongPassword(password);
    }
}
