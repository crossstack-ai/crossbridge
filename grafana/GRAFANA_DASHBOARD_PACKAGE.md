# Grafana Dashboard Setup - Complete Package

**Created:** January 29, 2026  
**Dashboard Version:** 3.0  
**Status:** ✅ Ready to Import  
**Dashboard File:** `grafana/dashboards/api_change_intelligence_v3.json`

---

## 📦 Package Contents

### 1. Dashboard JSON File ⭐
**File:** `grafana/dashboards/api_change_intelligence_v3.json`
- **Size:** ~18KB (530 lines)
- **UID:** Auto-assigned on import
- **Panels:** 14 comprehensive panels
- **Refresh:** Auto-refresh every 30 seconds
- **Time Range:** Default last 24 hours
- **✨ NEW:** Datasource dropdown for PostgreSQL selection

### 2. Setup Documentation
- **Quick Start:** `QUICK_START_API_DASHBOARD.md` (5-minute setup)
- **Detailed Guide:** `API_CHANGE_DASHBOARD_SETUP.md` (comprehensive)

### 3. Test Data Generator
**File:** `populate_api_change_test_data.py`
- Generates 50 API change events
- Creates 20 alert history records
- Populates 100+ Grafana metrics

### 4. Database Setup Scripts
- `setup_integration_test_db.py` - Creates database and schema
- `test_db_connection.py` - Verifies database connectivity

---

## 🎯 Dashboard Panels (14 Total)

### Key Metrics (Row 1)
1. **Total API Changes (24h)** - Stat panel with thresholds
2. **Breaking Changes (24h)** - Breaking change count
3. **Critical Risk Changes (24h)** - CRITICAL severity count
4. **Alerts Sent (24h)** - Total alerts dispatched

### Time Series Analysis (Row 2)
5. **API Changes Over Time** - Hourly trend chart
6. **Breaking vs Non-Breaking Changes** - Comparison with color coding

### Distribution Analysis (Row 3)
7. **Risk Level Distribution (24h)** - Donut chart with color coding
8. **Change Types Distribution (24h)** - Pie chart (ADDED/MODIFIED/REMOVED)
9. **Entity Types Distribution (24h)** - Pie chart (ENDPOINT/SCHEMA/etc.)

### Recent Activity (Row 4)
10. **Recent API Changes (Last 50)** - Interactive table with:
    - Time, Entity, Change Type, Entity Type, Path, Method
    - Breaking indicator (YES/NO)
    - Color-coded risk levels

### Top Changes (Row 5)
11. **Top 10 APIs with Most Changes** - Horizontal bar gauge
12. **Changes by HTTP Method** - Method breakdown (GET/POST/PUT/DELETE/PATCH)

### Alert Monitoring (Row 6)
13. **Recent Alerts (Last 50)** - Alert history table with:
    - Time, Title, Message, Severity, Source, Notifiers
    - Fixed column names for alert_history table
14. **Alerts by Severity Over Time** - Time series tracking alert frequency

---

## 🗄️ Database Schema

### Tables Required:

#### 1. api_changes (50 rows generated)
```sql
- change_id (unique)
- change_type (ADDED/MODIFIED/REMOVED)
- entity_type (ENDPOINT/SCHEMA/PARAMETER/etc.)
- entity_name
- path
- http_method (GET/POST/PUT/DELETE/PATCH)
- breaking (boolean)
- risk_level (LOW/MEDIUM/HIGH/CRITICAL)
- detected_at (timestamp)
- old_value, new_value
```

#### 2. alert_history (20 rows generated)
```sql
- alert_id (unique)
- title
- message
- severity (critical/high/medium/low/info)
- source
- sent_at (timestamp)
- notifiers_sent (count)
```

#### 3. grafana_api_metrics (192 rows generated)
```sql
- metric_time (timestamp)
- change_type
- entity_type
- severity
- risk_level
- breaking_count
- total_count
```

---

## 🚀 Quick Import Instructions

### Method 1: File Upload (Recommended)

1. **Open Grafana:** http://10.55.12.99:3000
2. **Go to Import:** Click **+** → **Import**
3. **Upload JSON:**
   - Click **Upload JSON file**
   - Select: `grafana/dashboards/api_change_intelligence_v2.json`
4. **Configure:**
   - Datasource: **CrossBridge PostgreSQL**
   - Folder: **CrossBridge** (create if needed)
5. **Import:** Click **Import** button

### Method 2: Copy-Paste JSON

1. **Open JSON file:** `api_change_intelligence_v2.json`
2. **Copy content:** Ctrl+A → Ctrl+C
3. **Go to Import:** Grafana → **+** → **Import**
4. **Paste:** Click **Import via panel json** → Ctrl+V
5. **Configure & Import**

---

## 📊 Sample Queries

The dashboard uses these PostgreSQL queries:

### Query 1: Total Changes (24h)
```sql
SELECT COUNT(*) as value 
FROM api_changes 
WHERE detected_at > NOW() - INTERVAL '24 hours'
```

### Query 2: Breaking Changes Over Time
```sql
SELECT 
  DATE_TRUNC('hour', detected_at) as time, 
  COUNT(*) as "Breaking Changes" 
FROM api_changes 
WHERE breaking = true 
AND $__timeFilter(detected_at) 
GROUP BY time 
ORDER BY time
```

### Query 3: Risk Level Distribution
```sql
SELECT 
  risk_level as metric, 
  COUNT(*) as value 
FROM api_changes 
WHERE detected_at > NOW() - INTERVAL '24 hours' 
GROUP BY risk_level 
ORDER BY COUNT(*) DESC
```

### Query 4: Recent Changes Table
```sql
SELECT 
  detected_at as "Time", 
  entity_name as "Entity", 
  change_type as "Change Type", 
  CASE WHEN breaking THEN '🔴 YES' ELSE '🟢 NO' END as "Breaking",
  risk_level as "Risk Level" 
FROM api_changes 
ORDER BY detected_at DESC 
LIMIT 50
```

---

## 🎨 Visual Features

### Color Coding
- **CRITICAL:** 🔴 Dark Red (#C4162A)
- **HIGH:** 🟠 Red (#E02F44)
- **MEDIUM:** 🟡 Orange (#FF9830)
- **LOW:** 🟢 Green (#73BF69)

### Thresholds
- **Total Changes:** Green (0-9), Yellow (10-49), Red (50+)
- **Breaking Changes:** Green (0), Orange (1-4), Red (5+)
- **Critical Changes:** Green (0), Red (1+)

### Annotations
- Red markers on timeline for CRITICAL risk changes
- Click to see change details

---

## ✅ Pre-Flight Checklist

Before importing dashboard:

- [ ] **Database:** PostgreSQL running at 10.60.67.247:5432
- [ ] **Database Name:** crossbridge_test exists
- [ ] **Schema:** Tables created (api_changes, alert_history, grafana_api_metrics)
- [ ] **Test Data:** 50+ rows in api_changes table
- [ ] **Grafana:** Accessible at http://10.55.12.99:3000
- [ ] **Datasource:** PostgreSQL datasource configured in Grafana
- [ ] **JSON File:** api_change_intelligence_v2.json downloaded

### Verify Database:
```bash
cd d:/Future-work2/crossbridge
python test_db_connection.py
```

### Generate Test Data:
```bash
python populate_api_change_test_data.py
```

---

## 🔧 Configuration Options

### Refresh Rate
Default: **30 seconds**

Change in dashboard:
- Top-right corner → Refresh dropdown
- Options: 10s, 30s, 1m, 5m, 15m, 30m, 1h

### Time Range
Default: **Last 24 hours**

Common ranges:
- Last 5 minutes
- Last 1 hour
- Last 6 hours
- **Last 7 days** ← Recommended for testing
- Last 30 days
- Custom range

### Datasource Variable
**Variable Name:** `DS_CROSSBRIDGE`

Update in:
- Dashboard Settings → Variables
- Set to your PostgreSQL datasource

---

## 📈 Dashboard Metrics Summary

| Metric | Description | Panel Type |
|--------|-------------|------------|
| Total Changes | All API changes in time period | Stat |
| Breaking Changes | Changes marked as breaking | Stat |
| Critical Changes | CRITICAL risk level changes | Stat |
| Alerts Sent | Alerts dispatched to notifiers | Stat |
| Changes Over Time | Hourly trend analysis | Time Series |
| Risk Distribution | Breakdown by risk level | Pie Chart |
| Recent Changes | Last 50 changes with details | Table |
| Top APIs | APIs with most changes | Bar Gauge |
| Alert History | Recent alerts sent | Table |
| Metrics Aggregation | Pre-calculated metrics | Time Series |

---

## 🔍 Troubleshooting

### Issue: "No Data" in Panels

**Cause:** No data in selected time range

**Solution:**
1. Change time range to "Last 7 days"
2. Run test data generator: `python populate_api_change_test_data.py`
3. Check database: `python test_db_connection.py`

### Issue: "Database Connection Failed"

**Solution:**
1. Verify PostgreSQL is running
2. Check network connectivity to 10.60.67.247:5432
3. Test credentials: user=postgres, password=admin
4. Verify database exists: crossbridge_test

### Issue: Panels Load Slowly

**Solution:**
1. Verify indexes exist (auto-created by setup script)
2. Reduce time range (use 24h instead of 30 days)
3. Increase refresh interval (use 1m instead of 30s)

---

## 📁 File Locations

```
crossbridge/
├── grafana/
│   ├── dashboards/
│   │   └── api_change_intelligence_v2.json  ⭐ Main Dashboard
│   ├── API_CHANGE_DASHBOARD_SETUP.md        📖 Detailed Guide
│   └── QUICK_START_API_DASHBOARD.md         🚀 Quick Start
├── setup_integration_test_db.py             🗄️ Database Setup
├── test_db_connection.py                    🔍 Connection Test
├── populate_api_change_test_data.py         📊 Test Data Generator
└── TEST_RESULTS_FINAL.md                    ✅ Test Results
```

---

## 🎯 Expected Results

After import, you should see:

✅ **4 Stat Panels** showing:
- 50 total changes
- ~15 breaking changes
- ~12 critical changes
- 20 alerts sent

✅ **2 Time Series Charts** with hourly trends

✅ **3 Pie Charts** showing distributions

✅ **1 Table** with 50 recent changes

✅ **2 Bar Gauges** with top APIs and methods

✅ **2 Alert Panels** with alert history

✅ **1 Metrics Panel** with aggregated data

---

## 🌟 Dashboard Features

- ✅ **Real-time Updates:** Auto-refresh every 30 seconds
- ✅ **Interactive:** Click charts to drill down
- ✅ **Color-Coded:** Risk levels visually distinct
- ✅ **Annotations:** Critical changes marked on timeline
- ✅ **Sortable:** Tables support sorting and filtering
- ✅ **Responsive:** Adapts to screen size
- ✅ **Sharable:** Export snapshots or share links
- ✅ **Alertable:** Add Grafana alerts to any panel

---

## 📞 Support

### Documentation
- **Quick Start:** [QUICK_START_API_DASHBOARD.md](QUICK_START_API_DASHBOARD.md)
- **Setup Guide:** [API_CHANGE_DASHBOARD_SETUP.md](API_CHANGE_DASHBOARD_SETUP.md)
- **Test Results:** [TEST_RESULTS_FINAL.md](../TEST_RESULTS_FINAL.md)

### Scripts
- **Test Connection:** `python test_db_connection.py`
- **Generate Data:** `python populate_api_change_test_data.py`
- **Setup Database:** `python setup_integration_test_db.py`

### Configuration
- **Main Config:** `crossbridge.yml` (lines 960-990)
- **Grafana Section:** Set `enabled: true`

---

## ✨ Next Steps

1. ✅ **Import Dashboard** (5 minutes)
2. ✅ **Verify Data** (check all panels)
3. ✅ **Customize** (adjust colors, thresholds)
4. ✅ **Set Alerts** (configure Grafana alerts)
5. ✅ **Share** (invite team members)
6. ✅ **Monitor** (watch for API changes in production)

---

**Package Version:** 2.0  
**Last Updated:** January 29, 2026  
**Status:** ✅ Production Ready  
**Test Data:** ✅ 50 changes, 20 alerts, 192 metrics generated
