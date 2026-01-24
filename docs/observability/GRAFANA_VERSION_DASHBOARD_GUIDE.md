# 🎯 Version-Aware Coverage in Grafana - Quick Start Guide

## ✅ Data Generated Successfully!

You now have **90 test events** with version tracking in your database:

| Version | Product    | Environment | Events |
|---------|------------|-------------|--------|
| 1.0.0   | MyWebApp   | production  | 20     |
| 2.0.0   | MyWebApp   | staging     | 25     |
| 2.1.0   | MyWebApp   | dev         | 30     |
| 3.2.0   | PaymentAPI | production  | 15     |

---

## 📊 View in Grafana (3 Steps)

### Step 1: Open Grafana
```
http://10.55.12.99:3000/
```
**Login:** admin / admin

### Step 2: Import Dashboard

1. Click **"+" (Create)** in left sidebar
2. Select **"Import dashboard"**
3. Click **"Upload JSON file"**
4. Select: `d:\Future-work2\crossbridge\grafana\dashboard_version_aware.json`
5. In the next screen:
   - **Name:** CrossBridge Version-Aware Coverage
   - **Folder:** General (or create new)
   - **PostgreSQL datasource:** Select your existing datasource
6. Click **"Import"**

### Step 3: Explore the Dashboard

You'll see **10 panels** with version-based analytics:

1. **Test Execution Trends by Version** - Time series showing test runs
2. **Test Coverage by Version** - Bar chart comparing versions
3. **Version Comparison Table** - Detailed comparison with pass rates
4. **Quick Stats** - Latest version, products tracked, environments
5. **Coverage Distribution by Product** - Pie chart
6. **Pass Rate Comparison** - Gradient bars showing quality
7. **Coverage Gap Analysis** - Version-to-version deltas

---

## 🎛️ Using Dashboard Filters

At the top of the dashboard, you'll see 3 filters:

**Product Filter:**
- Select "MyWebApp" or "PaymentAPI"
- Or choose "All" to see both

**Version Filter:**
- Multi-select: Compare v1.0.0 vs v2.0.0 vs v2.1.0
- Or choose "All" for complete view

**Environment Filter:**
- production / staging / dev
- See how each environment performs

---

## 🔍 What You Can Analyze

### 1. Release Readiness
**Question:** "Is v2.1.0 ready for production?"
- Check pass rate in dev (70%) vs v1.0.0 in production (95%)
- See if test count increased (30 vs 20 - good!)
- Identify if coverage is adequate

### 2. Version Comparison
**Question:** "How does v2.0.0 compare to v1.0.0?"
- v1.0.0: 95% pass rate (stable, production)
- v2.0.0: 80% pass rate (staging, more tests but lower quality)
- Delta: 5 more tests, but 15% drop in pass rate

### 3. Multi-Product View
**Question:** "Which product has better coverage?"
- MyWebApp: 75 total events across 3 versions
- PaymentAPI: 15 events, 98% pass rate (excellent!)

### 4. Environment Health
**Filter by environment:**
- Production: High pass rates (95-98%)
- Staging: Lower (80%) - expected for pre-release
- Dev: Lowest (70%) - expected for active development

---

## 📈 Sample SQL Queries (Run in Grafana Explore)

### Query 1: Coverage by Version
```sql
SELECT 
    application_version,
    COUNT(DISTINCT test_id) as total_tests,
    ROUND(AVG(CASE WHEN status = 'passed' THEN 100.0 ELSE 0 END), 2) as pass_rate
FROM test_execution_event
WHERE event_type = 'test_end'
GROUP BY application_version
ORDER BY application_version;
```

### Query 2: Product Comparison
```sql
SELECT 
    product_name,
    application_version,
    environment,
    COUNT(*) as test_count
FROM test_execution_event
WHERE event_type = 'test_end'
GROUP BY product_name, application_version, environment
ORDER BY product_name, application_version;
```

### Query 3: Latest Version Stats
```sql
SELECT 
    application_version,
    COUNT(DISTINCT test_id) as tests,
    ROUND(AVG(CASE WHEN status = 'passed' THEN 100.0 ELSE 0 END), 2) as pass_rate,
    MAX(timestamp) as last_run
FROM test_execution_event
WHERE event_type = 'test_end'
GROUP BY application_version
ORDER BY last_run DESC
LIMIT 1;
```

---

## 🔄 Generate More Data

Want to add more test events?

```bash
cd d:\Future-work2\crossbridge
D:/python314/python.exe quick_version_data.py
```

This will add another batch of version-tracked test events.

---

## 🚀 Use in Your Real Tests

### Option 1: Environment Variables (Recommended)
```bash
# Set before running tests
export APP_VERSION="2.1.0"
export PRODUCT_NAME="MyWebApp"
export ENVIRONMENT="production"

# Run your tests
pytest tests/
```

### Option 2: CI/CD Integration
```yaml
# GitHub Actions
- name: Run Tests
  env:
    APP_VERSION: ${{ github.ref_name }}
    PRODUCT_NAME: MyWebApp
    ENVIRONMENT: staging
  run: pytest tests/
```

### Option 3: crossbridge.yaml
```yaml
crossbridge:
  application:
    product_name: MyWebApp
    version: 2.1.0
    environment: production
  hooks:
    enabled: true
```

---

## 🎯 Key Benefits You Now Have

✅ **Track coverage evolution** - See how coverage changes with each version  
✅ **Release confidence** - Know if v3.0 is ready for production  
✅ **Regression detection** - Catch coverage drops early  
✅ **Multi-product support** - Manage multiple products in one view  
✅ **Environment awareness** - Compare dev/staging/production  
✅ **Historical trends** - See coverage improvements over time  

---

## ❓ Troubleshooting

**Dashboard shows "No Data":**
1. Check time range (top-right) - set to "Last 7 days"
2. Verify data: Run `verify_version_data.py`
3. Check datasource: Ensure PostgreSQL is connected

**Queries failing:**
1. Verify datasource name in dashboard matches yours
2. Check database connection in Grafana settings

**Want to reset and regenerate:**
```sql
-- In psql or database client
DELETE FROM test_execution_event WHERE application_version IS NOT NULL;
```
Then run `quick_version_data.py` again.

---

## 📚 More Information

- **Full Documentation:** `VERSION_TRACKING_IMPLEMENTATION.md`
- **Hook Integration:** `HOOK_AUTO_INTEGRATION_COMPLETE.md`
- **Post-Migration Intelligence:** `docs/POST_MIGRATION_INTELLIGENCE.md`

---

**You're all set! Open Grafana and explore your version-aware coverage dashboard! 🚀**
