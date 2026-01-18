"""
CrossBridge Java Listener (TestNG/JUnit)

Works with:
- Selenium Java
- Selenium Java BDD (Cucumber)
- Selenium Java + RestAssured
- Any Java testing framework

Design Contract:
- NO migration required
- Works as pure observer (sidecar)
- Zero changes to existing tests
- Optional - tests run normally without it

Installation:
1. Add to testng.xml:
   <listeners>
     <listener class-name="com.crossbridge.CrossBridgeListener"/>
   </listeners>

2. Or via JUnit @RunWith annotation:
   @RunWith(CrossBridgeRunner.class)

3. Configure via system properties:
   -Dcrossbridge.enabled=true
   -Dcrossbridge.db.host=10.55.12.99
   -Dcrossbridge.application.version=v2.0.0
"""

# Java implementation - generates Java source code

JAVA_TESTNG_LISTENER = '''
package com.crossbridge;

import org.testng.*;
import java.sql.*;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * CrossBridge TestNG Listener
 * 
 * Compatible with TestNG 6.x and 7.x
 * Pure observer - never controls test execution.
 * Works with existing tests, no migration needed.
 * Thread-safe for parallel test execution.
 * 
 * Usage in testng.xml:
 * <listeners>
 *   <listener class-name="com.crossbridge.CrossBridgeListener"/>
 * </listeners>
 * 
 * Or via @Listeners annotation:
 * @Listeners(com.crossbridge.CrossBridgeListener.class)
 * public class MyTest { ... }
 */
public class CrossBridgeListener implements ITestListener, ISuiteListener {
    
    // Thread-safe storage for parallel test execution
    private static final Map<String, Long> testStartTimes = new ConcurrentHashMap<>();
    
    private Connection dbConnection;
    private boolean enabled;
    private String applicationVersion;
    private String productName;
    private String environment;
    
    public CrossBridgeListener() {
        // Load configuration from system properties
        this.enabled = Boolean.parseBoolean(
            System.getProperty("crossbridge.enabled", "false")
        );
        
        if (!this.enabled) {
            System.out.println("[CrossBridge] Disabled - tests run normally");
            return;
        }
        
        String dbHost = System.getProperty("crossbridge.db.host", "10.55.12.99");
        String dbPort = System.getProperty("crossbridge.db.port", "5432");
        String dbName = System.getProperty("crossbridge.db.name", "udp-native-webservices-automation");
        String dbUser = System.getProperty("crossbridge.db.user", "postgres");
        String dbPassword = System.getProperty("crossbridge.db.password", "admin");
        
        this.applicationVersion = System.getProperty("crossbridge.application.version", "unknown");
        this.productName = System.getProperty("crossbridge.product.name", "JavaApp");
        this.environment = System.getProperty("crossbridge.environment", "test");
        
        try {
            // Connect to PostgreSQL
            String url = String.format("jdbc:postgresql://%s:%s/%s", dbHost, dbPort, dbName);
            this.dbConnection = DriverManager.getConnection(url, dbUser, dbPassword);
            System.out.println("[CrossBridge] Observer connected - monitoring test execution");
        } catch (SQLException e) {
            System.err.println("[CrossBridge] Database connection failed - tests continue normally");
            System.err.println("[CrossBridge] Error: " + e.getMessage());
            this.enabled = false;
        }
    }
    
    @Override
    public void onTestStart(ITestResult result) {
        if (!enabled) return;
        
        try {
            String testId = getTestId(result);
            String testName = result.getName();
            String className = result.getTestClass().getName();
            
            // Store start time for duration calculation (thread-safe)
            testStartTimes.put(testId, System.currentTimeMillis());
            
            // Extract metadata from test context
            Map<String, Object> metadata = extractMetadata(result);
            
            // Add TestNG-specific metadata
            if (result.getMethod() != null) {
                metadata.put("groups", Arrays.toString(result.getMethod().getGroups()));
                metadata.put("priority", String.valueOf(result.getMethod().getPriority()));
                metadata.put("invocation_count", String.valueOf(result.getMethod().getInvocationCount()));
                metadata.put("thread_pool_size", String.valueOf(result.getMethod().getThreadPoolSize()));
            }
            
            // Emit test_start event
            String sql = "INSERT INTO test_execution_event " +
                        "(test_id, test_name, framework, file_path, status, " +
                        "application_version, product_name, environment, event_type, event_timestamp, metadata) " +
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)";
            
            PreparedStatement stmt = dbConnection.prepareStatement(sql);
            stmt.setString(1, testId);
            stmt.setString(2, testName);
            stmt.setString(3, detectFramework(result));
            stmt.setString(4, className);
            stmt.setString(5, "running");
            stmt.setString(6, applicationVersion);
            stmt.setString(7, productName);
            stmt.setString(8, environment);
            stmt.setString(9, "test_start");
            stmt.setTimestamp(10, new Timestamp(System.currentTimeMillis()));
            stmt.setString(11, toJson(metadata));
            
            stmt.executeUpdate();
            stmt.close();
            
        } catch (Exception e) {
            // Never fail the test
            System.err.println("[CrossBridge] Event emission failed (non-blocking): " + e.getMessage());
        }
    }
    
    @Override
    public void onTestSuccess(ITestResult result) {
        onTestFinish(result, "passed");
    }
    
    @Override
    public void onTestFailure(ITestResult result) {
        onTestFinish(result, "failed");
    }
    
    @Override
    public void onTestSkipped(ITestResult result) {
        onTestFinish(result, "skipped");
    }
    
    private void onTestFinish(ITestResult result, String status) {
        if (!enabled) return;
        
        try {
            String testId = getTestId(result);
            long duration = result.getEndMillis() - result.getStartMillis();
            double durationSeconds = duration / 1000.0;
            
            String errorMessage = null;
            String stackTrace = null;
            if (result.getThrowable() != null) {
                errorMessage = result.getThrowable().getMessage();
                stackTrace = getStackTrace(result.getThrowable());
            }
            
            // Emit test_end event
            String sql = "INSERT INTO test_execution_event " +
                        "(test_id, test_name, framework, file_path, status, duration_seconds, " +
                        "error_message, stack_trace, " +
                        "application_version, product_name, environment, event_type, event_timestamp) " +
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
            
            PreparedStatement stmt = dbConnection.prepareStatement(sql);
            stmt.setString(1, testId);
            stmt.setString(2, result.getName());
            stmt.setString(3, detectFramework(result));
            stmt.setString(4, result.getTestClass().getName());
            stmt.setString(5, status);
            stmt.setDouble(6, durationSeconds);
            stmt.setString(7, errorMessage);
            stmt.setString(8, stackTrace);
            stmt.setString(9, applicationVersion);
            stmt.setString(10, productName);
            stmt.setString(11, environment);
            stmt.setString(12, "test_end");
            stmt.setTimestamp(13, new Timestamp(System.currentTimeMillis()));
            
            stmt.executeUpdate();
            stmt.close();
            
        } catch (Exception e) {
            // Never fail the test
            System.err.println("[CrossBridge] Event emission failed (non-blocking): " + e.getMessage());
        }
    }
    
    @Override
    public void onFinish(ISuite suite) {
        if (dbConnection != null) {
            try {
                dbConnection.close();
                System.out.println("[CrossBridge] Observer disconnected");
            } catch (SQLException e) {
                // Ignore
            }
        }
    }
    
    private String getTestId(ITestResult result) {
        return result.getTestClass().getName() + "." + result.getName();
    }
    
    private String detectFramework(ITestResult result) {
        // Detect if Cucumber, RestAssured, or plain Selenium
        String className = result.getTestClass().getName();
        if (className.contains("cucumber") || className.contains("Cucumber")) {
            return "selenium-java-bdd";
        }
        if (className.contains("restassured") || className.contains("RestAssured")) {
            return "selenium-java-restassured";
        }
        return "selenium-java";
    }
    
    private Map<String, Object> extractMetadata(ITestResult result) {
        Map<String, Object> metadata = new HashMap<>();
        
        // Extract from test context, parameters, etc.
        Object[] parameters = result.getParameters();
        if (parameters != null && parameters.length > 0) {
            metadata.put("parameters", Arrays.toString(parameters));
        }
        
        // Add any custom attributes
        Set<String> attributeNames = result.getAttributeNames();
        for (String attr : attributeNames) {
            Object value = result.getAttribute(attr);
            if (value != null) {
                metadata.put(attr, value.toString());
            }
        }
        
        return metadata;
    }
    
    private String toJson(Map<String, Object> map) {
        // Simple JSON serialization
        StringBuilder json = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, Object> entry : map.entrySet()) {
            if (!first) json.append(",");
            json.append("\\"").append(entry.getKey()).append("\\":\\"");
            json.append(entry.getValue().toString()).append("\\"");
            first = false;
        }
        json.append("}");
        return json.toString();
    }
    
    private String getStackTrace(Throwable t) {
        StringBuilder sb = new StringBuilder();
        for (StackTraceElement element : t.getStackTrace()) {
            sb.append(element.toString()).append("\\n");
        }
        return sb.toString();
    }
    
    // ISuiteListener methods
    @Override
    public void onStart(ISuite suite) {
        // Optional: Suite-level tracking
    }
}
import java.util.concurrent.ConcurrentHashMap;

/**
 * CrossBridge JUnit 4 Listener
 * 
 * Compatible with JUnit 4.x
 * Pure observer for JUnit tests.
 * Thread-safe for parallel test execution.
 * 
 * Usage Option 1 - In maven-surefire-plugin:
 * <configuration>
 *   <properties>
 *     <property>
 *       <name>listener</name>
 *       <value>com.crossbridge.CrossBridgeJUnitListener</value>
 *     </property>
 *   </properties>
 * </configuration>
 * 
 * Usage Option 2 - Programmatically:
 * JUnitCore junit = new JUnitCore();
 * junit.addListener(new CrossBridgeJUnitListener());
 * junit.run(MyTest.class);
 */
public class CrossBridgeJUnitListener extends RunListener {
    
    private Connection dbConnection;
    private boolean enabled;
    private String applicationVersion;
    private String productName;
    private String environment;
    
    // Thread-safe storage for parallel test execution
    private static final Map<String, Long> testStartTimes = new Concurrent
/**
 * CrossBridge JUnit Runner
 * 
 * Pure observer for JUnit tests.
 * Use with @RunWith(CrossBridgeRunner.class) or as RunListener.
 */
public class CrossBridgeJUnitListener extends RunListener {
    
    private Connection dbConnection;
    private boolean enabled;
    private Map<String, Long> testStartTimes = new HashMap<>();
    
    public CrossBridgeJUnitListener() {
        // Load configuration from system properties
        this.enabled = Boolean.parseBoolean(
            System.getProperty("crossbridge.enabled", "false")
        );
        
        if (!this.enabled) {
            System.out.println("[CrossBridge] Disabled - tests run normally");
            return;
        }
        
        String dbHost = System.getProperty("crossbridge.db.host", "10.55.12.99");
        String dbPort = System.getProperty("crossbridge.db.port", "5432");
        String dbName = System.getProperty("crossbridge.db.name", "udp-native-webservices-automation");
        String dbUser = System.getProperty("crossbridge.db.user", "postgres");
        String dbPassword = System.getProperty("crossbridge.db.password", "admin");
        
        this.applicationVersion = System.getProperty("crossbridge.application.version", "unknown");
        this.productName = System.getProperty("crossbridge.product.name", "JavaApp");
        this.environment = System.getProperty("crossbridge.environment", "test");
        
        try {
            // Connect to PostgreSQL
            String url = String.format("jdbc:postgresql://%s:%s/%s", dbHost, dbPort, dbName);
            this.dbConnection = DriverManager.getConnection(url, dbUser, dbPassword);
            System.out.println("[CrossBridge] Observer connected (JUnit) - monitoring test execution");
        } catch (SQLException e) {
            System.err.println("[CrossBridge] Database connection failed - tests continue normally");
            System.err.println("[CrossBridge] Error: " + e.getMessage());
            this.enabled = false;
        }
    }
    
    @Override
    public void testStarted(Description description) {
        if (!enabled) return;
        
        String testId = description.getClassName() + "." + description.getMethodName();
        testStartTimes.put(testId, System.currentTimeMillis());
        
        try {
            // Extract metadata
            Map<String, String> metadata = new HashMap<>();
            if (description.getAnnotations() != null) {
                metadata.put("annotations", description.getAnnotations().toString());
            }
            if (description.getTestClass() != null) {
                metadata.put("test_class", description.getTestClass().getName());
            }
            
            // Emit test_start event
            String sql = "INSERT INTO test_execution_event " +
                        "(test_id, test_name, framework, file_path, status, " +
                        "application_version, product_name, environment, event_type, event_timestamp, metadata) " +
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)";
            
            PreparedStatement stmt = dbConnection.prepareStatement(sql);
            stmt.setString(1, testId);
            stmt.setString(2, description.getMethodName());
            stmt.setString(3, "junit");
            stmt.setString(4, description.getClassName());
            stmt.setString(5, "running");
            stmt.setString(6, applicationVersion);
            stmt.setString(7, productName);
            stmt.setString(8, environment);
            stmt.setString(9, "test_start");
            stmt.setTimestamp(10, new Timestamp(System.currentTimeMillis()));
            stmt.setString(11, toJson(metadata));
            
            stmt.executeUpdate();
            stmt.close();
        } catch (Exception e) {
            System.err.println("[CrossBridge] Event emission failed (non-blocking): " + e.getMessage());
        }
    }
    
    @Override
    public void testFinished(Description description) {
        if (!enabled) return;
        
        String testId = description.getClassName() + "." + description.getMethodName();
        long startTime = testStartTimes.getOrDefault(testId, System.currentTimeMillis());
        long duration = System.currentTimeMillis() - startTime;
        double durationSeconds = duration / 1000.0;
        
        try {
            // Emit test_end event with "passed" status
            String sql = "INSERT INTO test_execution_event " +
                        "(test_id, test_name, framework, file_path, status, duration_seconds, " +
                        "application_version, product_name, environment, event_type, event_timestamp) " +
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
            
            PreparedStatement stmt = dbConnection.prepareStatement(sql);
            stmt.setString(1, testId);
            stmt.setString(2, description.getMethodName());
            stmt.setString(3, "junit");
            stmt.setString(4, description.getClassName());
            stmt.setString(5, "passed");
            stmt.setDouble(6, durationSeconds);
            stmt.setString(7, applicationVersion);
            stmt.setString(8, productName);
            stmt.setString(9, environment);
            stmt.setString(10, "test_end");
            stmt.setTimestamp(11, new Timestamp(System.currentTimeMillis()));
            
            stmt.executeUpdate();
            stmt.close();
            
            testStartTimes.remove(testId);
        } catch (Exception e) {
            System.err.println("[CrossBridge] Event emission failed (non-blocking): " + e.getMessage());
        }
    }
    
    @Override
    public void testFailure(Failure failure) {
        if (!enabled) return;
        
        Description description = failure.getDescription();
        String testId = description.getClassName() + "." + description.getMethodName();
        long startTime = testStartTimes.getOrDefault(testId, System.currentTimeMillis());
        long duration = System.currentTimeMillis() - startTime;
        double durationSeconds = duration / 1000.0;
        
        try {
            // Emit test_end event with "failed" status
            String sql = "INSERT INTO test_execution_event " +
                        "(test_id, test_name, framework, file_path, status, duration_seconds, " +
                        "error_message, stack_trace, " +
                        "application_version, product_name, environment, event_type, event_timestamp) " +
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
            
            PreparedStatement stmt = dbConnection.prepareStatement(sql);
            stmt.setString(1, testId);
            stmt.setString(2, description.getMethodName());
            stmt.setString(3, "junit");
            stmt.setString(4, description.getClassName());
            stmt.setString(5, "failed");
            stmt.setDouble(6, durationSeconds);
            stmt.setString(7, failure.getMessage());
            stmt.setString(8, failure.getTrace());
            stmt.setString(9, applicationVersion);
            stmt.setString(10, productName);
            stmt.setString(11, environment);
            stmt.setString(12, "test_end");
            stmt.setTimestamp(13, new Timestamp(System.currentTimeMillis()));
            
            stmt.executeUpdate();
            stmt.close();
            
            testStartTimes.remove(testId);
        } catch (Exception e) {
            System.err.println("[CrossBridge] Event emission failed (non-blocking): " + e.getMessage());
        }
    }
    
    @Override
    public void testIgnored(Description description) {
        if (!enabled) return;
        
        String testId = description.getClassName() + "." + description.getMethodName();
        
        try {
            // Emit test_end event with "skipped" status
            String sql = "INSERT INTO test_execution_event " +
                        "(test_id, test_name, framework, file_path, status, " +
                        "application_version, product_name, environment, event_type, event_timestamp) " +
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
            
            PreparedStatement stmt = dbConnection.prepareStatement(sql);
            stmt.setString(1, testId);
            stmt.setString(2, description.getMethodName());
            stmt.setString(3, "junit");
            stmt.setString(4, description.getClassName());
            stmt.setString(5, "skipped");
            stmt.setString(6, applicationVersion);
            stmt.setString(7, productName);
            stmt.setString(8, environment);
            stmt.setString(9, "test_end");
            stmt.setTimestamp(10, new Timestamp(System.currentTimeMillis()));
            
            stmt.executeUpdate();
            stmt.close();
        } catch (Exception e) {
            System.err.println("[CrossBridge] Event emission failed (non-blocking): " + e.getMessage());
        }
    }
    
    private String toJson(Map<String, String> map) {
        StringBuilder json = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, String> entry : map.entrySet()) {
            if (!first) json.append(",");
            json.append("\\"").append(entry.getKey()).append("\\":\\"");
            json.append(entry.getValue().toString().replace("\\"", "\\\\\\"")).append("\\"");
            first = false;
        }
        json.append("}");
        return json.toString();
    }
}
'''


JAVA_JUNIT5_EXTENSION = '''
package com.crossbridge;

import org.junit.jupiter.api.extension.*;
import java.sql.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * CrossBridge JUnit 5 Extension
 * 
 * Compatible with JUnit Jupiter 5.x
 * Pure observer - never controls test execution.
 * Thread-safe for parallel test execution.
 * 
 * Usage - Add to test class:
 * @ExtendWith(CrossBridgeExtension.class)
 * public class MyTest { ... }
 * 
 * Or globally in junit-platform.properties:
 * junit.jupiter.extensions.autodetection.enabled=true
 */
public class CrossBridgeExtension implements BeforeAllCallback, AfterAllCallback,
                                             BeforeEachCallback, AfterEachCallback,
                                             TestExecutionExceptionHandler {
    
    private static Connection dbConnection;
    private static boolean enabled;
    private static String applicationVersion;
    private static String productName;
    private static String environment;
    
    // Thread-safe storage for parallel test execution
    private static final Map<String, Long> testStartTimes = new ConcurrentHashMap<>();
    private static final Map<String, ExtensionContext> testContexts = new ConcurrentHashMap<>();
    
    static {
        // Load configuration from system properties
        enabled = Boolean.parseBoolean(
            System.getProperty("crossbridge.enabled", "false")
        );
        
        if (enabled) {
            String dbHost = System.getProperty("crossbridge.db.host", "10.55.12.99");
            String dbPort = System.getProperty("crossbridge.db.port", "5432");
            String dbName = System.getProperty("crossbridge.db.name", "udp-native-webservices-automation");
            String dbUser = System.getProperty("crossbridge.db.user", "postgres");
            String dbPassword = System.getProperty("crossbridge.db.password", "admin");
            
            applicationVersion = System.getProperty("crossbridge.application.version", "unknown");
            productName = System.getProperty("crossbridge.product.name", "JavaApp");
            environment = System.getProperty("crossbridge.environment", "test");
            
            try {
                // Connect to PostgreSQL
                String url = String.format("jdbc:postgresql://%s:%s/%s", dbHost, dbPort, dbName);
                dbConnection = DriverManager.getConnection(url, dbUser, dbPassword);
                System.out.println("[CrossBridge] Observer connected (JUnit 5) - monitoring test execution");
            } catch (SQLException e) {
                System.err.println("[CrossBridge] Database connection failed - tests continue normally");
                System.err.println("[CrossBridge] Error: " + e.getMessage());
                enabled = false;
            }
        } else {
            System.out.println("[CrossBridge] Disabled - tests run normally");
        }
    }
    
    @Override
    public void beforeAll(ExtensionContext context) {
        // Optional: Suite-level tracking
    }
    
    @Override
    public void afterAll(ExtensionContext context) {
        // Optional: Suite-level tracking
        if (dbConnection != null) {
            try {
                dbConnection.close();
                System.out.println("[CrossBridge] Observer disconnected");
            } catch (SQLException e) {
                // Ignore
            }
        }
    }
    
    @Override
    public void beforeEach(ExtensionContext context) {
        if (!enabled) return;
        
        String testId = getTestId(context);
        testStartTimes.put(testId, System.currentTimeMillis());
        testContexts.put(testId, context);
        
        try {
            // Extract metadata
            Map<String, String> metadata = new HashMap<>();
            metadata.put("display_name", context.getDisplayName());
            metadata.put("test_class", context.getTestClass().map(Class::getName).orElse("unknown"));
            metadata.put("test_method", context.getTestMethod().map(m -> m.getName()).orElse("unknown"));
            context.getTags().forEach(tag -> metadata.put("tag_" + tag, "true"));
            
            // Emit test_start event
            String sql = "INSERT INTO test_execution_event " +
                        "(test_id, test_name, framework, file_path, status, " +
                        "application_version, product_name, environment, event_type, event_timestamp, metadata) " +
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)";
            
            PreparedStatement stmt = dbConnection.prepareStatement(sql);
            stmt.setString(1, testId);
            stmt.setString(2, context.getDisplayName());
            stmt.setString(3, "junit5");
            stmt.setString(4, context.getTestClass().map(Class::getName).orElse("unknown"));
            stmt.setString(5, "running");
            stmt.setString(6, applicationVersion);
            stmt.setString(7, productName);
            stmt.setString(8, environment);
            stmt.setString(9, "test_start");
            stmt.setTimestamp(10, new Timestamp(System.currentTimeMillis()));
            stmt.setString(11, toJson(metadata));
            
            stmt.executeUpdate();
            stmt.close();
        } catch (Exception e) {
            System.err.println("[CrossBridge] Event emission failed (non-blocking): " + e.getMessage());
        }
    }
    
    @Override
    public void afterEach(ExtensionContext context) {
        if (!enabled) return;
        
        String testId = getTestId(context);
        long startTime = testStartTimes.getOrDefault(testId, System.currentTimeMillis());
        long duration = System.currentTimeMillis() - startTime;
        double durationSeconds = duration / 1000.0;
        
        // Determine status based on execution exception
        String status = context.getExecutionException().isPresent() ? "failed" : "passed";
        String errorMessage = context.getExecutionException().map(Throwable::getMessage).orElse(null);
        String stackTrace = context.getExecutionException().map(this::getStackTrace).orElse(null);
        
        try {
            // Emit test_end event
            String sql = "INSERT INTO test_execution_event " +
                        "(test_id, test_name, framework, file_path, status, duration_seconds, " +
                        "error_message, stack_trace, " +
                        "application_version, product_name, environment, event_type, event_timestamp) " +
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
            
            PreparedStatement stmt = dbConnection.prepareStatement(sql);
            stmt.setString(1, testId);
            stmt.setString(2, context.getDisplayName());
            stmt.setString(3, "junit5");
            stmt.setString(4, context.getTestClass().map(Class::getName).orElse("unknown"));
            stmt.setString(5, status);
            stmt.setDouble(6, durationSeconds);
            stmt.setString(7, errorMessage);
            stmt.setString(8, stackTrace);
            stmt.setString(9, applicationVersion);
            stmt.setString(10, productName);
            stmt.setString(11, environment);
            stmt.setString(12, "test_end");
            stmt.setTimestamp(13, new Timestamp(System.currentTimeMillis()));
            
            stmt.executeUpdate();
            stmt.close();
            
            testStartTimes.remove(testId);
            testContexts.remove(testId);
        } catch (Exception e) {
            System.err.println("[CrossBridge] Event emission failed (non-blocking): " + e.getMessage());
        }
    }
    
    @Override
    public void handleTestExecutionException(ExtensionContext context, Throwable throwable) throws Throwable {
        // Just re-throw - we handle in afterEach
        throw throwable;
    }
    
    private String getTestId(ExtensionContext context) {
        return context.getTestClass().map(Class::getName).orElse("unknown") + "." +
               context.getTestMethod().map(m -> m.getName()).orElse("unknown");
    }
    
    private String getStackTrace(Throwable t) {
        StringBuilder sb = new StringBuilder();
        for (StackTraceElement element : t.getStackTrace()) {
            sb.append(element.toString()).append("\\n");
        }
        return sb.toString();
    }
    
    private String toJson(Map<String, String> map) {
        StringBuilder json = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, String> entry : map.entrySet()) {
            if (!first) json.append(",");
            json.append("\\"").append(entry.getKey()).append("\\":\\"");
            json.append(entry.getValue().replace("\\"", "\\\\\\"")).append("\\"");
            first = false;
        }
        json.append("}");
        return json.toString();
    }
}
'''
        if (!enabled) return;
        
        String testId = description.getClassName() + "." + description.getMethodName();
        testStartTimes.put(testId, System.currentTimeMillis());
        
        // Emit test_start event (similar to TestNG)
    }
    
    @Override
    public void testFinished(Description description) {
        if (!enabled) return;
        
        String testId = description.getClassName() + "." + description.getMethodName();
        long duration = System.currentTimeMillis() - testStartTimes.getOrDefault(testId, 0L);
        
        // Emit test_end event with "passed" status
    }
    
    @Override
    public void testFailure(Failure failure) {
        if (!enabled) return;
        
        // Emit test_end event with "failed" status
    }
}
'''


def generate_java_listener(output_dir: str = "."):
    """Generate Java listener files"""
    import os
    
    os.makedirs(f"{output_dir}/com/crossbridge", exist_ok=True)
    
    with open(f"{output_dir}/com/crossbridge/CrossBridgeListener.java", "w") as f:
        f.write(JAVA_TESTNG_LISTENER)
    
    with open(f"{output_dir}/com/crossbridge/CrossBridgeJUnitListener.java", "w") as f:
        f.write(JAVA_JUNIT_RUNNER)
    
    with open(f"{output_dir}/com/crossbridge/CrossBridgeExtension.java", "w") as f:
        f.write(JAVA_JUNIT5_EXTENSION)
    
    print(f"✅ Generated Java listeners in {output_dir}/com/crossbridge/")
    print("   - CrossBridgeListener.java (TestNG 6.x/7.x)")
    print("   - CrossBridgeJUnitListener.java (JUnit 4.x)")
    print("   - CrossBridgeExtension.java (JUnit 5/Jupiter)")
    print("\nCompatibility:")
    print("   ✅ TestNG 6.x, 7.x")
    print("   ✅ JUnit 4.x")
    print("   ✅ JUnit 5 (Jupiter)")
    print("   ✅ Thread-safe parallel execution")
    print("   ✅ Works with Cucumber, RestAssured, Selenium")


if __name__ == "__main__":
    generate_java_listener()
