# Java AST-Based Test Parser

This directory contains AST-based parsing infrastructure for Java test frameworks.

## Architecture

```
adapters/java/
├── model.py           # Neutral test representation
├── detector.py        # Framework detection
├── ast_parser.py      # JavaParser integration (Python wrapper)
├── junit_parser.py    # JUnit-specific parsing logic
├── testng_parser.py   # TestNG-specific parsing logic
└── parser/            # JavaParser utility (Java)
    ├── pom.xml
    └── src/main/java/
        └── com/crossbridge/parser/
            └── JavaTestParser.java
```

## Why AST over Regex?

| Approach | Regex/Grep | AST (JavaParser) |
|----------|------------|------------------|
| **Accuracy** | Fragile, breaks on formatting | ✅ Accurate, format-independent |
| **Extensibility** | Hard to extend | ✅ Rich metadata extraction |
| **Structure** | No semantic understanding | ✅ Full syntax tree |
| **Maintenance** | Error-prone | ✅ Robust |

## Models

### JavaTestCase
Neutral representation of a test case:
- `framework`: junit4 | junit5 | testng
- `package`: Java package name
- `class_name`: Test class name
- `method_name`: Test method name
- `annotations`: List of annotations
- `tags`: Extracted tags/groups
- `file_path`: Source file path
- `line_number`: Location in file

### JavaTestClass
Represents a complete test class with all methods.

### JavaTestMethod
Represents a single test method with annotations.

## Usage

### Option 1: With JavaParser (AST-based, recommended)

```python
from adapters.java.ast_parser import parse_java_test_file

# Parse a Java test file
test_class = parse_java_test_file("src/test/java/com/example/MyTest.java")

if test_class:
    print(f"Class: {test_class.class_name}")
    print(f"Framework: {test_class.framework.value}")
    
    for method in test_class.test_methods:
        print(f"  Test: {method.method_name}")
        print(f"  Tags: {method.tags}")
```

### Option 2: Framework Detection

```python
from adapters.java.detector import detect_project_frameworks

frameworks = detect_project_frameworks(".", "src/test/java")
print(f"Detected frameworks: {frameworks}")
# Output: {'junit5', 'testng'}
```

### Option 3: Convert to TestMetadata

```python
from adapters.java.model import JavaTestCase

test_case = JavaTestCase(
    framework="junit5",
    package="com.example",
    class_name="LoginTest",
    method_name="testValidLogin",
    annotations=["Test", "Tag"],
    tags=["smoke"],
    file_path="src/test/java/com/example/LoginTest.java"
)

# Convert to CrossBridge TestMetadata
metadata = test_case.to_test_metadata()
```

## JavaParser Utility

The Java utility in `parser/` uses JavaParser to extract:
- Package declarations
- Class names
- Method names
- Annotations with attributes
- Import statements
- Line numbers

### Building the Parser

```bash
cd adapters/java/parser
mvn clean package
```

This creates `target/java-test-parser-1.0.jar` which is used by `ast_parser.py`.

### Parser Output Format

```json
{
  "package": "com.example",
  "className": "LoginTest",
  "imports": [
    "org.junit.jupiter.api.Test",
    "org.junit.jupiter.api.Tag"
  ],
  "annotations": [
    {
      "name": "Tag",
      "attributes": {"value": "\"integration\""}
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
          "name": "Tag",
          "attributes": {"value": "\"smoke\""}
        }
      ]
    }
  ]
}
```

## Migration Path

### Current: Parallel Execution (Hybrid Approach)
- Keep regex-based parsing as fallback
- Use AST when JAR is available
- Compare results for validation

### Next: AST Primary
- Make AST the primary method
- Regex as fallback only

### Future: AST Only
- Remove regex-based parsing
- Full AST coverage

## Benefits for CrossBridge

1. **Accuracy**: No false positives from comments or strings
2. **Rich Metadata**: Extract parameter types, return types, method bodies
3. **Future-Proof**: Easy to add new frameworks or annotations
4. **Coverage Mapping**: AST enables code coverage integration
5. **Impact Analysis**: Understand test dependencies and structure
6. **Refactoring Support**: Suggest test migrations with confidence

## Next Steps

1. ✅ Define neutral models
2. ✅ Create framework detector
3. ✅ Build AST parser wrapper
4. 🔄 Implement JavaParser utility (Java)
5. ⏳ Create JUnit-specific parser
6. ⏳ Create TestNG-specific parser
7. ⏳ Integrate with selenium_java extractor
8. ⏳ Add comprehensive tests
