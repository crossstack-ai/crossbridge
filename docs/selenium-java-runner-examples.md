# Selenium-Java Runner CLI Examples

## Basic Usage

### Run All Tests
```bash
# Run all tests in the project
python -m cli.main --project-root examples/selenium-java-sample run --framework selenium-java
```

### Run Specific Tests
```bash
# Run specific test class
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tests com.example.LoginTest

# Run multiple test classes
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tests com.example.LoginTest,com.example.UserProfileTest

# Run specific test method
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tests com.example.LoginTest#testValidLogin
```

## Selective Execution

### By Tags (JUnit 5)
```bash
# Run all smoke tests
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tags smoke

# Run multiple tags
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tags smoke,integration
```

### By Groups (TestNG)
```bash
# Run all smoke group tests
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --groups smoke

# Run multiple groups
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --groups smoke,regression
```

### By Categories (JUnit 4)
```bash
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --categories SmokeTests,IntegrationTests
```

## Advanced Features

### Dry Run Mode
```bash
# See what would be executed without running tests
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tests com.example.LoginTest \
  --dry-run
```

**Output:**
```
============================================================
Selenium-Java Test Execution
============================================================
Project: examples/selenium-java-sample
Build Tool: maven
Test Framework: junit5
Report Location: target/surefire-reports
Test Classes: com.example.LoginTest
============================================================

[DRY RUN] Would execute:
  mvn test -B -Dtest=com.example.LoginTest

Run without --dry-run to execute.
```

### Parallel Execution
```bash
# Run tests in parallel with 4 threads
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tags smoke \
  --parallel --threads 4
```

### Custom System Properties
```bash
# Pass custom properties to tests
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tests com.example.LoginTest \
  --properties "browser=chrome,headless=true,timeout=30"
```

### Verbose Output
```bash
# Show detailed execution logs
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tests com.example.LoginTest \
  --verbose
```

## Test Reports

### Standard Output
```
============================================================
Test Execution Result: PASSED
============================================================
Tests Run:    5
Tests Passed: 5
Tests Failed: 0
Tests Skipped: 0
Execution Time: 3.45s
============================================================

Test Reports:
  Location: examples/selenium-java-sample/target/surefire-reports
  JUnit XML: examples/selenium-java-sample/target/surefire-reports/TEST-*.xml
  Text Reports: examples/selenium-java-sample/target/surefire-reports/*.txt

💡 CI Integration: Use these report paths in your CI/CD pipeline
============================================================
```

### Maven Reports Location
```
target/surefire-reports/
├── TEST-com.example.LoginTest.xml
├── TEST-com.example.UserProfileTest.xml
├── com.example.LoginTest.txt
└── com.example.UserProfileTest.txt
```

### Gradle Reports Location
```
build/test-results/test/
├── TEST-com.example.LoginTest.xml
└── TEST-com.example.UserProfileTest.xml

build/reports/tests/test/
└── index.html  (HTML report)
```

## CI/CD Integration

### GitHub Actions
```yaml
name: Selenium Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Java
        uses: actions/setup-java@v3
        with:
          java-version: '11'
          distribution: 'temurin'
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install CrossBridge AI
        run: pip install -e .
      
      - name: Run smoke tests
        run: |
          python -m cli.main --project-root . run \
            --framework selenium-java \
            --tags smoke \
            --parallel --threads 4
      
      - name: Publish test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: target/surefire-reports/
```

### GitLab CI
```yaml
test:
  stage: test
  script:
    - pip install -e .
    - python -m cli.main --project-root . run --framework selenium-java --tags smoke
  artifacts:
    when: always
    reports:
      junit: target/surefire-reports/TEST-*.xml
```

### Jenkins
```groovy
pipeline {
    agent any
    
    stages {
        stage('Test') {
            steps {
                sh 'pip install -e .'
                sh 'python -m cli.main --project-root . run --framework selenium-java --tags smoke'
            }
        }
    }
    
    post {
        always {
            junit 'target/surefire-reports/TEST-*.xml'
        }
    }
}
```

## Impact-Based Execution

### Discover Tests with Page Object Mappings
```bash
python -m cli.main --project-root examples/selenium-java-sample discover \
  --framework selenium-java \
  --include-page-mapping
```

### Find Impacted Tests
```bash
# When LoginPage.java changes
python -m cli.main --project-root examples/selenium-java-sample impact \
  --framework selenium-java \
  --page-object LoginPage
```

**Output:**
```
Page Object: LoginPage
Impacted Tests:
  - com.example.LoginTest (confidence: 0.95)
  - com.example.UserProfileTest (confidence: 0.60)
```

### Run Only Impacted Tests
```bash
# Run tests impacted by LoginPage changes
python -m cli.main --project-root examples/selenium-java-sample run \
  --framework selenium-java \
  --tests com.example.LoginTest,com.example.UserProfileTest
```

## Common Workflows

### Development Workflow
```bash
# 1. Quick smoke test before commit
python -m cli.main --project-root . run --framework selenium-java --tags smoke

# 2. Dry run to verify command
python -m cli.main --project-root . run --framework selenium-java --tags smoke --dry-run

# 3. Run specific failing test
python -m cli.main --project-root . run --framework selenium-java --tests LoginTest#testValidLogin --verbose
```

### CI/CD Workflow
```bash
# 1. Smoke tests on every commit
python -m cli.main --project-root . run --framework selenium-java --tags smoke --parallel --threads 4

# 2. Full regression on main branch
if [ "$BRANCH" = "main" ]; then
  python -m cli.main --project-root . run --framework selenium-java --tags regression
fi

# 3. Publish reports
# Reports are at: target/surefire-reports/*.xml
```

### Change-Based Testing
```bash
# 1. Get changed Page Objects
CHANGED_POS=$(git diff --name-only HEAD~1 | grep "Page.java" | xargs)

# 2. Get impacted tests
IMPACTED_TESTS=$(python -m cli.main --project-root . impact --framework selenium-java --page-object LoginPage | grep "com.example")

# 3. Run only impacted tests
python -m cli.main --project-root . run --framework selenium-java --tests "$IMPACTED_TESTS"
```

## Error Handling

### Maven Not Found
```
Error: Maven not found. Please install Maven or use Maven wrapper (mvnw).
```

**Solution:** Install Maven or ensure it's in PATH

### No Build Tool Found
```
Error: No supported build tool found in /path/to/project. Expected pom.xml (Maven) or build.gradle (Gradle).
```

**Solution:** Run from a Maven/Gradle project directory

### Unsupported Feature
```
Error: Tags are not supported by junit4. Use categories instead.
```

**Solution:** Use correct selective execution feature for your framework:
- JUnit 4: `--categories`
- JUnit 5: `--tags`
- TestNG: `--groups`

## Tips & Best Practices

### Use Dry Run First
```bash
# Always verify command before executing
python -m cli.main --project-root . run --framework selenium-java --tags smoke --dry-run
```

### Combine with Impact Analysis
```bash
# Only run tests affected by changes
python -m cli.main --project-root . impact --framework selenium-java --page-object LoginPage
python -m cli.main --project-root . run --framework selenium-java --tests <impacted_tests>
```

### Use Parallel Execution for Speed
```bash
# Faster test execution
python -m cli.main --project-root . run --framework selenium-java --tags smoke --parallel --threads 4
```

### Save Reports for CI
```bash
# Reports are automatically saved to standard locations
# Maven: target/surefire-reports/*.xml
# Gradle: build/test-results/test/*.xml
```
