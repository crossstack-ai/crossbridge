# Unified Configuration Guide: Framework Rules in crossbridge.yml

## Overview

**Enhancement**: All framework-specific rule configurations can now be defined directly in `crossbridge.yml` instead of requiring separate YAML files for each framework.

**Benefits**:
- ✅ Single source of truth for all configuration
- ✅ No need to know which YAML file to edit
- ✅ Consistent with Crossbridge's single-config philosophy
- ✅ Easier for beginners
- ✅ Better for CI/CD (one file to manage)
- ✅ Backward compatible with existing individual YAML files

---

## How It Works

### 1. Priority System

The rule loading follows this priority:

```
1. crossbridge.yml → execution.intelligence.rules.<framework>
2. Framework-specific YAML → rules/<framework>.yaml
3. Generic fallback → rules/generic.yaml
```

### 2. Configuration Location

Add your rules under `execution.intelligence.rules` in crossbridge.yml:

```yaml
execution:
  framework: selenium  # Your chosen framework
  
  intelligence:
    ai_enabled: true
    
    # All framework rules in one place
    rules:
      selenium:
        - id: SEL_001
          description: Element locator issues
          match_any:
            - NoSuchElementException
            - StaleElementReferenceException
          failure_type: AUTOMATION_DEFECT
          confidence: 0.90
          priority: 10
      
      pytest:
        - id: PYT_001
          description: Fixture failures
          match_any:
            - fixture
            - "@pytest.fixture"
          failure_type: AUTOMATION_DEFECT
          confidence: 0.85
          priority: 15
      
      robot:
        - id: ROB_001
          description: Keyword failures
          match_any:
            - "Keyword"
            - "No keyword with name"
          failure_type: AUTOMATION_DEFECT
          confidence: 0.88
          priority: 12
```

### 3. Automatic Loading

The system automatically loads rules based on your framework setting:

```python
# User sets framework
execution:
  framework: selenium

# System automatically loads
execution.intelligence.rules.selenium
```

---

## Configuration Structure

### Rule Definition Format

Each rule follows this structure:

```yaml
- id: UNIQUE_ID              # Required: Unique identifier (e.g., SEL_001)
  description: "..."         # Required: Human-readable description
  match_any: [...]          # Required: List of patterns to match
  excludes: [...]           # Optional: Patterns to exclude
  failure_type: TYPE        # Required: AUTOMATION_DEFECT|PRODUCT_DEFECT|ENVIRONMENT_ISSUE
  confidence: 0.0-1.0       # Required: Confidence score (0.0 to 1.0)
  priority: 1-100           # Required: Priority (lower = more important)
```

### Failure Types

```yaml
AUTOMATION_DEFECT:      # Test/framework issues (locators, timeouts, fixtures)
PRODUCT_DEFECT:         # Application bugs (assertions, 5xx errors)
ENVIRONMENT_ISSUE:      # Infrastructure problems (connections, resources)
```

### Example Rules by Framework

#### Selenium
```yaml
selenium:
  - id: SEL_001
    description: Element locator not found or stale
    match_any:
      - NoSuchElementException
      - StaleElementReferenceException
    failure_type: AUTOMATION_DEFECT
    confidence: 0.90
    priority: 10
  
  - id: SEL_PROD_001
    description: Server errors (5xx)
    match_any:
      - "500 Internal Server Error"
      - "502 Bad Gateway"
    failure_type: PRODUCT_DEFECT
    confidence: 0.95
    priority: 5
```

#### Pytest
```yaml
pytest:
  - id: PYT_001
    description: Fixture failures
    match_any:
      - fixture
      - "@pytest.fixture"
    failure_type: AUTOMATION_DEFECT
    confidence: 0.85
    priority: 15
  
  - id: PYT_PROD_001
    description: Assertion failures
    match_any:
      - AssertionError
      - assert
    excludes:
      - fixture
    failure_type: PRODUCT_DEFECT
    confidence: 0.90
    priority: 10
```

#### Robot Framework
```yaml
robot:
  - id: ROB_001
    description: Keyword failures
    match_any:
      - "Keyword"
      - "No keyword with name"
    failure_type: AUTOMATION_DEFECT
    confidence: 0.88
    priority: 12
  
  - id: ROB_PROD_001
    description: Test assertions failed
    match_any:
      - "should be equal"
      - "should contain"
    failure_type: PRODUCT_DEFECT
    confidence: 0.90
    priority: 10
```

---

## Usage Examples

### Example 1: Basic Setup (Selenium)

```yaml
execution:
  framework: selenium
  source_root: ./src/test/java
  
  intelligence:
    ai_enabled: true
    
    rules:
      selenium:
        - id: SEL_001
          description: Element locator issues
          match_any:
            - NoSuchElementException
            - StaleElementReferenceException
          failure_type: AUTOMATION_DEFECT
          confidence: 0.90
          priority: 10
        
        - id: SEL_002
          description: Timeout waiting for element
          match_any:
            - TimeoutException
            - "wait timeout"
          failure_type: AUTOMATION_DEFECT
          confidence: 0.85
          priority: 15
```

### Example 2: Multi-Framework Setup

```yaml
execution:
  framework: pytest  # Active framework
  
  intelligence:
    rules:
      # Rules for all your frameworks
      pytest:
        - id: PYT_001
          # ... pytest rules
      
      selenium:
        - id: SEL_001
          # ... selenium rules
      
      robot:
        - id: ROB_001
          # ... robot rules
      
      # Generic fallback
      generic:
        - id: GEN_001
          description: Null pointer errors
          match_any:
            - NullPointerException
            - "'NoneType'"
          failure_type: PRODUCT_DEFECT
          confidence: 0.85
          priority: 20
```

### Example 3: Custom Rules

```yaml
execution:
  framework: selenium
  
  intelligence:
    rules:
      selenium:
        # Standard rules
        - id: SEL_001
          description: Element locator issues
          match_any:
            - NoSuchElementException
          failure_type: AUTOMATION_DEFECT
          confidence: 0.90
          priority: 10
        
        # Custom rule for your app
        - id: CUSTOM_001
          description: Custom app authentication failure
          match_any:
            - "AuthenticationException"
            - "Invalid credentials"
          failure_type: PRODUCT_DEFECT
          confidence: 0.95
          priority: 5
```

---

## Migration from Individual YAML Files

### Step 1: Locate Your Current Rules

```bash
# Find your current rule files
ls core/execution/intelligence/rules/
# Output: selenium.yaml, pytest.yaml, robot.yaml, etc.
```

### Step 2: Copy Rules to crossbridge.yml

```yaml
# Before (individual files)
# File: rules/selenium.yaml
rules:
  - id: SEL_001
    description: ...

# After (unified config)
# File: crossbridge.yml
execution:
  intelligence:
    rules:
      selenium:
        - id: SEL_001
          description: ...
```

### Step 3: Test

```bash
# Run tests to verify rules load correctly
crossbridge run --framework selenium

# Check which rules were loaded
crossbridge rules list
```

### Step 4: Optional Cleanup

```bash
# Individual YAML files can be kept as backup/fallback
# Or removed if you prefer unified config only
rm core/execution/intelligence/rules/selenium.yaml
```

---

## Backward Compatibility

The system maintains full backward compatibility:

### ✅ Scenario 1: Rules in crossbridge.yml
```yaml
# crossbridge.yml
execution:
  intelligence:
    rules:
      selenium: [...]

# Result: Loads from crossbridge.yml
```

### ✅ Scenario 2: No rules in crossbridge.yml, YAML file exists
```yaml
# crossbridge.yml
execution:
  intelligence:
    # No rules section

# rules/selenium.yaml exists
# Result: Loads from selenium.yaml
```

### ✅ Scenario 3: Neither exists
```yaml
# crossbridge.yml has no rules
# selenium.yaml doesn't exist

# Result: Loads from generic.yaml
```

---

## Advanced Features

### 1. Environment-Specific Rules

```yaml
# Development environment
development:
  execution:
    intelligence:
      rules:
        selenium:
          - id: DEV_001
            description: Relaxed timeouts for dev
            confidence: 0.70

# Production environment  
production:
  execution:
    intelligence:
      rules:
        selenium:
          - id: PROD_001
            description: Strict validation
            confidence: 0.95
```

### 2. Conditional Rule Loading

```yaml
execution:
  intelligence:
    rules:
      selenium:
        # Load different rules based on conditions
        - id: SEL_CI_001
          description: CI-specific timeout handling
          match_any:
            - "CI timeout"
          failure_type: ENVIRONMENT_ISSUE
          confidence: 0.85
          priority: 15
          # Only active in CI environments
```

### 3. Rule Inheritance

```yaml
execution:
  intelligence:
    rules:
      # Base rules for all Selenium variants
      selenium:
        - id: BASE_001
          description: Common element issues
          match_any:
            - NoSuchElementException
          failure_type: AUTOMATION_DEFECT
          confidence: 0.90
          priority: 10
      
      # Selenium Java inherits selenium rules + adds own
      selenium_java:
        # Inherits selenium rules automatically
        - id: JAVA_001
          description: Java-specific exceptions
          match_any:
            - WebDriverException
          failure_type: AUTOMATION_DEFECT
          confidence: 0.88
          priority: 12
```

---

## CLI Commands

### List Available Rules

```bash
# Show all rules for current framework
crossbridge rules list

# Show rules for specific framework
crossbridge rules list --framework selenium

# Show where rules are loaded from
crossbridge rules list --show-source
```

### Validate Configuration

```bash
# Validate crossbridge.yml structure
crossbridge config validate

# Check rule syntax
crossbridge rules validate

# Test rule matching
crossbridge rules test "NoSuchElementException occurred"
```

### Export Rules

```bash
# Export rules to separate YAML file
crossbridge rules export --framework selenium --output rules/selenium.yaml

# Export all frameworks
crossbridge rules export --all --output-dir rules/
```

---

## Troubleshooting

### Issue: Rules Not Loading

**Check 1**: Verify crossbridge.yml structure
```yaml
execution:
  intelligence:
    rules:
      <framework>:  # Must match execution.framework
        - id: ...
```

**Check 2**: Check framework name
```bash
# List supported frameworks
crossbridge frameworks list

# Common names: selenium, pytest, robot, playwright, etc.
```

**Check 3**: Enable debug logging
```bash
crossbridge run --log-level debug
# Look for: "Loaded X rules from crossbridge.yml"
```

### Issue: Rules Not Matching

**Check 1**: Test rule matching
```bash
crossbridge rules test "Your error message here"
```

**Check 2**: Check confidence threshold
```yaml
# Lower confidence threshold if needed
intelligence:
  min_confidence: 0.70  # Default: 0.80
```

**Check 3**: Verify match patterns
```yaml
rules:
  - id: TEST_001
    match_any:
      - "exact string"      # Case-insensitive substring match
      - "regex pattern"     # Supports patterns
```

---

## Best Practices

### 1. Start Simple
```yaml
# Begin with 3-5 core rules
selenium:
  - id: SEL_001  # Element issues
  - id: SEL_002  # Timeouts
  - id: SEL_PROD_001  # Server errors
```

### 2. Use Descriptive IDs
```yaml
# Good
- id: SEL_ELEMENT_NOT_FOUND
- id: PYT_FIXTURE_FAILURE

# Avoid
- id: RULE_001
- id: TEST_1
```

### 3. Set Appropriate Confidence
```yaml
# High confidence (0.90-1.0): Very specific patterns
- id: SEL_001
  match_any: ["NoSuchElementException"]
  confidence: 0.95

# Medium confidence (0.70-0.89): Common patterns
- id: SEL_002
  match_any: ["timeout", "wait"]
  confidence: 0.80

# Low confidence (0.50-0.69): Generic patterns
- id: GEN_001
  match_any: ["error", "failed"]
  confidence: 0.60
```

### 4. Use Priority Effectively
```yaml
# Critical product bugs (priority 1-10)
- id: PROD_001
  description: Server 500 errors
  priority: 5

# Automation issues (priority 10-20)
- id: AUTO_001
  description: Element locator issues
  priority: 15

# Minor issues (priority 20+)
- id: ENV_001
  description: Network timeouts
  priority: 25
```

### 5. Leverage Excludes
```yaml
# Avoid false positives
- id: PYT_PROD_001
  description: Assertion failures
  match_any:
    - AssertionError
    - assert
  excludes:
    - fixture       # Exclude fixture-related assertions
    - setup failed  # Exclude setup issues
  failure_type: PRODUCT_DEFECT
```

---

## Support

For questions or issues:
- Documentation: `docs/advanced_capabilities/`
- CLI help: `crossbridge rules --help`
- Examples: `crossbridge.yml` (this file)
- GitHub: Report issues or request features

---

## Framework Coverage

All 12 frameworks supported in unified configuration:

| Framework | Key | Example Rules |
|-----------|-----|---------------|
| Selenium | `selenium` | Element locators, timeouts |
| Pytest | `pytest` | Fixtures, assertions |
| Robot Framework | `robot` | Keywords, test assertions |
| Playwright | `playwright` | Selectors, navigation |
| REST Assured | `restassured` | API responses, assertions |
| Cypress | `cypress` | Commands, assertions |
| Cucumber | `cucumber` | Steps, scenario hooks |
| Behave | `behave` | Steps, fixtures |
| JUnit | `junit` | Assertions, setup |
| TestNG | `testng` | Assertions, configuration |
| SpecFlow | `specflow` | Steps, bindings |
| NUnit | `nunit` | Assertions, setup |

Each framework has 14-20 pre-configured rules available in individual YAML files or can be customized in crossbridge.yml.
