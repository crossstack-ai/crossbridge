# Version-Aware Coverage Tracking - Implementation Complete ✅

## 🎯 Overview

CrossBridge now supports **version-aware coverage tracking**, enabling you to analyze test coverage across different product versions, environments, and releases.

## 🚀 What's New

### Key Capabilities

✅ **Track coverage by product version** (v1.0, v2.0, v3.0)  
✅ **Multi-product support** (MyWebApp, PaymentAPI, OrderService)  
✅ **Environment segmentation** (dev, staging, production)  
✅ **Version-to-version comparison** (coverage gaps, regressions)  
✅ **Release readiness metrics** (is v3.0 ready for production?)  
✅ **Trend analysis** (how coverage evolves across versions)

---

## 📊 Use Cases

### 1. Release Readiness Assessment
```
Question: "Is v3.0 ready for production?"
Answer: Check v3.0 coverage in staging vs. v2.5 in production
```

### 2. Coverage Regression Detection
```
Alert: "v2.1.0 coverage dropped to 62% (was 85% in v2.0.0)"
Action: Investigate which features lost test coverage
```

### 3. Multi-Product Tracking
```
Track:
- MyWebApp v2.0 → 85% coverage
- PaymentAPI v3.2 → 98% coverage
- OrderService v1.5 → 72% coverage
```

### 4. Environment-Specific Analysis
```
Compare:
- Production (v2.0): 95% pass rate, 150 tests
- Staging (v2.1): 78% pass rate, 180 tests
- Dev (v3.0): 65% pass rate, 220 tests
```

---

## 🏗️ Architecture

### Event Schema Enhancement

Every CrossBridge event now includes version tracking:

```python
@dataclass
class CrossBridgeEvent:
    # Existing fields
    event_type: str
    framework: str
    test_id: str
    timestamp: datetime
    
    # NEW: Version tracking fields
    application_version: Optional[str] = None  # "2.1.0", "v3.0.0-beta"
    product_name: Optional[str] = None         # "MyWebApp", "PaymentAPI"
    environment: Optional[str] = None          # "dev", "staging", "production"
```

### Database Schema

```sql
-- New columns added to test_execution_event table
ALTER TABLE test_execution_event
ADD COLUMN application_version VARCHAR(50),
ADD COLUMN product_name VARCHAR(100),
ADD COLUMN environment VARCHAR(50);

-- Performance indexes
CREATE INDEX idx_app_version ON test_execution_event(application_version);
CREATE INDEX idx_product_name ON test_execution_event(product_name);
CREATE INDEX idx_environment ON test_execution_event(environment);
CREATE INDEX idx_version_product ON test_execution_event(application_version, product_name);
```

---

## 🔧 Configuration

### Method 1: Environment Variables (Recommended for CI/CD)

```bash
# Set before running tests
export APP_VERSION="2.1.0"
export PRODUCT_NAME="MyWebApp"
export ENVIRONMENT="production"

# Run tests - version info automatically captured
pytest tests/
robot tests/
npx playwright test
```

### Method 2: crossbridge.yaml Configuration

```yaml
crossbridge:
  # Application version tracking
  application:
    product_name: ${PRODUCT_NAME:-MyWebApp}
    version: ${APP_VERSION:-1.0.0}
    environment: ${ENVIRONMENT:-dev}
  
  hooks:
    enabled: true
```

### Method 3: CI/CD Integration

**GitHub Actions:**
```yaml
- name: Run Tests with Version Tracking
  env:
    APP_VERSION: ${{ github.event.release.tag_name }}
    PRODUCT_NAME: MyWebApp
    ENVIRONMENT: staging
  run: pytest tests/
```

**Jenkins:**
```groovy
withEnv([
    "APP_VERSION=${BUILD_TAG}",
    "PRODUCT_NAME=MyWebApp",
    "ENVIRONMENT=production"
]) {
    sh 'pytest tests/'
}
```

**GitLab CI:**
```yaml
test:
  script:
    - export APP_VERSION=$CI_COMMIT_TAG
    - export PRODUCT_NAME=MyWebApp
    - export ENVIRONMENT=$CI_ENVIRONMENT_NAME
    - pytest tests/
```

---

## 📊 Grafana Dashboard

### New Dashboard: `dashboard_version_aware.json`

**Import Steps:**
1. Open Grafana: http://10.55.12.99:3000/
2. Go to Dashboards → Import
3. Upload `grafana/dashboard_version_aware.json`
4. Select PostgreSQL datasource
5. Click Import

### Dashboard Panels

#### 1. **Test Execution Trends by Version**
- Time series graph showing test runs per version
- Compare multiple versions side-by-side
- Identify which versions are actively tested

#### 2. **Test Coverage by Version**
- Bar chart: Total tests per version
- Pass/fail breakdown
- Pass rate percentage

#### 3. **Version Comparison Table**
- Comprehensive comparison matrix
- Columns: Product, Version, Environment, Total Tests, Pass Rate, Last Execution
- Color-coded pass rates (red < 70%, yellow < 90%, green ≥ 90%)

#### 4. **Quick Stats**
- Latest Version tested
- Active Products count
- Environments tracked
- Total versions monitored

#### 5. **Coverage Distribution by Product**
- Pie chart showing test distribution across products
- Useful for multi-product organizations

#### 6. **Pass Rate Comparison**
- Bar chart with gradient gauge
- Visual comparison of quality across versions
- Quickly spot problematic versions

#### 7. **Coverage Gap Analysis**
- Version-to-version delta tracking
- Shows: Test Δ, Pass Rate Δ, Trend (✅ Improved / ⚠️ Degraded / ➡️ Stable)
- SQL uses window functions (LAG) for comparison

### Dashboard Filters

**Product Filter:**
- Select specific product or view all
- Dynamic query from database

**Version Filter:**
- Multi-select versions to compare
- Shows only versions with data

**Environment Filter:**
- Filter by dev/staging/production
- Helps isolate environment-specific issues

---

## 🧪 Testing & Validation

### 1. Run Database Migration (if needed)

```bash
cd d:\Future-work2\crossbridge
python scripts/migrate_add_version_tracking.py
```

**Expected Output:**
```
✓ Connected to database successfully
✓ Table 'test_execution_event' exists
✓ Column 'application_version' already exists
✓ Column 'product_name' already exists
✓ Column 'environment' already exists
✓ All indexes created
✅ Migration completed successfully!
```

### 2. Generate Sample Data

```bash
python scripts/generate_version_sample_data.py
```

**Expected Output:**
```
📦 Generating data for: MyWebApp v1.0.0 (production)
   Pass Rate: 95% | Tests: 50
   ✓ Generated 700 events

📦 Generating data for: MyWebApp v2.0.0 (staging)
   Pass Rate: 78% | Tests: 80
   ✓ Generated 1120 events

...

✅ Successfully generated 3500+ events across 6 versions
```

### 3. Verify Data in Database

```sql
-- Check version distribution
SELECT 
    application_version,
    product_name,
    environment,
    COUNT(*) as event_count
FROM test_execution_event
WHERE application_version IS NOT NULL
GROUP BY application_version, product_name, environment
ORDER BY application_version, product_name;
```

**Expected Result:**
```
 application_version | product_name | environment | event_count 
---------------------+--------------+-------------+-------------
 1.0.0               | MyWebApp     | production  |         700
 1.5.0               | MyWebApp     | production  |         840
 2.0.0               | MyWebApp     | staging     |        1120
 2.1.0               | MyWebApp     | dev         |        1400
 3.2.0               | PaymentAPI   | production  |         420
 3.3.0               | PaymentAPI   | staging     |         560
```

### 4. View in Grafana

1. Open: http://10.55.12.99:3000/
2. Navigate to **CrossBridge Coverage Intelligence (Version-Aware)** dashboard
3. Use filters to explore:
   - Select "MyWebApp" product
   - Compare v1.0.0 vs v2.0.0
   - Filter by "staging" environment

---

## 📈 Query Examples

### Coverage by Version

```sql
SELECT
    application_version AS version,
    COUNT(DISTINCT test_id) AS total_tests,
    ROUND(AVG(CASE WHEN status = 'passed' THEN 100.0 ELSE 0 END), 2) AS pass_rate,
    ROUND(AVG(duration_ms) / 1000.0, 2) AS avg_duration_seconds
FROM test_execution_event
WHERE 
    event_type = 'test_end'
    AND application_version IS NOT NULL
GROUP BY application_version
ORDER BY version DESC;
```

### Version-to-Version Comparison

```sql
WITH version_stats AS (
    SELECT
        application_version,
        COUNT(DISTINCT test_id) AS test_count,
        ROUND(AVG(CASE WHEN status = 'passed' THEN 100.0 ELSE 0 END), 2) AS pass_rate,
        LAG(COUNT(DISTINCT test_id)) OVER (ORDER BY application_version) AS prev_test_count
    FROM test_execution_event
    WHERE event_type = 'test_end' AND application_version IS NOT NULL
    GROUP BY application_version
)
SELECT
    application_version,
    test_count,
    pass_rate,
    (test_count - COALESCE(prev_test_count, test_count)) AS test_delta,
    CASE
        WHEN test_count > COALESCE(prev_test_count, test_count) THEN '✅ More tests'
        WHEN test_count < COALESCE(prev_test_count, test_count) THEN '⚠️ Fewer tests'
        ELSE '➡️ Same'
    END AS trend
FROM version_stats
ORDER BY application_version DESC;
```

### Multi-Product Overview

```sql
SELECT
    product_name,
    application_version,
    environment,
    COUNT(DISTINCT test_id) AS total_tests,
    ROUND(AVG(CASE WHEN status = 'passed' THEN 100.0 ELSE 0 END), 2) AS pass_rate,
    MAX(timestamp) AS last_run
FROM test_execution_event
WHERE event_type = 'test_end'
GROUP BY product_name, application_version, environment
ORDER BY product_name, application_version DESC;
```

---

## 🎯 Best Practices

### 1. Version Naming Convention

Use semantic versioning:
```bash
APP_VERSION="2.1.3"        # ✅ Good
APP_VERSION="v2.1.3"       # ✅ Good
APP_VERSION="2.1.3-beta"   # ✅ Good
APP_VERSION="release-123"  # ⚠️ Less useful for comparison
```

### 2. CI/CD Integration

**Always set version info in CI/CD:**
```yaml
# GitHub Actions
env:
  APP_VERSION: ${{ github.ref_name }}  # Tag or branch name
  PRODUCT_NAME: MyWebApp
  ENVIRONMENT: ${{ github.event.inputs.environment }}
```

### 3. Environment Consistency

Use standard environment names:
```
dev → Development
staging → Staging/QA
production → Production
```

### 4. Product Names

For mono-repos with multiple products:
```bash
# Frontend
export PRODUCT_NAME="MyWebApp-Frontend"

# Backend API
export PRODUCT_NAME="MyWebApp-API"

# Admin Portal
export PRODUCT_NAME="MyWebApp-Admin"
```

---

## 🔮 Advanced Use Cases

### 1. Release Gate Checks

```sql
-- Check if v3.0 is ready for production
SELECT
    CASE 
        WHEN AVG(CASE WHEN status = 'passed' THEN 100.0 ELSE 0 END) >= 95 THEN '✅ Ready'
        WHEN AVG(CASE WHEN status = 'passed' THEN 100.0 ELSE 0 END) >= 90 THEN '⚠️ Review needed'
        ELSE '❌ Not ready'
    END AS release_status,
    ROUND(AVG(CASE WHEN status = 'passed' THEN 100.0 ELSE 0 END), 2) AS pass_rate,
    COUNT(DISTINCT test_id) AS total_tests
FROM test_execution_event
WHERE 
    event_type = 'test_end'
    AND application_version = '3.0.0'
    AND environment = 'staging'
    AND timestamp > NOW() - INTERVAL '7 days';
```

### 2. Flaky Test Detection by Version

```sql
-- Find tests that became flaky in v2.0
SELECT
    test_id,
    application_version,
    COUNT(*) as total_runs,
    SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
    ROUND(100.0 * SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 2) as stability
FROM test_execution_event
WHERE 
    event_type = 'test_end'
    AND application_version = '2.0.0'
GROUP BY test_id, application_version
HAVING 
    COUNT(*) >= 5
    AND stability < 100 
    AND stability > 0
ORDER BY stability;
```

### 3. Coverage Evolution Timeline

```sql
SELECT
    DATE(timestamp) as date,
    application_version,
    COUNT(DISTINCT test_id) as tests_run,
    ROUND(AVG(CASE WHEN status = 'passed' THEN 100.0 ELSE 0 END), 2) as daily_pass_rate
FROM test_execution_event
WHERE 
    event_type = 'test_end'
    AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp), application_version
ORDER BY date DESC, application_version;
```

---

## ✅ Implementation Checklist

- [x] Event schema updated with version fields
- [x] Database schema includes version columns
- [x] Indexes created for performance
- [x] Hook SDK captures version from environment
- [x] Config template includes application section
- [x] Migration script created
- [x] Sample data generator with versions
- [x] Enhanced Grafana dashboard (10 panels)
- [x] Dashboard filters (product, version, environment)
- [x] SQL queries for version analysis
- [x] Documentation with examples

---

## 🎉 Summary

You can now:

✅ **Track coverage by version** - "How is v2.1.0 doing?"  
✅ **Compare releases** - "Is v3.0 better than v2.5?"  
✅ **Detect regressions** - "Coverage dropped in v2.1!"  
✅ **Multi-product support** - Track 10+ products simultaneously  
✅ **Environment awareness** - Separate dev/staging/prod analytics  
✅ **Release gates** - "Is v3.0 ready for production?"  
✅ **Trend analysis** - Coverage evolution over time  

**Next Steps:**
1. Run migration: `python scripts/migrate_add_version_tracking.py`
2. Generate sample data: `python scripts/generate_version_sample_data.py`
3. Import dashboard: `grafana/dashboard_version_aware.json`
4. Set version in CI/CD: `export APP_VERSION=2.1.0`
5. Run tests and explore Grafana! 🚀
