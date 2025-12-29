package com.crossbridge.tests;

import org.testng.annotations.*;
import static org.testng.Assert.*;

/**
 * Sample TestNG test class with data providers.
 */
public class DataDrivenTest {

    @DataProvider(name = "loginCredentials")
    public Object[][] createLoginData() {
        return new Object[][] {
            {"admin", "admin123", true},
            {"user1", "pass123", true},
            {"guest", "guest", true},
            {"invalid", "wrong", false},
            {"", "", false}
        };
    }

    @DataProvider(name = "searchQueries")
    public Object[][] createSearchData() {
        return new Object[][] {
            {"selenium", 10},
            {"testng", 8},
            {"java", 15},
            {"python", 12}
        };
    }

    @Test(dataProvider = "loginCredentials", groups = {"smoke", "login"})
    public void testLoginWithMultipleUsers(String username, String password, boolean shouldSucceed) {
        boolean result = performLogin(username, password);
        
        assertEquals(result, shouldSucceed,
                    String.format("Login with %s/%s should %s",
                                username, password, shouldSucceed ? "succeed" : "fail"));
    }

    @Test(dataProvider = "searchQueries", groups = {"regression", "search"})
    public void testSearchResults(String query, int expectedCount) {
        int actualCount = getSearchResultCount(query);
        
        assertEquals(actualCount, expectedCount,
                    String.format("Search for '%s' should return %d results", query, expectedCount));
    }

    @Test(groups = {"smoke"}, invocationCount = 3)
    public void testRepeatedExecution() {
        // This test will run 3 times
        assertTrue(performHealthCheck(), "Health check should pass");
    }

    @Test(groups = {"smoke"}, threadPoolSize = 3, invocationCount = 6)
    public void testConcurrentExecution() {
        // This test will run 6 times across 3 threads
        assertTrue(performHealthCheck(), "Concurrent health check should pass");
    }

    @Test(groups = {"regression"}, dependsOnGroups = {"smoke"})
    public void testDependentOnGroup() {
        assertTrue(true, "This runs after all smoke tests");
    }

    // Helper methods
    private boolean performLogin(String username, String password) {
        if (username == null || username.isEmpty() || password == null || password.isEmpty()) {
            return false;
        }
        return username.length() > 3 && password.length() > 3;
    }

    private int getSearchResultCount(String query) {
        switch (query) {
            case "selenium": return 10;
            case "testng": return 8;
            case "java": return 15;
            case "python": return 12;
            default: return 0;
        }
    }

    private boolean performHealthCheck() {
        return true;
    }
}
