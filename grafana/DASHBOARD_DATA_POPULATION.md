# Dashboard Data Population Guide

This guide explains how to populate sample test data for all 3 Grafana dashboards in the CrossBridge Intelligence Platform.

## Prerequisites

1. **Install psycopg2-binary** (PostgreSQL Python adapter):
   ```bash
   pip install psycopg2-binary
   ```

2. **PostgreSQL Database Access**:
   - Host: 10.60.67.247
   - Port: 5432
   - Database: cbridge-sidecar-stage1-unit-test
   - User: postgres
   - Password: admin

## Dashboards Covered

This data population script generates sample data for:

1. **AI Intelligence Dashboard** (`ai_intelligence_dashboard.json`)
   - 19 panels covering AI metrics, confidence, cost, tokens
   - Regression and flaky test detection
   - AI model performance comparison

2. **Execution Intelligence Dashboard** (`execution_intelligence_dashboard.json`)
   - Failure classification (Infrastructure vs Product vs Test Code)
   - CI/CD decision support
   - Confidence score trends

3. **Test Execution & Trend Analysis Dashboard** (`test_execution_trends_dashboard.json`)
   - Pass/fail rate trends
   - Test performance and duration tracking
   - Test stability scoring
   - Framework adoption trends

## Database Tables

The script populates the following PostgreSQL tables:

### test_runs
Stores test execution metadata:
- `test_name`: Name of the test
- `framework`: Testing framework (pytest, robot, jest, etc.)
- `status`: Test status (passed, failed, skipped)
- `duration_ms`: Execution duration in milliseconds
- `error_message`: Error message if failed
- `created_at`: Timestamp of execution
- `environment`: Environment (qa, stage, prod, local)
- `branch`: Git branch name

### failure_clusters
Stores AI-analyzed failure data:
- `test_run_id`: Foreign key to test_runs
- `cluster_id`: Unique cluster identifier
- `failure_message`: Failure description
- `root_cause`: AI-determined root cause
- `domain`: Failure domain (Product, Infrastructure, Test Code)
- `severity`: Severity level (low, medium, high, critical)
- `confidence_score`: AI confidence (0.0-1.0)
- `is_regression`: Boolean flag for new regressions
- `is_flaky`: Boolean flag for flaky tests
- `is_fixed`: Boolean flag for resolved failures
- `ai_model`: AI model used (gpt-4, claude-3-opus, etc.)

### ai_metrics
Stores detailed AI performance metrics:
- `cluster_id`: Reference to failure cluster
- `ai_model`: AI model used
- `confidence_score`: Analysis confidence
- `response_time_ms`: AI response time
- `tokens_used`: Token consumption
- `cost_usd`: Cost in USD
- `cache_hit`: Boolean for cache hits
- `error_occurred`: Boolean for AI errors
- `framework`: Testing framework

### analysis_summary
Stores CI/CD decision data:
- `framework`: Testing framework
- `total_failures`: Count of total failures
- `should_fail_ci`: Boolean CI/CD decision
- `confidence_score`: Overall confidence
- `infrastructure_count`: Infrastructure failures
- `product_count`: Product failures
- `test_code_count`: Test code failures

## Running the Data Population Script

### Option 1: Direct Python Execution (Recommended)
```bash
cd d:/Future-work2/crossbridge
python tests/integration/test_populate_dashboard_data.py
```

This will:
1. Connect to PostgreSQL
2. Create tables if they don't exist
3. Generate 7 days of test data (210 test runs)
4. Create failure clusters with AI analysis
5. Populate AI performance metrics
6. Generate CI/CD decision summaries
7. Display verification statistics

Expected output:
```
Connecting to database...
Tables created/verified successfully

[*] Starting dashboard data population...
  [*] Generating test runs...
    Generating 7 days x 30 runs/day...
    Day 1/7 complete - X failures
    Day 2/7 complete - X failures
    ...
  [+] Generated X failed test runs
  [*] Generating failure clusters with AI analysis...
  [+] Generated X failure clusters
  [*] Generating AI performance metrics...
    Progress: 50/X AI metrics
    Completed: X AI metrics
  [*] Generating CI/CD decision summaries...
  [+] Generated analysis summaries

[*] Verifying data integrity...

[+] test_runs: X records
[+] failure_clusters: X records
[+] ai_metrics: X records
[+] analysis_summary: X records

[STATS] Sample Dashboard Queries:
  - Pass Rate (24h): X%
  - New Regressions (24h): X
  - Flaky Tests (24h): X
  - Avg AI Confidence: X
  - Total AI Cost (24h): $X
  
  Top Frameworks (7 days):
    - pytest: X runs
    - robot: X runs
    ...

[SUCCESS] Dashboard data population complete!

[INFO] You can now view the dashboards in Grafana:
  1. AI Intelligence Dashboard
  2. Execution Intelligence Dashboard
  3. Test Execution & Trend Analysis Dashboard
```

### Option 2: Using pytest
```bash
cd d:/Future-work2/crossbridge
pytest tests/integration/test_populate_dashboard_data.py::test_populate_dashboard_data -v
```

## Data Generation Details

The script generates realistic sample data with the following characteristics:

### Test Runs (7 days, 30 runs/day = 210 total)
- **Pass Rate**: ~85% (degrades slightly over time to simulate code decay)
- **Frameworks**: pytest, selenium_pytest, robot, jest, playwright, cypress, junit
- **Environments**: qa, stage, prod, local
- **Branches**: main, develop, feature/test, release/1.0
- **Duration**: Varies by framework (jest ~800ms, selenium ~8000ms)
- **Time Distribution**: Randomly distributed across 24 hours

### Failure Clusters
Generated only for failed tests with:
- **AI Models**: gpt-4, gpt-3.5-turbo, claude-3-opus, claude-3-sonnet
- **Confidence Scores**: Model-specific (gpt-4: ~0.92, gpt-3.5-turbo: ~0.78)
- **Regression Detection**: ~30% of failures marked as regressions
- **Flaky Test Detection**: ~40% marked as flaky (intermittent)
- **Fixed Status**: ~30% marked as resolved
- **Domains**: Product (40%), Infrastructure (40%), Test Code (20%)
- **Severities**: low (20%), medium (40%), high (30%), critical (10%)

### AI Metrics
For each failure cluster:
- **Response Time**: Model-specific (gpt-4: ~3500ms, gpt-3.5-turbo: ~1200ms)
- **Token Usage**: Model-specific (gpt-4: ~1500 tokens, claude-3-opus: ~1800 tokens)
- **Cost**: Based on actual pricing (gpt-4: $0.03/1K, gpt-3.5-turbo: $0.002/1K)
- **Cache Hit Rate**: ~35%
- **Error Rate**: ~5%

### Analysis Summaries
Generated 3-5 times per day:
- Failure distribution across domains
- CI/CD decision (fail CI if >2 product failures)
- Overall confidence scores (0.7-0.95)

## Customizing Data Generation

To generate more data, edit [test_populate_dashboard_data.py](tests/integration/test_populate_dashboard_data.py):

```python
# Change these parameters in test_populate_dashboard_data():
test_run_ids = generate_test_runs(db_connection, num_days=30, runs_per_day=100)  # 30 days, 100 runs/day
```

## Verifying Dashboard Data

After running the script, verify data in PostgreSQL:

```sql
-- Check test runs
SELECT COUNT(*), status FROM test_runs GROUP BY status;

-- Check regressions
SELECT COUNT(*) FROM failure_clusters WHERE is_regression = true;

-- Check flaky tests
SELECT COUNT(*) FROM failure_clusters WHERE is_flaky = true;

-- Check AI cost
SELECT SUM(cost_usd) FROM ai_metrics WHERE created_at >= NOW() - INTERVAL '24 hours';
```

## Troubleshooting

### Connection Errors
```
[ERROR] Connection failed: connection refused
```
**Solution**: Verify PostgreSQL is running and accessible from your machine. Check firewall rules for port 5432.

### Import Errors
```
ModuleNotFoundError: No module named 'psycopg2'
```
**Solution**: Install psycopg2-binary:
```bash
pip install psycopg2-binary
```

### Slow Execution
The script commits data in batches to avoid long transactions:
- Test runs: Commit after each day
- AI metrics: Commit every 50 records
- Typical execution time: 10-30 seconds for 7 days

### Unicode Errors (Windows)
If you see Unicode encoding errors on Windows, the script uses ASCII-compatible output (no emojis).

## Next Steps

After populating data:

1. **Import Dashboards in Grafana**:
   - Go to Grafana > Dashboards > Import
   - Upload `grafana/ai_intelligence_dashboard.json`
   - Upload `grafana/execution_intelligence_dashboard.json`
   - Upload `grafana/test_execution_trends_dashboard.json`

2. **Configure Datasources**:
   - Add PostgreSQL datasource pointing to cbridge-sidecar-stage1-unit-test
   - Add Prometheus datasource for real-time metrics

3. **View Dashboards**:
   - AI Intelligence Dashboard: Real-time AI performance and regression detection
   - Execution Intelligence Dashboard: Failure classification and CI/CD decisions
   - Test Execution & Trend Analysis Dashboard: Pass/fail rates and performance trends

## Additional Resources

- **AI Dashboard README**: [grafana/AI_DASHBOARD_README.md](grafana/AI_DASHBOARD_README.md)
- **CrossBridge Main README**: [README.md](README.md)
- **Dashboard JSON Files**: [grafana/](grafana/)

## Database Cleanup

To clear sample data and start fresh:

```sql
TRUNCATE TABLE ai_metrics, failure_clusters, analysis_summary, test_runs RESTART IDENTITY CASCADE;
```

**Warning**: This will delete ALL data in these tables. Use with caution!

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review [grafana/AI_DASHBOARD_README.md](grafana/AI_DASHBOARD_README.md)
3. Verify database connectivity with:
   ```bash
   python test_db_quick.py
   ```
