# Grafana Dashboard Setup Guide - API Change Intelligence

**Dashboard Version:** 2.0  
**Date:** January 29, 2026  
**Database:** PostgreSQL 16.11 @ 10.60.67.247:5432  
**Database Name:** crossbridge_test

---

## 📊 Dashboard Overview

The **API Change Intelligence Dashboard** provides real-time monitoring of:
- API changes (breaking and non-breaking)
- Risk level distributions
- Alert history
- Confluence notifications
- Change trends over time

### Dashboard Features:
- ✅ 15 panels with comprehensive metrics
- ✅ Real-time updates (30s refresh)
- ✅ Time series charts for trend analysis
- ✅ Pie charts for distribution analysis
- ✅ Interactive tables with recent changes
- ✅ Color-coded risk levels
- ✅ Alert severity tracking
- ✅ Breaking change annotations

---

## 🚀 Quick Setup (5 Minutes)

### Step 1: Configure Grafana Datasource

1. **Access Grafana:**
   ```
   URL: http://10.55.12.99:3000
   Username: admin
   Password: admin (or your configured password)
   ```

2. **Add PostgreSQL Datasource:**
   - Navigate to: **Configuration** → **Data Sources**
   - Click: **Add data source**
   - Select: **PostgreSQL**
   
3. **Configure Connection:**
   ```yaml
   Name: CrossBridge PostgreSQL
   Host: 10.60.67.247:5432
   Database: crossbridge_test
   User: postgres
   Password: admin
   SSL Mode: disable
   Version: 16+ (or select latest)
   ```

4. **Save & Test:**
   - Click **Save & Test**
   - Should show: ✅ **Database Connection OK**

### Step 2: Import Dashboard

1. **Navigate to Import:**
   - Go to: **+ (Plus icon)** → **Import**
   - Or: **Dashboards** → **Browse** → **Import**

2. **Upload Dashboard JSON:**
   - Click: **Upload JSON file**
   - Select: `grafana/dashboards/api_change_intelligence_v2.json`
   - Or: Copy and paste the JSON content

3. **Configure Import:**
   - **Name:** API Change Intelligence Dashboard (or customize)
   - **Folder:** Select or create "CrossBridge" folder
   - **Datasource:** Select **CrossBridge PostgreSQL** (from Step 1)
   - **UID:** `api-change-intel-v2` (auto-filled)

4. **Import:**
   - Click: **Import**
   - Dashboard should load immediately

### Step 3: Verify Dashboard

1. **Check Panels:**
   - All 15 panels should load
   - If "No Data" appears, check time range (default: last 24 hours)

2. **Adjust Time Range:**
   - Top-right corner: Click time range selector
   - Try: "Last 7 days" or "Last 30 days"
   - Or use custom range

3. **Test Refresh:**
   - Dashboard auto-refreshes every 30 seconds
   - Manually refresh: Click **🔄 Refresh** button

---

## 📋 Dashboard Panels

### Row 1: Key Metrics (4 Stats)
1. **Total API Changes (24h)** - Count of all changes
   - 🟢 Green: 0-9 changes
   - 🟡 Yellow: 10-49 changes
   - 🔴 Red: 50+ changes

2. **Breaking Changes (24h)** - Count of breaking changes
   - 🟢 Green: 0 changes
   - 🟠 Orange: 1-4 changes
   - 🔴 Red: 5+ changes

3. **Critical Risk Changes (24h)** - Critical severity count
   - 🟢 Green: 0 changes
   - 🔴 Red: 1+ changes

4. **Alerts Sent (24h)** - Total alerts sent
   - 🔵 Blue: All counts

### Row 2: Time Series (2 Charts)
5. **API Changes Over Time** - Hourly breakdown
   - Shows total and breaking changes
   - Breaking changes highlighted in red

6. **Changes by Risk Level** - Stacked area chart
   - Color-coded by risk: CRITICAL (dark red), HIGH (red), MEDIUM (orange), LOW (green)

### Row 3: Distribution (3 Pie Charts)
7. **Risk Level Distribution (24h)** - Donut chart
8. **Change Types Distribution (24h)** - Pie chart
9. **Entity Types Distribution (24h)** - Pie chart

### Row 4: Recent Changes Table
10. **Recent API Changes (Last 50)** - Interactive table
    - Columns: Time, Entity, Change Type, Entity Type, Path, Method, Breaking, Risk Level
    - Sortable and filterable
    - Color-coded risk levels

### Row 5: Top Changes (2 Bar Gauges)
11. **Top 10 APIs with Most Changes** - Horizontal bar chart
12. **Changes by HTTP Method** - HTTP method breakdown

### Row 6: Alerts (2 Panels)
13. **Recent Alerts Sent** - Alert history table
    - Shows last 20 alerts
    - Color-coded severity

14. **Alerts by Severity Over Time** - Time series chart
    - Tracks alert frequency by severity

### Row 7: Metrics Aggregation
15. **Grafana Metrics Aggregation** - Pre-aggregated metrics
    - Uses `grafana_api_metrics` table for fast queries

---

## 🗄️ Database Schema Reference

### Tables Used by Dashboard:

#### 1. `api_changes`
```sql
CREATE TABLE api_changes (
    id SERIAL PRIMARY KEY,
    change_id VARCHAR(500) UNIQUE NOT NULL,
    change_type VARCHAR(100) NOT NULL,      -- ADDED, MODIFIED, REMOVED
    entity_type VARCHAR(100) NOT NULL,      -- ENDPOINT, SCHEMA, PARAMETER, etc.
    entity_name VARCHAR(500),               -- Name of changed entity
    path VARCHAR(500),                      -- API path
    http_method VARCHAR(10),                -- GET, POST, PUT, DELETE, etc.
    breaking BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(20),                 -- LOW, MEDIUM, HIGH, CRITICAL
    old_value TEXT,
    new_value TEXT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    recommended_tests TEXT[]
);
```

#### 2. `alert_history`
```sql
CREATE TABLE alert_history (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(500) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    message TEXT,
    severity VARCHAR(20) NOT NULL,          -- critical, high, medium, low, info
    source VARCHAR(200),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notifiers_sent INTEGER DEFAULT 0,       -- Number of notifiers (Email, Slack, Confluence)
    details JSONB,
    tags TEXT[]
);
```

#### 3. `grafana_api_metrics`
```sql
CREATE TABLE grafana_api_metrics (
    id SERIAL PRIMARY KEY,
    metric_time TIMESTAMP NOT NULL,
    change_type VARCHAR(100),
    entity_type VARCHAR(100),
    severity VARCHAR(20),
    risk_level VARCHAR(20),
    breaking_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 1,
    metadata JSONB
);
```

---

## 🔍 Sample Queries

### Query 1: Check Recent Changes
```sql
SELECT * FROM api_changes 
ORDER BY detected_at DESC 
LIMIT 10;
```

### Query 2: Count Breaking Changes
```sql
SELECT COUNT(*) 
FROM api_changes 
WHERE breaking = true 
AND detected_at > NOW() - INTERVAL '24 hours';
```

### Query 3: Risk Level Breakdown
```sql
SELECT risk_level, COUNT(*) as count 
FROM api_changes 
WHERE detected_at > NOW() - INTERVAL '24 hours'
GROUP BY risk_level 
ORDER BY count DESC;
```

### Query 4: Recent Alerts
```sql
SELECT sent_at, title, severity, notifiers_sent 
FROM alert_history 
ORDER BY sent_at DESC 
LIMIT 20;
```

---

## 🧪 Testing the Dashboard

### Generate Test Data (Optional)

If you want to populate sample data for testing:

```bash
cd d:/Future-work2/crossbridge
python populate_api_change_test_data.py
```

This will create:
- 50 sample API change events
- 10 alert history records
- 20 Grafana metrics records

### Verify Data in Database

```bash
python test_db_connection.py
```

Or connect via psql:
```bash
psql -h 10.60.67.247 -p 5432 -U postgres -d crossbridge_test
```

Then run:
```sql
SELECT COUNT(*) FROM api_changes;
SELECT COUNT(*) FROM alert_history;
SELECT COUNT(*) FROM grafana_api_metrics;
```

---

## ⚙️ Dashboard Configuration

### Refresh Rate
- **Default:** 30 seconds
- **Options:** 10s, 30s, 1m, 5m, 15m, 30m, 1h
- **Location:** Top-right corner dropdown

### Time Range
- **Default:** Last 24 hours
- **Common Options:**
  - Last 5 minutes
  - Last 15 minutes
  - Last 1 hour
  - Last 6 hours
  - Last 24 hours
  - Last 7 days
  - Last 30 days
  - Custom range

### Annotations
- **Critical Changes:** Red markers on time series charts
- Shows when CRITICAL risk changes were detected
- Click marker to see details

---

## 🔧 Troubleshooting

### Issue 1: "No Data" in Panels

**Possible Causes:**
1. No data in database for selected time range
2. Datasource not configured correctly
3. Tables not created

**Solutions:**
```bash
# Check database connection
python test_db_connection.py

# Verify tables exist
python -c "import psycopg2; conn = psycopg2.connect(host='10.60.67.247', port=5432, database='crossbridge_test', user='postgres', password='admin'); cursor = conn.cursor(); cursor.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'\"); print([row[0] for row in cursor.fetchall()]); conn.close()"

# Check data exists
python -c "import psycopg2; conn = psycopg2.connect(host='10.60.67.247', port=5432, database='crossbridge_test', user='postgres', password='admin'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM api_changes'); print(f'api_changes: {cursor.fetchone()[0]} rows'); conn.close()"
```

### Issue 2: "Database Connection Failed"

**Solution:**
1. Verify PostgreSQL is running
2. Check firewall rules allow port 5432
3. Verify credentials in Grafana datasource
4. Test connection from command line:
   ```bash
   python test_db_connection.py
   ```

### Issue 3: Panels Load Slowly

**Solutions:**
1. **Add Indexes** (if not already created):
   ```sql
   CREATE INDEX IF NOT EXISTS idx_api_changes_detected_at ON api_changes(detected_at DESC);
   CREATE INDEX IF NOT EXISTS idx_alert_history_sent_at ON alert_history(sent_at DESC);
   CREATE INDEX IF NOT EXISTS idx_grafana_metrics_time ON grafana_api_metrics(metric_time DESC);
   ```

2. **Increase Refresh Interval:** Change from 30s to 1m or 5m

3. **Reduce Time Range:** Use "Last 6 hours" instead of "Last 30 days"

### Issue 4: Wrong Datasource Selected

**Solution:**
1. Click **Dashboard Settings** (⚙️ gear icon)
2. Select **Variables** tab
3. Update `DS_CROSSBRIDGE` variable to correct datasource
4. Save dashboard

---

## 📊 Dashboard Customization

### Add Custom Panel

1. Click **Add Panel** (+ icon in dashboard)
2. Select **Add new panel**
3. Configure query:
   ```sql
   SELECT * FROM api_changes 
   WHERE risk_level = 'CRITICAL'
   ORDER BY detected_at DESC
   ```
4. Choose visualization type
5. Save panel

### Modify Existing Panel

1. Click panel title → **Edit**
2. Modify query or visualization settings
3. Click **Apply** to save

### Create Alert Rule

1. Edit panel → **Alert** tab
2. Configure alert conditions:
   ```
   WHEN count() OF query(A, 5m, now) IS ABOVE 10
   ```
3. Set notification channel (Email, Slack, etc.)
4. Save alert

---

## 🎨 Color Scheme Reference

### Risk Levels
- 🔴 **CRITICAL:** `dark-red` (#C4162A)
- 🟠 **HIGH:** `red` (#E02F44)
- 🟡 **MEDIUM:** `orange` (#FF9830)
- 🟢 **LOW:** `green` (#73BF69)

### Alert Severity
- 🔴 **critical:** `dark-red`
- 🟠 **high:** `red`
- 🟡 **medium:** `orange`
- 🟢 **low:** `green`
- 🔵 **info:** `blue`

---

## 📁 Dashboard Files

### Main Dashboard
- **File:** `grafana/dashboards/api_change_intelligence_v2.json`
- **UID:** `api-change-intel-v2`
- **Version:** 2.0
- **Panels:** 15
- **Lines:** ~600

### Supporting Files
- **Setup Script:** `setup_integration_test_db.py`
- **Connection Test:** `test_db_connection.py`
- **Test Data Generator:** `populate_api_change_test_data.py` (to be created)

---

## 🚀 Production Deployment

### 1. Update crossbridge.yml

Enable Grafana integration:
```yaml
grafana:
  enabled: true
  dashboard_path: grafana/dashboards/api_change_intelligence_v2.json
```

### 2. Configure Alerts (Optional)

Add Grafana alert rules for:
- Critical API changes detected
- High number of breaking changes
- Alert failure notifications

### 3. Set Up Backup

Schedule regular dashboard backups:
```bash
# Export dashboard JSON via API
curl -u admin:admin "http://10.55.12.99:3000/api/dashboards/uid/api-change-intel-v2" > backup_$(date +%Y%m%d).json
```

### 4. Share Dashboard

- **Public Link:** Dashboard Settings → Links → Share
- **Snapshot:** Dashboard Settings → Links → Snapshot
- **Embed:** Dashboard Settings → Links → Embed

---

## ✅ Next Steps

1. ✅ **Import Dashboard** - Follow Quick Setup above
2. ✅ **Verify Data** - Check all panels load correctly
3. ✅ **Customize** - Adjust colors, time ranges, refresh rates
4. ✅ **Set Alerts** - Configure Grafana alerts for critical events
5. ✅ **Share** - Provide dashboard access to your team

---

## 📞 Support

For issues or questions:
- Check [TEST_RESULTS_FINAL.md](../TEST_RESULTS_FINAL.md) for test results
- Review [crossbridge.yml](../crossbridge.yml) for configuration
- Run `python test_db_connection.py` to verify database

---

**Setup Guide Version:** 2.0  
**Last Updated:** January 29, 2026  
**Status:** ✅ Production Ready
