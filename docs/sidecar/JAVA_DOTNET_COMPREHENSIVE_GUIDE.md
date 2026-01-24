# Java & .NET Sidecar Integration - Complete Guide

Copyright (c) 2025 Vikas Verma  
Licensed under the Apache License, Version 2.0

**Date:** January 24, 2026  
**Status:** ✅ PRODUCTION READY  
**Frameworks:** TestNG, JUnit 4, JUnit 5, NUnit, SpecFlow

---

## Overview

CrossBridge sidecar observer provides **zero-code-change observability** for Java and .NET test frameworks. This comprehensive guide consolidates setup, compatibility verification, and troubleshooting for all supported Java/.NET frameworks.

---

## 🎯 Framework Compatibility Matrix

### Java Frameworks (5 Variants)

| Framework | Version | Status | Thread-Safe | Listener File | Verified |
|-----------|---------|--------|-------------|---------------|----------|
| **TestNG** | 6.x, 7.x | ✅ Compatible | ✅ Yes | CrossBridgeListener.java | ✅ |
| **JUnit 4** | 4.x | ✅ Compatible | ✅ Yes | CrossBridgeJUnitListener.java | ✅ |
| **JUnit 5** | Jupiter 5.x | ✅ Compatible | ✅ Yes | CrossBridgeExtension.java | ✅ |
| **Cucumber JVM** | All | ✅ Auto-detected | ✅ Yes | Works with TestNG/JUnit | ✅ |
| **RestAssured** | All | ✅ Auto-detected | ✅ Yes | Works with TestNG/JUnit | ✅ |

### .NET Frameworks (2 Variants)

| Framework | Version | Status | Thread-Safe | Listener File | Verified |
|-----------|---------|--------|-------------|---------------|----------|
| **NUnit** | 3.x | ✅ Compatible | ✅ Yes | nunit_listener.cs | ✅ |
| **SpecFlow** | 3.x+ | ✅ Compatible | ✅ Yes | specflow_plugin.cs | ✅ |

**Total: 7 framework variants** with full parallel execution support.

---

## Quick Start

### Java (TestNG Example)

```bash
# 1. Set environment variables
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_DB_HOST=localhost
export CROSSBRIDGE_APPLICATION_VERSION=v2.0.0

# 2. Generate listener file
python -m core.observability.hooks.java_listener

# 3. Add to testng.xml
<listeners>
  <listener class-name="com.crossbridge.CrossBridgeListener"/>
</listeners>

# 4. Run tests normally
mvn test
```

### .NET (NUnit Example)

```bash
# 1. Set environment variables
$env:CROSSBRIDGE_ENABLED = "true"
$env:CROSSBRIDGE_DB_HOST = "localhost"
$env:CROSSBRIDGE_APPLICATION_VERSION = "v2.0.0"

# 2. Generate listener file
python -m core.observability.hooks.nunit_listener

# 3. Add to test assembly
[assembly: CrossBridgeListener]

# 4. Run tests normally
dotnet test
```

---

## Java Framework Setup

### 1. TestNG (6.x/7.x)

**Listener File:** `CrossBridgeListener.java` (350 lines)

**Features:**
- ✅ Implements `ITestListener` and `ISuiteListener`
- ✅ Thread-safe `ConcurrentHashMap` for parallel execution
- ✅ Extracts test groups, priority, invocation count
- ✅ Captures test parameters and context
- ✅ Auto-detects Cucumber and RestAssured

#### Setup Method 1: testng.xml (Recommended)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE suite SYSTEM "https://testng.org/testng-1.0.dtd">
<suite name="CrossBridgeTestSuite" parallel="tests" thread-count="4">
  
  <listeners>
    <listener class-name="com.crossbridge.CrossBridgeListener"/>
  </listeners>
  
  <test name="LoginTests">
    <classes>
      <class name="com.example.tests.LoginTest"/>
      <class name="com.example.tests.LogoutTest"/>
    </classes>
  </test>
  
</suite>
```

#### Setup Method 2: Annotation

```java
import org.testng.annotations.*;
import com.crossbridge.CrossBridgeListener;

@Listeners(CrossBridgeListener.class)
public class MyTest {
    
    @Test(groups = {"smoke", "regression"}, priority = 1)
    public void testUserLogin() {
        // Your test code - NO CHANGES NEEDED
    }
    
    @Test(groups = {"smoke"}, priority = 2)
    public void testUserLogout() {
        // Your test code
    }
}
```

#### Parallel Execution

```xml
<suite name="ParallelSuite" parallel="methods" thread-count="10">
  <listeners>
    <listener class-name="com.crossbridge.CrossBridgeListener"/>
  </listeners>
  <!-- All methods run in parallel - CrossBridge handles concurrency -->
  <test name="ParallelTests">
    <classes>
      <class name="com.example.tests.ParallelTest"/>
    </classes>
  </test>
</suite>
```

#### Maven Configuration

```xml
<build>
  <plugins>
    <plugin>
      <groupId>org.apache.maven.plugins</groupId>
      <artifactId>maven-surefire-plugin</artifactId>
      <version>2.22.2</version>
      <configuration>
        <suiteXmlFiles>
          <suiteXmlFile>testng.xml</suiteXmlFile>
        </suiteXmlFiles>
        <systemPropertyVariables>
          <crossbridge.enabled>true</crossbridge.enabled>
          <crossbridge.db.host>10.55.12.99</crossbridge.db.host>
          <crossbridge.application.version>v2.0.0</crossbridge.application.version>
        </systemPropertyVariables>
      </configuration>
    </plugin>
  </plugins>
</build>
```

---

### 2. JUnit 4 (4.x)

**Listener File:** `CrossBridgeJUnitListener.java` (280 lines)

**Features:**
- ✅ Extends `RunListener` class
- ✅ Thread-safe `ConcurrentHashMap`
- ✅ Captures test annotations
- ✅ Handles ignored/skipped tests

#### Setup Method 1: maven-surefire-plugin (Recommended)

```xml
<build>
  <plugins>
    <plugin>
      <groupId>org.apache.maven.plugins</groupId>
      <artifactId>maven-surefire-plugin</artifactId>
      <version>2.22.2</version>
      <configuration>
        <properties>
          <property>
            <name>listener</name>
            <value>com.crossbridge.CrossBridgeJUnitListener</value>
          </property>
        </properties>
        <systemPropertyVariables>
          <crossbridge.enabled>true</crossbridge.enabled>
          <crossbridge.db.host>localhost</crossbridge.db.host>
          <crossbridge.application.version>v2.0.0</crossbridge.application.version>
        </systemPropertyVariables>
      </configuration>
    </plugin>
  </plugins>
</build>
```

#### Setup Method 2: Programmatic

```java
import org.junit.runner.JUnitCore;
import com.crossbridge.CrossBridgeJUnitListener;

public class TestRunner {
    public static void main(String[] args) {
        JUnitCore junit = new JUnitCore();
        junit.addListener(new CrossBridgeJUnitListener());
        junit.run(LoginTest.class, CheckoutTest.class);
    }
}
```

#### Parallel Execution

```xml
<plugin>
  <artifactId>maven-surefire-plugin</artifactId>
  <configuration>
    <parallel>methods</parallel>
    <threadCount>10</threadCount>
    <properties>
      <property>
        <name>listener</name>
        <value>com.crossbridge.CrossBridgeJUnitListener</value>
      </property>
    </properties>
  </configuration>
</plugin>
```

---

### 3. JUnit 5 (Jupiter 5.x)

**Listener File:** `CrossBridgeExtension.java` (320 lines)

**Features:**
- ✅ Implements `TestExecutionListener` interface
- ✅ Thread-safe `ConcurrentHashMap`
- ✅ Extracts tags, display names
- ✅ Handles parameterized tests
- ✅ Nested test context

#### Setup Method 1: @ExtendWith Annotation (Recommended)

```java
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import com.crossbridge.CrossBridgeExtension;

@ExtendWith(CrossBridgeExtension.class)
class MyTest {
    
    @Test
    @Tag("smoke")
    @DisplayName("Test user login functionality")
    void testUserLogin() {
        // Your test code - NO CHANGES NEEDED
    }
    
    @ParameterizedTest
    @ValueSource(strings = {"user1", "user2", "user3"})
    void testMultipleUsers(String username) {
        // Parameterized test
    }
}
```

#### Setup Method 2: Configuration File

Create `src/test/resources/junit-platform.properties`:

```properties
junit.jupiter.extensions.autodetection.enabled=true
```

And add to `META-INF/services/org.junit.jupiter.api.extension.Extension`:

```
com.crossbridge.CrossBridgeExtension
```

#### Maven Configuration

```xml
<dependencies>
  <dependency>
    <groupId>org.junit.jupiter</groupId>
    <artifactId>junit-jupiter</artifactId>
    <version>5.9.0</version>
    <scope>test</scope>
  </dependency>
</dependencies>

<build>
  <plugins>
    <plugin>
      <artifactId>maven-surefire-plugin</artifactId>
      <version>2.22.2</version>
      <configuration>
        <systemPropertyVariables>
          <crossbridge.enabled>true</crossbridge.enabled>
          <crossbridge.db.host>localhost</crossbridge.db.host>
        </systemPropertyVariables>
      </configuration>
    </plugin>
  </plugins>
</build>
```

---

### 4. Cucumber JVM (Auto-Detected)

**Detection:** Automatic when Cucumber classes are on classpath

**Works with:** TestNG or JUnit listeners

**Framework Tag:** `selenium-java-bdd`

#### Example with TestNG

```xml
<!-- testng.xml -->
<suite name="CucumberSuite">
  <listeners>
    <listener class-name="com.crossbridge.CrossBridgeListener"/>
  </listeners>
  <test name="CucumberTests">
    <classes>
      <class name="io.cucumber.testng.AbstractTestNGCucumberTests"/>
    </classes>
  </test>
</suite>
```

```java
// TestNG Cucumber Runner
import io.cucumber.testng.AbstractTestNGCucumberTests;
import io.cucumber.testng.CucumberOptions;

@CucumberOptions(
    features = "src/test/resources/features",
    glue = "com.example.stepdefs"
)
public class CucumberRunner extends AbstractTestNGCucumberTests {
    // CrossBridge automatically detects Cucumber
}
```

---

### 5. RestAssured (Auto-Detected)

**Detection:** Automatic when RestAssured classes are on classpath

**Works with:** TestNG or JUnit listeners

**Framework Tag:** `selenium-java-restassured`

```java
import io.restassured.RestAssured;
import org.testng.annotations.*;

@Listeners(com.crossbridge.CrossBridgeListener.class)
public class ApiTest {
    
    @Test
    public void testGetUser() {
        // CrossBridge detects RestAssured automatically
        RestAssured
            .given()
                .baseUri("https://api.example.com")
            .when()
                .get("/users/1")
            .then()
                .statusCode(200);
    }
}
```

---

## .NET Framework Setup

### 1. NUnit 3.x

**Listener File:** `nunit_listener.cs` (350 lines)

**Features:**
- ✅ Implements `ITestListener` and `ITestAction`
- ✅ Thread-safe `ConcurrentDictionary`
- ✅ Extracts properties and categories
- ✅ Handles all test states (passed/failed/skipped/inconclusive)

#### Setup Method 1: Assembly Attribute (Recommended)

```csharp
using NUnit.Framework;
using CrossBridge.Observability;

// Add to AssemblyInfo.cs or any test file
[assembly: CrossBridgeListener]

namespace MyTests
{
    [TestFixture]
    [Category("Smoke")]
    public class LoginTests
    {
        [Test]
        [Property("Priority", "High")]
        public void TestUserLogin()
        {
            // Your test code - NO CHANGES NEEDED
        }
    }
}
```

#### Setup Method 2: .runsettings File

```xml
<?xml version="1.0" encoding="utf-8"?>
<RunSettings>
  <TestRunParameters>
    <Parameter name="CROSSBRIDGE_ENABLED" value="true" />
    <Parameter name="CROSSBRIDGE_DB_HOST" value="localhost" />
    <Parameter name="CROSSBRIDGE_APPLICATION_VERSION" value="v2.0.0" />
  </TestRunParameters>
  
  <NUnit>
    <DomainUsage>Single</DomainUsage>
  </NUnit>
</RunSettings>
```

Run with:

```bash
dotnet test --settings test.runsettings
```

#### Parallel Execution

```csharp
[assembly: Parallelizable(ParallelScope.All)]
[assembly: LevelOfParallelism(10)]
[assembly: CrossBridgeListener]

[TestFixture]
[Parallelizable(ParallelScope.Children)]
public class ParallelTests
{
    [Test]
    public void TestMethod1() { }
    
    [Test]
    public void TestMethod2() { }
    // Both run in parallel - CrossBridge handles concurrency
}
```

---

### 2. SpecFlow 3.x+ (Already Implemented)

**Plugin File:** `specflow_plugin.cs`

**Features:**
- ✅ Implements SpecFlow plugin interface
- ✅ BDD scenario tracking
- ✅ Step-level instrumentation

See [RESTASSURED_IMPLEMENTATION_COMPLETE.md](RESTASSURED_IMPLEMENTATION_COMPLETE.md) for SpecFlow details.

---

## Technical Features

### 1. Thread Safety

All listeners use concurrent data structures:

**Java:**
```java
private static final ConcurrentHashMap<String, Long> testStartTimes = 
    new ConcurrentHashMap<>();
```

**C#:**
```csharp
private static readonly ConcurrentDictionary<string, DateTime> TestStartTimes = 
    new ConcurrentDictionary<string, DateTime>();
```

**Benefit:** Safe for parallel test execution with 10+ threads.

---

### 2. Framework Auto-Detection

CrossBridge intelligently detects frameworks:

```java
// Auto-detection logic
private String detectFramework() {
    if (hasCucumber()) return "selenium-java-bdd";
    if (hasRestAssured()) return "selenium-java-restassured";
    return "selenium-java";
}
```

**Detection methods:**
- Cucumber: Check for `cucumber.api.*` or `io.cucumber.*` in classpath
- RestAssured: Check for `io.restassured.*` in classpath
- JUnit version: Check for `org.junit.jupiter.*` vs `org.junit.*`

---

### 3. Metadata Extraction

**TestNG Metadata:**
```java
Map<String, String> metadata = new HashMap<>();
metadata.put("groups", Arrays.toString(method.getGroups()));
metadata.put("priority", String.valueOf(method.getPriority()));
metadata.put("invocationCount", String.valueOf(method.getInvocationCount()));
```

**JUnit 5 Metadata:**
```java
Set<String> tags = testIdentifier.getTags().stream()
    .map(TestTag::getName)
    .collect(Collectors.toSet());
metadata.put("tags", String.join(",", tags));
metadata.put("displayName", testIdentifier.getDisplayName());
```

**NUnit Metadata:**
```csharp
var metadata = new Dictionary<string, string>
{
    ["categories"] = string.Join(",", test.Properties["Category"]),
    ["priority"] = test.Properties["Priority"]?.FirstOrDefault()?.ToString() ?? "N/A"
};
```

---

### 4. Non-Blocking Error Handling

All listeners include try-catch blocks to prevent test disruption:

```java
@Override
public void onTestStart(ITestResult result) {
    try {
        // CrossBridge logic
        sendTestEvent("test_started", ...);
    } catch (Exception e) {
        // Log error but DON'T affect test execution
        System.err.println("CrossBridge error (non-fatal): " + e.getMessage());
    }
}
```

**Philosophy:** CrossBridge observes silently. Test failures should come from tests, not observers.

---

## Environment Variables

### Required

```bash
# Java
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_DB_HOST=localhost
export CROSSBRIDGE_DB_PORT=5432
export CROSSBRIDGE_DB_NAME=crossbridge
export CROSSBRIDGE_DB_USER=postgres
export CROSSBRIDGE_DB_PASSWORD=admin
export CROSSBRIDGE_APPLICATION_VERSION=v2.0.0

# .NET
$env:CROSSBRIDGE_ENABLED = "true"
$env:CROSSBRIDGE_DB_HOST = "localhost"
$env:CROSSBRIDGE_APPLICATION_VERSION = "v2.0.0"
```

### Optional

```bash
# Advanced configuration
export CROSSBRIDGE_BATCH_SIZE=10           # Event batching
export CROSSBRIDGE_TIMEOUT_MS=5000         # API timeout
export CROSSBRIDGE_RETRY_COUNT=3           # Retry attempts
export CROSSBRIDGE_LOG_LEVEL=INFO          # Logging verbosity
```

---

## Verification

### Test Database Connection

```sql
-- Connect to PostgreSQL
psql -h localhost -U postgres -d crossbridge

-- Verify events are being captured
SELECT 
    test_name,
    framework,
    status,
    execution_time_ms,
    created_at
FROM test_execution_event
ORDER BY created_at DESC
LIMIT 10;
```

### Expected Output

```
      test_name       |    framework     | status | execution_time_ms |     created_at      
----------------------+------------------+--------+-------------------+---------------------
 testUserLogin        | selenium-java    | passed | 1243              | 2026-01-24 10:15:30
 testCheckout         | selenium-java    | passed | 2156              | 2026-01-24 10:15:29
 testSearchProduct    | selenium-java-bdd| passed | 3421              | 2026-01-24 10:15:27
 testApiGetUser       | selenium-java-restassured | passed | 456  | 2026-01-24 10:15:25
```

---

## Parallel Execution Verification

### Run Parallel Tests

**TestNG:**
```xml
<suite name="ParallelSuite" parallel="methods" thread-count="10">
  <listeners>
    <listener class-name="com.crossbridge.CrossBridgeListener"/>
  </listeners>
  <test name="ParallelTest">
    <classes>
      <class name="com.example.tests.ParallelTest"/>
    </classes>
  </test>
</suite>
```

**NUnit:**
```csharp
[assembly: Parallelizable(ParallelScope.All)]
[assembly: LevelOfParallelism(10)]
[assembly: CrossBridgeListener]
```

### Verify Thread Safety

```sql
-- Check for concurrent test execution
SELECT 
    DATE_TRUNC('second', created_at) as second,
    COUNT(*) as concurrent_tests
FROM test_execution_event
WHERE created_at > NOW() - INTERVAL '5 minutes'
GROUP BY second
ORDER BY second DESC
LIMIT 10;

-- Expected: Multiple tests per second (parallel execution)
```

---

## Troubleshooting

### Issue 1: Listener Not Registering

**Java:**
```bash
# Verify listener is on classpath
mvn dependency:tree | grep crossbridge

# Check TestNG output for listener registration
mvn test -X | grep "CrossBridgeListener"

# Expected output:
# [INFO] Running tests with listener: com.crossbridge.CrossBridgeListener
```

**.NET:**
```bash
# Verify listener assembly is referenced
dotnet list reference

# Run with verbose logging
dotnet test --verbosity detailed
```

### Issue 2: Database Connection Failures

```bash
# Test database connectivity
telnet localhost 5432

# Verify environment variables
echo $CROSSBRIDGE_DB_HOST
echo $CROSSBRIDGE_ENABLED

# Check database logs
tail -f /var/log/postgresql/postgresql-16-main.log
```

### Issue 3: Events Not Appearing

```sql
-- Check if events table exists
SELECT COUNT(*) FROM test_execution_event;

-- Check recent events
SELECT * FROM test_execution_event 
WHERE created_at > NOW() - INTERVAL '10 minutes';

-- Check for errors in application logs
SELECT * FROM application_logs 
WHERE level = 'ERROR' 
ORDER BY timestamp DESC 
LIMIT 10;
```

---

## Best Practices

### 1. Use Configuration Management

Store credentials securely:

```bash
# Use environment-specific configs
export $(cat .env.${ENVIRONMENT} | xargs)

# Or use secrets management
export CROSSBRIDGE_DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id crossbridge-db-password --query SecretString --output text)
```

### 2. Enable Only in CI/CD

```bash
# Only enable in CI/CD environment
if [ "$CI" = "true" ]; then
    export CROSSBRIDGE_ENABLED=true
else
    export CROSSBRIDGE_ENABLED=false
fi
```

### 3. Monitor Performance

```sql
-- Check average event processing time
SELECT 
    AVG(execution_time_ms) as avg_execution_ms,
    framework
FROM test_execution_event
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY framework;

-- Identify slow tests
SELECT 
    test_name,
    execution_time_ms,
    framework
FROM test_execution_event
WHERE execution_time_ms > 5000
ORDER BY execution_time_ms DESC
LIMIT 10;
```

---

## Support

### Documentation
- **[No-Migration Complete Guide](NO_MIGRATION_IMPLEMENTATION_COMPLETE.md)** - Overview
- **[Automatic Sidecar Integration](AUTOMATIC_SIDECAR_INTEGRATION.md)** - Setup
- **[Quick Start](../quick-start/QUICK_START.md)** - Getting started

### Getting Help
- **📧 Email**: vikas.sdet@gmail.com
- ** GitHub Issues**: [Report Issues](https://github.com/crossstack-ai/crossbridge/issues)

---

**Zero code changes. Full observability. All Java/.NET frameworks.** 🚀
