# Grafana Dashboard Setup Guide

## Issue: No Data Appearing in Grafana

If you're seeing no data in the Grafana dashboard, follow these troubleshooting steps:

## 1. Verify Database Connection

Test the database connection from your terminal:

```bash
python -c "import psycopg2; conn = psycopg2.connect(host='10.60.67.247', port=5432, database='cbridge-unit-test-db', user='postgres', password='admin'); print('✅ Database connection successful'); conn.close()"
```

## 2. Configure Grafana Datasource

1. Go to Grafana: http://10.55.12.99:3000
2. Navigate to **Configuration** → **Data Sources**
3. Click **Add data source**
4. Select **PostgreSQL**
5. Configure:
   - **Name**: `CrossBridge PostgreSQL`
   - **Host**: `10.60.67.247:5432`
   - **Database**: `cbridge-unit-test-db`
   - **User**: `postgres`
   - **Password**: `admin`
   - **SSL Mode**: `disable`
   - **Version**: `12+` (or latest)
6. Click **Save & Test** - should show green checkmark

## 3. Import Dashboard

### Option A: Simple Dashboard (Recommended for Testing)

Import: `grafana/performance_profiling_dashboard_simple.json`

This dashboard uses:
- `datasource: null` (uses default datasource)
- Grafana time macros (`$__timeFrom()`, `$__timeTo()`)
- Simpler panel configuration

### Option B: Full Dashboard

Import: `grafana/performance_profiling_dashboard.json`

This is the comprehensive dashboard with 12 panels.

## 4. After Import

1. **Select the datasource**: In the import screen, select the PostgreSQL datasource you created
2. **Set time range**: Use "Last 24 hours" from the time picker
3. **Refresh**: Click the refresh button or wait for auto-refresh (30s)

## 5. Verify Data

Run this verification script:

```bash
python verify_grafana_queries.py
```

Expected output:
- Tests in last 24h: ~180+
- Total tests: 764+
- Frameworks: pytest, cypress, playwright, robot, etc.

## 6. Common Issues

### Issue: "Error reading PostgreSQL"
**Solution**: Check datasource configuration, ensure database name is correct

### Issue: "No data points"
**Solution**: 
- Check time range matches data range (2025-12-26 to 2026-01-25)
- Verify timezone settings (database uses Asia/Calcutta)
- Use Grafana's Query Inspector (click panel title → Inspect → Query) to see actual SQL

### Issue: "Permission denied"
**Solution**: Grant permissions:
```sql
GRANT USAGE ON SCHEMA crossbridge TO postgres;
GRANT SELECT ON ALL TABLES IN SCHEMA crossbridge TO postgres;
```

### Issue: "Table does not exist"
**Solution**: Verify schema name in queries:
```bash
python -c "import psycopg2; conn = psycopg2.connect(host='10.60.67.247', port=5432, database='cbridge-unit-test-db', user='postgres', password='admin'); cursor = conn.cursor(); cursor.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'crossbridge'\"); print('Tables:', [row[0] for row in cursor.fetchall()]); conn.close()"
```

## 7. Manual Query Test

Test a simple query in Grafana's Explore view:

1. Go to **Explore** (compass icon)
2. Select your PostgreSQL datasource
3. Enter query:
```sql
SELECT COUNT(*) as value FROM crossbridge.tests;
```
4. Click **Run Query**
5. Should return: 764 (or similar number)

## 8. Dashboard Panels

The dashboard includes:

1. **Total Tests** - Count of unique tests
2. **Avg Test Duration** - Average execution time in ms
3. **Tests by Framework** - Pie chart breakdown
4. **Test Duration Trend** - Time series by framework
5. **Recent Test Executions** - Live table of latest tests

## 9. Files

- `performance_profiling_dashboard.json` - Full dashboard (12 panels)
- `performance_profiling_dashboard_simple.json` - Simplified dashboard (5 panels)
- `populate_profiling_sample_data.py` - Generate sample data
- `verify_grafana_queries.py` - Test all queries
- `debug_grafana_queries.py` - Debug connection issues

## 10. Sample Data

If you need to regenerate sample data:

```bash
python populate_profiling_sample_data.py
```

This will create:
- 310 tests across 8 frameworks
- 30 days of historical data
- Step-level and HTTP call metrics

## Support

If issues persist:
1. Check Grafana logs: `/var/log/grafana/`
2. Check PostgreSQL logs
3. Use Query Inspector in Grafana to see exact SQL being executed
4. Verify user permissions on crossbridge schema
