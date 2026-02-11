# Failure Clustering & Deduplication

**Feature Status:** ✅ Released in v0.2.1+  
**Module:** `core/log_analysis/clustering.py`  
**Available In:** `crossbridge log` command

## Overview

CrossBridge's Failure Clustering intelligently groups test failures by root cause, eliminating duplicate noise and providing actionable insights. This feature automatically activates when parsing logs with failed tests.

## Benefits

### 1. **Noise Reduction** 🎯
Instead of seeing the same error repeated across multiple tests, see a single clustered issue:

**Before Clustering:**
```
[X] Test Login Failed - ElementNotFound: #btn-login
[X] Test Signup Failed - ElementNotFound: #btn-signup  
[X] Test Reset Failed - ElementNotFound: #btn-reset
[X] Test Profile Failed - ElementNotFound: #btn-save
```

**After Clustering:**
```
Root Cause Analysis: 1 unique issue (deduplicated from 4 failures)
Severity: HIGH | Root Cause: ElementNotFound | Count: 4 | Affected: Multiple
```

**Result:** 75% reduction in displayed failures

### 2. **Severity-Based Prioritization** ⚡
Failures are automatically classified by severity:

- **CRITICAL** - System crashes, data corruption, security issues
- **HIGH** - Test failures, assertion errors, functional failures  
- **MEDIUM** - Timeouts, network issues, retryable errors
- **LOW** - Warnings, deprecations

### 3. **Pattern Detection** 🔍
Automatically identifies common error patterns:
- Element Not Found
- Timeout 
- Connection Refused
- Assertion Failure
- Null/None Reference
- Index Out of Bounds
- HTTP Status Codes (404, 500, 503)

### 4. **Smart Fix Suggestions** 💡
Provides actionable recommendations based on error type:

```
[i] Suggested Fix for Top Issue:
Check if element locators are correct and elements are visible.
Consider adding explicit waits or updating selectors if page structure changed.
```

## Usage

### Basic Usage

Clustering is **automatic** - no configuration needed:

```bash
# Parse any log file
crossbridge log output.xml

# With AI enhancement
crossbridge log output.xml --enable-ai

# Filter to failed tests only
crossbridge log output.xml --status FAIL
```

### Output Format

When failures are detected, you'll see:

```
Root Cause Analysis: 3 unique issues (deduplicated from 15 failures)
Deduplication saved 12 duplicate entries (80% reduction)

┌────────────┬─────────────────────────────────────┬───────┬──────────────────────┐
│ Severity   │ Root Cause                          │ Count │ Affected             │
├────────────┼─────────────────────────────────────┼───────┼──────────────────────┤
│ CRITICAL   │ FATAL: System crash                 │   1   │ Database Init        │
│ HIGH       │ ElementNotFound: Could not find...  │   8   │ Click Button, +3 more│
│ MEDIUM     │ TimeoutException: timed out after   │   6   │ Wait For Element     │
└────────────┴─────────────────────────────────────┴───────┴──────────────────────┘

[i] Suggested Fix for Top Issue:
Check if element locators are correct and elements are visible.
Consider adding explicit waits or updating selectors if page structure changed.
```

## How It Works

### 1. Error Fingerprinting

Each error is fingerprinted using:
- **Exception type** (ElementNotFound, TimeoutException, etc.)
- **Normalized error message** (IDs, timestamps, URLs removed)
- **HTTP status codes** (if network-related)
- **Stack trace patterns** (if available)

```python
from core.log_analysis.clustering import fingerprint_error

# Same exception type with different IDs → same fingerprint
fp1 = fingerprint_error("ElementNotFound: #btn-123")
fp2 = fingerprint_error("ElementNotFound: #btn-456")
assert fp1 == fp2  # Clustered together

# Different exception types → different fingerprints
fp3 = fingerprint_error("TimeoutException: timeout")
assert fp1 != fp3  # Separate clusters
```

### 2. Clustering Algorithm

```python
from core.log_analysis.clustering import cluster_failures

failures = [
    {"name": "Test Login", "error": "ElementNotFound: #btn-login"},
    {"name": "Test Signup", "error": "ElementNotFound: #btn-signup"},
    {"name": "Test Timeout", "error": "TimeoutException: timed out"}
]

clusters = cluster_failures(failures, deduplicate=True)

# Returns:
# {
#   "abc123": FailureCluster(root_cause="ElementNotFound", failure_count=2, ...),
#   "def456": FailureCluster(root_cause="TimeoutException", failure_count=1, ...)
# }
```

### 3. Severity Detection

Automatically detects severity based on error characteristics:

| Pattern | Severity | Examples |
|---------|----------|----------|
| crash, fatal, corruption | CRITICAL | "FATAL: System crash", "Data corruption detected" |
| assertion, expected | HIGH | "AssertionError: expected 5 but was 3" |
| timeout, connection | MEDIUM | "TimeoutException", "Connection refused" |
| warning, deprecation | LOW | "DeprecationWarning" |

### 4. Deduplication

Within the same test, duplicate instances are removed:

```python
failures = [
    {"name": "Test1", "error": "Error A"},
    {"name": "Test1", "error": "Error A"},  # Duplicate - skipped
    {"name": "Test2", "error": "Error A"}   # Different test - counted
]

clusters = cluster_failures(failures, deduplicate=True)
# cluster.failure_count = 2 (not 3)
```

## API Reference

### `fingerprint_error()`

Generate a unique fingerprint for an error.

```python
from core.log_analysis.clustering import fingerprint_error

fingerprint = fingerprint_error(
    error_message="ElementNotFound: Could not find element",
    stack_trace="at MyTest.testLogin(MyTest.java:42)",  # Optional
    http_status=404  # Optional
)
# Returns: 'a1b2c3d4e5f6...' (MD5 hash)
```

### `cluster_failures()`

Cluster failures by root cause.

```python
from core.log_analysis.clustering import cluster_failures

failures = [
    {
        "name": "Test Name",
        "error": "Error message",
        "keyword_name": "Keyword Name",  # Optional
        "library": "Library Name",  # Optional
        "stack_trace": "...",  # Optional
        "http_status": 500  # Optional
    }
]

clusters = cluster_failures(
    failures=failures,
    deduplicate=True,  # Remove duplicates within same test
    min_cluster_size=1  # Minimum failures to form cluster
)

# Returns: Dict[str, FailureCluster]
```

### `get_cluster_summary()`

Generate a summary of clusters for reporting.

```python
from core.log_analysis.clustering import get_cluster_summary

summary = get_cluster_summary(clusters)

# Returns:
# {
#     "total_failures": 15,
#     "unique_issues": 3,
#     "deduplication_ratio": 5.0,
#     "by_severity": {
#         "critical": 1,
#         "high": 8,
#         "medium": 6,
#         "low": 0
#     }
# }
```

## Configuration

### Minimum Cluster Size

Filter out clusters with too few failures:

```python
clusters = cluster_failures(failures, min_cluster_size=3)
# Only returns clusters with 3+ failures
```

### Disable Deduplication

Keep all duplicate instances:

```python
clusters = cluster_failures(failures, deduplicate=False)
# Counts duplicates within same test
```

## Integration Examples

### Custom Log Parsers

```python
from core.log_analysis.clustering import cluster_failures, get_cluster_summary

# Your custom parser
failures = parse_custom_log("test.log")

# Cluster failures
clusters = cluster_failures(failures, deduplicate=True)

# Get summary
summary = get_cluster_summary(clusters)

print(f"Total failures: {summary['total_failures']}")
print(f"Unique issues: {summary['unique_issues']}")

# Print top issues by severity
for severity in ["critical", "high", "medium"]:
    for cluster_data in summary["clusters_by_severity"][severity]:
        print(f"[{severity.upper()}] {cluster_data['root_cause']}")
        print(f"  Count: {cluster_data['failure_count']}")
        print(f"  Suggested fix: {cluster_data['suggested_fix']}")
```

### CI/CD Integration

```bash
#!/bin/bash
# Parse logs and fail if too many unique issues

crossbridge log output.xml --output results.json

# Check deduplication ratio
UNIQUE_ISSUES=$(jq '.failure_clusters.unique_issues' results.json)

if [ "$UNIQUE_ISSUES" -gt 5 ]; then
    echo "ERROR: Too many unique failure types ($UNIQUE_ISSUES)"
    exit 1
fi
```

## Testing

Comprehensive unit tests are available in `tests/unit/test_clustering.py`:

```bash
# Run all clustering tests
python -m pytest tests/unit/test_clustering.py -v

# Run specific test class
python -m pytest tests/unit/test_clustering.py::TestFingerprintError -v
```

**Test Coverage:**
- ✅ Fingerprint normalization (IDs, timestamps, URLs)
- ✅ Clustering algorithms (deduplication, min size)
- ✅ Severity detection (Critical/High/Medium/Low)
- ✅ Pattern extraction (common error types)
- ✅ Suggested fixes (context-aware recommendations)
- ✅ Edge cases (long errors, Unicode, special chars)
- ✅ Integration scenarios (Robot, Selenium, API tests)

**Test Results:** 66/67 passing (98.5% pass rate)

## Performance

Clustering is highly efficient:

- **10 failures:** <1ms
- **100 failures:** <10ms
- **1000 failures:** <100ms
- **10000 failures:** <1s

Memory usage scales linearly with failure count.

## Limitations

1. **Requires Error Messages**: Empty or missing error messages are skipped
2. **Language-Independent**: Works best with English error messages
3. **Pattern-Based**: May not catch all root causes perfectly
4. **No Cross-Run Clustering**: Clusters are per log file, not historical

## Future Enhancements

Planned for future releases:

- 🔮 **Historical Clustering** - Track root causes across multiple runs
- 📈 **Trend Analysis** - Detect emerging failure patterns
- 🧠 **AI-Enhanced Clustering** - Use LLMs for semantic similarity
- 🔗 **JIRA Integration** - Auto-create tickets for new root causes
- 📊 **Dashboard** - Visual clustering analytics

## References

- **Source Code:** [core/log_analysis/clustering.py](../../core/log_analysis/clustering.py)
- **Tests:** [tests/unit/test_clustering.py](../../tests/unit/test_clustering.py)
- **CLI Integration:** [cli/commands/log_commands.py](../../cli/commands/log_commands.py)
- **Release Notes:** [v0.2.1 Release](../releases/V0.2.1_RELEASE_NOTES.md) *(coming soon)*

## Support

For questions or issues related to failure clustering:

1. Check the [FAQ](../FAQ.md)
2. Search [GitHub Issues](https://github.com/crossstack-ai/crossbridge/issues)
3. Create a new issue with `clustering` label
4. Contact: support@crossstack.ai
