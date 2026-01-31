# CrossBridge Sidecar Integration Guide

> **Quick Start**: Run CrossBridge as a sidecar container alongside your existing tests without migration

## Overview

CrossBridge can run as a **sidecar container** (observer mode) that monitors your test execution in real-time, providing continuous intelligence without requiring any test migration or code changes.

### Supported Frameworks
- ✅ **Java Selenium BDD** (TestNG/JUnit + Cucumber)
- ✅ **Robot Framework** (Python, Selenium, Requests)
- ✅ pytest, Cypress, Playwright, and 10+ more

### Benefits
- 🚀 **Zero Migration** - Works with existing tests
- 📊 **Real-time Intelligence** - Continuous monitoring and analysis
- 🔍 **Failure Analysis** - Automatic classification and root cause detection
- 📈 **Trend Tracking** - Historical analysis and flaky test detection
- 🎯 **Impact Analysis** - Code change impact prediction

---

## Integration Approach 1: Java Selenium BDD

### Prerequisites
- Java 11+ installed
- Maven or Gradle project
- Selenium WebDriver configured
- TestNG or JUnit with Cucumber

### Step 1: Add CrossBridge Listener

#### Option A: TestNG (testng.xml)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE suite SYSTEM "https://testng.org/testng-1.0.dtd">
<suite name="Test Suite" parallel="methods" thread-count="5">
    <listeners>
        <!-- Add CrossBridge Listener -->
        <listener class-name="com.crossbridge.CrossBridgeListener"/>
    </listeners>
    
    <test name="Smoke Tests">
        <classes>
            <class name="com.example.tests.LoginTests"/>
            <class name="com.example.tests.SearchTests"/>
        </classes>
    </test>
</suite>
```

#### Option B: JUnit (Annotation)
```java
import org.junit.runner.RunWith;
import com.crossbridge.CrossBridgeRunner;

@RunWith(CrossBridgeRunner.class)
public class MyTests extends TestBase {
    // Your existing tests - no changes needed
}
```

### Step 2: Configure System Properties

#### Maven (pom.xml)
```xml
<project>
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>3.0.0</version>
                <configuration>
                    <systemPropertyVariables>
                        <!-- CrossBridge Configuration -->
                        <crossbridge.enabled>true</crossbridge.enabled>
                        <crossbridge.db.host>10.55.12.99</crossbridge.db.host>
                        <crossbridge.db.port>5432</crossbridge.db.port>
                        <crossbridge.db.name>crossbridge</crossbridge.db.name>
                        <crossbridge.db.user>postgres</crossbridge.db.user>
                        <crossbridge.db.password>admin</crossbridge.db.password>
                        
                        <!-- Application Tracking -->
                        <crossbridge.product.name>${project.artifactId}</crossbridge.product.name>
                        <crossbridge.application.version>${project.version}</crossbridge.application.version>
                        <crossbridge.environment>${env}</crossbridge.environment>
                    </systemPropertyVariables>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

#### Gradle (build.gradle)
```groovy
test {
    systemProperties = [
        // CrossBridge Configuration
        'crossbridge.enabled': 'true',
        'crossbridge.db.host': '10.55.12.99',
        'crossbridge.db.port': '5432',
        'crossbridge.db.name': 'crossbridge',
        'crossbridge.db.user': 'postgres',
        'crossbridge.db.password': 'admin',
        
        // Application Tracking
        'crossbridge.product.name': project.name,
        'crossbridge.application.version': project.version,
        'crossbridge.environment': System.getenv('ENVIRONMENT') ?: 'test'
    ]
}
```

### Step 3: Run Tests

```bash
# Maven
mvn clean test -Dcrossbridge.enabled=true

# Gradle
gradle test --info

# With specific environment
mvn test -Dcrossbridge.enabled=true -Denv=staging
```

### Step 4: Docker Sidecar Pattern

```yaml
# docker-compose.yml
version: "3.9"

services:
  java-tests:
    image: maven:3.9-eclipse-temurin-11
    environment:
      # CrossBridge Configuration
      - crossbridge.enabled=true
      - crossbridge.db.host=10.55.12.99
      - crossbridge.db.port=5432
      - crossbridge.db.name=crossbridge
      - crossbridge.product.name=MyJavaApp
      - crossbridge.application.version=v2.0.0
      - crossbridge.environment=test
    volumes:
      - ./java-project:/workspace
      - ./test-results:/workspace/target
    working_dir: /workspace
    command: mvn clean test
    network_mode: bridge
```

```bash
# Run
docker-compose up --abort-on-container-exit

# View logs
docker-compose logs -f java-tests
```

---

## Integration Approach 2: Robot Framework

### Prerequisites
- Python 3.9+ installed
- Robot Framework: `pip install robotframework`
- RequestsLibrary: `pip install robotframework-requests`
- SeleniumLibrary (optional): `pip install robotframework-seleniumlibrary`

### Step 1: Add CrossBridge Listener

#### Option A: Command Line
```bash
robot --listener crossbridge.hooks.robot_hooks.CrossBridgeListener tests/
```

#### Option B: Robot Configuration (robot.toml)
```toml
[robot]
listeners = ["crossbridge.hooks.robot_hooks.CrossBridgeListener"]
```

#### Option C: Robot File Settings
```robot
*** Settings ***
Library    crossbridge.hooks.robot_hooks.CrossBridgeListener

*** Test Cases ***
My Test
    [Documentation]    This test is monitored by CrossBridge
    Log    Hello World
```

### Step 2: Set Environment Variables

```bash
# CrossBridge Configuration
export CROSSBRIDGE_HOOKS_ENABLED=true
export CROSSBRIDGE_DB_HOST=10.55.12.99
export CROSSBRIDGE_DB_PORT=5432
export CROSSBRIDGE_DB_NAME=crossbridge
export CROSSBRIDGE_DB_USER=postgres
export CROSSBRIDGE_DB_PASSWORD=admin

# Application Tracking
export CROSSBRIDGE_PRODUCT_NAME=MyRobotApp
export CROSSBRIDGE_APPLICATION_VERSION=v2.0.0
export CROSSBRIDGE_ENVIRONMENT=test
```

Or create `.env` file:
```bash
# .env
CROSSBRIDGE_HOOKS_ENABLED=true
CROSSBRIDGE_DB_HOST=10.55.12.99
CROSSBRIDGE_DB_PORT=5432
CROSSBRIDGE_DB_NAME=crossbridge
CROSSBRIDGE_PRODUCT_NAME=MyRobotApp
CROSSBRIDGE_APPLICATION_VERSION=v2.0.0
CROSSBRIDGE_ENVIRONMENT=test
```

### Step 3: Run Tests

```bash
# Basic execution with listener
robot --listener crossbridge.hooks.robot_hooks.CrossBridgeListener tests/

# With variables
robot --listener crossbridge.hooks.robot_hooks.CrossBridgeListener \
      --variable CROSSBRIDGE_ENABLED:true \
      --variable CROSSBRIDGE_APPLICATION_VERSION:v2.0.0 \
      tests/

# With tags
robot --listener crossbridge.hooks.robot_hooks.CrossBridgeListener \
      --include smoke \
      tests/

# Parallel execution
pabot --processes 4 \
      --listener crossbridge.hooks.robot_hooks.CrossBridgeListener \
      tests/
```

### Step 4: Docker Sidecar Pattern

```yaml
# docker-compose.yml
version: "3.9"

services:
  robot-tests:
    image: python:3.11-slim
    environment:
      # CrossBridge Configuration
      - CROSSBRIDGE_HOOKS_ENABLED=true
      - CROSSBRIDGE_DB_HOST=10.55.12.99
      - CROSSBRIDGE_DB_PORT=5432
      - CROSSBRIDGE_DB_NAME=crossbridge
      - CROSSBRIDGE_DB_USER=postgres
      - CROSSBRIDGE_DB_PASSWORD=admin
      
      # Application Tracking
      - CROSSBRIDGE_PRODUCT_NAME=MyRobotApp
      - CROSSBRIDGE_APPLICATION_VERSION=v2.0.0
      - CROSSBRIDGE_ENVIRONMENT=test
    volumes:
      - ./robot-project:/workspace
      - ./test-results:/workspace/results
    working_dir: /workspace
    command: >
      bash -c "pip install robotframework robotframework-requests robotframework-seleniumlibrary &&
               robot --listener crossbridge.hooks.robot_hooks.CrossBridgeListener
                     --outputdir results
                     tests/"
    network_mode: bridge
```

```bash
# Run
docker-compose up --abort-on-container-exit

# View logs
docker-compose logs -f robot-tests
```

---

## Verification

### 1. Check CrossBridge Logs
```bash
# Local
tail -f logs/crossbridge.log

# Docker
docker-compose logs -f crossbridge-observer
```

### 2. Verify Database Entries
```sql
-- Connect to PostgreSQL
psql -h 10.55.12.99 -U postgres -d crossbridge

-- Check recent test executions
SELECT * FROM test_executions 
ORDER BY created_at DESC 
LIMIT 10;

-- Check test results
SELECT test_name, status, duration_ms, created_at
FROM test_results
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;

-- Check failure classifications
SELECT test_name, failure_type, is_intermittent, confidence
FROM failure_classifications
WHERE created_at > NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;
```

### 3. Check Health Endpoints (if enabled)
```bash
# Health check
curl http://localhost:9090/health

# Readiness probe
curl http://localhost:9090/ready

# Prometheus metrics
curl http://localhost:9090/metrics
```

### 4. View Grafana Dashboards (if configured)
```bash
# Open browser
http://localhost:3000

# Default credentials (if not changed)
Username: admin
Password: admin
```

---

## Troubleshooting

### Issue: CrossBridge listener not found

**Java:**
```bash
# Verify listener class is in classpath
mvn dependency:tree | grep crossbridge

# Add dependency explicitly if needed
<dependency>
    <groupId>com.crossbridge</groupId>
    <artifactId>crossbridge-java-listener</artifactId>
    <version>0.2.0</version>
</dependency>
```

**Robot:**
```bash
# Verify CrossBridge is installed
pip list | grep crossbridge

# Install if missing
pip install crossbridge
```

### Issue: Database connection failed

```bash
# Check database connectivity
pg_isready -h 10.55.12.99 -p 5432

# Test connection
psql -h 10.55.12.99 -U postgres -d crossbridge -c "SELECT 1;"

# Check firewall rules
telnet 10.55.12.99 5432
```

### Issue: No events in database

```bash
# Check CrossBridge is enabled
# Java: -Dcrossbridge.enabled=true
# Robot: CROSSBRIDGE_HOOKS_ENABLED=true

# Enable debug logging
# Java: -Dcrossbridge.log.level=DEBUG
# Robot: export CROSSBRIDGE_LOG_LEVEL=DEBUG

# Check listener registration
# Java: Look for "CrossBridge listener registered" in logs
# Robot: Look for "CrossBridge Robot Framework listener enabled" in logs
```

---

## Best Practices

### 1. Use Environment Variables for Secrets
```bash
# Don't hardcode passwords
export CROSSBRIDGE_DB_PASSWORD=$(cat /run/secrets/db_password)
```

### 2. Enable Only in CI/CD
```java
// Java - Enable only in CI
boolean crossbridgeEnabled = System.getenv("CI") != null;
System.setProperty("crossbridge.enabled", String.valueOf(crossbridgeEnabled));
```

```python
# Robot - Enable only in CI
import os
CROSSBRIDGE_ENABLED = os.getenv('CI') is not None
```

### 3. Use Application Version from Git
```bash
# Maven
export CROSSBRIDGE_APPLICATION_VERSION=$(git describe --tags --always)
mvn test -Dcrossbridge.application.version=${CROSSBRIDGE_APPLICATION_VERSION}

# Robot
export CROSSBRIDGE_APPLICATION_VERSION=$(git describe --tags --always)
robot --variable CROSSBRIDGE_APPLICATION_VERSION:${CROSSBRIDGE_APPLICATION_VERSION} tests/
```

### 4. Configure Sampling for High-Volume Tests
```yaml
# crossbridge.yml
sidecar:
  sampling:
    enabled: true
    rates:
      events: 0.1  # Sample 10% of events
      logs: 0.05   # Sample 5% of logs
```

---

## Advanced Configuration

### Resource Limits
```yaml
# crossbridge.yml
sidecar:
  resources:
    max_cpu_percent: 5.0      # 5% CPU limit
    max_memory_mb: 100        # 100 MB limit
```

### Custom Metrics
```java
// Java
CrossBridge.recordMetric("test.custom.duration", duration);
CrossBridge.recordMetric("test.api.calls", apiCallCount);
```

```robot
# Robot
*** Keywords ***
Record Custom Metric
    [Arguments]    ${metric_name}    ${value}
    CrossBridge.Record Metric    ${metric_name}    ${value}
```

---

## Next Steps

1. **View Results**: Access Grafana dashboards at http://localhost:3000
2. **API Integration**: Use CrossBridge REST API for custom queries
3. **CI/CD Integration**: Add CrossBridge to your pipeline
4. **Alerting**: Configure Slack/Teams notifications for failures
5. **Advanced Features**: Enable AI-powered failure prediction

## Support

- **Documentation**: https://github.com/crossstack-ai/crossbridge
- **Issues**: https://github.com/crossstack-ai/crossbridge/issues
- **Community**: Join our Slack channel
- **Email**: support@crossstack.ai
