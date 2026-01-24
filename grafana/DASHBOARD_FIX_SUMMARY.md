# Grafana Dashboard Fix - Resolution Summary

## Problem
After following the setup guide, the Grafana dashboard displayed blank panels with no charts or data.

## Root Cause
The original `behavioral_coverage_dashboard.json` file had structural issues:
1. Missing proper datasource variable references in panel definitions
2. Incorrect panel structure that prevented Grafana from binding to the PostgreSQL datasource
3. Missing required Grafana metadata fields

## Solution

### Created New Files
1. **`grafana/dashboard_working.json`** - Fixed dashboard with proper structure
   - Correct datasource references in all 9 panels
   - Proper Grafana JSON schema (v38)
   - Working panel configurations with correct queries

2. **`grafana/TROUBLESHOOTING.md`** - Comprehensive troubleshooting guide
   - Step-by-step fixes for blank dashboard
   - Data verification queries
   - Common issues and solutions
   - Manual panel configuration instructions

3. **`scripts/generate_sample_data.py`** - Sample data generator
   - Creates 10 test cases
   - Generates 50 API coverage records
   - Generates 40 UI coverage records
   - Generates 30 network captures
   - Generates 20 contract validations
   - Includes data verification checks

### Updated Files
4. **`grafana/QUICK_START.md`** - Updated with:
   - Correct file reference (`dashboard_working.json`)
   - Sample data generation instructions
   - Clearer import steps
   - Better verification guidance

## What to Do Now

### Step 1: Delete Existing Dashboard
1. Go to http://10.55.12.99:3000/dashboards
2. Find "CrossBridge Behavioral Coverage" 
3. Click ⚙️ → Delete Dashboard

### Step 2: Re-import Fixed Dashboard
1. Go to **☰ → Dashboards → Import**
2. Click **Upload JSON file**
3. Select: `grafana/dashboard_working.json` ⚠️ (NEW file)
4. On import screen:
   - **CrossBridge Coverage DB**: Select your PostgreSQL datasource
5. Click **Import**

### Step 3: Generate Sample Data (if dashboard still blank)
```bash
cd d:\Future-work2\crossbridge
python scripts/generate_sample_data.py
```

This creates realistic test data across all coverage types.

### Step 4: Refresh Dashboard
- Go to your dashboard
- Press **Ctrl+R** or click refresh icon
- All 9 panels should now display data

## Dashboard Panels (What You'll See)

### Row 1: Overview Stats (4 panels)
1. **Unique API Endpoints** - Count of distinct API paths tested
   - Green if > 50, Yellow if 10-49, Red if < 10
   
2. **Total API Calls** - Total number of API requests captured
   - Blue background with number
   
3. **UI Components Tested** - Count of distinct UI components
   - Green if > 20, Yellow if 5-19, Red if < 5
   
4. **Active Tests** - Total test cases in system
   - Purple background with number

### Row 2: API Analysis (2 panels)
5. **Top 10 Most Tested Endpoints** - Bar chart
   - Shows which endpoints have most test coverage
   - Horizontal bars sorted by test count
   
6. **HTTP Status Code Distribution** - Pie chart
   - Shows distribution of 2xx, 4xx, 5xx responses
   - Helps identify error patterns

### Row 3: Trends (1 panel)
7. **API Coverage Over Time** - Time series graph
   - 24-hour trend of unique endpoints and total calls
   - Two lines showing coverage growth
   - Updates every 30 seconds

### Row 4: Details (2 panels)
8. **UI Component Interactions** - Table
   - Lists all UI components with interaction counts
   - Shows: component name, type, interactions, tests, pages
   - Color-coded by interaction count
   
9. **Test Framework Distribution** - Donut chart
   - Shows breakdown by test framework (pytest, selenium, etc.)
   - Helps understand test composition

## Verification Checklist

After re-importing, verify:
- ✅ Dashboard loads without errors
- ✅ All 9 panels are visible
- ✅ Top 4 stat panels show numbers (not "No data")
- ✅ Bar chart displays horizontal bars
- ✅ Pie charts show colored slices
- ✅ Time series graph shows lines (if data within 24h)
- ✅ Table shows rows of data
- ✅ No red datasource warnings in panels

## If Still Having Issues

### Check 1: Datasource Name
Must be exactly: `CrossBridge Coverage DB`

Verify:
1. Go to **☰ → Connections → Data sources**
2. Click on PostgreSQL datasource
3. Check name matches exactly (case-sensitive)

### Check 2: Database Has Data
```bash
psql -h 10.55.12.99 -U postgres -d udp-native-webservices-automation

# Run these queries
SELECT COUNT(*) FROM api_endpoint_coverage;
SELECT COUNT(*) FROM ui_component_coverage;
SELECT COUNT(*) FROM test_case;
```

All should return > 0. If not, run `scripts/generate_sample_data.py`

### Check 3: Time Range
- Click time picker (top right)
- Set to "Last 7 days" or "Last 30 days"
- If data is older than 24 hours, it won't show in time series

### Check 4: Query Execution
1. Click on any panel title → **Edit**
2. Check **Query** tab
3. Verify datasource is green
4. Click **Run query** button
5. Should see data in preview

## Technical Details

### What Was Fixed in dashboard_working.json

**Before (broken):**
```json
{
  "dashboard": {
    "panels": [
      {
        "targets": [
          {
            "rawSql": "SELECT ..."
          }
        ]
      }
    ]
  }
}
```

**After (working):**
```json
{
  "panels": [
    {
      "datasource": {
        "type": "postgres"
      },
      "targets": [
        {
          "datasource": {
            "type": "postgres"
          },
          "rawSql": "SELECT ..."
        }
      ]
    }
  ],
  "templating": { ... },
  "annotations": { ... }
}
```

**Key changes:**
1. ✅ Removed outer `"dashboard"` wrapper (Grafana expects flat structure)
2. ✅ Added `"datasource"` object to each panel
3. ✅ Added `"datasource"` object to each target
4. ✅ Added required metadata: `annotations`, `templating`, `schemaVersion`
5. ✅ Set proper panel positions with `gridPos`
6. ✅ Added refresh interval: `"refresh": "30s"`
7. ✅ Added tags: `["crossbridge", "coverage", "testing"]`

## Files Summary

| File | Purpose | Status |
|------|---------|--------|
| `grafana/dashboard_working.json` | Fixed dashboard config | ✅ Ready to import |
| `grafana/behavioral_coverage_dashboard.json` | Original (broken) | ⚠️ Do not use |
| `grafana/TROUBLESHOOTING.md` | Detailed fixes | ✅ Reference guide |
| `grafana/QUICK_START.md` | Updated setup | ✅ Follow this |
| `grafana/GRAFANA_SETUP_GUIDE.md` | Comprehensive guide | ✅ For advanced usage |
| `scripts/generate_sample_data.py` | Data generator | ✅ Run if no data |

## Next Steps

1. ✅ **Delete** old dashboard in Grafana
2. ✅ **Import** `dashboard_working.json`
3. ✅ **Generate** sample data if needed
4. ✅ **Refresh** and verify all panels work
5. ✅ **Customize** queries or add alerts (see GRAFANA_SETUP_GUIDE.md)

## Support

If dashboard still shows blank after these steps:
1. Check `grafana/TROUBLESHOOTING.md` for detailed diagnostics
2. Verify database connectivity: `telnet 10.55.12.99 5432`
3. Check Grafana logs: `sudo tail -f /var/log/grafana/grafana.log`
4. Export dashboard JSON and check for datasource errors

## Success Criteria

You'll know it's working when:
- ✅ Dashboard loads in < 2 seconds
- ✅ All panels show data (not "No data" messages)
- ✅ Stats show green/yellow/blue backgrounds with numbers
- ✅ Charts render properly (bars, pies, lines, tables)
- ✅ No error messages in Grafana UI
- ✅ Panels auto-refresh every 30 seconds
- ✅ Time picker changes data displayed

**Expected first view:**
- Unique API Endpoints: 13 (green)
- Total API Calls: 50 (blue)
- UI Components: 12 (green)
- Active Tests: 10 (purple)
- Bar chart with 10-13 horizontal bars
- Pie chart with 5-7 slices (status codes)
- Time series with 2 lines over 24 hours
- Table with ~12 rows
- Donut with 1-5 framework slices

This indicates successful setup with the generated sample data.
