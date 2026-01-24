"""
Java TestNG/JUnit Listener for Performance Profiling

Generates Java listener code for TestNG and JUnit integration.
"""

TESTNG_LISTENER_JAVA = """
package com.crossbridge.profiling;

import org.testng.*;
import java.sql.*;
import java.time.Instant;
import java.util.UUID;

/**
 * CrossBridge Performance Profiling Listener for TestNG
 * 
 * Usage in testng.xml:
 * <listeners>
 *   <listener class-name="com.crossbridge.profiling.CrossBridgeProfilingListener"/>
 * </listeners>
 */
public class CrossBridgeProfilingListener implements ITestListener, IInvokedMethodListener {
    
    private static final String RUN_ID = UUID.randomUUID().toString();
    private static final boolean ENABLED = 
        Boolean.parseBoolean(System.getenv().getOrDefault("CROSSBRIDGE_PROFILING_ENABLED", "false"));
    
    private Connection connection;
    private ThreadLocal<Long> testStartTime = new ThreadLocal<>();
    
    @Override
    public void onStart(ITestContext context) {
        if (!ENABLED) return;
        
        try {
            // Initialize PostgreSQL connection
            String host = System.getenv().getOrDefault("CROSSBRIDGE_DB_HOST", "localhost");
            String port = System.getenv().getOrDefault("CROSSBRIDGE_DB_PORT", "5432");
            String database = System.getenv().getOrDefault("CROSSBRIDGE_DB_NAME", "crossbridge");
            String user = System.getenv().getOrDefault("CROSSBRIDGE_DB_USER", "postgres");
            String password = System.getenv().getOrDefault("CROSSBRIDGE_DB_PASSWORD", "");
            
            String url = String.format("jdbc:postgresql://%s:%s/%s", host, port, database);
            connection = DriverManager.getConnection(url, user, password);
            
            System.out.println("[CrossBridge Profiling] Enabled for run: " + RUN_ID);
        } catch (Exception e) {
            System.err.println("[CrossBridge Profiling] Failed to initialize: " + e.getMessage());
        }
    }
    
    @Override
    public void onTestStart(ITestResult result) {
        if (!ENABLED) return;
        
        testStartTime.set(System.currentTimeMillis());
        
        try {
            String testId = getTestId(result);
            insertEvent(testId, "test_start", 0, "unknown");
        } catch (Exception e) {
            // Silent failure
        }
    }
    
    @Override
    public void onTestSuccess(ITestResult result) {
        onTestEnd(result, "passed");
    }
    
    @Override
    public void onTestFailure(ITestResult result) {
        onTestEnd(result, "failed");
    }
    
    @Override
    public void onTestSkipped(ITestResult result) {
        onTestEnd(result, "skipped");
    }
    
    private void onTestEnd(ITestResult result, String status) {
        if (!ENABLED) return;
        
        Long startTime = testStartTime.get();
        if (startTime == null) return;
        
        try {
            long duration = System.currentTimeMillis() - startTime;
            String testId = getTestId(result);
            
            insertEvent(testId, "test_end", duration, status);
        } catch (Exception e) {
            // Silent failure
        } finally {
            testStartTime.remove();
        }
    }
    
    @Override
    public void beforeInvocation(IInvokedMethod method, ITestResult testResult) {
        // Track method-level timing if needed
    }
    
    @Override
    public void afterInvocation(IInvokedMethod method, ITestResult testResult) {
        // Track method-level timing if needed
    }
    
    @Override
    public void onFinish(ITestContext context) {
        if (!ENABLED) return;
        
        try {
            if (connection != null && !connection.isClosed()) {
                connection.close();
            }
            System.out.println("[CrossBridge Profiling] Session complete");
        } catch (Exception e) {
            // Silent failure
        }
    }
    
    private String getTestId(ITestResult result) {
        return String.format("%s.%s.%s",
            result.getTestClass().getName(),
            result.getMethod().getMethodName(),
            result.getInstanceName()
        );
    }
    
    private void insertEvent(String testId, String eventType, long duration, String status) {
        if (connection == null) return;
        
        try {
            String sql = "INSERT INTO profiling.tests " +
                        "(run_id, test_id, duration_ms, status, framework, created_at) " +
                        "VALUES (?, ?, ?, ?, ?, ?)";
            
            try (PreparedStatement stmt = connection.prepareStatement(sql)) {
                stmt.setObject(1, UUID.fromString(RUN_ID));
                stmt.setString(2, testId);
                stmt.setInt(3, (int) duration);
                stmt.setString(4, status);
                stmt.setString(5, "testng");
                stmt.setTimestamp(6, Timestamp.from(Instant.now()));
                
                stmt.executeUpdate();
            }
        } catch (Exception e) {
            // Silent failure - never break tests
            System.err.println("[CrossBridge Profiling] Failed to insert event: " + e.getMessage());
        }
    }
}
"""

JUNIT_LISTENER_JAVA = """
package com.crossbridge.profiling;

import org.junit.runner.Description;
import org.junit.runner.Result;
import org.junit.runner.notification.RunListener;
import org.junit.runner.notification.Failure;

import java.sql.*;
import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * CrossBridge Performance Profiling Listener for JUnit 4
 * 
 * Usage with Maven Surefire:
 * <configuration>
 *   <properties>
 *     <property>
 *       <name>listener</name>
 *       <value>com.crossbridge.profiling.CrossBridgeJUnitListener</value>
 *     </property>
 *   </properties>
 * </configuration>
 */
public class CrossBridgeJUnitListener extends RunListener {
    
    private static final String RUN_ID = UUID.randomUUID().toString();
    private static final boolean ENABLED = 
        Boolean.parseBoolean(System.getenv().getOrDefault("CROSSBRIDGE_PROFILING_ENABLED", "false"));
    
    private Connection connection;
    private ConcurrentHashMap<Description, Long> testStartTimes = new ConcurrentHashMap<>();
    
    @Override
    public void testRunStarted(Description description) {
        if (!ENABLED) return;
        
        try {
            String host = System.getenv().getOrDefault("CROSSBRIDGE_DB_HOST", "localhost");
            String port = System.getenv().getOrDefault("CROSSBRIDGE_DB_PORT", "5432");
            String database = System.getenv().getOrDefault("CROSSBRIDGE_DB_NAME", "crossbridge");
            String user = System.getenv().getOrDefault("CROSSBRIDGE_DB_USER", "postgres");
            String password = System.getenv().getOrDefault("CROSSBRIDGE_DB_PASSWORD", "");
            
            String url = String.format("jdbc:postgresql://%s:%s/%s", host, port, database);
            connection = DriverManager.getConnection(url, user, password);
            
            System.out.println("[CrossBridge Profiling] Enabled for run: " + RUN_ID);
        } catch (Exception e) {
            System.err.println("[CrossBridge Profiling] Failed to initialize: " + e.getMessage());
        }
    }
    
    @Override
    public void testStarted(Description description) {
        if (!ENABLED) return;
        
        testStartTimes.put(description, System.currentTimeMillis());
    }
    
    @Override
    public void testFinished(Description description) {
        if (!ENABLED) return;
        
        Long startTime = testStartTimes.remove(description);
        if (startTime == null) return;
        
        try {
            long duration = System.currentTimeMillis() - startTime;
            String testId = getTestId(description);
            
            insertEvent(testId, duration, "passed");
        } catch (Exception e) {
            // Silent failure
        }
    }
    
    @Override
    public void testFailure(Failure failure) {
        if (!ENABLED) return;
        
        Description description = failure.getDescription();
        Long startTime = testStartTimes.remove(description);
        
        if (startTime != null) {
            try {
                long duration = System.currentTimeMillis() - startTime;
                String testId = getTestId(description);
                
                insertEvent(testId, duration, "failed");
            } catch (Exception e) {
                // Silent failure
            }
        }
    }
    
    @Override
    public void testRunFinished(Result result) {
        if (!ENABLED) return;
        
        try {
            if (connection != null && !connection.isClosed()) {
                connection.close();
            }
            System.out.println("[CrossBridge Profiling] Session complete");
        } catch (Exception e) {
            // Silent failure
        }
    }
    
    private String getTestId(Description description) {
        return String.format("%s.%s",
            description.getClassName(),
            description.getMethodName()
        );
    }
    
    private void insertEvent(String testId, long duration, String status) {
        if (connection == null) return;
        
        try {
            String sql = "INSERT INTO profiling.tests " +
                        "(run_id, test_id, duration_ms, status, framework, created_at) " +
                        "VALUES (?, ?, ?, ?, ?, ?)";
            
            try (PreparedStatement stmt = connection.prepareStatement(sql)) {
                stmt.setObject(1, UUID.fromString(RUN_ID));
                stmt.setString(2, testId);
                stmt.setInt(3, (int) duration);
                stmt.setString(4, status);
                stmt.setString(5, "junit");
                stmt.setTimestamp(6, Timestamp.from(Instant.now()));
                
                stmt.executeUpdate();
            }
        } catch (Exception e) {
            System.err.println("[CrossBridge Profiling] Failed to insert event: " + e.getMessage());
        }
    }
}
"""

# Python helper
def create_java_profiling_listeners(output_dir: str = "src/main/java/com/crossbridge/profiling"):
    """
    Create Java profiling listener files.
    
    Returns:
        Dictionary mapping filenames to their content
    """
    return {
        "CrossBridgeProfilingListener.java": TESTNG_LISTENER_JAVA,
        "CrossBridgeJUnitListener.java": JUNIT_LISTENER_JAVA,
    }
