package com.crossbridge.cucumber;

import io.cucumber.plugin.ConcurrentEventListener;
import io.cucumber.plugin.event.*;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * CrossBridge Cucumber Plugin for remote sidecar integration
 * 
 * Usage in cucumber.properties:
 * cucumber.plugin=com.crossbridge.cucumber.CrossBridgeCucumberPlugin
 * 
 * Or via command line:
 * mvn test -Dcucumber.plugin="com.crossbridge.cucumber.CrossBridgeCucumberPlugin"
 * 
 * Environment Variables:
 * - CROSSBRIDGE_ENABLED: Set to "true" to enable
 * - CROSSBRIDGE_SIDECAR_HOST: Sidecar server hostname (default: localhost)
 * - CROSSBRIDGE_SIDECAR_PORT: Sidecar server port (default: 8765)
 */
public class CrossBridgeCucumberPlugin implements ConcurrentEventListener {
    
    private boolean enabled;
    private String apiHost;
    private int apiPort;
    private String eventsUrl;
    private static final int TIMEOUT_MS = 2000;
    
    public CrossBridgeCucumberPlugin() {
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
                    System.out.println(String.format("✅ CrossBridge Cucumber plugin connected to %s:%d", apiHost, apiPort));
                } else {
                    this.enabled = false;
                }
                conn.disconnect();
            } catch (Exception e) {
                System.out.println("⚠️ CrossBridge Cucumber plugin failed to connect: " + e.getMessage());
                this.enabled = false;
            }
        }
    }
    
    @Override
    public void setEventPublisher(EventPublisher publisher) {
        publisher.registerHandlerFor(TestRunStarted.class, this::handleTestRunStarted);
        publisher.registerHandlerFor(TestRunFinished.class, this::handleTestRunFinished);
        publisher.registerHandlerFor(TestCaseStarted.class, this::handleTestCaseStarted);
        publisher.registerHandlerFor(TestCaseFinished.class, this::handleTestCaseFinished);
        publisher.registerHandlerFor(TestStepStarted.class, this::handleTestStepStarted);
        publisher.registerHandlerFor(TestStepFinished.class, this::handleTestStepFinished);
    }
    
    private void handleTestRunStarted(TestRunStarted event) {
        Map<String, Object> data = new HashMap<>();
        data.put("timestamp", event.getInstant().toString());
        sendEvent("run_start", data);
    }
    
    private void handleTestRunFinished(TestRunFinished event) {
        Map<String, Object> data = new HashMap<>();
        data.put("timestamp", event.getInstant().toString());
        sendEvent("run_end", data);
    }
    
    private void handleTestCaseStarted(TestCaseStarted event) {
        TestCase testCase = event.getTestCase();
        Map<String, Object> data = new HashMap<>();
        data.put("test_name", testCase.getName());
        data.put("feature", testCase.getUri().toString());
        data.put("line", testCase.getLocation().getLine());
        data.put("tags", testCase.getTags().toString());
        sendEvent("test_start", data);
    }
    
    private void handleTestCaseFinished(TestCaseFinished event) {
        TestCase testCase = event.getTestCase();
        Result result = event.getResult();
        
        Map<String, Object> data = new HashMap<>();
        data.put("test_name", testCase.getName());
        data.put("status", result.getStatus().toString());
        data.put("duration_ms", result.getDuration().toMillis());
        
        if (result.getError() != null) {
            data.put("error_message", result.getError().getMessage());
        }
        
        sendEvent("test_end", data);
    }
    
    private void handleTestStepStarted(TestStepStarted event) {
        TestStep testStep = event.getTestStep();
        if (testStep instanceof PickleStepTestStep) {
            PickleStepTestStep pickleStep = (PickleStepTestStep) testStep;
            Map<String, Object> data = new HashMap<>();
            data.put("step_text", pickleStep.getStep().getText());
            data.put("step_keyword", pickleStep.getStep().getKeyword());
            sendEvent("step_start", data);
        }
    }
    
    private void handleTestStepFinished(TestStepFinished event) {
        TestStep testStep = event.getTestStep();
        Result result = event.getResult();
        
        if (testStep instanceof PickleStepTestStep) {
            PickleStepTestStep pickleStep = (PickleStepTestStep) testStep;
            Map<String, Object> data = new HashMap<>();
            data.put("step_text", pickleStep.getStep().getText());
            data.put("status", result.getStatus().toString());
            data.put("duration_ms", result.getDuration().toMillis());
            sendEvent("step_end", data);
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
            event.put("framework", "cucumber");
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
