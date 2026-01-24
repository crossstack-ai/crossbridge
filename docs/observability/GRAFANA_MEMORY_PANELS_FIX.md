# Grafana Memory & Embedding Panels - Troubleshooting Guide

## Issue
Memory & embedding panels in Grafana showing blank/no data.

## Root Cause Analysis

### ✅ Data Exists in Database
```sql
SELECT COUNT(*) FROM memory_embeddings;
-- Result: 50 embeddings
```

### ✅ Queries Are Valid
All SQL queries in the dashboard work correctly:
- Panel 14: `SELECT COUNT(*) as total_embeddings FROM memory_embeddings` → Returns 50
- Panel 15: `SELECT entity_type, COUNT(*) as count FROM memory_embeddings GROUP BY entity_type` → Returns data
- Panel 16-18: All queries return valid results

### ❌ Likely Issue: Dashboard Not Re-Imported

**The dashboard JSON was updated AFTER you initially imported it into Grafana.** Grafana is showing the old version with only 13 panels.

## Solution: Re-Import Updated Dashboard

### Method 1: Update Existing Dashboard (Recommended)

1. **Open Grafana** → Navigate to your CrossBridge dashboard
2. **Click the gear icon** (⚙️) → Select "JSON Model"
3. **Replace entire JSON** with contents from: `grafana/dashboards/crossbridge_overview.json`
4. **Click "Save changes"**
5. **Refresh the dashboard**

### Method 2: Import as New Dashboard

1. **Delete old dashboard** (or rename it)
2. **Go to Dashboards** → **Import**
3. **Upload file**: `grafana/dashboards/crossbridge_overview.json`
4. **Select PostgreSQL datasource**
5. **Click "Import"**

### Method 3: Command Line (if Grafana API is accessible)

```bash
# Get Grafana credentials
GRAFANA_URL="http://localhost:3000"
GRAFANA_TOKEN="your-api-token"

# Update dashboard
curl -X POST "$GRAFANA_URL/api/dashboards/db" \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d @grafana/dashboards/crossbridge_overview.json
```

## Verify After Re-Import

### Expected Dashboard Structure

**Total Panels**: 18 (was 13 before)

**New Panels Added (14-18)**:
- Panel 14: Memory & Embeddings Overview (Stat)
- Panel 15: Embeddings by Entity Type (Pie Chart)
- Panel 16: Recent Embeddings Created (Table)
- Panel 17: Embedding Storage Trend (Time Series)
- Panel 18: Embedding Vector Dimensions Info (Stat)

### Test Queries in Grafana

After re-importing, test each panel by clicking "Edit" and "Refresh":

**Panel 14 - Should show**: `50` (total embeddings count)

**Panel 15 - Should show**: Pie chart with:
- test_case: 50 (100%)

**Panel 16 - Should show**: Table with 20 rows showing:
- entity_type: test_case
- test_name: test_pytest_login_0, test_junit_checkout_1, etc.
- model: text-embedding-3-small
- created_at: Recent timestamps

**Panel 17 - Should show**: Single data point (all embeddings created at same time)

**Panel 18 - Should show**:
- dimension: 1536
- model: text-embedding-3-small

## Additional Troubleshooting

### If Panels Still Show No Data

1. **Check Grafana Datasource Connection**
   ```
   Configuration → Data Sources → PostgreSQL
   Host: 10.60.67.247:5432
   Database: cbridge-unit-test-db
   User: postgres
   ```
   Click "Save & Test" - should show green checkmark

2. **Check Panel Query Tab**
   - Open panel edit mode
   - Go to "Query" tab
   - Click "Run queries" button
   - Should see data in preview

3. **Check Time Range**
   - Top right corner: Change to "Last 30 days" or "Last 90 days"
   - Memory embeddings were created today (2026-01-24)

4. **Regenerate Embeddings with Better Distribution**
   ```bash
   # This will create embeddings spread over 7 days
   python scripts/generate_embeddings_with_dates.py
   ```

### Verify Data Directly

```sql
-- Check data exists
SELECT COUNT(*) FROM memory_embeddings;

-- Check by entity type
SELECT entity_type, COUNT(*) FROM memory_embeddings GROUP BY entity_type;

-- Check date range
SELECT MIN(created_at), MAX(created_at) FROM memory_embeddings;

-- Sample data
SELECT 
    entity_type, 
    (metadata->>'test_name') as test_name,
    (metadata->>'model') as model,
    (metadata->>'dimension') as dimension,
    created_at
FROM memory_embeddings 
LIMIT 5;
```

## Generate Better Test Data (Optional)

The current embeddings all have the same timestamp. For better visualization in the trend chart, generate embeddings spread over time:

```bash
python scripts/generate_embeddings_with_dates.py
```

This will:
- Delete existing embeddings
- Create 50 new embeddings spread over the last 7 days
- Each day will have 7-8 embeddings
- Trend chart will show growth over time

## Summary

**Action Required**: **Re-import the updated dashboard JSON into Grafana**

The dashboard file was updated with 5 new memory/embedding panels (panels 14-18), but Grafana is still showing the old version. Simply updating the dashboard JSON in Grafana will immediately show all the new panels with data.

---

**Files Updated**:
- `grafana/dashboards/crossbridge_overview.json` - Now has 18 panels (was 13)
- Database has 50 embeddings ready to display
- All queries tested and working
