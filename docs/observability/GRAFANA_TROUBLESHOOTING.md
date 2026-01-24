# Grafana Dashboard Troubleshooting

## Issue: Blank Dashboard Despite Data Existing

### Confirmed Facts
- ✅ Database has 110 events with version data
- ✅ Data is within the last 24 hours (Jan 17, 2026)
- ✅ Queries work when run directly against PostgreSQL
- ❌ Dashboard shows blank charts

### Root Cause
The dashboard JSON has a **hardcoded datasource UID** that doesn't match your Grafana instance.

## Solution: Use the Simplified Dashboard

### Step 1: Delete Current Dashboard
1. Go to http://10.55.12.99:3000/d/902/cb-dashboard-testing
2. Click **Dashboard settings** (gear icon, top right)
3. Scroll down and click **Delete dashboard**

### Step 2: Import Simplified Dashboard
1. Go to http://10.55.12.99:3000/
2. Click **+ → Import**
3. Click **Upload JSON file**
4. Select: `d:\Future-work2\crossbridge\grafana\dashboard_version_simple.json`
5. **Important**: In the import screen, select your PostgreSQL datasource from the dropdown
6. Click **Import**

### Step 3: Verify Datasource Connection
If still blank after importing:

1. Open any panel in edit mode (click panel title → Edit)
2. At the bottom, check if you see "No data" or a connection error
3. Click the **datasource dropdown** and manually select your PostgreSQL datasource
4. Click **Apply** and **Save dashboard**

## Alternative: Create Dashboard from Scratch

If import still doesn't work, let's verify your datasource first:

### Test Query in Grafana Explore
1. Go to http://10.55.12.99:3000/explore
2. Select your **PostgreSQL** datasource
3. Switch to **Code** mode
4. Paste this query:
```sql
SELECT 
    application_version,
    COUNT(*) as tests
FROM test_execution_event
WHERE application_version IS NOT NULL
GROUP BY application_version
ORDER BY application_version
```
5. Click **Run query**
6. **If this works**, your datasource is fine and we need to fix the dashboard
7. **If this fails**, your datasource connection needs to be fixed

## Next Steps Based on Results

### If Explore Query Works
- The simplified dashboard should work
- Each panel just needs the datasource selected during import

### If Explore Query Fails
We need to check:
1. Datasource connection settings
2. Database permissions
3. SSL/TLS requirements

## Quick Win: Single Panel Test

Create a test panel manually:
1. Create new dashboard: **+ → Dashboard**
2. Add panel
3. Select your PostgreSQL datasource
4. Query:
```sql
SELECT COUNT(*) as "Total Events"
FROM test_execution_event
WHERE application_version IS NOT NULL
```
5. If this shows "110", your datasource works
6. Then import the simplified dashboard
