package com.example;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

public class UserProfileTest {
    
    @Test
    @Tag("smoke")
    public void testViewProfile() {
        System.out.println("Viewing user profile");
        assertTrue(true);
    }
    
    @Test
    @Tag("regression")
    public void testEditProfile() {
        System.out.println("Editing user profile");
        assertTrue(true);
    }
}
