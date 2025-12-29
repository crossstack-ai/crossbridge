# Selenium-Java Sample Project

Sample Maven project for testing CrossBridge AI Selenium-Java runner.

## Structure

```
selenium-java-sample/
├── pom.xml                           # Maven configuration
├── src/
│   ├── main/java/com/example/pages/
│   │   └── LoginPage.java           # Page Object
│   └── test/java/com/example/
│       ├── LoginTest.java           # Login tests (3 tests, tags: smoke, regression)
│       └── UserProfileTest.java     # Profile tests (2 tests, tags: smoke, regression)
```

## Running Tests with CrossBridge AI

### Run All Tests in a Class
```bash
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tests com.example.LoginTest
```

### Run Specific Test Method
```bash
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tests com.example.LoginTest#testValidLogin
```

### Run Multiple Test Classes
```bash
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tests com.example.LoginTest,com.example.UserProfileTest
```

### Run Tests by Tag
```bash
# Run all smoke tests
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tags smoke

# Run regression tests
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tags regression
```

### Discover Tests with Page Object Mappings
```bash
python -m cli.main --project-root examples/selenium-java-sample discover \
  --framework selenium-java \
  --include-page-mapping
```

## Running Tests Directly with Maven

```bash
cd examples/selenium-java-sample

# Run all tests
mvn test

# Run specific test class
mvn test -Dtest=LoginTest

# Run specific method
mvn test -Dtest=LoginTest#testValidLogin

# Run tests by tag
mvn test -Dgroups=smoke
```

## Test Details

### LoginTest (3 tests)
- `testValidLogin` - @Tag("smoke")
- `testInvalidLogin` - @Tag("smoke")  
- `testLoginWithEmptyCredentials` - @Tag("regression")

### UserProfileTest (2 tests)
- `testViewProfile` - @Tag("smoke")
- `testEditProfile` - @Tag("regression")

**Total: 5 tests** (3 smoke, 2 regression)
