package com.crossbridge.sidecar;

import org.testng.ITestContext;
import org.testng.ITestListener;
import org.testng.ITestResult;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * CrossBridge TestNG Listener for remote sidecar integration
 * 
 * Usage in testng.xml:
 * <listeners>
 *   <listener class-name="com.crossbridge.sidecar.CrossBridgeTestNGListener"/>
 * </listeners>
 * 
 * Or via command line:
 * mvn test -Dlistener=com.crossbridge.sidecar.CrossBridgeTestNGListener
 * 
 * Environment Variables:
 * - CROSSBRIDGE_ENABLED: Set to "true" to enable
 * - CROSSBRIDGE_SIDECAR_HOST: Sidecar server hostname (default: localhost)
 * - CROSSBRIDGE_SIDECAR_PORT: Sidecar server port (default: 8765)
 */
public class CrossBridgeTestNGListener implements ITestListener {
    
    private boolean enabled;
    private String apiHost;
    private int apiPort;
    private String eventsUrl;
    private static final int TIMEOUT_MS = 2000;
    
    public CrossBridgeTestNGListener() {
        this.enabled = "true".equalsIgnoreCase(System.getenv("CROSSBRIDGE_ENABLED"));
        
        if (this.enabled) {
            this.apiHost = System.getenv().getOrDefault("CROSSBRIDGE_SIDECAR_HOST", 
                                                        System.getenv().getOrDefault("CROSSBRIDGE_API_HOST", "localhost"));
            this.apiPort = Integer.parseInt(System.getenv().getOrDefault("CROSSBRIDGE_SIDECAR_PORT",
                                                                         System.getenv().getOrDefault("CROSSBRIDGE_API_PORT", "8765")));
            this.eventsUrl = String.format("http://%s:%d/events", apiHost, apiPort);
            
            // Check health
            try {
                URL healthUrl = new URL(String.format("http://%s:%d/health", apiHost, apiPort));
                HttpURLConnection conn = (HttpURLConnection) healthUrl.openConnection();
                conn.setConnectTimeout(TIMEOUT_MS);
                conn.setReadTimeout(TIMEOUT_MS);
                conn.setRequestMethod("GET");
                
                int responseCode = conn.getResponseCode();
                if (responseCode == 200) {
                    System.out.println(String.format("✅ CrossBridge TestNG listener connected to %s:%d", apiHost, apiPort));
                } else {
                    this.enabled = false;
                }
                conn.disconnect();
            } catch (Exception e) {
                System.out.println("⚠️ CrossBridge TestNG listener failed to connect: " + e.getMessage());
                this.enabled = false;
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
            event.put("framework", "testng");
            event.put("data", data);
            event.put("timestamp", java.time.Instant.now().toString());
            
            // Convert to JSON (simple approach - consider using Jackson/Gson for production)
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
    public void onStart(ITestContext context) {
        Map<String, Object> data = new HashMap<>();
        data.put("suite_name", context.getName());
        data.put("output_directory", context.getOutputDirectory());
        sendEvent("suite_start", data);
    }
    
    @Override
    public void onFinish(ITestContext context) {
        Map<String, Object> data = new HashMap<>();
        data.put("suite_name", context.getName());
        data.put("passed", context.getPassedTests().size());
        data.put("failed", context.getFailedTests().size());
        data.put("skipped", context.getSkippedTests().size());
        data.put("elapsed_time_ms", context.getEndDate().getTime() - context.getStartDate().getTime());
        sendEvent("suite_end", data);
    }
    
    @Override
    public void onTestStart(ITestResult result) {
        Map<String, Object> data = new HashMap<>();
        data.put("test_name", result.getName());
        data.put("test_class", result.getTestClass().getName());
        data.put("method_name", result.getMethod().getMethodName());
        sendEvent("test_start", data);
    }
    
    @Override
    public void onTestSuccess(ITestResult result) {
        Map<String, Object> data = new HashMap<>();
        data.put("test_name", result.getName());
        data.put("test_class", result.getTestClass().getName());
        data.put("status", "PASS");
        data.put("elapsed_time_ms", result.getEndMillis() - result.getStartMillis());
        sendEvent("test_end", data);
    }
    
    @Override
    public void onTestFailure(ITestResult result) {
        Map<String, Object> data = new HashMap<>();
        data.put("test_name", result.getName());
        data.put("test_class", result.getTestClass().getName());
        data.put("status", "FAIL");
        data.put("message", result.getThrowable() != null ? result.getThrowable().getMessage() : "");
        data.put("elapsed_time_ms", result.getEndMillis() - result.getStartMillis());
        sendEvent("test_end", data);
    }
    
    @Override
    public void onTestSkipped(ITestResult result) {
        Map<String, Object> data = new HashMap<>();
        data.put("test_name", result.getName());
        data.put("test_class", result.getTestClass().getName());
        data.put("status", "SKIP");
        sendEvent("test_end", data);
    }
    
    @Override
    public void onTestFailedButWithinSuccessPercentage(ITestResult result) {
        onTestSuccess(result);
    }
}
