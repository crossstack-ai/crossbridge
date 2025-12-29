# CrossBridge Java Test Parser

AST-based parser for Java test files using JavaParser.

## Build

```bash
mvn clean package
```

This creates `target/java-test-parser-1.0.jar` with all dependencies bundled.

## Usage

```bash
java -jar target/java-test-parser-1.0.jar path/to/TestFile.java
```

## Output

JSON format:

```json
{
  "packageName": "com.example",
  "className": "LoginTest",
  "imports": [
    "org.junit.jupiter.api.Test",
    "org.junit.jupiter.api.Tag",
    "org.junit.jupiter.api.DisplayName"
  ],
  "annotations": [
    {
      "name": "Tag",
      "attributes": {
        "value": "\"integration\""
      }
    }
  ],
  "testMethods": [
    {
      "name": "testValidLogin",
      "lineNumber": 15,
      "annotations": [
        {
          "name": "Test",
          "attributes": {}
        },
        {
          "name": "DisplayName",
          "attributes": {
            "value": "\"Test valid login credentials\""
          }
        },
        {
          "name": "Tag",
          "attributes": {
            "value": "\"smoke\""
          }
        }
      ]
    }
  ]
}
```

## Python Integration

The Python wrapper in `adapters/java/ast_parser.py` calls this JAR:

```python
from adapters.java.ast_parser import parse_java_test_file

test_class = parse_java_test_file("src/test/java/com/example/MyTest.java")
```

## Dependencies

- JavaParser 3.25.8 - AST parsing
- Gson 2.10.1 - JSON serialization

## Supported Annotations

### JUnit 4
- `@Test`
- `@Before`, `@After`
- `@BeforeClass`, `@AfterClass`
- `@Ignore`
- `@Category`

### JUnit 5
- `@Test`
- `@ParameterizedTest`
- `@RepeatedTest`
- `@BeforeEach`, `@AfterEach`
- `@BeforeAll`, `@AfterAll`
- `@Disabled`
- `@Tag`
- `@DisplayName`

### TestNG
- `@Test` (with attributes: groups, enabled, dataProvider, etc.)
- `@BeforeMethod`, `@AfterMethod`
- `@BeforeClass`, `@AfterClass`
- `@BeforeSuite`, `@AfterSuite`
- `@DataProvider`

## Requirements

- Java 11 or higher
- Maven 3.6 or higher
