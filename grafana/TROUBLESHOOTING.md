# Grafana Dashboard Troubleshooting Guide

## Issue: Blank Dashboard / No Charts Displayed

### Problem
After importing the dashboard, you see panel titles but no actual data/charts are displayed.

### Root Cause
The datasource was not properly linked to the dashboard panels during import.

### Solution Steps

#### Step 1: Delete the Existing Dashboard
1. Go to: http://10.55.12.99:3000/dashboards
2. Find "CrossBridge Behavioral Coverage" dashboard
3. Click on it, then click the ⚙️ (settings) icon at top right
4. Scroll down and click **Delete Dashboard**
5. Confirm deletion

#### Step 2: Verify Data Source Name
1. Go to: **☰ → Connections → Data sources**
2. Click on your PostgreSQL data source
3. **CRITICAL**: The name MUST be exactly: `CrossBridge Coverage DB`
4. If it's different, either:
   - **Option A**: Rename it to `CrossBridge Coverage DB`
   - **Option B**: Note the exact name for next step

#### Step 3: Re-Import Dashboard
1. Go to: **☰ → Dashboards → Import**
2. Click **Upload JSON file**
3. Select: `grafana/dashboard_working.json` (NEW fixed version)
4. On the import page:
   - **Name**: Keep as "CrossBridge Behavioral Coverage" or customize
   - **Folder**: Choose or leave as "General"
   - **CrossBridge Coverage DB**: Select your PostgreSQL datasource from dropdown
     - If your datasource has a different name, select it here
5. Click **Import**

#### Step 4: Verify Data Display
The dashboard should now show:
- **Top Row**: 4 stat panels with numbers (API endpoints, calls, UI components, tests)
- **Middle**: Bar chart of top tested endpoints
- **Middle**: Pie chart of HTTP status codes
- **Bottom**: Time series graph showing API coverage over 24 hours
- **Bottom**: Table of UI component interactions
- **Bottom**: Donut chart of test framework distribution

### If Still Blank After Re-Import

#### Check 1: Verify Database Has Data
```sql
-- Connect to database
psql -h 10.55.12.99 -U postgres -d udp-native-webservices-automation

-- Check for data
SELECT COUNT(*) FROM api_endpoint_coverage;
SELECT COUNT(*) FROM ui_component_coverage;
SELECT COUNT(*) FROM test_case;
```

**Expected**: Each query should return a number > 0

**If all return 0**: You need to generate test data first:
```bash
cd d:\Future-work2\crossbridge
python test_ai_summary_quick.py  # Generates sample data
```

#### Check 2: Test Query Manually
In Grafana:
1. Go to **☰ → Explore**
2. Select datasource: **CrossBridge Coverage DB**
3. Click **Code** to enter SQL mode
4. Enter test query:
```sql
SELECT COUNT(DISTINCT endpoint_path) as value FROM api_endpoint_coverage;
```
5. Click **Run query**

**Expected**: Should return a number
**If error**: Check the error message:
- "relation does not exist" → Schema not applied, run `scripts/apply_coverage_schema_only.py`
- "connection refused" → Database not accessible
- "authentication failed" → Wrong credentials

#### Check 3: Verify Panel Configuration
1. Open dashboard
2. Click on any panel title → **Edit**
3. Check the **Query** tab:
   - **Data source**: Should show "CrossBridge Coverage DB" (green indicator)
   - If red indicator: Click dropdown and select correct datasource
   - **Query**: Should show SQL query
4. Click **Apply** to save

Repeat for each panel if needed.

#### Check 4: Check Grafana Logs
```bash
# On Grafana server
sudo tail -f /var/log/grafana/grafana.log

# Look for errors related to:
# - Database queries
# - Panel rendering
# - Datasource connection
```

#### Check 5: Verify PostgreSQL Accepts Connections
```bash
# From Grafana server
psql -h 10.55.12.99 -U postgres -d udp-native-webservices-automation

# If this fails:
# 1. Check pg_hba.conf allows connections from Grafana IP
# 2. Check postgresql.conf has listen_addresses = '*'
# 3. Restart PostgreSQL: sudo systemctl restart postgresql
```

## Issue: "Database Connection Failed" When Testing Data Source

### Check 1: Network Connectivity
```bash
# From Grafana server
ping 10.55.12.99
telnet 10.55.12.99 5432
```

### Check 2: PostgreSQL Configuration
Edit `/etc/postgresql/*/main/postgresql.conf`:
```
listen_addresses = '*'
port = 5432
```

Edit `/etc/postgresql/*/main/pg_hba.conf`:
```
# Add this line (replace with actual Grafana IP for security)
host    all    all    0.0.0.0/0    md5
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### Check 3: Firewall Rules
```bash
# Allow PostgreSQL port
sudo ufw allow 5432/tcp
```

## Issue: Queries Run But Show "No data"

### Solution 1: Check Time Range
- Dashboard default time range: Last 24 hours
- If your data is older, change time range:
  1. Click time picker at top right
  2. Select **Last 7 days** or **Last 30 days**
  3. Or use **Custom** to select specific date range

### Solution 2: Generate Sample Data
```python
# Run this to insert sample data
from core.coverage.behavioral_collectors import *
from persistence.db_manager import DBManager
from datetime import datetime

db = DBManager()
session = db.get_session()

# Sample API coverage
api_collector = ApiEndpointCollector(db)
api_collector.record_api_call(
    test_case_id="test-123",
    endpoint_path="/api/users",
    http_method="GET",
    status_code=200,
    response_time_ms=45.5,
    request_payload={"limit": 10},
    response_payload={"users": []},
    headers={"Content-Type": "application/json"}
)

# Sample UI coverage
ui_collector = UiComponentCollector(db)
ui_collector.record_interaction(
    test_case_id="test-123",
    component_name="LoginButton",
    component_type="button",
    interaction_type="click",
    page_url="/login",
    state_before={"visible": True},
    state_after={"visible": True, "clicked": True}
)

session.commit()
session.close()
print("Sample data inserted!")
```

## Issue: Panels Show Different Datasource Names

### Solution: Manually Update Each Panel
1. Open dashboard
2. Click **⚙️ (Dashboard settings)** at top right
3. Click **JSON Model** in left sidebar
4. Search for `"datasource":`
5. Replace any inconsistent datasource references with:
```json
"datasource": {
  "type": "postgres",
  "uid": "${DS_CROSSBRIDGE_COVERAGE_DB}"
}
```
6. Click **Save changes**
7. Click **Save dashboard**

## Quick Reference: Working Dashboard Features

### Panel 1: Unique API Endpoints (Stat)
- **Query**: `SELECT COUNT(DISTINCT endpoint_path) as value FROM api_endpoint_coverage;`
- **Expected**: Green background with number > 0
- **Colors**: Red (0-9), Yellow (10-49), Green (50+)

### Panel 2: Total API Calls (Stat)
- **Query**: `SELECT COUNT(*) as value FROM api_endpoint_coverage;`
- **Expected**: Blue background with number > 0

### Panel 3: UI Components Tested (Stat)
- **Query**: `SELECT COUNT(DISTINCT component_name) as value FROM ui_component_coverage;`
- **Expected**: Green background with number > 0
- **Colors**: Red (0-4), Yellow (5-19), Green (20+)

### Panel 4: Active Tests (Stat)
- **Query**: `SELECT COUNT(DISTINCT id) as value FROM test_case;`
- **Expected**: Purple background with number > 0

### Panel 5: Top 10 Most Tested Endpoints (Bar Chart)
- **Query**: Shows endpoints with most test coverage
- **Expected**: Horizontal bars showing endpoint names and test counts

### Panel 6: HTTP Status Code Distribution (Pie Chart)
- **Query**: Groups API calls by status code
- **Expected**: Pie slices for 200, 201, 404, 500, etc.

### Panel 7: API Coverage Over Time (Time Series)
- **Query**: Shows trends over last 24 hours
- **Expected**: Line graph with 2 series (Unique Endpoints, Total Calls)

### Panel 8: UI Component Interactions (Table)
- **Query**: Lists components with interaction counts
- **Expected**: Table with columns: component_name, component_type, total_interactions, unique_tests, pages_count

### Panel 9: Test Framework Distribution (Donut Chart)
- **Query**: Groups tests by framework (pytest, selenium, etc.)
- **Expected**: Donut chart showing framework percentages

## Still Having Issues?

### Contact Support
1. Export dashboard JSON: **Dashboard settings → JSON Model → Copy to clipboard**
2. Export Grafana logs: `sudo journalctl -u grafana-server --since "1 hour ago" > grafana.log`
3. Export query results:
```sql
-- Save this output
\o output.txt
SELECT * FROM api_endpoint_coverage LIMIT 5;
SELECT * FROM ui_component_coverage LIMIT 5;
\o
```
4. Share these files for debugging

### Common Gotchas
- ❌ Datasource name mismatch (must be exact)
- ❌ Time range too narrow (data outside range)
- ❌ No data in database (run tests first)
- ❌ Wrong database selected (check db name)
- ❌ PostgreSQL not accepting remote connections (pg_hba.conf)
- ❌ Firewall blocking port 5432

### Working Setup Checklist
- ✅ PostgreSQL accessible from Grafana server
- ✅ Datasource named exactly: `CrossBridge Coverage DB`
- ✅ Datasource test passes (green ✅)
- ✅ Database has data (queries return > 0)
- ✅ Dashboard imported using `dashboard_working.json`
- ✅ Panels linked to correct datasource
- ✅ Time range includes data timestamps
