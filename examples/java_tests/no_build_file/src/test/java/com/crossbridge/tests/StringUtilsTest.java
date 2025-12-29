package com.crossbridge.tests;

import org.testng.annotations.*;
import static org.testng.Assert.*;

/**
 * TestNG test without build file - relies on source code detection.
 */
public class StringUtilsTest {

    @Test(groups = "smoke")
    public void testReverseString() {
        String input = "hello";
        String expected = "olleh";
        
        String result = reverseString(input);
        
        assertEquals(result, expected, "String should be reversed");
    }

    @Test(groups = "regression")
    public void testPalindrome() {
        String palindrome = "racecar";
        
        assertTrue(isPalindrome(palindrome),
                  "Racecar should be identified as palindrome");
    }

    @Test(groups = "regression")
    public void testNotPalindrome() {
        String notPalindrome = "hello";
        
        assertFalse(isPalindrome(notPalindrome),
                   "Hello should not be identified as palindrome");
    }

    private String reverseString(String str) {
        return new StringBuilder(str).reverse().toString();
    }

    private boolean isPalindrome(String str) {
        String reversed = reverseString(str);
        return str.equals(reversed);
    }
}
