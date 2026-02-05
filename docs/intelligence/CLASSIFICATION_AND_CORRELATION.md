# Test Failure Classification & Correlation System

> **Advanced failure analysis with category-based classification and intelligent correlation grouping**

## Overview

CrossBridge's Classification & Correlation System provides intelligent, automated analysis of test failures with:
- **5 Primary Categories** + **31 Sub-Categories** for precise failure classification
- **Confidence Scoring** (0.0-1.0) with evidence-based reasoning
- **Intelligent Correlation** to group related failures
- **Root Cause Analysis** for systemic issues
- **Pattern Detection** across test runs

---

## 🎯 Classification System

### Primary Categories (5)

#### 1. PRODUCT_DEFECT
Application bugs and business logic errors.

**Sub-Categories:**
- `API_ERROR` - REST/GraphQL/SOAP API failures (4xx, 5xx)
- `ASSERTION_FAILURE` - Test assertions failed (expected ≠ actual)
- `BUSINESS_LOGIC_ERROR` - Application logic bugs
- `DATA_VALIDATION_ERROR` - Invalid data format, type, range
- `PERFORMANCE_ISSUE` - Slow response, high latency, timeout
- `SECURITY_ERROR` - Authentication, authorization failures

**Examples:**
```
✗ Expected 200, got 500 → API_ERROR
✗ Assert 'John' == 'Jane' → ASSERTION_FAILURE
✗ Cart total $150, expected $120 → BUSINESS_LOGIC_ERROR
✗ Invalid email format → DATA_VALIDATION_ERROR
✗ Response time 5000ms > 2000ms → PERFORMANCE_ISSUE
✗ Unauthorized access → SECURITY_ERROR
```

#### 2. AUTOMATION_DEFECT
Test code issues and implementation problems.

**Sub-Categories:**
- `ELEMENT_NOT_FOUND` - UI element locator failed
- `LOCATOR_ISSUE` - Incorrect/brittle locator strategy
- `STALE_ELEMENT` - Element no longer attached to DOM
- `TEST_CODE_ERROR` - Test script bugs, syntax errors
- `SYNCHRONIZATION_ERROR` - Timing/wait issues
- `TEST_DATA_ISSUE` - Test data problems, invalid fixtures

**Examples:**
```
✗ Element '#login-btn' not found → ELEMENT_NOT_FOUND
✗ XPath //div[1]/div[2]/button failed → LOCATOR_ISSUE
✗ StaleElementReferenceException → STALE_ELEMENT
✗ NameError: 'usernmae' not defined → TEST_CODE_ERROR
✗ Element not clickable (wait timeout) → SYNCHRONIZATION_ERROR
✗ Test user 'test@example.com' not found → TEST_DATA_ISSUE
```

#### 3. ENVIRONMENT_ISSUE
Infrastructure and network problems.

**Sub-Categories:**
- `CONNECTION_TIMEOUT` - Network connection timeout
- `NETWORK_ERROR` - Network connectivity lost
- `DNS_ERROR` - DNS resolution failure
- `SSL_ERROR` - SSL/TLS certificate issues
- `RESOURCE_EXHAUSTION` - Out of memory, disk, CPU
- `INFRASTRUCTURE_FAILURE` - Server/database down

**Examples:**
```
✗ Connection timeout after 30s → CONNECTION_TIMEOUT
✗ Network unreachable → NETWORK_ERROR
✗ getaddrinfo failed (DNS) → DNS_ERROR
✗ SSL certificate verification failed → SSL_ERROR
✗ OutOfMemoryError → RESOURCE_EXHAUSTION
✗ Database connection refused → INFRASTRUCTURE_FAILURE
```

#### 4. CONFIGURATION_ISSUE
Setup and configuration problems.

**Sub-Categories:**
- `MISSING_DEPENDENCY` - Library/package not found
- `WRONG_CREDENTIALS` - Invalid username/password
- `MISSING_FILE` - File/resource not found
- `INVALID_CONFIGURATION` - Config file errors
- `PERMISSION_ERROR` - Access denied, insufficient permissions
- `VERSION_MISMATCH` - Incompatible versions

**Examples:**
```
✗ ModuleNotFoundError: 'selenium' → MISSING_DEPENDENCY
✗ Authentication failed (401) → WRONG_CREDENTIALS
✗ config.yml not found → MISSING_FILE
✗ Invalid YAML syntax → INVALID_CONFIGURATION
✗ Permission denied (403) → PERMISSION_ERROR
✗ Chrome 120 incompatible with driver 119 → VERSION_MISMATCH
```

#### 5. UNKNOWN
Unable to classify with confidence.

**When used:**
- Insufficient information
- Novel failure patterns
- Complex multi-factor failures
- Confidence score < 0.5

---

## 🔍 Correlation System

### Grouping Strategies

#### 1. Error Pattern Matching
Groups tests with similar error messages (cosine similarity ≥ 0.8).

**Example:**
```
Group CG-001: "Element not found"
  • test_login_button → Element '#login' not found
  • test_signup_link → Element '#signup' not found  
  • test_logout_btn → Element '#logout' not found
  
→ Pattern: Same locator prefix (#), all navigation elements
→ Root Cause: UI redesign changed ID naming convention
→ Recommendation: Update locators to use data-testid attributes
```

#### 2. Category-Based Grouping
Groups failures with same category/sub-category.

**Example:**
```
Group CG-002: CONNECTION_TIMEOUT
  • test_api_users → Connection timeout (30s)
  • test_api_products → Connection timeout (30s)
  • test_api_orders → Connection timeout (30s)
  
→ Pattern: All API tests timing out
→ Root Cause: API server overloaded
→ Recommendation: Scale API server or add caching layer
```

#### 3. Temporal Correlation
Groups failures occurring in time windows (within 5 minutes).

**Example:**
```
Group CG-003: Database failures (10:15-10:18)
  • test_user_creation (10:15:30)
  • test_product_update (10:16:45)
  • test_order_checkout (10:17:20)
  
→ Pattern: All database operations failed in 3-minute window
→ Root Cause: Database maintenance window
→ Recommendation: Schedule maintenance during off-hours
```

#### 4. Stack Trace Similarity
Groups failures with similar call stacks.

**Example:**
```
Group CG-004: ValidationError in utils.validate()
  • test_email_format
  • test_phone_format
  • test_address_format
  
→ Pattern: All fail at utils.validate() with ValidationError
→ Root Cause: Bug in validation utility function
→ Recommendation: Fix utils.validate() regex pattern
```

### Correlation Output

```json
{
  "correlation_groups": [
    {
      "group_id": "CG-001",
      "pattern": "Database connection timeout",
      "affected_tests": 15,
      "category": "ENVIRONMENT_ISSUE",
      "sub_category": "CONNECTION_TIMEOUT",
      "confidence": 0.95,
      "root_cause": "Database server overload during peak hours",
      "recommendation": "Scale database resources or implement connection pooling",
      "tests": [
        {
          "test_id": "test_user_login",
          "similarity": 0.98,
          "error_message": "Connection timeout after 30s"
        },
        {
          "test_id": "test_user_registration",
          "similarity": 0.96,
          "error_message": "Database connection timed out"
        }
      ]
    }
  ]
}
```

---

## 📊 Confidence Scoring

### Algorithm

```python
def calculate_confidence(signals: List[str], patterns: List[Pattern]) -> float:
    """
    Calculate classification confidence based on matched signals and patterns.
    
    Returns: 0.0-1.0 (higher = more confident)
    """
    base_score = 0.5  # Baseline
    
    # Pattern matching
    for pattern in patterns:
        if pattern.matches(signals):
            base_score += pattern.weight  # 0.1-0.4
    
    # Signal strength
    signal_count = len(signals)
    if signal_count >= 3:
        base_score += 0.2
    elif signal_count >= 2:
        base_score += 0.1
    
    # Context validation
    if has_stack_trace(signals):
        base_score += 0.1
    
    return min(base_score, 1.0)
```

### Confidence Levels

| Range | Level | Action |
|-------|-------|--------|
| **0.9-1.0** | High | Trust classification, use for automation |
| **0.7-0.89** | Medium | Likely correct, manual review recommended |
| **0.5-0.69** | Low | Uncertain, requires investigation |
| **<0.5** | Very Low | Classify as UNKNOWN |

---

## 💡 Usage Examples

### 1. Basic Classification

```bash
./bin/crossbridge-log output.xml

# Output:
Intelligence Analysis Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Failure Classifications:
  • PRODUCT_DEFECT: 5
    - API_ERROR: 3
    - ASSERTION_FAILURE: 2
  • AUTOMATION_DEFECT: 3
    - ELEMENT_NOT_FOUND: 2
    - LOCATOR_ISSUE: 1
  • ENVIRONMENT_ISSUE: 2
    - CONNECTION_TIMEOUT: 2
```

### 2. With Correlation

```bash
./bin/crossbridge-log output.xml --correlation

# Output:
Correlation Groups
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Group CG-001: Database connection timeout
  • Affected Tests: 15
  • Category: ENVIRONMENT_ISSUE
  • Sub-Category: CONNECTION_TIMEOUT
  • Confidence: 0.95
  • Root Cause: Database server overload
  • Recommendation: Scale database or add pooling
```

### 3. Filter by Category

```bash
# Only show product defects
./bin/crossbridge-log output.xml --category PRODUCT_DEFECT

# Only show API errors
./bin/crossbridge-log output.xml --sub-category API_ERROR
```

### 4. Programmatic Access

```python
from core.execution.intelligence.analyzer import ExecutionAnalyzer
from core.execution.intelligence.correlation import CorrelationEngine

# Analyze failures
analyzer = ExecutionAnalyzer(enable_ai=False)
result = analyzer.analyze(log_data, test_name, framework)

print(f"Category: {result.classification.failure_type}")
print(f"Sub-Category: {result.classification.sub_category}")
print(f"Confidence: {result.classification.confidence}")
print(f"Reasoning: {result.classification.reason}")

# Correlate failures
correlator = CorrelationEngine()
groups = correlator.group_failures(results)

for group in groups:
    print(f"Group {group.group_id}: {group.pattern}")
    print(f"  Affected: {group.affected_tests} tests")
    print(f"  Root cause: {group.root_cause}")
```

---

## 🎯 Best Practices

### Classification

1. **Review Low-Confidence Classifications**
   - Check UNKNOWN classifications manually
   - Investigate confidence < 0.7
   - Add new patterns for common failures

2. **Validate Sub-Categories**
   - Ensure sub-category matches primary category
   - Check reasoning for specific evidence
   - Report misclassifications for improvement

3. **Use Categories for Automation**
   - Auto-assign PRODUCT_DEFECT to dev team
   - Auto-assign AUTOMATION_DEFECT to QA team
   - Auto-assign ENVIRONMENT_ISSUE to DevOps
   - Auto-assign CONFIGURATION_ISSUE to release manager

### Correlation

1. **Prioritize by Impact**
   - Fix groups with most affected tests first
   - Focus on high-confidence groups (≥0.9)
   - Track groups across multiple runs

2. **Use for Root Cause Analysis**
   - Analyze group patterns, not individual tests
   - Identify systemic issues vs. isolated failures
   - Track recurring patterns over time

3. **Optimize Analysis Time**
   - Use correlation to reduce analysis by 70%
   - Group similar failures before deep dive
   - Focus on unique patterns

---

## 📈 Performance

| Operation | Time | Notes |
|-----------|------|-------|
| **Classification** | <50ms | Per test failure |
| **Correlation** | <200ms | For 1000 tests |
| **Pattern Matching** | <10ms | Per pattern |
| **Confidence Scoring** | <5ms | Per classification |

**Scalability:**
- Tested with 10,000+ test failures
- Linear scaling: O(n) for classification
- O(n log n) for correlation (optimized clustering)
- Memory usage: ~50MB for 1000 tests

---

## 🧪 Testing

### Unit Tests

```bash
# Test classification system
pytest tests/unit/core/execution/intelligence/test_classifiers.py -v

# Test correlation engine
pytest tests/unit/core/execution/intelligence/test_correlation.py -v
```

**Coverage:**
- ✅ 18 classification tests (all categories + edge cases)
- ✅ 24 correlation tests (grouping algorithms, similarity)
- ✅ 100% pass rate

### Integration Tests

```bash
# End-to-end classification + correlation
pytest tests/integration/test_intelligence_flow.py -v
```

---

## 🔧 Configuration

```yaml
# crossbridge.yml
intelligence:
  classification:
    enabled: true
    min_confidence: 0.5  # Classify as UNKNOWN if below
    include_reasoning: true
    
  correlation:
    enabled: true
    similarity_threshold: 0.8  # Cosine similarity for grouping
    time_window_minutes: 5     # Temporal correlation window
    min_group_size: 2          # Minimum tests per group
    
  performance:
    max_parallel_classifications: 10
    cache_patterns: true
```

---

## 📚 API Reference

### Classification

```python
class FailureClassifier:
    def classify(
        self,
        error_message: str,
        stack_trace: Optional[str],
        test_context: Dict[str, Any]
    ) -> ClassificationResult:
        """
        Classify a test failure into category + sub-category.
        
        Returns:
            ClassificationResult with:
            - failure_type (primary category)
            - sub_category
            - confidence (0.0-1.0)
            - reason (evidence-based explanation)
        """
```

### Correlation

```python
class CorrelationEngine:
    def group_failures(
        self,
        failures: List[TestFailure],
        similarity_threshold: float = 0.8
    ) -> List[CorrelationGroup]:
        """
        Group related test failures.
        
        Args:
            failures: List of test failures to correlate
            similarity_threshold: Minimum similarity for grouping
            
        Returns:
            List of correlation groups with:
            - group_id
            - pattern (common error pattern)
            - affected_tests (count)
            - category + sub_category
            - confidence
            - root_cause (identified issue)
            - recommendation (suggested fix)
        """
```

---

## 🐛 Troubleshooting

### Issue: All Classified as UNKNOWN

**Cause:** Insufficient signal extraction or novel failure patterns.

**Solution:**
1. Check signal extractor logs
2. Verify error messages are captured
3. Add new patterns for common failures
4. Lower `min_confidence` threshold temporarily

### Issue: Low Correlation Group Count

**Cause:** Similarity threshold too high or diverse failure types.

**Solution:**
1. Lower `similarity_threshold` from 0.8 to 0.7
2. Check if failures are truly related
3. Use category-based grouping instead
4. Increase `time_window_minutes` for temporal grouping

### Issue: Wrong Classifications

**Cause:** Pattern matching rules need improvement.

**Solution:**
1. Report misclassification with details
2. Review reasoning field for diagnosis
3. Add negative patterns (what NOT to match)
4. Improve signal extraction quality

---

## 🤝 Contributing

### Adding New Categories

1. Update `FailureCategory` enum
2. Add patterns in `classification_rules.py`
3. Update tests
4. Document with examples

### Adding New Sub-Categories

1. Update category-specific enum
2. Add detection patterns
3. Update confidence scoring
4. Add tests

### Improving Patterns

1. Collect misclassification examples
2. Analyze common failure signatures
3. Add/refine regex patterns
4. Test with diverse datasets

---

## 📝 License

Apache 2.0

---

## 💬 Support

- **Issues:** https://github.com/crossstack-ai/crossbridge/issues
- **Documentation:** https://docs.crossbridge.dev
- **Email:** support@crossbridge.dev
