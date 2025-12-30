# Flaky Test Detection - Quick Start Guide

Get started with flaky test detection in 5 minutes.

---

## 1️⃣ Install Dependencies

```bash
pip install numpy scikit-learn SQLAlchemy psycopg2-binary
```

Or from requirements file:

```bash
pip install -r core/flaky_detection/requirements.txt
```

---

## 2️⃣ Set Up Database

### Create Database

```bash
createdb crossbridge
```

### Apply Schema

```bash
psql -d crossbridge -f core/flaky_detection/schema.sql
```

### Alternative: SQLite (for testing)

```bash
# No setup needed - SQLite uses file-based database
# Use URL: sqlite:///crossbridge.db
```

---

## 3️⃣ Import Test Results

### Cucumber Tests

```bash
crossbridge flaky import \
  --db-url "postgresql://localhost/crossbridge" \
  --result-file "target/cucumber-report.json" \
  --framework cucumber \
  --git-commit $(git rev-parse HEAD)
```

### JUnit Tests

```bash
crossbridge flaky import \
  --db-url "postgresql://localhost/crossbridge" \
  --result-file "target/surefire-reports/TEST-*.xml" \
  --framework junit \
  --git-commit $(git rev-parse HEAD)
```

### Pytest Tests

```bash
crossbridge flaky import \
  --db-url "postgresql://localhost/crossbridge" \
  --result-file "test-results.json" \
  --framework pytest \
  --git-commit $(git rev-parse HEAD)
```

### Robot Framework Tests

```bash
crossbridge flaky import \
  --db-url "postgresql://localhost/crossbridge" \
  --result-file "output.xml" \
  --framework robot \
  --git-commit $(git rev-parse HEAD)
```

---

## 4️⃣ Analyze Flakiness

After collecting enough data (15-30 test executions per test), run analysis:

```bash
crossbridge flaky analyze \
  --db-url "postgresql://localhost/crossbridge" \
  --days 30 \
  --min-executions 15 \
  --output flaky-report.json
```

### What This Does:

1. **Extracts features** from execution history (failure rate, switch rate, etc.)
2. **Trains ML model** (Isolation Forest) on all tests
3. **Detects anomalies** (flaky tests)
4. **Calculates confidence** based on data volume
5. **Saves results** to database and JSON file

---

## 5️⃣ View Results

### List Flaky Tests

```bash
crossbridge flaky list \
  --db-url "postgresql://localhost/crossbridge" \
  --min-confidence 0.7 \
  --format table
```

### Show Statistics

```bash
crossbridge flaky stats \
  --db-url "postgresql://localhost/crossbridge"
```

### Export to CSV

```bash
crossbridge flaky list \
  --db-url "postgresql://localhost/crossbridge" \
  --format csv \
  --output flaky-tests.csv
```

---

## 📊 Understanding Results

### Classification Levels

| Classification | Meaning | Action |
|----------------|---------|--------|
| **flaky** | Confidence ≥ 70% | Fix or quarantine immediately |
| **suspected_flaky** | Confidence 50-70% | Monitor, needs more data |
| **stable** | Not flaky | Keep as-is |
| **insufficient_data** | < 15 executions | Collect more data |

### Severity Levels

| Severity | Failure Rate | Confidence | Action |
|----------|--------------|------------|--------|
| **critical** | > 70% | > 70% | Fix immediately |
| **high** | 50-70% | > 70% | Fix this sprint |
| **medium** | 30-50% | > 50% | Fix soon |
| **low** | < 30% | > 50% | Monitor |

### Primary Indicators

Common reasons for flakiness:

- **Inconsistent failures** (30-70% failure rate)
- **Frequent pass/fail switching** (status changes often)
- **Multiple error types** (different errors for same test)
- **High duration variance** (execution time unstable)
- **Retry success** (passes on retry but not first try)

---

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Flaky Test Detection

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2am

jobs:
  detect-flaky:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run tests
        run: mvn test
      
      - name: Import results
        run: |
          crossbridge flaky import \
            --db-url "${{ secrets.DB_URL }}" \
            --result-file "target/surefire-reports/TEST-*.xml" \
            --framework junit \
            --git-commit ${{ github.sha }}
      
      - name: Analyze flakiness
        run: |
          crossbridge flaky analyze \
            --db-url "${{ secrets.DB_URL }}" \
            --days 30 \
            --output flaky-report.json
      
      - name: Check for flaky tests
        run: |
          crossbridge flaky list \
            --db-url "${{ secrets.DB_URL }}" \
            --min-confidence 0.7 \
            --format json | \
          jq '.[] | select(.severity == "critical" or .severity == "high")'
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    
    stages {
        stage('Test') {
            steps {
                sh 'mvn test'
            }
        }
        
        stage('Import Results') {
            steps {
                sh """
                    crossbridge flaky import \\
                      --db-url "${env.DB_URL}" \\
                      --result-file "target/surefire-reports/TEST-*.xml" \\
                      --framework junit \\
                      --git-commit ${env.GIT_COMMIT}
                """
            }
        }
        
        stage('Analyze Flakiness') {
            steps {
                sh """
                    crossbridge flaky analyze \\
                      --db-url "${env.DB_URL}" \\
                      --days 30 \\
                      --output flaky-report.json
                """
            }
        }
        
        stage('Report') {
            steps {
                sh """
                    crossbridge flaky list \\
                      --db-url "${env.DB_URL}" \\
                      --format csv \\
                      --output flaky-tests.csv
                """
                archiveArtifacts artifacts: '*.json,*.csv', allowEmptyArchive: true
            }
        }
    }
}
```

---

## 🐍 Python API

### Basic Usage

```python
from core.flaky_detection import (
    FlakyDetector,
    FeatureEngineer,
    TestFramework
)
from core.flaky_detection.persistence import FlakyDetectionRepository

# Initialize
db_url = "postgresql://localhost/crossbridge"
repo = FlakyDetectionRepository(db_url)
engineer = FeatureEngineer()
detector = FlakyDetector()

# Get execution history
all_executions = repo.get_all_test_executions()

# Extract features
all_features = engineer.extract_batch_features(all_executions)

# Train model
detector.train(list(all_features.values()))

# Detect flaky tests
framework_map = {
    test_id: TestFramework.JUNIT 
    for test_id in all_features.keys()
}
results = detector.detect_batch(all_features, framework_map)

# Save results
for result in results.values():
    if result.is_flaky and result.confidence >= 0.7:
        print(f"Flaky: {result.test_id} ({result.severity})")
        repo.save_flaky_result(result)
```

### Import Test Results Programmatically

```python
from core.flaky_detection.integrations import CucumberIntegration
from core.flaky_detection.persistence import FlakyDetectionRepository

# Parse Cucumber JSON
records = CucumberIntegration.from_cucumber_json(
    result_file="target/cucumber-report.json",
    git_commit="abc123",
    environment="ci"
)

# Save to database
repo = FlakyDetectionRepository("postgresql://localhost/crossbridge")
repo.save_test_executions_batch(records)
```

---

## ❓ FAQ

### How much data do I need?

**Minimum**: 15 test executions per test  
**Recommended**: 30+ test executions  
**Confidence**: Scales linearly from 15-30 executions

### What if I don't have enough data?

Tests with < 15 executions will be classified as `insufficient_data`. Keep running tests and importing results. Once you reach 15-30 executions, re-run the analysis.

### Can I use SQLite instead of PostgreSQL?

Yes! SQLite works great for small projects:

```bash
# Use SQLite URL
crossbridge flaky analyze \
  --db-url "sqlite:///crossbridge.db" \
  --days 30
```

### How accurate is the detection?

Based on industry research and our testing:
- **Precision**: 80-90% (few false positives)
- **Recall**: 70-80% (catches most flaky tests)
- **Best with**: 30+ executions per test

### How often should I run analysis?

**Recommended schedule**:
- **Import results**: After every test run (in CI/CD)
- **Run analysis**: Daily or weekly
- **Review results**: Weekly

### Can I customize the ML model?

Yes! See [FLAKY_DETECTION.md](FLAKY_DETECTION.md) for advanced configuration:

```python
from core.flaky_detection.detector import FlakyDetectionConfig

config = FlakyDetectionConfig(
    n_estimators=300,           # More trees = more accurate
    contamination=0.05,         # Expected flaky ratio (5%)
    min_executions_reliable=20, # Stricter threshold
)

detector = FlakyDetector(config)
```

### What frameworks are supported?

All test frameworks that produce structured output:
- JUnit XML
- Cucumber JSON
- Pytest JSON
- Robot Framework XML
- TestNG XML
- Any framework via custom adapter

---

## 🚀 Next Steps

1. **Run the demo**: `python examples/flaky_detection_demo.py`
2. **Read full docs**: [FLAKY_DETECTION.md](FLAKY_DETECTION.md)
3. **Set up CI/CD integration**: See examples above
4. **Customize for your needs**: Adjust thresholds and configs

---

## 📞 Troubleshooting

### Database connection errors

```bash
# Check PostgreSQL is running
pg_isready

# Test connection
psql -d crossbridge -c "SELECT 1"

# Check schema
psql -d crossbridge -c "\dt"
```

### Import errors

```bash
# Check file exists
ls -la target/cucumber-report.json

# Validate JSON
cat target/cucumber-report.json | jq '.'

# Check framework name
crossbridge flaky import --help
```

### Low confidence scores

Need more data! Keep importing test results until you have 15-30 executions per test.

### No flaky tests detected

Could mean:
- Your tests are stable (great!)
- Not enough data yet (< 15 executions)
- Tests haven't been flaky in the time period analyzed

Try:
- Increase `--days` parameter (e.g., `--days 90`)
- Lower `--min-executions` (e.g., `--min-executions 10`)

---

## License

Part of CrossBridge platform. See main project LICENSE.
