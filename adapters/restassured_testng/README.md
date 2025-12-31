# RestAssured + TestNG Adapter

Adapter for executing and analyzing REST API tests using RestAssured with TestNG framework.

## Overview

This adapter provides support for Java-based REST API testing using RestAssured 5.x with TestNG 7.x. It can detect projects, extract test metadata, and execute tests via Maven or Gradle.

## Features

- ✅ **Project Detection**: Automatically detects RestAssured + TestNG projects from Maven pom.xml, Gradle build files, or source files
- ✅ **Test Discovery**: Extracts test metadata without execution
- ✅ **Maven Support**: Execute tests using Maven Surefire
- ✅ **Gradle Support**: Execute tests using Gradle test task
- ✅ **TestNG Groups**: Filter tests by TestNG groups
- ✅ **Parallel Execution**: Configure parallel test execution
- ✅ **Result Parsing**: Parse TestNG XML and Maven Surefire XML reports
- ✅ **Test Filtering**: Run specific tests or test classes

## Installation

The adapter is part of the CrossBridge project. No separate installation needed.

## Quick Start

###  Basic Usage

```python
from adapters.restassured_testng.adapter import RestAssuredTestNGAdapter

# Create adapter
adapter = RestAssuredTestNGAdapter("/path/to/project")

# Discover all tests
tests = adapter.discover_tests()
print(f"Found {len(tests)} tests")

# Run all tests
results = adapter.run_tests()

# Run specific groups
results = adapter.run_tests(tags=["smoke", "regression"])

# Run specific tests
results = adapter.run_tests(tests=["com.example.UserApiTest#testGetUser"])
```

### Detection

```python
from adapters.restassured_testng.adapter import RestAssuredTestNGAdapter

# Check if project uses RestAssured + TestNG
if RestAssuredTestNGAdapter.detect_project("/path/to/project"):
    print("RestAssured + TestNG project detected!")
```

## Configuration

```python
from adapters.restassured_testng.config import RestAssuredConfig
from adapters.restassured_testng.adapter import RestAssuredTestNGAdapter

config = RestAssuredConfig(
    project_root="/path/to/project",
    src_root="src/test/java",  # Test source directory
    maven_command="mvn",
    gradle_command="gradle",
    testng_xml="testng.xml",  # TestNG suite file
    parallel_threads=4,  # Parallel execution
    groups=["smoke", "regression"],  # Default groups to run
    build_tool="maven"  # or "gradle", auto-detected if None
)

adapter = RestAssuredTestNGAdapter("/path/to/project", config)
```

## Test Structure

### Example Test File

```java
package com.example.api;

import io.restassured.RestAssured;
import io.restassured.response.Response;
import org.testng.annotations.Test;
import static org.testng.Assert.*;

@Test(groups = {"api"})
public class UserApiTest {
    
    @Test(priority = 1, groups = {"smoke"})
    public void testGetAllUsers() {
        Response response = RestAssured
            .given()
                .baseUri("https://api.example.com")
            .when()
                .get("/users")
            .then()
                .extract().response();
        
        assertEquals(200, response.statusCode());
    }
    
    @Test(priority = 2, groups = {"regression"})
    public void testCreateUser() {
        String requestBody = "{\"name\": \"John\", \"email\": \"john@example.com\"}";
        
        Response response = RestAssured
            .given()
                .baseUri("https://api.example.com")
                .contentType("application/json")
                .body(requestBody)
            .when()
                .post("/users")
            .then()
                .extract().response();
        
        assertEquals(201, response.statusCode());
    }
    
    @Test(enabled = false, description = "Test for updating user")
    public void testUpdateUser() {
        // Disabled test
    }
}
```

## Test Discovery

The adapter extracts metadata from test files:

```python
tests = adapter.discover_tests()

for test in tests:
    print(f"Test: {test.test_name}")
    print(f"  Framework: {test.framework}")
    print(f"  Type: {test.test_type}")  # "api"
    print(f"  Tags: {test.tags}")
    print(f"  File: {test.file_path}")
```

## Test Execution

### Maven

```python
# Run all tests
adapter.run_tests()

# Run specific groups
adapter.run_tests(tags=["smoke"])

# Run specific tests
adapter.run_tests(tests=["com.example.UserApiTest#testGetUser"])
```

### Gradle

```python
config = RestAssuredConfig(
    project_root="/path/to/project",
    build_tool="gradle"
)
adapter = RestAssuredTestNGAdapter("/path/to/project", config)

adapter.run_tests(tags=["smoke"])
```

### Parallel Execution

```python
config = RestAssuredConfig(
    project_root="/path/to/project",
    parallel_threads=4
)
adapter = RestAssuredTestNGAdapter("/path/to/project", config)

adapter.run_tests()  # Runs tests in parallel
```

## Result Format

```python
results = adapter.run_tests()

for result in results:
    print(f"Test: {result.name}")
    print(f"  Status: {result.status}")  # "pass", "fail", "skip", "error"
    print(f"  Duration: {result.duration_ms}ms")
    if result.status == "fail":
        print(f"  Error: {result.message}")
```

## TestNG Integration

### Groups

```java
@Test(groups = {"smoke", "api"})
public class ApiTest {
    @Test(groups = {"regression"})
    public void test1() { }
}
```

Run specific groups:
```python
adapter.run_tests(tags=["smoke"])  # Runs all tests in "smoke" group
```

### Priority

```java
@Test(priority = 1)
public void testFirst() { }

@Test(priority = 2)
public void testSecond() { }
```

### Enabled/Disabled

```java
@Test(enabled = false)
public void disabledTest() { }
```

### Description

```java
@Test(description = "Test user creation API")
public void testCreateUser() { }
```

## Maven Configuration

### pom.xml

```xml
<dependencies>
    <!-- RestAssured -->
    <dependency>
        <groupId>io.rest-assured</groupId>
        <artifactId>rest-assured</artifactId>
        <version>5.3.0</version>
        <scope>test</scope>
    </dependency>
    
    <!-- TestNG -->
    <dependency>
        <groupId>org.testng</groupId>
        <artifactId>testng</artifactId>
        <version>7.7.0</version>
        <scope>test</scope>
    </dependency>
</dependencies>

<build>
    <plugins>
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <version>3.0.0-M7</version>
            <configuration>
                <suiteXmlFiles>
                    <suiteXmlFile>testng.xml</suiteXmlFile>
                </suiteXmlFiles>
            </configuration>
        </plugin>
    </plugins>
</build>
```

## Gradle Configuration

### build.gradle

```groovy
dependencies {
    testImplementation 'io.rest-assured:rest-assured:5.3.0'
    testImplementation 'org.testng:testng:7.7.0'
}

test {
    useTestNG() {
        suites 'testng.xml'
    }
}
```

## Best Practices

1. **Organize Tests by Groups**: Use TestNG groups to categorize tests (smoke, regression, api)
2. **Use Priority Wisely**: Set priorities for tests that have dependencies
3. **Descriptive Test Names**: Use clear test method names
4. **Proper Assertions**: Use TestNG assertions for better error messages
5. **Test Data Management**: Use @DataProvider for parameterized tests
6. **Base URI Configuration**: Use RestAssured.baseURI for environment configuration

## Limitations

- Method-level group extraction is currently limited (class-level groups work correctly)
- TestNG XML suite file support is basic
- DataProvider tests are detected but not fully analyzed
- Listener configurations are not extracted

## Troubleshooting

### Tests Not Detected

- Ensure test files have RestAssured imports (`import io.restassured.*`)
- Ensure test methods have `@Test` annotation
- Check that test files are in `src/test/java` or configure `src_root`

### Maven/Gradle Execution Fails

- Verify Maven/Gradle is installed and in PATH
- Check that dependencies are properly configured
- Ensure testng.xml file exists if specified

### No Results Parsed

- Check that Surefire reports directory exists (`target/surefire-reports`)
- For Gradle, check `test-output` directory
- Ensure tests actually ran (check build output)

## Examples

See `examples/java_tests/restassured_sample/` for complete example projects.

## Related Adapters

- [Selenium + Java + TestNG](../selenium_java/)
- [Selenium BDD + Java](../selenium_bdd_java/)
- [Java Adapter](../java/)

## Contributing

When contributing to this adapter:
1. Add tests to `tests/unit/adapters/test_restassured_testng.py`
2. Update patterns in `patterns.py` if adding new detection
3. Document new features in this README
4. Ensure backward compatibility

## License

Part of the CrossBridge project. See main LICENSE file.
