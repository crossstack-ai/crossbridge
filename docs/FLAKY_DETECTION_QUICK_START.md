# Flaky Test Detection - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Start PostgreSQL
```bash
docker run -d \
  --name crossbridge-db \
  -e POSTGRES_DB=crossbridge \
  -e POSTGRES_USER=crossbridge \
  -e POSTGRES_PASSWORD=crossbridge \
  -p 5432:5432 \
  postgres:15
```

### 2. Set Environment Variable
```bash
export CROSSBRIDGE_DB_URL="postgresql://crossbridge:crossbridge@localhost:5432/crossbridge"
```

### 3. Initialize Database
```bash
python -c "from core.flaky_detection.persistence import FlakyDetectionRepository; FlakyDetectionRepository('$CROSSBRIDGE_DB_URL').create_tables()"
```

### 4. Run Detection
```bash
# Store test results first
pytest --json-report --json-report-file=results.json
python scripts/store_test_results.py results.json

# Run flaky detection
crossbridge flaky detect --days 30
```

---

## 📋 CLI Commands

### Detect Flaky Tests
```bash
crossbridge flaky detect                    # Analyze last 30 days
crossbridge flaky detect --days 60          # Custom time window
crossbridge flaky detect --framework pytest # Filter by framework
crossbridge flaky detect --output report.json --verbose
```

### List Flaky Tests
```bash
crossbridge flaky list                      # All flaky tests
crossbridge flaky list --severity critical  # Only critical
crossbridge flaky list --framework junit    # Filter by framework
crossbridge flaky list --limit 20           # Limit results
```

### View Test Report
```bash
crossbridge flaky report test_login         # Detailed report for specific test
```

### Export Results
```bash
crossbridge flaky export flaky_tests.json              # JSON export
crossbridge flaky export flaky_tests.csv --format csv  # CSV export
```

---

## 🔧 CI/CD Integration

### GitHub Actions (Minimal)
```yaml
- name: Detect Flaky Tests
  env:
    CROSSBRIDGE_DB_URL: ${{ secrets.DB_URL }}
  run: |
    pytest --json-report --json-report-file=results.json
    python scripts/store_test_results.py results.json
    crossbridge flaky detect --output flaky_report.json
```

### GitLab CI (Minimal)
```yaml
flaky_detection:
  script:
    - pytest --json-report --json-report-file=results.json
    - python scripts/store_test_results.py results.json
    - crossbridge flaky detect
  variables:
    CROSSBRIDGE_DB_URL: $DB_CONNECTION_STRING
```

---

## 📊 Grafana Dashboard

### Import Dashboard
1. Navigate to **Dashboards** → **Import**
2. Upload `grafana/flaky_test_dashboard.json`
3. Select PostgreSQL datasource
4. Click **Import**

### Dashboard Panels
- **Flaky Test Summary** - Total count
- **Severity Distribution** - Critical/High/Medium/Low breakdown
- **Trend Chart** - 30-day history
- **Top 10 Flaky Tests** - Most problematic tests
- **Framework Breakdown** - Tests by framework
- **Test Execution Status** - Real-time pass/fail

---

## 🎯 Key Features

### ML-Based Detection
- **Isolation Forest** algorithm with 200 trees
- 10 feature analysis: failure rate, timing variance, retry patterns, error diversity
- Confidence scoring based on execution history

### External Test Management
- **TestRail** integration: Map flaky tests to TestRail IDs
- **Zephyr** integration: Link to Zephyr test cases
- **qTest** integration: Associate with qTest cases

### Severity Classification
- **CRITICAL**: >80% failure rate, high confidence
- **HIGH**: 60-80% failure rate
- **MEDIUM**: 40-60% failure rate  
- **LOW**: 20-40% failure rate

---

## 🔍 Example Output

```
📋 DETECTION RESULTS
==================
Total tests:      45
Flaky detected:   3 (6.7%)
Stable tests:     42 (93.3%)

By Severity:
   🔴 CRITICAL  1 test(s)
   🟠 HIGH      1 test(s)
   🟡 MEDIUM    1 test(s)

❌ test_login
   Classification: FLAKY
   Framework:      pytest
   Flaky Score:    0.842
   Confidence:     95%
   External IDs:   testrail:C12345
   Severity:       CRITICAL
   Failure Rate:   85.0%
   Indicators:
      • High failure rate (85.0%)
      • Frequent pass/fail switching (78.9%)
      • Often succeeds on retry (65.0%)
```

---

## 📈 Typical Workflow

### Week 1: Setup & Baseline
1. Deploy PostgreSQL database
2. Configure CI pipeline to store test results
3. Run `crossbridge flaky detect` after test runs
4. Establish baseline metrics

### Week 2: Monitoring
1. Import Grafana dashboard
2. Monitor flaky test trends
3. Review weekly reports
4. Identify critical tests

### Week 3: Action
1. Create tickets for critical flaky tests
2. Add TestRail/Zephyr IDs to tests
3. Prioritize fixes by severity + business impact
4. Track fix effectiveness

### Week 4: Optimization
1. Reduce false positives by adjusting confidence threshold
2. Set up Slack/email notifications
3. Add quality gates to CI (fail on critical flaky tests)
4. Document flaky test patterns

---

## 🛠️ Advanced Configuration

### Custom Detection Config
```python
from core.flaky_detection import FlakyDetectionConfig, FlakyDetector

config = FlakyDetectionConfig(
    n_estimators=300,              # More trees = better accuracy
    contamination=0.15,            # Expected % of flaky tests
    min_confidence_threshold=0.8,  # Higher = fewer false positives
    min_executions_for_analysis=15 # More history = better confidence
)

detector = FlakyDetector(config)
```

### Database Maintenance
```bash
# Clean up old records (keep last 90 days)
python -c "
from core.flaky_detection.persistence import FlakyDetectionRepository
repo = FlakyDetectionRepository('$CROSSBRIDGE_DB_URL')
deleted = repo.cleanup_old_executions(days_to_keep=90)
print(f'Deleted {deleted} old records')
"
```

---

## 🐛 Troubleshooting

### "Insufficient tests for training"
**Problem**: Need at least 10 tests with ≥10 executions each  
**Solution**: Reduce `--min-executions` or increase `--days`

### "Database not configured"
**Problem**: CROSSBRIDGE_DB_URL not set  
**Solution**: `export CROSSBRIDGE_DB_URL="postgresql://..."`

### "No test executions found"
**Problem**: Test results not stored in database  
**Solution**: Run `python scripts/store_test_results.py results.json` after tests

### Database Connection Timeout
**Problem**: Cannot connect to PostgreSQL  
**Solution**: Verify database is running: `psql "$CROSSBRIDGE_DB_URL" -c "SELECT 1"`

---

## 📚 Full Documentation

- **Complete Guide**: [CI_CD_FLAKY_INTEGRATION.md](CI_CD_FLAKY_INTEGRATION.md)
- **Demo Script**: Run `python demo_flaky_detection.py`
- **API Reference**: See `core/flaky_detection/` module docs

---

## 🎓 Best Practices

1. **Run Detection Daily**: Catch flaky tests early
2. **Track Trends**: Monitor flaky test count over time
3. **Fix Critical First**: High failure rate + high impact
4. **Use External IDs**: Map to TestRail/Zephyr for tracking
5. **Set Quality Gates**: Block deployments with critical flaky tests
6. **Clean Database**: Remove old executions (90-day retention)
7. **Review Weekly**: Team review of flaky test dashboard
8. **Document Patterns**: Common causes and solutions

---

## 💡 Tips

- **Minimum Data**: Need 10+ tests with 10+ executions each for ML training
- **Confidence Matters**: Higher confidence (>0.8) = more reliable detection
- **External IDs**: Use pytest markers: `@pytest.mark.testrail("C12345")`
- **Batch Analysis**: Analyze larger time windows (30-60 days) for better accuracy
- **False Positives**: Adjust `contamination` rate if too many stable tests flagged

---

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/crossstack-ai/crossbridge/issues)
- **Docs**: https://docs.crossstack.ai/crossbridge
- **Email**: support@crossstack.ai
