# Flaky Test Detection - CrossBridge

## Overview

CrossBridge's flaky test detection system uses machine learning (Isolation Forest) to identify intermittently failing tests across all frameworks. The system is:

- **Framework-agnostic**: Works with JUnit, Cucumber, Pytest, Robot, and more
- **ML-powered**: Uses Isolation Forest for anomaly detection
- **Confidence-based**: Provides reliability scores for classifications
- **Production-ready**: Includes database persistence, CLI commands, and comprehensive reporting

## What is a Flaky Test?

A test is considered **flaky** if it:
- Fails intermittently without code changes
- Sometimes passes, sometimes fails on the same commit
- Has varying failure reasons (non-deterministic)
- Is timing-sensitive, infrastructure-sensitive, or order-dependent

Flaky tests are **NOT**:
- Tests that consistently fail
- Tests that fail due to broken infrastructure
- Tests that fail due to actual bugs

## Architecture

```
Test Execution (Any Framework)
        ↓
Normalized Execution Records (TestExecutionRecord)
        ↓
Feature Engineering (10 statistical features)
        ↓
Isolation Forest ML Model
        ↓
Flaky Score + Classification + Confidence
        ↓
Database Persistence + Reporting
```

## Quick Start

### 1. Import Test Results

```bash
# Import JUnit XML results
crossbridge flaky import \
  --db-url "postgresql://localhost/crossbridge" \
  --result-file "target/surefire-reports/TEST-*.xml" \
  --framework junit \
  --git-commit $(git rev-parse HEAD) \
  --environment ci

# Import Cucumber JSON results
crossbridge flaky import \
  --db-url "postgresql://localhost/crossbridge" \
  --result-file "target/cucumber-report.json" \
  --framework cucumber \
  --git-commit $(git rev-parse HEAD)
```

### 2. Analyze for Flakiness

After collecting 20-30 executions per test:

```bash
crossbridge flaky analyze \
  --db-url "postgresql://localhost/crossbridge" \
  --days 30 \
  --min-executions 15 \
  --output flaky-report.json
```

### 3. List Flaky Tests

```bash
# List all flaky tests
crossbridge flaky list \
  --db-url "postgresql://localhost/crossbridge" \
  --min-confidence 0.7

# List only critical flaky tests
crossbridge flaky list \
  --db-url "postgresql://localhost/crossbridge" \
  --severity critical \
  --format json
```

### 4. View Statistics

```bash
crossbridge flaky stats \
  --db-url "postgresql://localhost/crossbridge"
```

## Core Concepts

### 1. Normalized Execution Record

All test results are converted to a framework-agnostic format:

```python
from core.flaky_detection import TestExecutionRecord, TestFramework, TestStatus

record = TestExecutionRecord(
    test_id="com.example.TestClass.testMethod",
    framework=TestFramework.JUNIT,
    status=TestStatus.PASSED,
    duration_ms=150.5,
    executed_at=datetime.now(),
    error_signature="AssertionError: Expected value",
    git_commit="abc123",
    environment="ci",
    tags=["smoke", "critical"]
)
```

### 2. Feature Engineering

10 statistical features are extracted from execution history:

| Feature | Description | Flaky Indicator |
|---------|-------------|-----------------|
| **failure_rate** | Failures / total runs | 0.1 - 0.9 range |
| **pass_fail_switch_rate** | Status changes / transitions | > 0.3 |
| **duration_variance** | Variance in execution time | High variance |
| **duration_cv** | Coefficient of variation (std/mean) | > 0.5 |
| **retry_success_rate** | Successful retries / retries | > 0.5 |
| **avg_retry_count** | Average retries per run | > 1.0 |
| **unique_error_count** | Distinct error types | > 2 |
| **error_diversity_ratio** | Unique errors / failures | > 0.5 |
| **same_commit_failure_rate** | Failures on same commit | 0.2 - 0.8 |
| **recent_failure_rate** | Failures in last N runs | > 0.3 |

### 3. ML Model (Isolation Forest)

**Why Isolation Forest?**
- Unsupervised learning (no labeled data needed)
- Excellent for outlier/anomaly detection
- Flaky tests are outliers in the stable test population
- Handles multi-dimensional features well

**How it works:**
1. Trains on all tests (stable + flaky)
2. Identifies anomalous patterns
3. Lower anomaly score = more flaky
4. Binary classification: flaky vs. stable

### 4. Confidence Scoring

Confidence is based on data availability:

```
confidence = min(1.0, total_executions / 30)
```

| Executions | Confidence | Reliability |
|-----------|-----------|-------------|
| < 15 | < 0.5 | Insufficient data |
| 15-30 | 0.5-1.0 | Suspected flaky |
| ≥ 30 | 1.0 | High confidence |

### 5. Severity Classification

| Severity | Failure Rate | Confidence | Description |
|----------|-------------|-----------|-------------|
| **Critical** | ≥ 50% | ≥ 0.5 | Fails half the time |
| **High** | 30-49% | ≥ 0.5 | Frequent failures |
| **Medium** | 15-29% | ≥ 0.5 | Occasional failures |
| **Low** | < 15% | ≥ 0.5 | Rare failures |

## Database Schema

### Tables

1. **test_execution**: Stores all test execution records
2. **flaky_test**: Current flaky test detection results
3. **flaky_test_history**: Historical trend data

### Setup

```bash
# Apply schema
psql -d crossbridge -f core/flaky_detection/schema.sql
```

Or programmatically:

```python
from core.flaky_detection.persistence import FlakyDetectionRepository

repo = FlakyDetectionRepository("postgresql://localhost/crossbridge")
repo.create_tables()
```

## Python API

### Basic Usage

```python
from core.flaky_detection import (
    FlakyDetector,
    FeatureEngineer,
    TestExecutionRecord,
    TestFramework
)
from core.flaky_detection.persistence import FlakyDetectionRepository

# Initialize
repo = FlakyDetectionRepository("postgresql://localhost/crossbridge")
engineer = FeatureEngineer()
detector = FlakyDetector()

# Get execution history
executions = repo.get_executions_by_test("com.example.Test.method")

# Extract features
features = engineer.extract_features(executions)

# Train model (do once with all tests)
all_executions = repo.get_all_test_executions()
all_features = engineer.extract_batch_features(all_executions)
detector.train(list(all_features.values()))

# Detect flakiness
result = detector.detect(features, TestFramework.JUNIT, "My Test")

print(f"Flaky: {result.is_flaky}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Severity: {result.severity}")
print(f"Indicators: {result.primary_indicators}")

# Save result
repo.save_flaky_result(result)
```

### Framework Integration

```python
from core.flaky_detection.integrations import convert_test_results
from pathlib import Path

# Convert Cucumber results
records = convert_test_results(
    result_file=Path("target/cucumber-report.json"),
    framework=TestFramework.CUCUMBER,
    git_commit="abc123",
    environment="ci"
)

# Save to database
repo.save_executions_batch(records)
```

## CLI Commands

### `crossbridge flaky analyze`

Analyze tests for flakiness using ML.

**Options:**
- `--db-url`: Database connection URL (required)
- `--framework`: Filter by framework (default: all)
- `--days`: Days of history to analyze (default: 30)
- `--min-executions`: Minimum executions required (default: 15)
- `--output`: Save JSON report to file

**Example:**
```bash
crossbridge flaky analyze \
  --db-url "postgresql://localhost/crossbridge" \
  --framework cucumber \
  --days 60 \
  --output report.json
```

### `crossbridge flaky list`

List detected flaky tests.

**Options:**
- `--db-url`: Database connection URL (required)
- `--min-confidence`: Minimum confidence threshold (default: 0.5)
- `--severity`: Filter by severity (critical/high/medium/low)
- `--framework`: Filter by framework
- `--format`: Output format (table/json/csv, default: table)

**Example:**
```bash
crossbridge flaky list \
  --db-url "postgresql://localhost/crossbridge" \
  --severity critical \
  --format json > critical-flaky.json
```

### `crossbridge flaky import`

Import test results into database.

**Options:**
- `--db-url`: Database connection URL (required)
- `--result-file`: Test result file path (required)
- `--framework`: Framework type (junit/cucumber/pytest/robot, required)
- `--git-commit`: Git commit SHA
- `--environment`: Test environment (default: unknown)
- `--build-id`: CI build identifier

**Example:**
```bash
crossbridge flaky import \
  --db-url "postgresql://localhost/crossbridge" \
  --result-file "target/surefire-reports/TEST-*.xml" \
  --framework junit \
  --git-commit $(git rev-parse HEAD) \
  --environment ci \
  --build-id ${CI_BUILD_ID}
```

### `crossbridge flaky stats`

Show flaky test statistics.

**Options:**
- `--db-url`: Database connection URL (required)

**Example:**
```bash
crossbridge flaky stats --db-url "postgresql://localhost/crossbridge"
```

## Best Practices

### 1. Data Collection

- **Collect at least 20-30 executions** per test for reliable detection
- **Run tests across different commits** to capture true flakiness
- **Include environment metadata** (CI, local, staging, etc.)
- **Track git commits** to detect same-commit failures

### 2. CI/CD Integration

```yaml
# Example: GitHub Actions
name: Test and Analyze Flakiness

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Run Tests
        run: mvn test
      
      - name: Import Results
        if: always()
        run: |
          crossbridge flaky import \
            --db-url "${{ secrets.DB_URL }}" \
            --result-file "target/surefire-reports/TEST-*.xml" \
            --framework junit \
            --git-commit ${{ github.sha }} \
            --environment ci \
            --build-id ${{ github.run_id }}
      
      - name: Analyze Flakiness
        run: |
          crossbridge flaky analyze \
            --db-url "${{ secrets.DB_URL }}" \
            --output flaky-report.json
      
      - name: Upload Report
        uses: actions/upload-artifact@v2
        with:
          name: flaky-report
          path: flaky-report.json
```

### 3. Monitoring

- **Run analysis weekly** to catch new flaky tests early
- **Track trends** using the flaky_test_history table
- **Set up alerts** for critical flaky tests
- **Review indicators** to understand root causes

### 4. Remediation

When a flaky test is detected:

1. **Review indicators** - Understand why it's flaky
2. **Examine error patterns** - Look for common themes
3. **Check timing** - Look for duration variance
4. **Fix or quarantine** - Either fix the test or isolate it

## Limitations & Future Work

### Current Limitations

- **Requires historical data**: Need 15-30 executions per test
- **Static model**: Model doesn't auto-retrain (yet)
- **No step-level analysis**: BDD scenarios analyzed as a whole
- **No root cause identification**: System identifies flakiness but not causes

### Planned Enhancements (Release Stage+)

- [ ] Auto-retraining when new data arrives
- [ ] Per-framework feature tuning
- [ ] Step-level flakiness for BDD
- [ ] Root cause clustering (similar flaky patterns)
- [ ] AI-powered repair suggestions
- [ ] Predictive quarantine (before CI failure)
- [ ] Integration with test execution (skip flaky tests)

## Troubleshooting

### "Insufficient training data"

**Problem**: < 10 tests with execution history

**Solution**: Import more test results. Need at least 10 tests with 15+ executions each.

### Low confidence scores

**Problem**: Tests classified as "insufficient_data"

**Solution**: Run tests more times. Need 15-30 executions for reliable classification.

### Model not detecting obvious flaky tests

**Problem**: Known flaky tests not flagged

**Possible causes:**
- Not enough execution variance in data
- Test always fails or always passes (not flaky, just broken)
- Infrastructure issues (not test flakiness)

**Solution**: Review feature values. If failure_rate is 100% or 0%, test is not flaky.

### Database connection errors

**Problem**: Can't connect to PostgreSQL

**Solution**: 
- Verify database is running
- Check connection string format
- Ensure database exists
- Check firewall/network settings

## FAQ

**Q: How many test executions do I need?**  
A: Minimum 15 for "suspected flaky", 30+ for high confidence detection.

**Q: Does this work with all test frameworks?**  
A: Yes, as long as you can convert results to TestExecutionRecord format.

**Q: Can I use this without a database?**  
A: Not currently. Database is required for historical tracking.

**Q: How accurate is the detection?**  
A: With 30+ executions, confidence is typically 80-95%. Accuracy depends on data quality.

**Q: What if my entire test suite is unstable?**  
A: Isolation Forest assumes most tests are stable. If >30% are flaky, results may be unreliable.

**Q: Can this detect flaky tests caused by test order dependencies?**  
A: Yes, if the order dependency causes intermittent failures. Feature: pass_fail_switch_rate.

## References

- [Isolation Forest Paper](https://cs.nju.edu.cn/zhouzh/zhouzh.files/publication/icdm08b.pdf)
- [Google's Flaky Test Research](https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html)
- [Microsoft's Flaky Test Detection](https://www.microsoft.com/en-us/research/publication/predicting-flaky-tests-at-microsoft/)

## License

Part of CrossBridge platform. See main project LICENSE.
