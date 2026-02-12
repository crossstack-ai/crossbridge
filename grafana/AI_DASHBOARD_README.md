# CrossBridge AI Intelligence Dashboard

Comprehensive Grafana dashboard for monitoring AI-powered test intelligence with real-time metrics, cost tracking, regression detection, and flaky test identification.

## 📊 Dashboard Overview

**File:** `ai_intelligence_dashboard.json`  
**Datasources Required:** PostgreSQL + Prometheus (optional)  
**Refresh Rate:** 30 seconds  
**Default Time Range:** Last 7 days

---

## 🎯 Key Features

### Row 1: AI Analysis Overview (Real-Time Metrics)
- **AI Analysis Volume** - Clusters analyzed per minute
- **Average AI Confidence** - Gauge showing confidence score (0-1)
- **AI Cost** - Total USD spent in last 24h
- **AI Error Rate** - Percentage of failed AI analyses
- **Cache Hit Rate** - Efficiency of AI result caching

### Row 2: Confidence & Performance Trends
- **AI Confidence Score Trend** - 7-day trend by model
- **AI Response Time** - p95 and average response times

### Row 3: Token & Cost Monitoring
- **Token Usage by Model** - Stacked bar chart showing token consumption
- **Cost Breakdown by Model** - Donut chart of costs per AI model

### Row 4: Confidence Intelligence
- **Confidence Score Distribution** - Histogram (Very Low to Very High)
- **Framework Analysis Breakdown** - Tests analyzed per framework

### Row 5: Regression Detection 🔴
- **New Failures** - Regressions detected in last 24h
- **Flaky Tests** - Tests appearing intermittently (1-4 times in 5 runs)
- **Fixed Failures** - Issues resolved since last run

### Row 6: Trend Analysis
- **Failure Trend** - 7-day view of total, new, and flaky failures
- **Top Root Causes** - Most frequent issues across runs

### Row 7: AI Model Comparison
- **AI Model Performance** - Comparison of confidence, tokens, inference time
- **Domain Distribution** - Product vs Infrastructure vs Test failures

### Row 8: Heatmap Analysis
- **AI Analysis Volume by Hour** - 7-day heatmap showing usage patterns

---

## 🏗️ Architecture

### Data Sources

#### 1. **Prometheus** (Real-Time Operational Metrics)
```
Endpoint: http://crossbridge-sidecar:8765/ai-metrics/prometheus
Scrape Interval: 15s
```

**Metrics Exposed:**
- `crossbridge_ai_confidence_score` - Average confidence (gauge)
- `crossbridge_ai_tokens_used_total` - Cumulative tokens (counter)
- `crossbridge_ai_cost_usd_total` - Cumulative cost (counter)
- `crossbridge_ai_response_time_ms` - Response time (gauge)
- `crossbridge_ai_errors_total` - Error count (counter)
- `crossbridge_ai_cache_hits_total` - Cache hits (counter)
- `crossbridge_ai_clusters_analyzed_total` - Clusters processed (counter)

#### 2. **PostgreSQL** (Intelligence Store - Historical Analysis)
```
Host: postgres:5432
Database: crossbridge_intelligence
```

**Core Tables:**
- `test_runs` - Test execution metadata
- `failure_clusters` - Clustered failures with AI analysis
- `ai_metrics` - Detailed AI performance data

---

## 📦 Installation

### Step 1: Setup Prometheus (Optional but Recommended)

**prometheus.yml:**
```yaml
scrape_configs:
  - job_name: 'crossbridge-ai'
    static_configs:
      - targets: ['crossbridge-sidecar:8765']
    metrics_path: '/ai-metrics/prometheus'
    scrape_interval: 15s
    scrape_timeout: 10s
```

### Step 2: Setup PostgreSQL Intelligence Store

**Create Database:**
```sql
CREATE DATABASE crossbridge_intelligence;
```

**Run Migrations:**
```sql
-- Core tables (from recommended schema)
CREATE TABLE test_runs (
    run_id TEXT PRIMARY KEY,
    framework TEXT,
    total_tests INT,
    failed_tests INT,
    duration_seconds INT,
    ai_enabled BOOLEAN,
    ai_provider TEXT,
    ai_model TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE failure_clusters (
    id SERIAL PRIMARY KEY,
    run_id TEXT REFERENCES test_runs(run_id),
    cluster_hash TEXT,
    root_cause TEXT,
    severity TEXT,
    domain TEXT,
    occurrences INT,
    confidence FLOAT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    is_regression BOOLEAN,
    is_flaky BOOLEAN
);

CREATE TABLE ai_metrics (
    run_id TEXT REFERENCES test_runs(run_id),
    ai_model TEXT,
    tokens_used INT,
    inference_time_ms INT,
    cluster_count INT,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT now()
);

-- Indexes for performance
CREATE INDEX idx_failure_clusters_run_id ON failure_clusters(run_id);
CREATE INDEX idx_failure_clusters_regression ON failure_clusters(is_regression);
CREATE INDEX idx_failure_clusters_flaky ON failure_clusters(is_flaky);
CREATE INDEX idx_failure_clusters_created_at ON failure_clusters(last_seen);
CREATE INDEX idx_ai_metrics_created_at ON ai_metrics(created_at);
```

### Step 3: Import Dashboard to Grafana

#### Option A: Grafana UI
1. Navigate to **Dashboards → Import**
2. Upload `ai_intelligence_dashboard.json`
3. Select datasources:
   - **PostgreSQL**: CrossBridge Intelligence Store
   - **Prometheus**: CrossBridge Metrics (optional)
4. Click **Import**

#### Option B: Grafana API
```bash
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_GRAFANA_API_KEY" \
  -d @ai_intelligence_dashboard.json
```

#### Option C: Grafana Provisioning (GitOps)
```yaml
# /etc/grafana/provisioning/dashboards/crossbridge.yaml
apiVersion: 1
providers:
  - name: 'CrossBridge'
    folder: 'Test Intelligence'
    type: file
    options:
      path: /var/lib/grafana/dashboards/crossbridge
```

Copy `ai_intelligence_dashboard.json` to `/var/lib/grafana/dashboards/crossbridge/`

---

## 🔧 Configuration

### Dashboard Variables

The dashboard includes three template variables for filtering:

1. **Framework** - Filter by test framework (Robot, Pytest, Selenium, etc.)
2. **AI Model** - Filter by AI model (GPT-4, Claude, Local LLM, etc.)
3. **Severity** - Filter by failure severity (CRITICAL, HIGH, MEDIUM, LOW)

### Customization

#### Adjust Time Range
```json
"time": {
  "from": "now-30d",  // Change to 30 days
  "to": "now"
}
```

#### Adjust Refresh Rate
```json
"refresh": "1m"  // Change to 1 minute
```

#### Adjust Cost Thresholds
```json
"thresholds": {
  "steps": [
    { "value": 0, "color": "green" },
    { "value": 5, "color": "yellow" },   // Adjust warning threshold
    { "value": 20, "color": "red" }      // Adjust critical threshold
  ]
}
```

---

## 🚀 Integration with CrossBridge

### Enable Dashboard Metrics Recording

**In your test execution:**
```python
from services.ai_dashboard_service import get_dashboard_service

# After AI analysis
dashboard = get_dashboard_service()
dashboard.record_analysis(
    run_id="test-run-12345",
    framework="robot",
    model="gpt-4",
    provider="openai",
    confidence_scores=[0.85, 0.92, 0.78],
    tokens_used=1500,
    cost=0.045,
    response_time_ms=850,
    clusters_analyzed=5,
    cache_hit=True
)
```

### Expose Prometheus Metrics

**Sidecar API automatically exposes:**
```
GET http://crossbridge-sidecar:8765/ai-metrics/prometheus
```

### Query Dashboard Summary

**Via REST API:**
```bash
curl http://crossbridge-sidecar:8765/ai-metrics/summary?time_window=7d
```

---

## 📈 Dashboard Panels Reference

| Panel ID | Title | Type | Datasource | Purpose |
|----------|-------|------|------------|---------|
| 1 | AI Analysis Overview | Stat | Prometheus | Real-time cluster analysis rate |
| 2 | Average AI Confidence | Gauge | Prometheus | Current confidence level |
| 3 | AI Cost (24h) | Stat | Prometheus | Daily cost tracking |
| 4 | AI Error Rate | Stat | Prometheus | Error percentage monitoring |
| 5 | Cache Hit Rate | Gauge | Prometheus | Caching efficiency |
| 6 | Confidence Trend | Timeseries | Prometheus | 7-day confidence by model |
| 7 | Response Time (p95) | Timeseries | Prometheus | Performance monitoring |
| 8 | Token Usage | Timeseries | Prometheus | Token consumption by model |
| 9 | Cost Breakdown | Pie Chart | Prometheus | Cost distribution |
| 10 | Confidence Distribution | Bar Chart | PostgreSQL | Score histogram |
| 11 | Framework Breakdown | Bar Chart | Prometheus | Usage by framework |
| 12 | New Failures | Table | PostgreSQL | Regression detection |
| 13 | Flaky Tests | Table | PostgreSQL | Intermittent failures |
| 14 | Fixed Failures | Table | PostgreSQL | Resolved issues |
| 15 | Failure Trend | Timeseries | PostgreSQL | 7-day trend analysis |
| 16 | Top Root Causes | Table | PostgreSQL | Cross-run analysis |
| 17 | Model Performance | Table | PostgreSQL | AI model comparison |
| 18 | Domain Distribution | Pie Chart | PostgreSQL | Product/Infra/Test split |
| 19 | Analysis Heatmap | Heatmap | PostgreSQL | Hourly usage pattern |

---

## 🧠 Intelligence Features

### Regression Detection Logic
```python
def detect_regression(cluster_hash, current_run_id):
    previous = fetch_previous_runs(limit=5)
    if cluster_hash not in previous:
        return True  # Mark as regression
    return False
```

### Flaky Test Detection Logic
```python
def is_flaky(cluster_hash):
    appearances = count_appearances(cluster_hash, last_n=5)
    return 1 < appearances < 5  # Appears but not every run
```

### Confidence Score Ranges
- **Very Low (0-0.4)** 🔴 - Manual review required
- **Low (0.4-0.6)** 🟠 - AI uncertain, validate results
- **Medium (0.6-0.8)** 🟡 - Good confidence, trust results
- **High (0.8-0.9)** 🟢 - High confidence, actionable
- **Very High (0.9-1.0)** 💚 - Very high confidence, fully automated

---

## 🔍 Alerting Rules (Recommended)

### Grafana Alerts

**High AI Error Rate:**
```yaml
alert: HighAIErrorRate
expr: sum(rate(crossbridge_ai_errors_total[5m])) / sum(rate(crossbridge_ai_clusters_analyzed_total[5m])) > 0.1
for: 5m
annotations:
  summary: "AI error rate above 10%"
```

**Low Confidence Trend:**
```yaml
alert: LowConfidenceTrend
expr: avg(crossbridge_ai_confidence_score) < 0.7
for: 10m
annotations:
  summary: "Average AI confidence below 70%"
```

**High AI Cost:**
```yaml
alert: HighAICost
expr: sum(increase(crossbridge_ai_cost_usd_total[1h])) > 5
annotations:
  summary: "AI costs exceed $5/hour"
```

---

## 🎯 Use Cases

### 1. Cost Monitoring
- Track daily/monthly AI costs
- Compare cost efficiency across models
- Optimize token usage

### 2. Quality Assurance
- Monitor AI confidence trends
- Identify low-confidence analyses
- Validate AI accuracy

### 3. Performance Optimization
- Track response time degradation
- Monitor cache effectiveness
- Optimize inference speed

### 4. Regression Management
- Detect new failures immediately
- Track regression resolution
- Prioritize critical regressions

### 5. Flaky Test Identification
- Identify intermittent failures
- Quantify flakiness impact
- Prioritize flaky test fixes

### 6. Root Cause Analysis
- Cross-run pattern identification
- Domain-based failure classification
- Historical trend analysis

---

## 📚 Related Documentation

- [AI Dashboard Metrics Implementation](../../core/log_analysis/ai_dashboard_metrics.py)
- [Dashboard Service API](../../services/ai_dashboard_service.py)
- [Sidecar API Endpoints](../../services/sidecar_api.py)
- [Execution Intelligence Dashboard](./execution_intelligence_dashboard.json)
- [Flaky Test Dashboard](./flaky_dashboard_ready_template.json)

---

## 🤝 Contributing

To enhance the dashboard:

1. Add new panels using Grafana Dashboard JSON schema
2. Add Prometheus metrics via `export_prometheus_metrics()`
3. Add PostgreSQL queries using Intelligence Store tables
4. Update this README with new features
5. Submit PR with dashboard JSON + documentation

---

## 📝 License

Apache License 2.0 - See [LICENSE](../../LICENSE)

---

## 🆘 Troubleshooting

### Dashboard shows "No data"
- Check Prometheus scraping: `curl http://crossbridge-sidecar:8765/ai-metrics/prometheus`
- Check PostgreSQL connection in Grafana datasources
- Verify test runs are recording metrics: `SELECT COUNT(*) FROM test_runs;`

### Metrics not updating
- Check sidecar API is running: `curl http://crossbridge-sidecar:8765/health`
- Verify dashboard service is enabled in code
- Check Prometheus scrape interval (should be 15s)

### High cardinality warnings
- Limit model/framework labels
- Aggregate before storing
- Use recording rules in Prometheus

---

**Built with ❤️ by CrossStack AI**
