# Grafana Dashboard Setup Guide

## Quick Setup

### 1. Access Grafana
- URL: http://10.55.12.99:3000/
- Username: `admin`
- Password: `admin`

### 2. Add PostgreSQL Data Source

1. **Navigate to Data Sources**
   - Click on ⚙️ (Configuration) in the left sidebar
   - Select "Data Sources"
   - Click "Add data source"

2. **Configure PostgreSQL**
   - Select "PostgreSQL" from the list
   - Configure with these settings:

   ```
   Name: CrossBridge Coverage DB
   Host: 10.55.12.99:5432
   Database: udp-native-webservices-automation
   User: postgres
   Password: admin
   TLS/SSL Mode: disable
   Version: 12+
   ```

3. **Test Connection**
   - Click "Save & Test"
   - Should show green "Database Connection OK"

### 3. Import Dashboard

**Method 1: Via UI**
1. Click "+" (Create) → "Import" in left sidebar
2. Click "Upload JSON file"
3. Select `grafana/behavioral_coverage_dashboard.json`
4. Select data source: "CrossBridge Coverage DB"
5. Click "Import"

**Method 2: Via API**
```bash
curl -X POST http://admin:admin@10.55.12.99:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @grafana/behavioral_coverage_dashboard.json
```

**Method 3: Copy-Paste**
1. Click "+" → "Import"
2. Paste contents of `behavioral_coverage_dashboard.json`
3. Click "Load"
4. Select data source and import

---

## Dashboard Panels Overview

### 📊 Summary Statistics (Top Row)
1. **API Endpoint Coverage** - Total unique endpoints tested
2. **Total API Calls** - Cumulative API call count
3. **UI Components Tested** - Unique UI elements interacted with
4. **Active Tests** - Total test cases in database

### 📈 Coverage Analysis
5. **Top 10 Most Tested API Endpoints** - Bar chart showing endpoint test coverage
6. **HTTP Status Code Distribution** - Pie chart of response codes
7. **API Endpoint Coverage Over Time** - Time series of coverage growth
8. **UI Component Interactions** - Table of UI component usage

### 🔍 Test Distribution
9. **Test Framework Distribution** - Pie chart of pytest/junit/robot distribution
10. **Contract Validation Status** - Success rate percentage
11. **Network Traffic Volume** - Request volume and latency over time

### 📋 Detailed Views
12. **API Endpoints by HTTP Method** - GET/POST/PUT/DELETE breakdown
13. **Recent Test Executions** - Latest test runs with coverage data

---

## Custom Queries

### Query 1: Coverage Gaps (Endpoints with Low Test Coverage)
```sql
SELECT 
  endpoint_path,
  http_method,
  test_count,
  total_calls
FROM api_endpoint_summary
WHERE test_count < 3
ORDER BY total_calls DESC;
```

### Query 2: Most Active Pages
```sql
SELECT 
  page_url,
  COUNT(DISTINCT component_name) as components,
  SUM(interaction_count) as total_interactions
FROM ui_component_coverage
WHERE page_url IS NOT NULL
GROUP BY page_url
ORDER BY total_interactions DESC;
```

### Query 3: Test Execution Frequency (Last 7 Days)
```sql
SELECT 
  DATE_TRUNC('day', created_at) as day,
  COUNT(DISTINCT test_case_id) as unique_tests,
  COUNT(*) as total_coverage_records
FROM api_endpoint_coverage
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY day
ORDER BY day;
```

### Query 4: Contract Validation Failures
```sql
SELECT 
  cc.contract_name,
  cc.contract_version,
  tc.framework,
  tc.method_name,
  cc.validation_errors,
  cc.created_at
FROM contract_coverage cc
JOIN test_case tc ON cc.test_case_id = tc.id
WHERE cc.validation_passed = false
ORDER BY cc.created_at DESC
LIMIT 20;
```

### Query 5: API Response Time Analysis
```sql
SELECT 
  endpoint_path,
  http_method,
  AVG(execution_time_ms) as avg_time,
  MIN(execution_time_ms) as min_time,
  MAX(execution_time_ms) as max_time,
  COUNT(*) as call_count
FROM api_endpoint_coverage
WHERE execution_time_ms IS NOT NULL
GROUP BY endpoint_path, http_method
HAVING COUNT(*) > 5
ORDER BY avg_time DESC;
```

### Query 6: Feature Coverage Summary
```sql
SELECT 
  f.name as feature,
  f.type,
  COUNT(DISTINCT tfm.test_case_id) as test_count,
  COUNT(DISTINCT tccm.code_unit_id) as code_units_covered
FROM feature f
LEFT JOIN test_feature_map tfm ON f.id = tfm.feature_id
LEFT JOIN test_code_coverage_map tccm ON tfm.test_case_id = tccm.test_case_id
GROUP BY f.id, f.name, f.type
ORDER BY test_count DESC;
```

---

## Creating Custom Panels

### Add a New Panel

1. **Click "Add Panel"** in dashboard edit mode
2. **Select Visualization Type**:
   - Time series - For trends over time
   - Bar chart - For comparisons
   - Stat - For single metrics
   - Table - For detailed data
   - Pie chart - For distributions

3. **Configure Query**:
   - Format: `Time series` or `Table`
   - Write SQL query against PostgreSQL
   - Use `$__timeFilter(column)` for time range filtering
   - Use variables like `$endpoint` for dynamic filtering

4. **Example Time Series Query**:
```sql
SELECT 
  $__timeGroup(created_at, '1h') as time,
  COUNT(DISTINCT endpoint_path) as "Unique Endpoints",
  COUNT(*) as "Total Calls"
FROM api_endpoint_coverage
WHERE $__timeFilter(created_at)
GROUP BY time
ORDER BY time;
```

---

## Dashboard Variables

Add variables for dynamic filtering:

### Variable 1: Test Framework
- **Name**: `framework`
- **Type**: Query
- **Query**: `SELECT DISTINCT framework FROM test_case ORDER BY framework;`
- **Multi-value**: Yes

### Variable 2: HTTP Method
- **Name**: `http_method`
- **Type**: Query
- **Query**: `SELECT DISTINCT http_method FROM api_endpoint_coverage ORDER BY http_method;`
- **Multi-value**: Yes

### Variable 3: Time Range
- **Name**: `time_range`
- **Type**: Interval
- **Values**: `1h,6h,12h,24h,7d,30d`

### Using Variables in Queries
```sql
SELECT * FROM api_endpoint_coverage
WHERE http_method = ANY(string_to_array('$http_method', ','))
AND created_at > NOW() - INTERVAL '$time_range';
```

---

## Alert Configuration

### Alert 1: Low API Coverage
```
Condition: When API endpoint count < 10
Notification: Email/Slack
Frequency: Every 1 hour
Message: "API coverage dropped below threshold"
```

### Alert 2: High Error Rate
```sql
SELECT 
  COUNT(*) * 100.0 / (SELECT COUNT(*) FROM api_endpoint_coverage) as error_rate
FROM api_endpoint_coverage
WHERE status_code >= 400;
```
```
Condition: When error_rate > 10%
Notification: Email/Slack
Frequency: Every 15 minutes
```

### Alert 3: Contract Validation Failures
```sql
SELECT COUNT(*) as failures
FROM contract_coverage
WHERE validation_passed = false
AND created_at > NOW() - INTERVAL '1 hour';
```
```
Condition: When failures > 5
Notification: Email/Slack
Frequency: Every 30 minutes
```

---

## Advanced Features

### 1. Template Variables for Dynamic Dashboards
Create dropdown filters at the top of dashboard:

```sql
-- Variable: endpoint_filter
SELECT DISTINCT endpoint_path 
FROM api_endpoint_coverage 
ORDER BY endpoint_path;

-- Use in panel:
SELECT * FROM api_endpoint_coverage
WHERE endpoint_path = '$endpoint_filter';
```

### 2. Annotations
Add event markers to time series:

```sql
-- Query for annotations
SELECT 
  created_at as time,
  'New Test Added' as text,
  method_name as tags
FROM test_case
WHERE created_at > NOW() - INTERVAL '7 days';
```

### 3. Data Links
Link panels to drill-down views:
- Click on endpoint → Show all tests for that endpoint
- Click on test → Show full test execution details

### 4. Panel Repeat
Automatically create one panel per framework:
- Enable "Repeat" on panel
- Select variable: `$framework`
- One panel appears for each framework value

---

## Maintenance

### Refresh Dashboard Data
- Auto-refresh: Set to 30s, 1m, 5m (top-right dropdown)
- Manual: Click refresh icon
- Cache: Grafana caches queries for performance

### Optimize Query Performance
1. Add indexes to frequently queried columns
2. Use `LIMIT` for large result sets
3. Use aggregations instead of raw data
4. Consider materialized views for complex queries

### Backup Dashboard
```bash
# Export dashboard JSON
curl http://admin:admin@10.55.12.99:3000/api/dashboards/uid/<dashboard-uid> > backup.json

# Or via UI: Dashboard Settings → JSON Model → Copy
```

---

## Troubleshooting

### Issue: "Database Connection Failed"
**Solution**: Check PostgreSQL connection:
```bash
psql -h 10.55.12.99 -U postgres -d udp-native-webservices-automation
```

### Issue: "No data" in panels
**Solutions**:
1. Check if data exists: Run query in pgAdmin/psql
2. Verify time range (top-right corner)
3. Check panel query syntax
4. Ensure data source is selected

### Issue: Slow queries
**Solutions**:
1. Add indexes on timestamp columns
2. Reduce time range
3. Use aggregations
4. Check query execution plan:
```sql
EXPLAIN ANALYZE <your-query>;
```

### Issue: Variables not working
**Solution**: 
- Check variable preview shows values
- Verify variable syntax in queries: `$variable_name`
- For multi-value: Use `IN ('$variable_name:csv')`

---

## Next Steps

1. ✅ Import dashboard
2. ✅ Verify all panels load data
3. ⏳ Customize panel layouts
4. ⏳ Add alert rules
5. ⏳ Create team-specific dashboards
6. ⏳ Set up Slack/email notifications
7. ⏳ Share dashboard URL with team

---

## Resources

- **Dashboard File**: `grafana/behavioral_coverage_dashboard.json`
- **Database**: PostgreSQL @ 10.55.12.99:5432
- **Grafana**: http://10.55.12.99:3000/
- **Schema Docs**: See `BEHAVIORAL_COVERAGE_USAGE.md`

## Quick Access URLs

After import, dashboard will be available at:
```
http://10.55.12.99:3000/d/<dashboard-uid>/crossbridge-behavioral-coverage
```

Share this URL with your team for instant access! 🎉
