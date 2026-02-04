package com.crossbridge.restassured;

import io.restassured.filter.Filter;
import io.restassured.filter.FilterContext;
import io.restassured.response.Response;
import io.restassured.specification.FilterableRequestSpecification;
import io.restassured.specification.FilterableResponseSpecification;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * CrossBridge Rest Assured Filter for remote sidecar integration
 * 
 * Usage:
 * import static io.restassured.RestAssured.*;
 * 
 * given()
 *   .filter(new CrossBridgeRestAssuredFilter())
 *   .when()
 *   .get("/api/endpoint")
 *   .then()
 *   .statusCode(200);
 * 
 * Or globally:
 * RestAssured.filters(new CrossBridgeRestAssuredFilter());
 * 
 * Environment Variables:
 * - CROSSBRIDGE_ENABLED: Set to "true" to enable
 * - CROSSBRIDGE_SIDECAR_HOST: Sidecar server hostname (default: localhost)
 * - CROSSBRIDGE_SIDECAR_PORT: Sidecar server port (default: 8765)
 */
public class CrossBridgeRestAssuredFilter implements Filter {
    
    private static boolean enabled;
    private static String apiHost;
    private static int apiPort;
    private static String eventsUrl;
    private static final int TIMEOUT_MS = 2000;
    
    static {
        enabled = "true".equalsIgnoreCase(System.getenv("CROSSBRIDGE_ENABLED"));
        
        if (enabled) {
            apiHost = System.getenv().getOrDefault("CROSSBRIDGE_SIDECAR_HOST", 
                                                   System.getenv().getOrDefault("CROSSBRIDGE_API_HOST", "localhost"));
            apiPort = Integer.parseInt(System.getenv().getOrDefault("CROSSBRIDGE_SIDECAR_PORT",
                                                                    System.getenv().getOrDefault("CROSSBRIDGE_API_PORT", "8765")));
            eventsUrl = String.format("http://%s:%d/events", apiHost, apiPort);
            
            // Check health
            try {
                URL healthUrl = new URL(String.format("http://%s:%d/health", apiHost, apiPort));
                HttpURLConnection conn = (HttpURLConnection) healthUrl.openConnection();
                conn.setConnectTimeout(TIMEOUT_MS);
                conn.setReadTimeout(TIMEOUT_MS);
                conn.setRequestMethod("GET");
                
                int responseCode = conn.getResponseCode();
                if (responseCode == 200) {
                    System.out.println(String.format("✅ CrossBridge Rest Assured filter connected to %s:%d", apiHost, apiPort));
                } else {
                    enabled = false;
                }
                conn.disconnect();
            } catch (Exception e) {
                System.out.println("⚠️ CrossBridge Rest Assured filter failed to connect: " + e.getMessage());
                enabled = false;
            }
        }
    }
    
    @Override
    public Response filter(FilterableRequestSpecification requestSpec, 
                          FilterableResponseSpecification responseSpec, 
                          FilterContext ctx) {
        long startTime = System.currentTimeMillis();
        
        // Send request start event
        sendEvent("request_start", createRequestData(requestSpec));
        
        // Execute request
        Response response = ctx.next(requestSpec, responseSpec);
        
        long endTime = System.currentTimeMillis();
        
        // Send request end event
        Map<String, Object> responseData = createResponseData(requestSpec, response, endTime - startTime);
        sendEvent("request_end", responseData);
        
        return response;
    }
    
    private Map<String, Object> createRequestData(FilterableRequestSpecification requestSpec) {
        Map<String, Object> data = new HashMap<>();
        data.put("method", requestSpec.getMethod());
        data.put("uri", requestSpec.getURI());
        data.put("headers", requestSpec.getHeaders().asList().toString());
        return data;
    }
    
    private Map<String, Object> createResponseData(FilterableRequestSpecification requestSpec, 
                                                    Response response, 
                                                    long durationMs) {
        Map<String, Object> data = new HashMap<>();
        data.put("method", requestSpec.getMethod());
        data.put("uri", requestSpec.getURI());
        data.put("status_code", response.getStatusCode());
        data.put("duration_ms", durationMs);
        data.put("success", response.getStatusCode() >= 200 && response.getStatusCode() < 300);
        return data;
    }
    
    private void sendEvent(String eventType, Map<String, Object> data) {
        if (!enabled) {
            return;
        }
        
        try {
            // Build event payload
            Map<String, Object> event = new HashMap<>();
            event.put("event_type", eventType);
            event.put("framework", "restassured");
            event.put("data", data);
            event.put("timestamp", java.time.Instant.now().toString());
            
            // Convert to JSON
            String jsonPayload = toJson(event);
            
            // Send HTTP POST
            URL url = new URL(eventsUrl);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(TIMEOUT_MS);
            conn.setReadTimeout(TIMEOUT_MS);
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);
            
            try (OutputStream os = conn.getOutputStream()) {
                byte[] input = jsonPayload.getBytes(StandardCharsets.UTF_8);
                os.write(input, 0, input.length);
            }
            
            conn.getResponseCode(); // Trigger request
            conn.disconnect();
            
        } catch (Exception e) {
            // Fail-open: never block test execution
        }
    }
    
    private String toJson(Map<String, Object> map) {
        StringBuilder json = new StringBuilder("{");
        boolean first = true;
        
        for (Map.Entry<String, Object> entry : map.entrySet()) {
            if (!first) json.append(",");
            first = false;
            
            json.append("\"").append(entry.getKey()).append("\":");
            Object value = entry.getValue();
            
            if (value instanceof String) {
                json.append("\"").append(((String) value).replace("\"", "\\\"")).append("\"");
            } else if (value instanceof Map) {
                json.append(toJson((Map<String, Object>) value));
            } else {
                json.append("\"").append(String.valueOf(value)).append("\"");
            }
        }
        
        json.append("}");
        return json.toString();
    }
}
