# Grafana Dashboard - Manual Setup Instructions

## Quick 5-Minute Setup

### Step 1: Add PostgreSQL Data Source (2 minutes)

1. **Open Grafana**: http://10.55.12.99:3000/
2. **Login**: admin / admin
3. **Go to Configuration** (⚙️ icon) → **Data sources**
4. **Click "Add data source"**
5. **Select "PostgreSQL"**
6. **Enter these details**:

```
Name: CrossBridge Coverage DB
Host: 10.55.12.99:5432
Database: udp-native-webservices-automation
User: postgres
Password: admin
SSL Mode: disable
Version: 12+
```

7. **Click "Save & Test"** - Should show green ✅

---

---

### Step 2: Import Dashboard (3 minutes)

**IMPORTANT**: Use the `dashboard_working.json` file (not `behavioral_coverage_dashboard.json`)

**Option A: Upload File** (Easiest - RECOMMENDED)
1. Click **"+"** (Create) → **"Import"** OR **☰ → Dashboards → Import**
2. Click **"Upload JSON file"**
3. Select file: `grafana/dashboard_working.json` ⚠️ (NOT behavioral_coverage_dashboard.json)
4. On import screen:
   - Set **Name**: "CrossBridge Behavioral Coverage" (or customize)
   - Set **Folder**: General (or choose another)
   - **CrossBridge Coverage DB**: Select your PostgreSQL datasource from dropdown
5. Click **"Import"**

**Option B: Copy-Paste**
1. Open file: `grafana/dashboard_working.json`
2. Copy entire contents (Ctrl+A, Ctrl+C)
3. Go to Grafana → **☰ → Dashboards → Import**
4. Paste JSON in text box
5. Click **"Load"**
6. On import screen, select datasource: **"CrossBridge Coverage DB"**
7. Click **"Import"**

---

### Step 3: Verify Dashboard (1 minute)

Dashboard should load with these panels:
- ✅ 4 stat cards at top (API Endpoints, Total Calls, UI Components, Active Tests)
- ✅ Bar chart showing top tested endpoints
- ✅ Pie chart with HTTP status codes
- ✅ Time series graph showing coverage over time
- ✅ Table with UI components
- ✅ Donut chart with test frameworks

**If you see BLANK panels or "No data":**

---

### Step 4: Generate Sample Data (Optional - if dashboard is blank)

**Option A: Python Script (Recommended)**
```bash
cd d:\Future-work2\crossbridge
python scripts/generate_sample_data.py
```

This will create:
- 10 test cases
- 50 API coverage records
- 40 UI coverage records  
- 30 network captures
- 20 contract validations

**Option B: Manual SQL Insert**

```sql
-- Connect to database
psql -h 10.55.12.99 -U postgres -d udp-native-webservices-automation

-- Insert test case
INSERT INTO test_case (id, framework, package, class_name, method_name, file_path, tags)
VALUES (gen_random_uuid(), 'pytest', 'tests.api', 'TestOrders', 'test_get_orders', 'tests/api/test_orders.py', ARRAY['api', 'smoke']);

-- Insert API coverage
INSERT INTO api_endpoint_coverage (id, test_case_id, endpoint_path, http_method, status_code, created_at)
SELECT 
  gen_random_uuid(),
  (SELECT id FROM test_case LIMIT 1),
  '/api/v1/orders',
  'GET',
  200,
  NOW() - (random() * interval '24 hours');

-- Repeat 10 times for different endpoints
INSERT INTO api_endpoint_coverage (id, test_case_id, endpoint_path, http_method, status_code, created_at)
SELECT 
  gen_random_uuid(),
  (SELECT id FROM test_case LIMIT 1),
  '/api/v1/users/' || floor(random() * 1000)::text,
  (ARRAY['GET', 'POST', 'PUT', 'DELETE'])[floor(random() * 4 + 1)],
  (ARRAY[200, 201, 400, 404, 500])[floor(random() * 5 + 1)],
  NOW() - (random() * interval '7 days')
FROM generate_series(1, 50);
```

Refresh dashboard - data should appear!

---

## Common Panels Explained

### Panel 1: API Endpoint Coverage
**Shows**: Total unique API endpoints tested
**Query**: `SELECT COUNT(DISTINCT endpoint_path) FROM api_endpoint_coverage`
**Color**: Red <10, Yellow <50, Green ≥50

### Panel 5: Top 10 Most Tested Endpoints
**Shows**: Which endpoints have most test coverage
**Query**: Joins endpoint_path with test counts
**Use**: Identify well-tested vs. untested endpoints

### Panel 7: Coverage Over Time
**Shows**: How coverage grows over time
**Query**: Time-series aggregation by hour
**Use**: Track coverage trends, identify testing gaps

### Panel 8: UI Component Interactions
**Shows**: All UI components with interaction counts
**Query**: From `ui_component_coverage` table
**Use**: Verify UI test coverage

---

## Customize Dashboard

### Change Time Range
- Click time picker (top-right)
- Select: "Last 5 minutes", "Last 1 hour", "Last 24 hours", "Last 7 days", etc.
- Or set custom range

### Auto-Refresh
- Click refresh dropdown (top-right)
- Select: 5s, 10s, 30s, 1m, 5m
- Dashboard updates automatically

### Edit Panel
1. Click panel title → **"Edit"**
2. Modify SQL query
3. Change visualization type
4. Adjust thresholds/colors
5. Click **"Apply"** to save

### Add New Panel
1. Click **"Add panel"** (top-right)
2. Write SQL query
3. Choose visualization
4. Configure display options
5. Click **"Apply"**

---

## Useful Queries to Add

### Coverage Gaps (Low Test Count)
```sql
SELECT 
  endpoint_path,
  http_method,
  test_count
FROM api_endpoint_summary
WHERE test_count < 3
ORDER BY test_count;
```

### Error Rate Over Time
```sql
SELECT 
  DATE_TRUNC('hour', created_at) as time,
  COUNT(*) FILTER (WHERE status_code >= 400) * 100.0 / COUNT(*) as error_rate
FROM api_endpoint_coverage
WHERE $__timeFilter(created_at)
GROUP BY time
ORDER BY time;
```

### Most Active Tests
```sql
SELECT 
  tc.method_name,
  COUNT(aec.id) as api_calls
FROM test_case tc
JOIN api_endpoint_coverage aec ON tc.id = aec.test_case_id
GROUP BY tc.id, tc.method_name
ORDER BY api_calls DESC
LIMIT 10;
```

---

## Troubleshooting

### ❌ "Database Connection OK" fails
**Fix**: Check PostgreSQL is accessible
```bash
psql -h 10.55.12.99 -U postgres -d udp-native-webservices-automation
```
If connection fails, check firewall/network

### ❌ Panels show "No data"
**Fix 1**: Check time range (set to "Last 7 days")
**Fix 2**: Verify data exists in database
```sql
SELECT COUNT(*) FROM api_endpoint_coverage;
```
**Fix 3**: Check panel query syntax (click Edit → Query tab)

### ❌ Import fails
**Fix**: Ensure data source is created first (Step 1)
**Fix**: Try copy-paste method instead of file upload

### ❌ Variables not working
**Fix**: Go to Dashboard Settings → Variables → Add variable
**Fix**: Use correct variable syntax in queries: `$variable_name`

---

## Next Steps

After setup:
1. ✅ Share dashboard URL with team
2. ✅ Set up alerts (optional)
3. ✅ Create additional custom panels
4. ✅ Configure Slack/email notifications
5. ✅ Schedule regular dashboard reviews

---

## Dashboard Features

✅ **13 pre-built panels** covering:
- API endpoint coverage statistics
- UI component interaction tracking
- HTTP status code distribution
- Test framework breakdown
- Contract validation metrics
- Network traffic analysis
- Time-series trends

✅ **Auto-refresh** - Updates every 30 seconds

✅ **Responsive** - Works on desktop, tablet, mobile

✅ **Shareable** - Send URL to colleagues

✅ **Exportable** - Download as PDF/PNG

---

## Support

- **Setup Issues**: See `GRAFANA_SETUP_GUIDE.md` for detailed troubleshooting
- **Query Examples**: See "Custom Queries" section in setup guide
- **Dashboard JSON**: `grafana/behavioral_coverage_dashboard.json`
- **Database Schema**: See `BEHAVIORAL_COVERAGE_USAGE.md`

**Enjoy your new Coverage Dashboard! 📊✨**
