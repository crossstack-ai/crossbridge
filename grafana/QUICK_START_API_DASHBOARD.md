# Grafana Dashboard Quick Start - 5 Minutes

## 🚀 Quick Setup Steps

### 1️⃣ Generate Test Data (1 minute)

```bash
cd d:/Future-work2/crossbridge
python populate_api_change_test_data.py
```

**This creates:**
- 50 API change events (last 7 days)
- 20 alert history records
- 100 Grafana metrics

---

### 2️⃣ Configure Grafana Datasource (2 minutes)

1. **Open Grafana:** http://10.55.12.99:3000
2. **Login:** admin / admin
3. **Add Datasource:**
   - Go to: ⚙️ **Configuration** → **Data Sources**
   - Click: **Add data source**
   - Select: **PostgreSQL**
   
4. **Enter Details:**
   ```
   Name: CrossBridge PostgreSQL
   Host: 10.60.67.247:5432
   Database: crossbridge_test
   User: postgres
   Password: admin
   SSL Mode: disable
   Version: 16+
   ```

5. **Test:** Click **Save & Test** → Should see ✅ green checkmark

---

### 3️⃣ Import Dashboard (2 minutes)

1. **Navigate:** **+ (Plus)** → **Import**

2. **Upload:** Click **Upload JSON file**
   - File: `grafana/dashboards/api_change_intelligence_v2.json`

3. **Configure:**
   - Datasource: Select **CrossBridge PostgreSQL**
   - Folder: Select or create "CrossBridge"

4. **Import:** Click **Import** button

---

### 4️⃣ View Dashboard (instant)

1. **Dashboard loads automatically**
2. **Set time range:** Top-right → Select **Last 7 days**
3. **All 15 panels should show data** ✅

---

## 📊 Expected Results

You should see:
- ✅ **Total API Changes:** 50+ in last 7 days
- ✅ **Breaking Changes:** Multiple breaking changes
- ✅ **Risk Distribution:** Pie chart with LOW/MEDIUM/HIGH/CRITICAL
- ✅ **Time Series:** Line charts with change trends
- ✅ **Recent Changes Table:** Last 50 changes with details
- ✅ **Alerts:** 20 alert history records

---

## 🎯 Dashboard Panels Overview

| Panel | Description |
|-------|-------------|
| **Stats (Row 1)** | Total Changes, Breaking Changes, Critical Changes, Alerts |
| **Time Series (Row 2)** | Changes Over Time, Changes by Risk Level |
| **Pie Charts (Row 3)** | Risk Distribution, Change Types, Entity Types |
| **Table (Row 4)** | Recent 50 API changes with filtering |
| **Bar Charts (Row 5)** | Top APIs, Changes by HTTP Method |
| **Alerts (Row 6)** | Recent Alerts Table, Alerts Over Time |
| **Metrics (Row 7)** | Pre-aggregated Grafana metrics |

---

## 🔧 Troubleshooting

### "No Data" in Panels?

**Check 1:** Verify data exists
```bash
python test_db_connection.py
```

**Check 2:** Adjust time range
- Change from "Last 24 hours" to "Last 7 days"

**Check 3:** Verify datasource
- Dashboard Settings → Variables → Check `DS_CROSSBRIDGE`

---

### Dashboard Import Failed?

**Solution:** Copy JSON content manually
1. Open: `grafana/dashboards/api_change_intelligence_v2.json`
2. Copy entire content (Ctrl+A, Ctrl+C)
3. In Grafana Import: Select **Import via panel json**
4. Paste content (Ctrl+V)
5. Configure datasource
6. Import

---

## 📁 Files Reference

| File | Purpose |
|------|---------|
| `api_change_intelligence_v2.json` | Dashboard JSON (15 panels) |
| `API_CHANGE_DASHBOARD_SETUP.md` | Detailed setup guide |
| `populate_api_change_test_data.py` | Test data generator |
| `test_db_connection.py` | Database connection tester |
| `setup_integration_test_db.py` | Database schema creator |

---

## ✅ Success Checklist

- [ ] PostgreSQL connection working
- [ ] Test data generated (50+ changes)
- [ ] Grafana datasource configured
- [ ] Dashboard imported successfully
- [ ] All 15 panels showing data
- [ ] Time range set to "Last 7 days"
- [ ] Auto-refresh working (30s)

---

## 🎨 Dashboard Features

- ✅ **Real-time updates** - Auto-refreshes every 30 seconds
- ✅ **Interactive** - Click charts to filter
- ✅ **Color-coded** - Risk levels have distinct colors
- ✅ **Annotations** - Critical changes marked on timeline
- ✅ **Sortable tables** - Click headers to sort
- ✅ **Time range picker** - Select any time period
- ✅ **Drill-down** - Click metrics to see details

---

## 📞 Need Help?

See detailed guide: [API_CHANGE_DASHBOARD_SETUP.md](API_CHANGE_DASHBOARD_SETUP.md)

---

**Total Setup Time:** ~5 minutes  
**Dashboard Version:** 2.0  
**Status:** ✅ Production Ready
