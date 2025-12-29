package com.crossbridge.tests;

import org.testng.annotations.*;
import static org.testng.Assert.*;

/**
 * Sample TestNG test class for API testing.
 */
public class ApiTest {

    @BeforeSuite
    public void setupSuite() {
        System.out.println("Setting up test suite...");
    }

    @BeforeClass
    public void setupClass() {
        System.out.println("Setting up ApiTest class...");
    }

    @BeforeMethod
    public void setupMethod() {
        System.out.println("Setting up test method...");
    }

    @Test(groups = {"smoke", "api"}, priority = 1)
    public void testGetRequest() {
        String endpoint = "/api/users";
        int statusCode = sendGetRequest(endpoint);
        
        assertEquals(statusCode, 200, "GET request should return 200");
    }

    @Test(groups = {"smoke", "api"}, priority = 2, dependsOnMethods = {"testGetRequest"})
    public void testPostRequest() {
        String endpoint = "/api/users";
        String payload = "{\"name\":\"John\",\"email\":\"john@example.com\"}";
        
        int statusCode = sendPostRequest(endpoint, payload);
        
        assertEquals(statusCode, 201, "POST request should return 201");
    }

    @Test(groups = {"regression", "api"})
    public void testPutRequest() {
        String endpoint = "/api/users/1";
        String payload = "{\"name\":\"Jane\",\"email\":\"jane@example.com\"}";
        
        int statusCode = sendPutRequest(endpoint, payload);
        
        assertEquals(statusCode, 200, "PUT request should return 200");
    }

    @Test(groups = {"regression", "api"})
    public void testDeleteRequest() {
        String endpoint = "/api/users/1";
        
        int statusCode = sendDeleteRequest(endpoint);
        
        assertEquals(statusCode, 204, "DELETE request should return 204");
    }

    @Test(groups = {"regression", "api"}, enabled = false)
    public void testPatchRequest() {
        // Disabled test for PATCH endpoint
        fail("PATCH endpoint not implemented yet");
    }

    @Test(groups = {"api"}, expectedExceptions = IllegalArgumentException.class)
    public void testInvalidEndpoint() {
        String endpoint = null;
        sendGetRequest(endpoint);
    }

    @Test(groups = {"api", "timeout"}, timeOut = 5000)
    public void testRequestTimeout() {
        String endpoint = "/api/slow-endpoint";
        int statusCode = sendGetRequest(endpoint);
        
        assertTrue(statusCode > 0, "Request should complete within timeout");
    }

    @AfterMethod
    public void tearDownMethod() {
        System.out.println("Cleaning up test method...");
    }

    @AfterClass
    public void tearDownClass() {
        System.out.println("Cleaning up ApiTest class...");
    }

    @AfterSuite
    public void tearDownSuite() {
        System.out.println("Cleaning up test suite...");
    }

    // Helper methods
    private int sendGetRequest(String endpoint) {
        if (endpoint == null) {
            throw new IllegalArgumentException("Endpoint cannot be null");
        }
        return 200;
    }

    private int sendPostRequest(String endpoint, String payload) {
        return 201;
    }

    private int sendPutRequest(String endpoint, String payload) {
        return 200;
    }

    private int sendDeleteRequest(String endpoint) {
        return 204;
    }
}
