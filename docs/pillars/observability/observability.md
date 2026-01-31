# Observability Stack

> **Zero-impact performance profiling, monitoring, and intelligence dashboards**

CrossBridge AI provides comprehensive observability for test automation without modifying test code.

---

## 🎯 Overview

### Key Components

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Test Execution    │         │   Sidecar        │         │   Observability     │
│   (No Changes!)     │         │   Runtime        │         │                     │
│                     │         │                  │         │                     │
│  • Existing tests   │────────▶│  • Sampler       │────────▶│  • Prometheus       │
│  • Any framework    │  events │  • Observer      │ metrics │  • Grafana          │
│  • Zero impact      │         │  • Profiler      │         │  • PostgreSQL       │
│                     │         │  • <5% CPU       │         │  • InfluxDB         │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

### Three Pillars

1. **Sidecar Runtime** - Zero-impact event capture
2. **Storage Backends** - PostgreSQL, InfluxDB, local files
3. **Visualization** - Grafana dashboards, metrics, alerts

---

## 🔍 Sidecar Runtime

### Zero-Impact Observability

**Key Features**:
- ⚡ **Fail-open**: Never blocks test execution (catches all exceptions)
- 📦 **Bounded queues**: Load shedding (5000-10000 events)
- 🎲 **Smart sampling**: Configurable rates (1-100%)
- 🔄 **Adaptive sampling**: Auto-boost 5x for 60s on anomalies
- 💾 **Resource budgets**: Auto-throttle at 5% CPU / 100MB RAM
- 🏥 **Health endpoints**: `/health`, `/ready`, `/metrics`
- 📊 **Prometheus metrics**: Production-grade observability

### Configuration

```yaml
# crossbridge.yml
runtime:
  sidecar:
    enabled: true
    
    sampling:
      events: 0.1          # 10% event sampling
      logs: 0.05           # 5% log sampling
      profiling: 0.01      # 1% profiling sampling
      adaptive: enabled    # Auto-boost on anomalies
    
    resources:
      max_queue_size: 10000
      max_cpu_percent: 5.0
      max_memory_mb: 100
    
    health:
      endpoint: "/health"
      port: 8080
```

### Usage

```python
from core.sidecar import SidecarRuntime

with SidecarRuntime() as sidecar:
    # Observe events
    sidecar.observe('test_event', {
        'test_id': 'test_123',
        'status': 'passed',
        'duration': 2.34
    })
    
    # Get health status
    health = sidecar.get_health()
    # {'status': 'healthy', 'components': {...}}
    
    # Export Prometheus metrics
    metrics = sidecar.export_metrics()
```

**Documentation**: [Sidecar Runtime Guide](sidecar/SIDECAR_RUNTIME.md)

---

## 📊 Performance Profiling

### What Gets Profiled

**Test Execution**:
- Test duration (setup, execution, teardown)
- Pass/fail/skip counts
- Error types and frequencies

**HTTP Requests**:
- API call latency
- Status codes distribution
- Request/response sizes
- Retry patterns

**WebDriver Commands**:
- Click, navigate, wait operations
- Element locator performance
- Screenshot timing
- Browser operations

**Infrastructure**:
- Database query times
- Network latency
- Memory usage
- CPU utilization

### Framework Support

**All 13 frameworks supported**:
- ✅ Python: pytest, Robot, Selenium, Behave
- ✅ Java: TestNG, JUnit, RestAssured, Selenium, Cucumber
- ✅ .NET: NUnit, SpecFlow, Selenium
- ✅ JavaScript: Cypress, Playwright

### Configuration

```yaml
# crossbridge.yml
crossbridge:
  profiling:
    enabled: true
    
    storage:
      backend: postgres  # or influxdb, local
      
      postgres:
        host: localhost
        port: 5432
        database: crossbridge
        table: profiling_events
      
      influxdb:
        url: http://localhost:8086
        org: crossbridge
        bucket: test_profiling
```

### Usage

**Automatic Profiling** (via hooks):

```python
# conftest.py (pytest)
pytest_plugins = ["crossbridge.pytest_plugin"]

# Tests run normally, profiling happens automatically
```

**Manual Profiling**:

```python
from core.profiling import Profiler

with Profiler() as profiler:
    # Your test code
    response = requests.get("https://api.example.com")
    assert response.status_code == 200

# Profiling data saved automatically
```

---

## 💾 Storage Backends

### PostgreSQL (Recommended for Production)

**Schema**:
```sql
CREATE TABLE profiling_events (
    id SERIAL PRIMARY KEY,
    test_name TEXT,
    framework TEXT,
    duration_ms NUMERIC,
    status TEXT,
    timestamp TIMESTAMPTZ,
    metadata JSONB
);

CREATE INDEX idx_profiling_timestamp ON profiling_events(timestamp);
CREATE INDEX idx_profiling_test ON profiling_events(test_name);
```

**Benefits**:
- ACID transactions
- Rich querying (SQL)
- Integration with existing systems
- Cost-effective storage

### InfluxDB (Time-Series Optimization)

**Schema**:
```
measurement: test_execution
tags: test_name, framework, status
fields: duration_ms, cpu_percent, memory_mb
time: timestamp
```

**Benefits**:
- Optimized for time-series
- Built-in downsampling
- Better for high-frequency data
- Native Grafana integration

### Local Files (Development)

**Format**: JSON or CSV

```json
{
  "test_name": "test_login",
  "duration_ms": 2340,
  "status": "passed",
  "timestamp": "2026-01-31T10:15:30Z"
}
```

**Benefits**:
- No database required
- Easy debugging
- Portable

---

## 📈 Grafana Dashboards

### Pre-built Dashboards

**1. Test Execution Overview**:
- Total tests executed (gauge)
- Pass/fail rate (timeseries)
- Duration trends (graph)
- Flaky test alerts

**2. Performance Profiling**:
- Slowest tests (table)
- Duration distribution (histogram)
- Performance regression (trend)
- Resource usage (gauge)

**3. HTTP Request Analysis**:
- Request count (counter)
- Latency P50/P95/P99 (graph)
- Error rate (gauge)
- Status code distribution (pie chart)

**4. WebDriver Commands**:
- Command frequency (bar chart)
- Operation timing (heatmap)
- Element locator performance

**5. Flaky Test Monitor**:
- Flaky test count (gauge)
- Severity distribution (donut)
- Top 10 flaky tests (table)
- Historical trend (timeseries)

**6. Failure Analysis**:
- Failure classification (pie chart)
- Product defect count (alert)
- Automation issue trend
- Environment failure correlation

### Setup

```bash
# Import dashboard
curl -X POST http://localhost:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d @grafana/crossbridge_dashboard.json

# Or manually:
# 1. Open Grafana (http://localhost:3000)
# 2. Import dashboard from grafana/crossbridge_dashboard.json
# 3. Select PostgreSQL datasource
# 4. Save
```

### Alert Rules

**Pre-configured alerts**:
- Flaky test count > 10
- Test failure rate > 20%
- Performance regression (P95 > 10% increase)
- Sidecar health degraded

---

## 🔧 Prometheus Metrics

### Exported Metrics

**Counters**:
- `crossbridge_tests_total{status="passed|failed|skipped"}`
- `crossbridge_http_requests_total{status_code="200|404|500"}`
- `crossbridge_failures_total{classification="product_defect|locator_issue"}`

**Gauges**:
- `crossbridge_flaky_tests_count`
- `crossbridge_sidecar_queue_size`
- `crossbridge_sidecar_cpu_percent`
- `crossbridge_sidecar_memory_mb`

**Histograms**:
- `crossbridge_test_duration_seconds`
- `crossbridge_http_request_latency_seconds`
- `crossbridge_webdriver_command_duration_seconds`

### Scrape Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'crossbridge'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

---

## 🚀 Quick Setup

### 1. Enable Profiling

```bash
# Configure environment
cp .env.example .env

# Edit .env
nano .env
# DATABASE_URL=postgresql://user:pass@localhost:5432/crossbridge
# CROSSBRIDGE_PROFILING=true
```

### 2. Set Up Database

```bash
# PostgreSQL
psql -U postgres -d crossbridge -f scripts/setup_profiling_db.sql

# Or use helper script
python scripts/setup_profiling.py
```

### 3. Install Grafana (Optional)

```bash
# Docker
docker run -d -p 3000:3000 grafana/grafana

# Or native
# brew install grafana  # macOS
# apt install grafana   # Ubuntu
```

### 4. Run Tests

```bash
# Tests run normally, profiling happens automatically
pytest tests/

# View results in Grafana
open http://localhost:3000
```

---

## 📊 Performance Impact

### Sidecar Overhead

**Measured impact**:
- CPU: <1% average, <5% peak
- Memory: 50-80MB typical, <100MB max
- Latency: <1ms per event
- Throughput: 10,000+ events/sec

### Storage Requirements

**PostgreSQL**:
- ~500 bytes per event
- 1M events = ~500 MB
- Recommend partitioning after 10M events

**InfluxDB**:
- ~300 bytes per point (optimized)
- 1M points = ~300 MB
- Auto-downsampling after 30 days

---

## 🔒 Security & Privacy

### Data Protection

- **No sensitive data logged** by default
- **Configurable PII masking**
- **Encrypted storage** (database-level)
- **Access control** (role-based)

### Network Security

- **TLS for metrics endpoint**
- **API key authentication**
- **IP whitelisting** (optional)
- **Private network** recommended

---

## 📚 Learn More

- [Sidecar Runtime](sidecar/SIDECAR_RUNTIME.md) - Zero-impact observability
- [Performance Profiling](profiling/README.md) - Profiling system details
- [Test Infrastructure](TEST_INFRASTRUCTURE_AND_SIDECAR_HARDENING.md) - Hardening guide
- [Configuration](configuration/UNIFIED_CONFIGURATION_GUIDE.md) - All settings

---

**Ready to enable observability?** Follow the [quick setup guide](#-quick-setup) above.
