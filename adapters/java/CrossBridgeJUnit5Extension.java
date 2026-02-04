package com.crossbridge.sidecar;

import org.junit.jupiter.api.extension.*;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * CrossBridge JUnit 5 Extension for remote sidecar integration
 * 
 * Usage:
 * Add to test class:
 * @ExtendWith(CrossBridgeJUnit5Extension.class)
 * public class MyTest { ... }
 * 
 * Or register globally in test resources:
 * META-INF/services/org.junit.jupiter.api.extension.Extension
 * 
 * Environment Variables:
 * - CROSSBRIDGE_ENABLED: Set to "true" to enable
 * - CROSSBRIDGE_SIDECAR_HOST: Sidecar server hostname (default: localhost)
 * - CROSSBRIDGE_SIDECAR_PORT: Sidecar server port (default: 8765)
 */
public class CrossBridgeJUnit5Extension implements 
        BeforeAllCallback, 
        AfterAllCallback,
        BeforeEachCallback,
        AfterEachCallback,
        TestWatcher {
    
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
                    System.out.println(String.format("✅ CrossBridge JUnit5 extension connected to %s:%d", apiHost, apiPort));
                } else {
                    enabled = false;
                }
                conn.disconnect();
            } catch (Exception e) {
                System.out.println("⚠️ CrossBridge JUnit5 extension failed to connect: " + e.getMessage());
                enabled = false;
            }
        }
    }
    
    private void sendEvent(String eventType, Map<String, Object> data) {
        if (!enabled) {
            return;
        }
        
        try {
            // Build event payload
            Map<String, Object> event = new HashMap<>();
            event.put("event_type", eventType);
            event.put("framework", "junit5");
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
    
    @Override
    public void beforeAll(ExtensionContext context) {
        Map<String, Object> data = new HashMap<>();
        data.put("test_class", context.getRequiredTestClass().getName());
        data.put("display_name", context.getDisplayName());
        sendEvent("class_start", data);
    }
    
    @Override
    public void afterAll(ExtensionContext context) {
        Map<String, Object> data = new HashMap<>();
        data.put("test_class", context.getRequiredTestClass().getName());
        sendEvent("class_end", data);
    }
    
    @Override
    public void beforeEach(ExtensionContext context) {
        Map<String, Object> data = new HashMap<>();
        data.put("test_name", context.getDisplayName());
        data.put("test_method", context.getRequiredTestMethod().getName());
        data.put("test_class", context.getRequiredTestClass().getName());
        sendEvent("test_start", data);
    }
    
    @Override
    public void afterEach(ExtensionContext context) {
        // Will be handled by TestWatcher methods
    }
    
    @Override
    public void testSuccessful(ExtensionContext context) {
        Map<String, Object> data = new HashMap<>();
        data.put("test_name", context.getDisplayName());
        data.put("test_method", context.getRequiredTestMethod().getName());
        data.put("test_class", context.getRequiredTestClass().getName());
        data.put("status", "PASS");
        sendEvent("test_end", data);
    }
    
    @Override
    public void testFailed(ExtensionContext context, Throwable cause) {
        Map<String, Object> data = new HashMap<>();
        data.put("test_name", context.getDisplayName());
        data.put("test_method", context.getRequiredTestMethod().getName());
        data.put("test_class", context.getRequiredTestClass().getName());
        data.put("status", "FAIL");
        data.put("message", cause.getMessage() != null ? cause.getMessage() : "");
        sendEvent("test_end", data);
    }
    
    @Override
    public void testAborted(ExtensionContext context, Throwable cause) {
        Map<String, Object> data = new HashMap<>();
        data.put("test_name", context.getDisplayName());
        data.put("test_method", context.getRequiredTestMethod().getName());
        data.put("test_class", context.getRequiredTestClass().getName());
        data.put("status", "SKIP");
        sendEvent("test_end", data);
    }
    
    @Override
    public void testDisabled(ExtensionContext context, java.util.Optional<String> reason) {
        Map<String, Object> data = new HashMap<>();
        data.put("test_name", context.getDisplayName());
        context.getTestMethod().ifPresent(method -> 
            data.put("test_method", method.getName())
        );
        data.put("test_class", context.getRequiredTestClass().getName());
        data.put("status", "DISABLED");
        reason.ifPresent(r -> data.put("reason", r));
        sendEvent("test_disabled", data);
    }
}
