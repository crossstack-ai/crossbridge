# Grafana Dashboard Troubleshooting & Panel Enhancements

Copyright (c) 2025 Vikas Verma  
Licensed under the Apache License, Version 2.0

**Last Updated**: January 24, 2026

---

## Overview

This guide consolidates all Grafana dashboard troubleshooting, panel enhancements, and best practices for CrossBridge AI observability dashboards.

---

## Common Issues & Solutions

### Issue 1: Blank Dashboard Despite Data Existing

**Symptoms:**
- ✅ Database has data (confirmed via SQL queries)
- ✅ Data is recent (within dashboard time range)
- ✅ Queries work when run directly against PostgreSQL
- ❌ Dashboard shows blank charts or "No data"

**Root Causes:**
1. Hardcoded datasource UID doesn't match your Grafana instance
2. Dashboard imported but datasource not selected
3. Time range filter excluding all data
4. Query syntax incompatible with datasource

**Solution:**

#### Method 1: Re-Import Dashboard with Correct Datasource

```bash
# Step 1: Delete current dashboard (optional)
# Go to Dashboard settings → Delete dashboard

# Step 2: Import dashboard
# 1. Go to Grafana → + → Import
# 2. Upload: grafana/dashboards/crossbridge_overview.json
# 3. SELECT YOUR POSTGRESQL DATASOURCE from dropdown
# 4. Click Import
```

#### Method 2: Update Datasource in Existing Dashboard

```bash
# Step 1: Open dashboard → Settings (gear icon)
# Step 2: Go to JSON Model
# Step 3: Find all instances of "datasource" and update:

# From:
"datasource": {
  "type": "postgres",
  "uid": "some-hardcoded-uid"
}

# To:
"datasource": {
  "type": "postgres",
  "uid": "${DS_POSTGRESQL}"  # Use variable
}

# Step 4: Save changes
# Step 5: Refresh dashboard
```

#### Method 3: Test Datasource First

Before importing dashboards, verify datasource works:

```sql
-- 1. Go to Grafana → Explore
-- 2. Select PostgreSQL datasource
-- 3. Run this test query:

SELECT COUNT(*) as total_tests
FROM test_execution_event
WHERE created_at > NOW() - INTERVAL '24 hours';

-- If this returns data, datasource is configured correctly
```

---

### Issue 2: Memory & Embedding Panels Not Showing Data

**Symptoms:**
- Test execution panels work fine
- Memory/embedding panels show "No data"
- Database has embeddings (verified)

**Root Cause:**
Dashboard JSON updated after initial import. Grafana is using cached old version with only 13 panels (missing panels 14-18 for memory/embeddings).

**Solution: Re-Import Updated Dashboard**

```bash
# Expected Panel Count: 18 (was 13 before)

# New Panels (14-18):
# - Panel 14: Memory & Embeddings Overview (Stat)
# - Panel 15: Embeddings by Entity Type (Pie Chart)
# - Panel 16: Recent Embeddings Created (Table)
# - Panel 17: Embedding Storage Trend (Time Series)
# - Panel 18: Embedding Vector Dimensions Info (Stat)

# To re-import:
# 1. Dashboard settings → JSON Model
# 2. Replace entire JSON with: grafana/dashboards/crossbridge_overview.json
# 3. Save changes
# 4. Refresh page
```

**Verify After Re-Import:**

| Panel | Expected Result |
|-------|----------------|
| Panel 14 | Total embeddings count (e.g., 50) |
| Panel 15 | Pie chart by entity_type (test_case, page, step, etc.) |
| Panel 16 | Table with 20 recent embeddings |
| Panel 17 | Time series of embedding creation |
| Panel 18 | Vector dimension info (1536 or 3072) |

---

### Issue 3: Panels Show UUID Instead of Test Names

**Symptoms:**
- "Recent Embeddings" panel shows UUIDs like `a1b2c3d4-...`
- No readable test names
- Missing framework/file information

**Root Cause:**
Query using `entity_id` directly without JOINing to `test_case` table.

**Solution: Enhanced Query with LEFT JOIN**

**Before (Original Query):**
```sql
SELECT 
    entity_type, 
    entity_id::text as entity_id, 
    content_hash, 
    (metadata->>'test_name') as test_name, 
    (metadata->>'model') as model, 
    created_at 
FROM memory_embeddings 
ORDER BY created_at DESC 
LIMIT 20
```

**Problems:**
- Shows raw UUID for entity_id
- `metadata->>'test_name'` often NULL
- No framework or file information

**After (Enhanced Query):**
```sql
SELECT 
    COALESCE(
        tc.test_name,                              -- Priority 1: Actual test name
        me.metadata->>'name',                       -- Priority 2: Metadata name
        SUBSTRING(me.metadata->>'text', 1, 50),    -- Priority 3: Description
        CAST(me.entity_id AS VARCHAR)              -- Priority 4: UUID fallback
    ) as "Test Case ID",
    me.entity_type as "Type",
    COALESCE(tc.framework, me.metadata->>'framework', 'N/A') as "Framework",
    COALESCE(
        SUBSTRING(tc.test_file_path, 1, 40),
        me.metadata->>'file',
        'N/A'
    ) as "File",
    COALESCE(tc.suite_name, 'N/A') as "Suite",
    COALESCE(me.metadata->>'model', 'N/A') as "Model",
    me.created_at as "Created At"
FROM memory_embeddings me
LEFT JOIN test_case tc ON me.entity_id = tc.id
ORDER BY me.created_at DESC
LIMIT 20
```

**Improvements:**
- ✅ Shows actual test names (e.g., "test_playwright_checkout_1")
- ✅ Falls back gracefully if no test_case match
- ✅ Displays framework (pytest, junit, etc.)
- ✅ Shows truncated file path
- ✅ Includes test suite name
- ✅ Shows embedding model used

---

### Issue 4: Time Range Issues

**Symptoms:**
- Dashboard shows "No data"
- But query in Explore returns data
- Data exists in correct time period

**Root Cause:**
Dashboard time range filter not aligned with data timestamps.

**Solution:**

```bash
# Option 1: Use Relative Time Ranges
# In dashboard settings:
Time range: Last 24 hours
Refresh: 1m

# Option 2: Check Timezone
# Ensure Grafana timezone matches database timezone:
# Settings → Preferences → Timezone → Use local browser time

# Option 3: Use Time Macros in Queries
SELECT *
FROM test_execution_event
WHERE created_at BETWEEN $__timeFrom() AND $__timeTo()
ORDER BY created_at DESC
LIMIT 100
```

---

## Panel Enhancement Examples

### Enhanced Flaky Test Detection Panel

**Original:**
```sql
SELECT 
    test_name,
    flaky_score
FROM flaky_test
WHERE flaky_score > 0.7
ORDER BY flaky_score DESC
LIMIT 10
```

**Enhanced (with more context):**
```sql
SELECT 
    ft.test_name as "Test Name",
    tc.framework as "Framework",
    SUBSTRING(tc.test_file_path, 1, 50) as "File",
    ft.flaky_score as "Flaky Score",
    ft.severity as "Severity",
    ft.failure_rate as "Failure Rate %",
    ft.confidence_score as "Confidence",
    ft.last_detected_at as "Last Detected"
FROM flaky_test ft
LEFT JOIN test_case tc ON ft.test_case_id = tc.id
WHERE ft.flaky_score > 0.7
ORDER BY ft.flaky_score DESC
LIMIT 10
```

### Enhanced Test Execution Trend Panel

**Original:**
```sql
SELECT 
    created_at as time,
    COUNT(*) as tests
FROM test_execution_event
GROUP BY created_at
ORDER BY time
```

**Enhanced (with status breakdown):**
```sql
SELECT 
    time_bucket('1 hour', created_at) as time,
    status,
    COUNT(*) as tests
FROM test_execution_event
WHERE created_at > $__timeFrom()
  AND created_at < $__timeTo()
GROUP BY time, status
ORDER BY time, status
```

### Enhanced Coverage Panel

**Original:**
```sql
SELECT 
    feature_name,
    coverage_percentage
FROM functional_coverage
ORDER BY coverage_percentage ASC
LIMIT 10
```

**Enhanced (with trend and target):**
```sql
SELECT 
    fc.feature_name as "Feature",
    fc.coverage_percentage as "Current %",
    fc.target_coverage as "Target %",
    (fc.coverage_percentage - fc.target_coverage) as "Gap",
    fc.tests_passed as "Passed",
    fc.tests_failed as "Failed",
    fc.last_updated as "Last Updated",
    CASE 
        WHEN fc.coverage_percentage >= fc.target_coverage THEN '✅'
        WHEN fc.coverage_percentage >= fc.target_coverage * 0.8 THEN '⚠️'
        ELSE '❌'
    END as "Status"
FROM functional_coverage fc
WHERE fc.last_updated > NOW() - INTERVAL '7 days'
ORDER BY fc.coverage_percentage ASC
LIMIT 10
```

---

## Best Practices

### 1. Use Variables for Datasources

Instead of hardcoding datasource UIDs:

```json
{
  "datasource": {
    "type": "postgres",
    "uid": "${DS_POSTGRESQL}"
  }
}
```

### 2. Use Time Macros

Always use Grafana time macros in queries:

```sql
WHERE created_at BETWEEN $__timeFrom() AND $__timeTo()
```

### 3. Add Fallbacks for NULL Values

Use `COALESCE` to handle NULL values gracefully:

```sql
COALESCE(tc.test_name, me.metadata->>'name', 'Unknown') as "Test Name"
```

### 4. Truncate Long Text

Prevent UI overflow by truncating long values:

```sql
SUBSTRING(tc.test_file_path, 1, 50) as "File"
```

### 5. Use Visual Indicators

Add emoji or symbols for quick status recognition:

```sql
CASE 
    WHEN flaky_score > 0.8 THEN '🔴 Critical'
    WHEN flaky_score > 0.6 THEN '🟡 High'
    ELSE '🟢 Medium'
END as "Severity"
```

### 6. Optimize Queries

For large datasets:

```sql
-- Add indexes
CREATE INDEX idx_test_execution_created_at ON test_execution_event(created_at);
CREATE INDEX idx_flaky_test_score ON flaky_test(flaky_score) WHERE flaky_score > 0.7;

-- Limit result sets
LIMIT 100

-- Use time buckets for aggregations
time_bucket('1 hour', created_at)
```

---

## Datasource Configuration

### PostgreSQL Datasource Settings

```yaml
Name: CrossBridge PostgreSQL
Type: PostgreSQL
Host: 10.60.67.247:5432
Database: cbridge-unit-test-db
User: postgres
Password: [your-password]
SSL Mode: disable (or require if SSL enabled)
Version: 16+
TimescaleDB: Enabled (if using time_bucket)
```

### Test Datasource

```sql
-- Basic connectivity test
SELECT NOW();

-- Data availability test
SELECT COUNT(*) FROM test_execution_event;

-- Recent data test
SELECT COUNT(*) 
FROM test_execution_event 
WHERE created_at > NOW() - INTERVAL '24 hours';
```

---

## Dashboard Maintenance

### Regular Checks

**Weekly:**
- ✅ Verify all panels showing data
- ✅ Check query performance (< 1s response time)
- ✅ Review time range settings
- ✅ Test dashboard variables

**Monthly:**
- ✅ Update dashboard JSON if panels added
- ✅ Optimize slow queries
- ✅ Archive old dashboards
- ✅ Review and update thresholds

### Version Control

Keep dashboard JSON in version control:

```bash
# Export dashboard
curl "http://grafana:3000/api/dashboards/uid/crossbridge" \
  -H "Authorization: Bearer $TOKEN" \
  > grafana/dashboards/crossbridge_overview_v$(date +%Y%m%d).json

# Commit to git
git add grafana/dashboards/
git commit -m "Update Grafana dashboard - $(date)"
```

---

## Troubleshooting Checklist

When dashboard issues occur, check in this order:

1. **✅ Database Connection**
   ```bash
   psql -h 10.60.67.247 -U postgres -d cbridge-unit-test-db -c "SELECT 1;"
   ```

2. **✅ Data Exists**
   ```sql
   SELECT COUNT(*) FROM test_execution_event;
   ```

3. **✅ Data in Time Range**
   ```sql
   SELECT MIN(created_at), MAX(created_at) FROM test_execution_event;
   ```

4. **✅ Grafana Datasource**
   - Go to Configuration → Data Sources
   - Click "Test" button
   - Should show "Database Connection OK"

5. **✅ Panel Query**
   - Edit panel
   - Check query syntax
   - Run query manually
   - Check for errors in Query Inspector

6. **✅ Time Range**
   - Check dashboard time picker
   - Verify timezone settings
   - Use "Last 24 hours" for testing

7. **✅ Dashboard JSON**
   - Check datasource UIDs
   - Verify panel IDs are unique
   - Confirm query syntax is correct

---

## Advanced: Programmatic Dashboard Updates

### Using Grafana API

```bash
#!/bin/bash
# Update dashboard via API

GRAFANA_URL="http://10.55.12.99:3000"
GRAFANA_TOKEN="your-api-token"
DASHBOARD_JSON="grafana/dashboards/crossbridge_overview.json"

# Create or update dashboard
curl -X POST "$GRAFANA_URL/api/dashboards/db" \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d @"$DASHBOARD_JSON"
```

### Bulk Panel Updates

```python
import json

# Load dashboard
with open('grafana/dashboards/crossbridge_overview.json') as f:
    dashboard = json.load(f)

# Update all panel queries
for panel in dashboard['dashboard']['panels']:
    if 'targets' in panel:
        for target in panel['targets']:
            # Add time filter to all queries
            if 'WHERE' in target.get('rawSql', ''):
                target['rawSql'] += '\n  AND created_at BETWEEN $__timeFrom() AND $__timeTo()'

# Save updated dashboard
with open('grafana/dashboards/crossbridge_overview_updated.json', 'w') as f:
    json.dump(dashboard, f, indent=2)
```

---

## Support & Resources

### Documentation
- **[Grafana Version Dashboard Guide](GRAFANA_VERSION_DASHBOARD_GUIDE.md)** - Setup guide
- **[Continuous Intelligence README](CONTINUOUS_INTELLIGENCE_README.md)** - Overview
- **[Manual Dashboard Creation](MANUAL_DASHBOARD_CREATION.md)** - Step-by-step

### Getting Help
- **📧 Email**: vikas.sdet@gmail.com
- **� GitHub Issues**: [Report Issues](https://github.com/crossstack-ai/crossbridge/issues)

---

**Keep your dashboards updated and your data visible!** 📊
