# CrossBridge Performance Profiling - Grafana Integration Guide

## Overview

This guide provides Grafana dashboard configuration and SQL queries for visualizing CrossBridge performance profiling data from PostgreSQL.

## Prerequisites

- Grafana instance (tested with Grafana 9.x+)
- PostgreSQL datasource configured in Grafana
- CrossBridge profiling enabled with PostgreSQL storage backend

## Datasource Configuration

### Step 1: Add PostgreSQL Datasource in Grafana

1. Navigate to **Configuration > Data Sources**
2. Click **Add data source**
3. Select **PostgreSQL**
4. Configure connection:
   - **Host**: `10.60.67.247:5432`
   - **Database**: `cbridge-unit-test-db`
   - **User**: `postgres`
   - **Password**: `admin`
   - **SSL Mode**: `disable` (for on-prem)
   - **PostgreSQL details**:
     - Version: 12+
     - TimescaleDB: No
5. Click **Save & Test**

### Step 2: Configure Time Column

- **Time column**: `created_at`
- **Time zone**: UTC

---

## Dashboard Panels

### Panel 1: Slowest Tests (Top 10)

**Visualization**: Bar Chart  
**Description**: Shows the 10 slowest tests by average duration

**SQL Query**:
```sql
SELECT
  test_id,
  AVG(duration_ms) as avg_duration_ms,
  COUNT(*) as execution_count
FROM profiling.tests
WHERE
  $__timeFilter(created_at)
GROUP BY test_id
ORDER BY avg_duration_ms DESC
LIMIT 10
```

**Panel Settings**:
- Time series: No
- Format: Table
- Transform: Organize fields (show test_id, avg_duration_ms)

---

### Panel 2: Test Duration Trend Over Time

**Visualization**: Time series  
**Description**: Shows test duration trends for specific tests

**SQL Query**:
```sql
SELECT
  created_at AS time,
  test_id,
  duration_ms
FROM profiling.tests
WHERE
  $__timeFilter(created_at)
  AND test_id IN ('test_login', 'test_checkout', 'test_search')
ORDER BY time
```

**Panel Settings**:
- Time series: Yes
- Legend: Show values (min, max, avg, last)
- Unit: milliseconds (ms)

---

### Panel 3: Test Execution Timeline

**Visualization**: State timeline  
**Description**: Visual timeline of test executions

**SQL Query**:
```sql
SELECT
  created_at AS time,
  test_id,
  CASE
    WHEN status = 'passed' THEN 1
    WHEN status = 'failed' THEN 2
    ELSE 0
  END as state
FROM profiling.tests
WHERE
  $__timeFilter(created_at)
ORDER BY time
```

---

### Panel 4: Slow Endpoints (API Performance)

**Visualization**: Bar Chart  
**Description**: Top 10 slowest API endpoints

**SQL Query**:
```sql
SELECT
  endpoint,
  AVG(duration_ms) as avg_duration_ms,
  COUNT(*) as call_count,
  AVG(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) * 100 as error_rate
FROM profiling.http_calls
WHERE
  $__timeFilter(created_at)
GROUP BY endpoint
ORDER BY avg_duration_ms DESC
LIMIT 10
```

---

### Panel 5: HTTP Status Code Distribution

**Visualization**: Pie Chart  
**Description**: Distribution of HTTP status codes

**SQL Query**:
```sql
SELECT
  status_code::text as status,
  COUNT(*) as count
FROM profiling.http_calls
WHERE
  $__timeFilter(created_at)
GROUP BY status_code
ORDER BY count DESC
```

---

### Panel 6: WebDriver Command Performance

**Visualization**: Heatmap  
**Description**: Performance heatmap of Selenium WebDriver commands

**SQL Query**:
```sql
SELECT
  DATE_TRUNC('hour', created_at) AS time,
  command,
  AVG(duration_ms) as avg_duration
FROM profiling.driver_commands
WHERE
  $__timeFilter(created_at)
GROUP BY time, command
ORDER BY time
```

---

### Panel 7: Test Performance Percentiles

**Visualization**: Time series  
**Description**: P50, P90, P95, P99 test duration percentiles

**SQL Query**:
```sql
SELECT
  DATE_TRUNC('hour', created_at) AS time,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_ms) as p50,
  PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY duration_ms) as p90,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as p99
FROM profiling.tests
WHERE
  $__timeFilter(created_at)
GROUP BY time
ORDER BY time
```

---

### Panel 8: Step Duration Breakdown

**Visualization**: Bar Chart (Stacked)  
**Description**: Setup, test execution, and teardown time breakdown

**SQL Query**:
```sql
SELECT
  test_id,
  SUM(CASE WHEN event_type = 'setup_end' THEN duration_ms ELSE 0 END) as setup_time,
  SUM(CASE WHEN event_type = 'step_end' THEN duration_ms ELSE 0 END) as test_time,
  SUM(CASE WHEN event_type = 'teardown_end' THEN duration_ms ELSE 0 END) as teardown_time
FROM profiling.steps
WHERE
  $__timeFilter(created_at)
  AND test_id IN (
    SELECT test_id FROM profiling.tests 
    WHERE $__timeFilter(created_at) 
    ORDER BY duration_ms DESC 
    LIMIT 10
  )
GROUP BY test_id
ORDER BY (setup_time + test_time + teardown_time) DESC
```

---

### Panel 9: Execution Rate (Tests per Minute)

**Visualization**: Time series  
**Description**: Test execution rate over time

**SQL Query**:
```sql
SELECT
  DATE_TRUNC('minute', created_at) AS time,
  COUNT(*) as tests_per_minute
FROM profiling.tests
WHERE
  $__timeFilter(created_at)
GROUP BY time
ORDER BY time
```

---

### Panel 10: Performance Regression Detection

**Visualization**: Table  
**Description**: Tests with >30% performance regression vs baseline

**SQL Query**:
```sql
WITH baseline AS (
  SELECT
    test_id,
    AVG(duration_ms) as avg_duration
  FROM profiling.tests
  WHERE
    created_at >= NOW() - INTERVAL '7 days'
    AND created_at < NOW() - INTERVAL '1 day'
  GROUP BY test_id
),
recent AS (
  SELECT
    test_id,
    AVG(duration_ms) as avg_duration
  FROM profiling.tests
  WHERE
    created_at >= NOW() - INTERVAL '1 day'
  GROUP BY test_id
)
SELECT
  r.test_id,
  b.avg_duration as baseline_ms,
  r.avg_duration as recent_ms,
  ROUND(((r.avg_duration - b.avg_duration) / b.avg_duration * 100)::numeric, 2) as change_percent
FROM recent r
JOIN baseline b ON r.test_id = b.test_id
WHERE
  r.avg_duration > b.avg_duration * 1.3  -- 30% slower
ORDER BY change_percent DESC
LIMIT 20
```

---

### Panel 11: Framework Distribution

**Visualization**: Pie Chart  
**Description**: Distribution of tests by framework

**SQL Query**:
```sql
SELECT
  framework,
  COUNT(*) as count
FROM profiling.tests
WHERE
  $__timeFilter(created_at)
GROUP BY framework
```

---

### Panel 12: API Response Time by Endpoint

**Visualization**: Time series  
**Description**: Track specific API endpoint response times

**SQL Query**:
```sql
SELECT
  created_at AS time,
  endpoint,
  duration_ms
FROM profiling.http_calls
WHERE
  $__timeFilter(created_at)
  AND endpoint IN ('/api/login', '/api/users', '/api/checkout')
ORDER BY time
```

---

## Dashboard Variables

Add these variables to make your dashboard interactive:

### Variable: test_id
- **Type**: Query
- **Query**:
  ```sql
  SELECT DISTINCT test_id
  FROM profiling.tests
  WHERE $__timeFilter(created_at)
  ORDER BY test_id
  ```
- **Multi-value**: Yes
- **Include All**: Yes

### Variable: framework
- **Type**: Query
- **Query**:
  ```sql
  SELECT DISTINCT framework
  FROM profiling.tests
  ORDER BY framework
  ```
- **Multi-value**: Yes
- **Include All**: Yes

### Variable: run_id
- **Type**: Query
- **Query**:
  ```sql
  SELECT DISTINCT run_id
  FROM profiling.tests
  WHERE $__timeFilter(created_at)
  ORDER BY created_at DESC
  ```
- **Multi-value**: No

---

## Sample Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Performance Overview Dashboard                              │
├─────────────────────────────────────────────────────────────┤
│  Variables: [Time Range] [Framework] [Test ID]              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Total Tests  │  │ Avg Duration │  │ P95 Duration │      │
│  │    1,234     │  │   1,500 ms   │  │   3,200 ms   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌───────────────────────────────────────────────────┐      │
│  │  Test Duration Trend Over Time                    │      │
│  │  [Time Series Chart]                              │      │
│  └───────────────────────────────────────────────────┘      │
│                                                              │
│  ┌────────────────────┐  ┌────────────────────┐            │
│  │ Slowest Tests      │  │ Slow Endpoints     │            │
│  │ [Bar Chart]        │  │ [Bar Chart]        │            │
│  └────────────────────┘  └────────────────────┘            │
│                                                              │
│  ┌───────────────────────────────────────────────────┐      │
│  │  Performance Regression Detection                 │      │
│  │  [Table with alerts]                              │      │
│  └───────────────────────────────────────────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Alerting Rules

### Alert 1: High Test Duration

**Condition**: Test duration > 5 seconds  
**Query**:
```sql
SELECT
  test_id,
  MAX(duration_ms) as max_duration
FROM profiling.tests
WHERE
  created_at >= NOW() - INTERVAL '5 minutes'
GROUP BY test_id
HAVING MAX(duration_ms) > 5000
```

### Alert 2: API Endpoint Slow Response

**Condition**: Endpoint response time > 1 second  
**Query**:
```sql
SELECT
  endpoint,
  AVG(duration_ms) as avg_duration
FROM profiling.http_calls
WHERE
  created_at >= NOW() - INTERVAL '5 minutes'
GROUP BY endpoint
HAVING AVG(duration_ms) > 1000
```

### Alert 3: High Error Rate

**Condition**: HTTP 4xx/5xx rate > 5%  
**Query**:
```sql
SELECT
  endpoint,
  COUNT(*) as total_calls,
  SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors,
  (SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END)::float / COUNT(*)) * 100 as error_rate
FROM profiling.http_calls
WHERE
  created_at >= NOW() - INTERVAL '5 minutes'
GROUP BY endpoint
HAVING (SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END)::float / COUNT(*)) * 100 > 5
```

---

## Exporting Dashboard

To export your dashboard configuration:

1. Open the dashboard
2. Click the **Settings** icon (gear)
3. Select **JSON Model**
4. Copy the JSON
5. Save to file: `grafana/dashboards/crossbridge-performance.json`

---

## Testing the Integration

1. **Generate Test Data**: Run the unit tests
   ```bash
   pytest tests/test_performance_profiling.py -v
   ```

2. **Verify Data in PostgreSQL**:
   ```sql
   SELECT COUNT(*) FROM profiling.tests;
   SELECT COUNT(*) FROM profiling.http_calls;
   SELECT COUNT(*) FROM profiling.driver_commands;
   ```

3. **Open Grafana**: Navigate to your dashboard and verify panels are displaying data

---

## Troubleshooting

### No Data Showing

1. Check time range in Grafana
2. Verify PostgreSQL connection
3. Check profiling is enabled in `crossbridge.yml`
4. Verify tests are running and generating events

### Slow Queries

1. Ensure indexes are created (handled by PostgreSQL backend initialization)
2. Limit time ranges for large datasets
3. Use aggregation queries for overview panels

### Permission Issues

Ensure PostgreSQL user has:
```sql
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA profiling TO postgres;
GRANT USAGE ON SCHEMA profiling TO postgres;
```

---

## Next Steps

1. Customize panels for your specific use cases
2. Add more alerting rules
3. Create team-specific dashboards
4. Set up automated reports
5. Integrate with Slack/Teams for alerts

---

**Support**: For issues, contact vikas.sdet@gmail.com or file GitHub issues.
