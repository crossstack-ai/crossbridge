# Execution Intelligence - Enhanced Rule Examples

This document provides comprehensive rule examples aligned with industry-standard execution intelligence patterns.

## Rule Structure

```yaml
rules:
  - id: UNIQUE_ID              # Unique rule identifier
    match_any: ["pattern1"]    # Match if ANY pattern found
    requires_all: ["req1"]     # Must match ALL required patterns (optional)
    excludes: ["excl1"]        # Exclude if ANY exclusion pattern found (optional)
    failure_type: TYPE         # Classification type
    confidence: 0.9            # Base confidence (0.0-1.0)
    priority: 10               # Priority (lower = higher priority)
    framework: framework_name  # Specific framework (optional)
    description: "..."         # Human-readable description
```

## Failure Types

- `PRODUCT_DEFECT` - Real bugs in application code → Fail CI/CD
- `AUTOMATION_DEFECT` - Test code problems (syntax, imports, setup)
- `LOCATOR_ISSUE` - UI element selectors broken/changed
- `ENVIRONMENT_ISSUE` - Infrastructure failures (network, DB, timeouts)
- `FLAKY_TEST` - Intermittent failures, timing issues

## Rule Categories

### 1. Flaky Detection Rules

#### Retry Success Pattern (ChatGPT Blueprint Aligned)
```yaml
- id: FLAKY_RETRY_PASS
  match_any: 
    - "attempt 2"
    - "attempt 3"
    - "retry successful"
    - "passed after retry"
  requires_all:
    - "passed"
  failure_type: FLAKY_TEST
  confidence: 0.85
  priority: 10
  description: "Test passed after retry - likely flaky timing issue"
```

#### Intermittent Timeout
```yaml
- id: FLAKY_INTERMITTENT_TIMEOUT
  match_any:
    - "timeout"
    - "timed out"
  requires_all:
    - "random"
    - "intermittent"
  failure_type: FLAKY_TEST
  confidence: 0.8
  priority: 15
  description: "Random timeout suggests flaky test timing"
```

#### Race Condition Pattern
```yaml
- id: FLAKY_RACE_CONDITION
  match_any:
    - "race condition"
    - "timing issue"
    - "element not ready"
    - "still loading"
  failure_type: FLAKY_TEST
  confidence: 0.9
  priority: 10
  description: "Race condition or timing dependency detected"
```

### 2. Infrastructure Rules (ChatGPT Blueprint Aligned)

#### Network Failure
```yaml
- id: INFRA_NETWORK_ERROR
  match_any:
    - "connection refused"
    - "connection reset"
    - "network error"
    - "network is unreachable"
    - "host is unreachable"
  failure_type: ENVIRONMENT_ISSUE
  confidence: 0.95
  priority: 5
  description: "Infrastructure network connectivity failure"
```

#### DNS Resolution Failure
```yaml
- id: INFRA_DNS_FAILURE
  match_any:
    - "dns resolution failed"
    - "could not resolve hostname"
    - "name or service not known"
    - "getaddrinfo failed"
  failure_type: ENVIRONMENT_ISSUE
  confidence: 0.95
  priority: 5
  description: "DNS resolution failure - infrastructure issue"
```

#### Database Connection
```yaml
- id: INFRA_DATABASE_ERROR
  match_any:
    - "connection to database"
    - "database connection refused"
    - "cannot connect to database"
    - "database timeout"
  failure_type: ENVIRONMENT_ISSUE
  confidence: 0.9
  priority: 10
  description: "Database connectivity issue - infrastructure"
```

#### Service Unavailable
```yaml
- id: INFRA_SERVICE_DOWN
  match_any:
    - "503 Service Unavailable"
    - "502 Bad Gateway"
    - "504 Gateway Timeout"
    - "service not available"
  failure_type: ENVIRONMENT_ISSUE
  confidence: 0.95
  priority: 5
  description: "Backend service unavailable - infrastructure issue"
```

### 3. Product Defect Rules

#### Application Error (5xx)
```yaml
- id: PRODUCT_HTTP_500_ERROR
  match_any:
    - "500 Internal Server Error"
    - "HTTP 500"
  excludes:
    - "mock"
    - "stub"
    - "test server"
  failure_type: PRODUCT_DEFECT
  confidence: 0.9
  priority: 5
  description: "Application returning 500 error - product bug"
```

#### Null Pointer Exception
```yaml
- id: PRODUCT_NULL_POINTER
  match_any:
    - "NullPointerException"
    - "null reference"
    - "cannot read property of null"
    - "undefined is not an object"
  excludes:
    - "test code"
    - "test setup"
  failure_type: PRODUCT_DEFECT
  confidence: 0.85
  priority: 10
  description: "Null pointer in application code - product bug"
```

#### Business Logic Assertion
```yaml
- id: PRODUCT_BUSINESS_LOGIC_FAIL
  match_any:
    - "expected balance"
    - "expected total"
    - "expected result"
  requires_all:
    - "AssertionError"
  excludes:
    - "test data"
    - "mock"
  failure_type: PRODUCT_DEFECT
  confidence: 0.8
  priority: 15
  description: "Business logic assertion failure - likely product bug"
```

### 4. Automation Defect Rules

#### Test Code Syntax Error
```yaml
- id: AUTOMATION_SYNTAX_ERROR
  match_any:
    - "SyntaxError"
    - "IndentationError"
    - "unexpected token"
    - "invalid syntax"
  failure_type: AUTOMATION_DEFECT
  confidence: 1.0
  priority: 1
  description: "Test code syntax error - fix test code"
```

#### Import/Dependency Error
```yaml
- id: AUTOMATION_IMPORT_ERROR
  match_any:
    - "ImportError"
    - "ModuleNotFoundError"
    - "cannot find module"
    - "cannot resolve"
  requires_all:
    - "test"
  failure_type: AUTOMATION_DEFECT
  confidence: 0.95
  priority: 5
  description: "Missing test dependency or import - fix test setup"
```

#### Test Setup Failure
```yaml
- id: AUTOMATION_SETUP_FAILURE
  match_any:
    - "setup failed"
    - "before all failed"
    - "beforeEach failed"
    - "fixture failed"
  failure_type: AUTOMATION_DEFECT
  confidence: 0.9
  priority: 10
  description: "Test setup/fixture failure - fix test infrastructure"
```

### 5. Locator Rules

#### Element Not Found
```yaml
- id: LOCATOR_NOT_FOUND
  match_any:
    - "NoSuchElementException"
    - "element not found"
    - "unable to locate element"
    - "could not find element"
  failure_type: LOCATOR_ISSUE
  confidence: 0.95
  priority: 5
  description: "UI element locator broken or element not present"
```

#### Stale Element Reference
```yaml
- id: LOCATOR_STALE_ELEMENT
  match_any:
    - "StaleElementReferenceException"
    - "stale element"
    - "element is no longer attached"
  failure_type: LOCATOR_ISSUE
  confidence: 0.9
  priority: 10
  description: "Element reference stale - may need wait or re-locate"
```

#### Selector Timeout
```yaml
- id: LOCATOR_SELECTOR_TIMEOUT
  match_any:
    - "selector timeout"
    - "waiting for selector"
    - "element not visible"
  requires_all:
    - "timeout"
  failure_type: LOCATOR_ISSUE
  confidence: 0.85
  priority: 15
  description: "Selector timeout - element may not exist or timing issue"
```

## Framework-Specific Rule Examples

### Selenium (Java/Python)

```yaml
# Selenium-specific patterns
rules:
  - id: SEL_WEBDRIVER_TIMEOUT
    match_any:
      - "TimeoutException"
      - "WebDriverWait"
    framework: selenium
    failure_type: ENVIRONMENT_ISSUE
    confidence: 0.85
    priority: 10
    
  - id: SEL_ELEMENT_CLICK_INTERCEPTED
    match_any:
      - "ElementClickInterceptedException"
      - "click intercepted"
    framework: selenium
    failure_type: LOCATOR_ISSUE
    confidence: 0.9
    priority: 10
```

### Pytest

```yaml
# Pytest-specific patterns
rules:
  - id: PYT_FIXTURE_ERROR
    match_any:
      - "fixture"
      - "@pytest.fixture"
    requires_all:
      - "error"
    framework: pytest
    failure_type: AUTOMATION_DEFECT
    confidence: 0.9
    priority: 10
    
  - id: PYT_ASSERT_FAILED
    match_any:
      - "AssertionError"
      - "assert"
    framework: pytest
    failure_type: PRODUCT_DEFECT
    confidence: 0.8
    priority: 15
```

### Robot Framework

```yaml
# Robot Framework-specific patterns
rules:
  - id: ROB_KEYWORD_FAILED
    match_any:
      - "keyword failed"
      - "execution failed"
    framework: robot
    failure_type: AUTOMATION_DEFECT
    confidence: 0.85
    priority: 10
    
  - id: ROB_ELEMENT_NOT_VISIBLE
    match_any:
      - "element not visible"
      - "element should be visible"
    framework: robot
    failure_type: LOCATOR_ISSUE
    confidence: 0.9
    priority: 10
```

### Playwright

```yaml
# Playwright-specific patterns
rules:
  - id: PLW_NAVIGATION_TIMEOUT
    match_any:
      - "page.goto: Timeout"
      - "navigation timeout"
    framework: playwright
    failure_type: ENVIRONMENT_ISSUE
    confidence: 0.85
    priority: 10
    
  - id: PLW_LOCATOR_ERROR
    match_any:
      - "locator.click: Error"
      - "strict mode violation"
    framework: playwright
    failure_type: LOCATOR_ISSUE
    confidence: 0.9
    priority: 10
```

### Cypress

```yaml
# Cypress-specific patterns
rules:
  - id: CYP_COMMAND_TIMEOUT
    match_any:
      - "cy.get() timed out"
      - "Cypress command timeout"
    framework: cypress
    failure_type: LOCATOR_ISSUE
    confidence: 0.85
    priority: 10
    
  - id: CYP_NETWORK_STUBBING_ERROR
    match_any:
      - "cy.intercept()"
      - "network stub"
    requires_all:
      - "error"
    framework: cypress
    failure_type: AUTOMATION_DEFECT
    confidence: 0.9
    priority: 10
```

## Advanced Rule Patterns

### Multi-Pattern Matching

```yaml
# Requires ALL patterns to match
- id: INFRA_COMPLETE_OUTAGE
  match_any:
    - "timeout"
    - "connection refused"
  requires_all:
    - "all requests failed"
    - "100% failure rate"
  failure_type: ENVIRONMENT_ISSUE
  confidence: 1.0
  priority: 1
  description: "Complete service outage detected"
```

### Exclusion Patterns

```yaml
# Match unless exclusion found
- id: PRODUCT_VALIDATION_ERROR
  match_any:
    - "validation failed"
    - "invalid input"
  excludes:
    - "test data"
    - "mock validation"
    - "expected failure"
  failure_type: PRODUCT_DEFECT
  confidence: 0.85
  priority: 10
  description: "Application validation logic failed"
```

### Regex Patterns (Supported)

```yaml
# Use regex for complex patterns
- id: INFRA_HTTP_RETRY
  match_any:
    - "HTTP [45]\\d{2}"  # 4xx or 5xx
    - "attempt \\d+ of \\d+"  # Retry pattern
  failure_type: ENVIRONMENT_ISSUE
  confidence: 0.8
  priority: 15
```

## Rule Priority Guidelines

**Priority Ranges:**
- **1-10:** Critical, deterministic patterns (exact exception names)
- **11-50:** High confidence patterns (clear signals)
- **51-100:** Medium confidence (may need corroboration)
- **101+:** Low confidence, fallback rules

**Priority Examples:**
```yaml
# Priority 1: Exact match, 100% confident
- id: CRITICAL_SYNTAX
  priority: 1
  confidence: 1.0
  
# Priority 10: Strong pattern
- id: STRONG_SIGNAL
  priority: 10
  confidence: 0.9

# Priority 50: Good pattern but needs context
- id: MEDIUM_SIGNAL
  priority: 50
  confidence: 0.75

# Priority 100: Weak signal, fallback
- id: WEAK_SIGNAL
  priority: 100
  confidence: 0.6
```

## Confidence Scoring Tips

1. **Exact Exception Names:** 0.9-1.0
2. **Clear Error Messages:** 0.8-0.9
3. **Ambiguous Patterns:** 0.6-0.8
4. **Fuzzy Matches:** 0.5-0.7

## Testing Your Rules

```bash
# Test rule matching
python -c "
from core.execution.intelligence.rules.engine import load_rule_pack
pack = load_rule_pack('selenium')
message = 'TimeoutException: Timeout waiting for element'
matches = pack.find_matching_rules(message)
print(f'Matched {len(matches)} rules')
for rule in matches:
    print(f'  {rule.id}: {rule.confidence}')
"
```

## Best Practices

1. **Start Specific, Then Generalize**
   - Begin with exact patterns
   - Add broader patterns only if needed

2. **Use Exclusions Wisely**
   - Exclude test infrastructure patterns
   - Exclude mock/stub scenarios

3. **Layer by Confidence**
   - High confidence rules first (priority 1-10)
   - Medium confidence as fallback (priority 11-50)

4. **Document Your Rules**
   - Clear description explaining the pattern
   - Why this confidence level?

5. **Test with Real Logs**
   - Verify rules match actual failures
   - Adjust confidence based on false positives

## Example: Complete Rule Set

```yaml
# Comprehensive rule set for Selenium Python
name: selenium_python
version: 1.0.0
description: Production-grade rules for Selenium Python automation

rules:
  # Critical infrastructure (Priority 1-10)
  - id: SEL_PY_NETWORK_DOWN
    match_any: ["connection refused", "network unreachable"]
    failure_type: ENVIRONMENT_ISSUE
    confidence: 0.95
    priority: 5
    
  # Product defects (Priority 10-20)
  - id: SEL_PY_HTTP_500
    match_any: ["500 Internal Server Error"]
    failure_type: PRODUCT_DEFECT
    confidence: 0.9
    priority: 10
    
  # Locator issues (Priority 20-30)
  - id: SEL_PY_NO_ELEMENT
    match_any: ["NoSuchElementException"]
    failure_type: LOCATOR_ISSUE
    confidence: 0.95
    priority: 25
    
  # Flaky tests (Priority 30-40)
  - id: SEL_PY_RETRY_SUCCESS
    match_any: ["retry successful"]
    failure_type: FLAKY_TEST
    confidence: 0.85
    priority: 35
    
  # Automation defects (Priority 40-50)
  - id: SEL_PY_IMPORT_ERROR
    match_any: ["ImportError", "ModuleNotFoundError"]
    failure_type: AUTOMATION_DEFECT
    confidence: 0.95
    priority: 45
```

---

**See Also:**
- [Rule Engine Documentation](../rules/engine.py)
- [Unified Configuration Guide](../../UNIFIED_CONFIGURATION_GUIDE.md)
- [Confidence Scoring Algorithm](../confidence/scoring.py)
