# CrossBridge AI

> **AI-Powered Test Automation Modernization & Transformation Platform**  
> Reduce test automation debt, unlock legacy test value, and accelerate delivery with AI-guided modernization.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Development Status](https://img.shields.io/badge/status-v0.2.1-green.svg)](https://github.com/crossstack-ai/crossbridge)
[![Production Ready](https://img.shields.io/badge/production-98.7%25-brightgreen.svg)](docs/releases/V0.2.0_RELEASE_NOTES.md)
[![CrossStack AI](https://img.shields.io/badge/by-CrossStack%20AI-blue)](https://crossstack.ai)

CrossBridge AI is an open-source platform by **CrossStack AI** that helps organizations and teams **modernize, analyze, and optimize test automation** in a framework-agnostic way.

**Latest Release:** v0.2.1 (February 6, 2026) - Intelligence Analysis Enhancements 🚀  
**Previous Release:** v0.2.0 (January 29, 2026) - [Release Notes](docs/releases/V0.2.0_RELEASE_NOTES.md)

---

## 🚀 Mission

Modern test automation ecosystems are fragmented, brittle, and expensive to maintain.  
CrossBridge AI enables teams to:

- 🧠 **Analyze existing automation across languages & frameworks**
- 🔄 **Upgrade legacy tests intelligently**
- 🚫 **Avoid costly rewrites**
- 🚀 **Accelerate QA velocity with AI-infused insights**

Whether you have Selenium, Cypress, Robot, or pytest suites — CrossBridge works **with or without migration changes**.

---

## 🧩 Core Capabilities

### 🔹 1. **Legacy Support Without Migration**
Work with existing tests as-is — zero code changes required.

**NO MIGRATION MODE** (Sidecar Observer):
```
┌─────────────────────┐         ┌──────────────────┐         
│   Your Tests        │         │   CrossBridge    │         
│   (NO CHANGES!)     │────────▶│   (Observer)     │────────▶ 📊 Intelligence
│                     │         │                  │         
│  • Selenium Java    │         │  • Auto-detect   │         • Coverage tracking
│  • Cypress          │         │  • Auto-register │         • Flaky detection  
│  • pytest           │         │  • AI analysis   │         • Risk scores
│  • Robot Framework  │         │  • Zero impact   │         • Test optimization
└─────────────────────┘         └──────────────────┘         
```

**Features:**
- Sidecar observer — no code changes
- Continuous intelligence dashboards
- Works with 12+ frameworks

✔ Selenium, pytest, Cypress, Robot, JUnit, TestNG, NUnit, BDD frameworks, and more

---

## 🎯 Quick Start: Unified CLI (NEW!)

**The easiest way to integrate CrossBridge: Zero code changes, unified command interface.**

### Installation (30 seconds)

```bash
# Install from PyPI (recommended)
pip install crossbridge

# Or from source
pip install -e .

# Or from Git
pip install git+https://github.com/crossstack-ai/crossbridge.git
```

📖 **[Complete Installation Guide](docs/INSTALLATION.md)** - Enterprise, offline, CI/CD, and more installation scenarios

### Usage

**Run tests with monitoring:**
```bash
# Instead of: robot tests/
crossbridge run robot tests/

# Instead of: pytest tests/
crossbridge run pytest tests/

# Instead of: jest tests/
crossbridge run jest tests/

# Instead of: mvn test
crossbridge run mvn test
```

**Parse and analyze logs:**
```bash
# Parse Robot Framework output
crossbridge log output.xml

# Parse with AI enhancement
crossbridge log output.xml --enable-ai

# Filter failed tests with intelligent clustering
crossbridge log output.xml --status FAIL
```

**✨ NEW: Intelligent Failure Clustering (v0.2.1+)**

CrossBridge now automatically deduplicates and clusters failures by root cause with domain classification:

```bash
# Example output with clustering:
Root Cause Analysis: 2 unique issues (deduplicated from 8 failures)
Deduplication saved 6 duplicate entries (75% reduction)
Domain breakdown: 1 Product, 1 Test

┌────────┬────────┬──────────────────────────────────┬───────┬──────────────────┐
│Severity│Domain  │Root Cause                        │Count  │Affected          │
├────────┼────────┼──────────────────────────────────┼───────┼──────────────────┤
│HIGH    │🐛 PROD │API Error: HTTP 500               │   5   │Get User, +2..    │
│MEDIUM  │🤖 TEST │ElementNotFound: Could not find.. │   3   │Click Button      │
└────────┴────────┴──────────────────────────────────┴───────┴──────────────────┘

[i] Suggested Fix for Top Issue:
Check API endpoint health and error logs. This is a product-level issue
requiring backend investigation.
```

**Benefits:**
- 🎯 **Reduces Noise** - Shows "8 failures → 2 root issues"
- ⚡ **Faster Triage** - Prioritized by severity (Critical/High/Medium/Low)
- 🔍 **Smart Routing** - Classifies failures by domain (Infra/Env/Test/Product)
- 🎫 **Fewer Misdirected Tickets** - Routes to correct teams (30-50% improvement)
- 🔍 **Pattern Detection** - Identifies common error patterns automatically
- 💡 **Smart Fixes** - Suggests solutions based on error type
- 📊 **Deduplication Stats** - Shows reduction percentage

No configuration needed - clustering works automatically on all log parsing operations!

**✨ NEW: Enterprise Analysis Features (v0.3.0+)**

CrossBridge now includes advanced features for enterprise-grade failure analysis:

```bash
# Regression detection - compare with previous run to identify new failures
crossbridge log output.xml --compare-with previous_run.json

# Triage mode - generate CI/CD dashboard-friendly output with top N critical issues
crossbridge log output.xml --triage --max-ai-clusters 5 -o triage.json

# AI summary only - focus on top failures requiring AI analysis
crossbridge log output.xml --enable-ai --ai-summary-only --max-ai-clusters 10
```

**Advanced Features:**

**1. 🔄 Regression Detection**
- Compare current run with previous results to identify:
  - **New failures** - Issues appearing for the first time
  - **Recurring failures** - Known issues that persist
  - **Resolved failures** - Previously failing tests now passing
- Automatic similarity matching (85% threshold)
- Tracks failure evolution across test runs

**2. 📊 Confidence Scoring**
- Multi-signal hybrid scoring algorithm:
  - **Cluster Signal (30%)** - Based on failure count and test coverage
  - **Domain Signal (30%)** - Confidence in domain classification
  - **Pattern Signal (20%)** - Error pattern consistency
  - **AI Signal (20%)** - AI analysis confidence (when enabled)
- Confidence score range: 0.0 - 1.0
- Helps prioritize investigation efforts

**3. 🧹 AI Output Sanitization**
- Removes AI disclaimers and apologies automatically
- Cleaner, more professional analysis output
- 90% more concise AI responses
- Blacklist-based phrase removal

**4. 📦 Structured JSON Output**
- Enterprise-grade structured format for CI/CD integration
- Machine-readable analysis results
- Domain-specific recommendations
- Test statistics and metadata
- Compatible with data warehouses and BI tools

**5. 🎯 Triage Mode**
- Condensed dashboard output for CI/CD pipelines
- Focus on top N critical issues (configurable)
- Reduced token size for faster dashboard rendering
- Includes recommended actions per issue
- Ideal for Jenkins, GitHub Actions, GitLab CI

**Example Outputs:**

```bash
# Regression analysis output
🔄 Performing regression analysis...
✅ Regression analysis complete:
   New failures: 3
   Recurring: 5
   Resolved: 2

# Confidence scoring output
📊 Computing confidence scores...
Cluster: API Timeout → Score: 0.88 (High confidence)
Cluster: Element Not Found → Score: 0.45 (Medium confidence)

# Triage mode output (JSON)
{
  "critical_issues": [
    {
      "cluster_id": "cluster_1",
      "root_cause": "HTTP 500 Internal Server Error",
      "severity": "critical",
      "confidence_score": 0.92,
      "failure_count": 12,
      "affected_tests": ["Test Login", "Test Checkout"],
      "recommended_actions": [
        "🚨 URGENT: Check backend service health immediately",
        "Review API endpoint logs for 500 errors"
      ],
      "is_new_regression": true
    }
  ],
  "summary": {
    "total_issues": 1,
    "new_regressions": 1,
    "critical_count": 1
  }
}
```

**Benefits:**
- 🚀 **Faster Root Cause Analysis** - Confidence scores guide investigation priority
- 📈 **Trend Tracking** - Regression detection tracks failure evolution
- 🤝 **Better Team Collaboration** - Structured output integrates with dashboards
- 💡 **Actionable Insights** - Domain-specific recommendations accelerate fixes
- 🎯 **CI/CD Optimized** - Triage mode reduces dashboard load times by 80%

No configuration needed - enterprise features work seamlessly with existing workflows!

**✨ NEW: AI Dashboard Metrics & Observability (v0.3.0+)**

CrossBridge now provides comprehensive dashboard metrics for AI-enhanced analysis:

```bash
# Available dashboard endpoints via sidecar API (http://localhost:8765)

# Get AI metrics summary (last 24 hours)
curl http://localhost:8765/ai-metrics/summary?hours=24

# Get Prometheus-compatible metrics for scraping
curl http://localhost:8765/ai-metrics/prometheus

# Get Grafana-optimized dashboard data
curl http://localhost:8765/ai-metrics/grafana?hours=168

# Get time-series trend data
curl http://localhost:8765/ai-metrics/trends?granularity=day&hours=168

# Get framework-specific metrics
curl http://localhost:8765/ai-metrics/framework/robot?hours=168
```

**Dashboard Features:**

**1. 📊 AI Performance Metrics**
- **Confidence Score Trends** - Track AI analysis confidence over time
- **Distribution Analysis** - Confidence score buckets (Very Low → Very High)
- **Response Time Tracking** - Monitor AI API latency and performance
- **Error Rate Monitoring** - Track AI request failures and retry rates

**2. 💰 Cost & Token Usage Tracking**
- **Real-time Cost Tracking** - Monitor AI usage costs per analysis
- **Token Consumption** - Track input/output tokens across providers
- **Cost by Model** - Breakdown of expenses by AI model (GPT-4, Claude, etc.)
- **Budget Alerts** - Thresholds for cost control and optimization

**3. 📈 Time-Series Aggregation**
- **Multiple Granularities** - Hourly, daily, weekly, monthly views
- **Trend Visualization** - Confidence scores, costs, and analysis counts over time
- **Framework Breakdown** - Per-framework metrics (Robot, Cypress, etc.)
- **Historical Analysis** - 30-day retention with configurable cleanup

**4. 🎯 Prometheus/Grafana Integration**
- **Prometheus Metrics Export** - Standard /metrics endpoint format
- **Grafana-Ready Data** - Pre-formatted for dashboard panels
- **Custom Labels** - Framework, model, provider tags for filtering
- **Alerting Support** - Threshold-based alerts on error rates and costs

**5. 🔍 Quality Metrics**
- **Cache Hit Rates** - Track AI response caching effectiveness
- **Suggestions Quality** - Monitor fix recommendation acceptance
- **Model Comparison** - Compare performance across AI providers
- **A/B Testing Support** - Evaluate different AI configurations

**Example Grafana Dashboard Panels:**

```json
{
  "single_stats": {
    "total_analyses": {
      "value": 156,
      "unit": "analyses",
      "description": "Total AI Analyses"
    },
    "avg_confidence": {
      "value": 0.87,
      "unit": "percent",
      "thresholds": {"green": 0.8, "yellow": 0.6, "red": 0.4}
    },
    "total_cost": {
      "value": 12.45,
      "unit": "USD"
    }
  },
  "time_series": {
    "confidence_trend": [
      {"time": "2026-02-11T00:00:00", "value": 0.85},
      {"time": "2026-02-12T00:00:00", "value": 0.87}
    ]
  }
}
```

**Prometheus Metrics Exposed:**

- `crossbridge_ai_confidence_score` - Average confidence score (gauge)
- `crossbridge_ai_tokens_used_total` - Total tokens consumed (counter)
- `crossbridge_ai_cost_usd_total` - Total cost in USD (counter)
- `crossbridge_ai_response_time_ms` - AI response time (gauge)
- `crossbridge_ai_errors_total` - Total AI errors (counter)
- `crossbridge_ai_cache_hits_total` - Total cache hits (counter)
- `crossbridge_ai_clusters_analyzed_total` - Total clusters analyzed (counter)

**Benefits:**
- 📊 **Real-Time Visibility** - Monitor AI performance and costs in real-time
- 💰 **Cost Optimization** - Identify expensive operations and optimize usage
- 🔍 **Quality Assurance** - Track confidence scores and error rates
- 📈 **Trend Analysis** - Identify patterns and anomalies over time
- 🎯 **Grafana Integration** - Pre-built dashboards for immediate insights
- ⚡ **Performance Monitoring** - Detect AI API slowdowns and bottlenecks

**Automated Metric Collection:**

Metrics are automatically recorded during AI-enhanced log parsing:
- Runs in background via sidecar API
- No performance impact on test execution
- 30-day retention with automatic cleanup
- File-based persistence (`data/ai_metrics.json`)
- In-memory cache for fast access (last 1000 analyses)

**Integration with Existing Tools:**
- ✅ Compatible with Prometheus/Grafana stack
- ✅ Works with existing CrossBridge intelligence features
- ✅ Integrates with enterprise analysis (regression, confidence scoring)
- ✅ Zero configuration - works out of the box
- ✅ RESTful API for custom integrations

**That's it!** No listener files, no configuration changes, no repository modifications.

### Legacy Script Support

The original bash scripts are still available for backward compatibility:

```bash
# Legacy commands (deprecated but still work)
./bin/crossbridge-run robot tests/
./bin/crossbridge-log output.xml

# New unified commands (recommended)
crossbridge run robot tests/
crossbridge log output.xml
```

**Migration Path:** Update `crossbridge-run` → `crossbridge run` and `crossbridge-log` → `crossbridge log` in your CI/CD scripts.

### How It Works

1. 🔍 **Auto-detects** your test framework (Robot, Pytest, Jest, JUnit, Mocha)
2. 📥 **Downloads** the appropriate adapter from CrossBridge sidecar
3. ⚙️ **Configures** monitoring automatically via environment variables
4. ▶️ **Runs** your tests with CrossBridge observability enabled

All adapters are cached locally (`~/.crossbridge/adapters/`) and auto-refresh every 24 hours.

**Supported Frameworks:**
- 🤖 Robot Framework
- 🧪 Pytest
- 🃏 Jest
- ☕ JUnit/Maven
- ☕ Mocha

📖 **Full Documentation:** [Universal Wrapper Guide](docs/UNIVERSAL_WRAPPER.md)

---

### 🔹 2. **Intelligent Test Migration & Transformation**
Automate conversion from outdated frameworks to modern ones:

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Legacy Tests      │         │   CrossBridge    │         │   Modern Tests      │
│                     │         │                  │         │                     │
│  • Selenium Java    │────────▶│  • Smart Parser  │────────▶│  • Robot Framework  │
│  • Cucumber BDD     │         │  • AI Enhancement│         │  • Playwright       │
│  • Pytest Selenium  │         │  • Pattern Match │         │  • Maintainable     │
│  • .NET SpecFlow    │         │  • Validation    │         │  • Modern Syntax    │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

**Features:**
- Selenium → Playwright transformation
- Legacy BDD → Modern structured tests
- AI-assisted locator improvement
- Pattern-based intelligent parsing

### 🔹 3. **AI-Powered Test Intelligence** ⭐ ENHANCED!
Reduce maintenance costs with intelligent insights and automated failure analysis:

#### **Advanced Failure Classification** 🆕
- 📊 **Category-Based Classification** - 5 primary categories + 31 specialized sub-categories
  - `PRODUCT_DEFECT` (API errors, assertions, business logic, data validation, performance, security)
  - `AUTOMATION_DEFECT` (element not found, locators, stale elements, test code, synchronization)
  - `ENVIRONMENT_ISSUE` (timeouts, network, DNS, SSL, resource exhaustion, infrastructure)
  - `CONFIGURATION_ISSUE` (dependencies, credentials, files, config, permissions, versions)
  - `UNKNOWN` (unclassifiable failures)
- 🎯 **Confidence Scoring** - 0.0-1.0 confidence for each classification
- 📝 **Evidence-Based Reasoning** - Detailed explanation with specific patterns detected
- ⚡ **Fast Performance** - <50ms per classification

#### **Test Failure Correlation & Grouping** 🆕
- 🔗 **Intelligent Grouping** - Automatically groups related failures
- 🎯 **Root Cause Analysis** - Identifies common underlying issues
- 📈 **Pattern Detection** - Tracks failure trends across test runs
- ⏱️ **Temporal Correlation** - Groups failures in time windows
- 💡 **70% Faster Analysis** - Analyze groups instead of individual tests
- 🔍 **Impact Assessment** - Prioritize fixes by affected test count

#### **Failure Deduplication & Clustering** 🔥 CRITICAL!
- 🎯 **Smart Fingerprinting** - MD5 hash of normalized error signatures
- 🧹 **Noise Reduction** - "23 failures → 5 unique root issues" (75-90% reduction)
- 🔄 **Normalization Engine** - Removes timestamps, IDs, URLs, line numbers
- 📊 **Impact Severity Scoring** - Deterministic prioritization (HTTP status + 60+ patterns)
  - 🔴 CRITICAL: System crashes, memory errors, security violations, HTTP 500
  - 🟠 HIGH: Assertion failures, element not found, API 40x errors, SQL errors
  - 🟡 MEDIUM: Timeouts, network issues, service unavailable, rate limiting  
  - ⚪ LOW: Warnings, redirects, non-critical issues
  - ⚡ **Instant prioritization** without AI dependency
- 🚀 **Massive Triage Speedup** - Eliminate duplicate failure analysis
- 📋 **Visual Summary Tables** - Clustered view with affected test counts
- 💡 **Fix Suggestions** - Actionable recommendations per cluster

**Real-World Example:**
```
Before: "Checking Instant VM Job Status → failed" (appears 3 times)
After:  "1 root issue: Element not found (3 occurrences)"
Result: 75% noise reduction, instant root cause visibility
```

#### **AI-Enhanced Analysis** 🤖 ENHANCED!
- 🧠 **Root Cause Insights** - AI explains "why" tests failed
- 🔧 **Intelligent Recommendation Summarization** 🆕 - AI condenses verbose output into concise, actionable recommendations
  - Eliminates mid-sentence truncation (complete messages, not "...due to several")
  - Automatically combines duplicate recommendations
  - Removes verbose explanations while maintaining technical accuracy
- 🔧 **Fix Recommendations** - Specific code-level suggestions
- 📊 **Pattern Matching** - Historical failure analysis
- 💰 **Cost Transparency** - Show costs before/after processing
- 🎫 **License Management** - Tier-based token limits (FREE to UNLIMITED)
- ✅ **Graceful Fallback** - Works without AI if license invalid
- 🌟 **Supported Providers:**
  - **Cloud:** OpenAI (GPT-3.5, GPT-4), Anthropic (Claude), Azure OpenAI
  - **Self-hosted:** Ollama (deepseek-coder, llama3), vLLM (any HuggingFace model)
- 🎨 **Dynamic UI** - Provider-aware banners with cost info
- 🚀 **Smart Startup Logging** - Clear provider detection messages:
  - ✅ AI AVAILABLE - OpenAI credentials configured (💰 Cost: ~$0.01-$0.10 per run)
  - ✅ AI AVAILABLE - Self-hosted model: deepseek-coder:6.7b at http://... (💰 Cost: Free)
  - ℹ️  AI NOT CONFIGURED - Will run rule-based analysis only
- 📊 **Smart Duration** - Auto-format time (45s → 3m 25s → 2h 15m)
- 🔍 **Comprehensive Logging** - All providers log API calls with timing, tokens, and costs
- 📝 **Concise Formatting** - Clean output without AI disclaimers (90% less verbose)

#### **Intelligent Sampling & Storage** 🆕
- 🎲 **Smart Sampling** - Multiple strategies (uniform, stratified, priority-based, failure-biased)
- 📦 **Storage Optimization** - 80% reduction with 10% sampling
- 🔄 **Adaptive Sampling** - Auto-adjust based on anomaly detection
- 💾 **Automatic Cleanup** - Configurable retention (default: 30 days)
- 📊 **Statistical Significance** - Maintains 95% CI with ±5% margin

#### **Traditional Intelligence** (Existing Features)
- 🔍 **Flaky test detection** with ML-based analysis
- 📊 **Coverage analysis** across behavioral and functional dimensions
- 🎯 **Test risk insight and prioritization**
- 🔧 **Self-healing locator suggestions**
- 📈 **Impact analysis** linking tests to code changes

**Quick Start:**
```bash
# Basic analysis (free, deterministic)
./bin/crossbridge-log output.xml

# With correlation grouping
./bin/crossbridge-log output.xml --correlation

# With AI enhancement (requires license for cloud providers)
./bin/crossbridge-log output.xml --enable-ai

# Self-hosted AI (no license needed, free inference)
# 1. Set up Ollama with deepseek-coder:6.7b
# 2. Configure crossbridge.yml for Ollama
# 3. Run: ./bin/crossbridge-log output.xml --enable-ai
#    ✓ Shows green banner for self-hosted
#    ✓ Duration auto-formatted (3m 25s, 2h 15m)
#    ✓ No cost displayed (local inference)
```

**Testing:**
- ✅ 253 AI tests passing (100% success rate)
- ✅ 18 classification tests + 24 correlation tests + 27 AI license tests
- ✅ Performance validated: <50ms classification, <200ms correlation (1K tests)

📖 **Documentation:** [CrossBridge Log CLI Guide](docs/cli/CROSSBRIDGE_LOG.md) | [Intelligence Features](docs/EXECUTION_INTELLIGENCE.md)

### 🔹 4. **Structured Log Analysis (TestNG + Framework Logs)** 🆕 PRODUCTION READY!

> **Deterministic failure classification without regex hell**  
> Parse structured test results (TestNG XML) + framework logs (log4j/slf4j) for reliable root cause analysis.

**Why Structured Log Analysis?**
- ✅ **Deterministic** - XML-based parsing, not fragile regex
- ✅ **Comprehensive** - Analyzes test results + framework logs + driver logs
- ✅ **Correlated** - Links test failures with framework errors
- ✅ **Categorized** - Automatic classification (test/infra/env/app failures)
- ✅ **Production-Ready** - Proven at scale with TestNG/Java/Selenium stacks

**Architecture:**
```
┌─────────────────────┐       ┌──────────────────────┐       ┌────────────────────┐
│  Test Artifacts     │       │  CrossBridge         │       │  Structured Output │
│                     │       │  Log Ingestion       │       │                    │
│  • testng-results   │──────▶│  • TestNG Parser     │──────▶│  • Correlated      │
│  • framework.log    │       │  • Log Parser        │       │    Failures        │
│  • driver logs      │       │  • Correlation       │       │  • Root Causes     │
│                     │       │    Engine            │       │  • Categorization  │
└─────────────────────┘       └──────────────────────┘       └────────────────────┘
```

**Supported Formats:**
- **Test Results:** TestNG XML (`testng-results.xml`), JUnit XML (coming soon)
- **Framework Logs:** log4j, slf4j, logback (standard Java logging)
- **Driver Logs:** Selenium WebDriver logs (optional)

**✅ RestAssured Compatibility:**
This works **perfectly** with RestAssured + TestNG frameworks:
- RestAssured uses TestNG for test execution (generates identical `testng-results.xml`)
- Framework logs capture RestAssured HTTP client activity
- Additional benefit: HTTP request/response details in framework logs
- Same correlation engine links API test failures with HTTP errors

**Key Features:**

**1. TestNG XML Parsing** 🎯
- Structured extraction of test methods, status, duration
- Exception details with full stack traces
- Automatic categorization (assertion vs infrastructure vs environment)
- Group/suite hierarchy preservation

**2. Framework Log Correlation** 🔗
- Parse ERROR/WARN entries from framework logs
- Time-window correlation with test failures
- Test class name matching for precise correlation
- Multi-line stack trace extraction

**3. Failure Classification** 🏷️
- **TEST_ASSERTION** - AssertionError, test logic failures
- **INFRASTRUCTURE** - Timeouts, connection errors, WebDriver issues
- **ENVIRONMENT** - Config missing, NullPointer, file not found
- **APPLICATION** - HTTP 500, application crashes
- **FLAKY** - Intermittent failures (future enhancement)

**4. Correlation Engine** 🧠
- Links TestNG failures → Framework logs → Driver logs
- Confidence scoring (0.0-1.0) for correlation quality
- Root cause extraction from logs
- Infrastructure vs test failure separation

**Configuration** (`crossbridge.yml`):
```yaml
log_analysis:
  enabled: true  # Enable structured log ingestion
  
  testng:
    path: test-output/testng-results.xml
    auto_discover: true  # Search workspace for TestNG XMLs
  
  framework_log:
    path: logs/framework.log
    levels: [ERROR, WARN]  # Only parse errors/warnings
    
  driver_logs:
    enabled: false  # Optional
    directory: logs/drivers
  
  correlation:
    time_window_seconds: 30  # Correlate logs ±30s from test
    min_confidence: 0.5
```

**CLI Usage:**
```bash
# Parse TestNG results (auto-discovers framework logs)
crossbridge log test-output/testng-results.xml

# Explicit framework log
crossbridge log test-output/testng-results.xml --framework-log logs/app.log

# Include driver logs
crossbridge log test-output/testng-results.xml --driver-logs logs/drivers/

# JSON output for CI/CD
crossbridge log test-output/testng-results.xml --output json > results.json
```

**Output Example:**
```
=========================================
           TestNG Test Results
=========================================

Status: FAIL

Test Statistics:
  Total:    24
  Passed:   18
  Failed:   6
  Pass Rate: 75.0%

Root Cause Analysis: 3 unique issues (deduplicated from 6 failures)
Deduplication saved 3 duplicate entries (50% reduction)
Domain breakdown: 2 Product, 1 Infra

⚠️  Systemic Patterns Detected:
   ⚠️  Multiple assertion failures suggests possible systemic regression

╭────────────────┬────────────┬──────────────────────────────────────────────┬─────────┬─────────────────────────╮
│ Severity       │ Domain     │ Root Cause                                   │   Count │ Affected Tests          │
├────────────────┼────────────┼──────────────────────────────────────────────┼─────────┼─────────────────────────┤
│ ⚠️  HIGH       │ 🔧 INFRA   │ Session not created - WebDriver timeout      │       3 │ LoginTest, +2 more      │
│ ⚠️  HIGH       │ 🐛 PROD    │ Expected 200 but was 500                     │       2 │ ApiTest, StatusTest     │
│ ⚠️  HIGH       │ 🐛 PROD    │ Assertion failed: Element not visible        │       1 │ UI_ValidationTest       │
╰────────────────┴────────────┴──────────────────────────────────────────────┴─────────┴─────────────────────────╯

━━━ Detailed Failure Analysis ━━━

1. ⚠️  HIGH - Session not created - WebDriver timeout
   Occurrences: 3
   Affected Tests:
      • LoginTest.testValidCredentials
      • LoginTest.testInvalidCredentials
      • ProfileTest.testLoadProfile
   💡 Suggested Fix:
      Check WebDriver/browser compatibility and driver version

2. ⚠️  HIGH - Expected 200 but was 500
   Occurrences: 2
   Affected Tests:
      • ApiTest.testGetEndpoint
      • StatusTest.testHealthCheck
   💡 Suggested Fix:
      Review test expectations and actual application behavior

⏱️  Slowest Tests (Top 5):
╭─────────────────────────────────────────┬──────────────╮
│ Test Case                               │     Duration │
├─────────────────────────────────────────┼──────────────┤
│ com.example.SlowTest.testLongOperation  │        2m 30s│
│ com.example.ApiTest.testIntegration     │        1m 45s│
│ com.example.UITest.testCompleteFlow     │        1m 20s│
╰─────────────────────────────────────────┴──────────────╯
```

**Features:**
- ✅ Comprehensive test statistics and pass rate
- ✅ Intelligent failure clustering and deduplication (powered by `core.log_analysis.clustering`)
- ✅ Domain classification (Product, Infrastructure, Environment, Test)
- ✅ Severity-based prioritization (Critical, High, Medium, Low)
- ✅ Root cause analysis with suggested fixes
- ✅ Systemic pattern detection (identifies widespread issues)
- ✅ Slowest tests profiling for performance optimization
- ✅ Detailed error messages with stack traces
- ✅ Rich console output with tables and formatting (powered by Rich library)

**AI-Enhanced Analysis:**
```bash
# Enable AI for deeper failure analysis
crossbridge log test-output/testng-results.xml --enable-ai
```

**Legacy Output Example (pre-clustering):**
```
🔍 Parsing TestNG results: test-output/testng-results.xml
✅ Parsed 24 tests: 18 passed, 6 failed

🔗 Correlating with framework logs...
   Found 12 ERROR entries, 8 WARN entries
   Correlated 5/6 failures with framework logs (confidence: 0.85)

📊 Failure Classification:
   • 3 INFRASTRUCTURE (Connection timeout, Session not created)
   • 2 TEST_ASSERTION (Expected value mismatch)
   • 1 ENVIRONMENT (Config file missing)

💡 Top Issues:
   1. [CRITICAL] Session not created (3 tests affected)
      → Check WebDriver/browser compatibility
   2. [HIGH] AssertionError in LoginTest (2 tests)
      → Review test expectations vs actual behavior
```

**Execution Orchestration Integration:**
When using execution orchestration, structured log analysis runs automatically after test execution:
```python
from core.execution.orchestration import create_orchestrator, ExecutionRequest

orchestrator = create_orchestrator(workspace=Path("./my-project"))
request = ExecutionRequest(
    framework="testng",
    strategy="impacted",
    environment="dev"
)

result = orchestrator.execute(request)

# Access structured failures
for failure in result.structured_failures:
    print(f"Test: {failure.structured_failure.test_name}")
    print(f"Category: {failure.category}")
    print(f"Root Cause: {failure.root_cause}")
    print(f"Confidence: {failure.correlation_confidence:.2f}")
```

**Benefits:**
- 🎯 **80% Faster Root Cause Analysis** - Direct to correlated errors
- 🔍 **Infrastructure Detection** - Separate infra from test failures
- 📊 **Reliable Analytics** - Structured data, not regex parsing
- 🔗 **Full Context** - Test + framework + driver logs united
- 🚀 **CI/CD Ready** - JSON output, deterministic results

**Unit Test Coverage:**
- ✅ 150+ unit tests covering all parsers and correlation engine
- ✅ TestNG XML parsing: malformed XML, empty suites, all status types
- ✅ Framework log parsing: multiple formats, multi-line stack traces
- ✅ Correlation engine: confidence scoring, categorization, edge cases
- ✅ 100% pass rate with comprehensive edge case coverage

**Known Limitations:**
- Currently supports TestNG XML (JUnit XML coming in v0.3.1)
- Best results with standard log4j/slf4j patterns
- Driver log parsing is optional enhancement

#### Cypress Enhanced Output Example

**Modern JavaScript/TypeScript E2E Testing with Intelligent Analysis:**

```bash
crossbridge log cypress/results/mochawesome.json
```

**Output:**
```
           Cypress Test Results
=========================================

Status: FAIL

Test Statistics:
  Total:    45
  Passed:   38
  Failed:   7
  Pass Rate: 84.4%
  Duration: 2m 15s

Root Cause Analysis: 4 unique issues (deduplicated from 7 failures)
Deduplication saved 3 duplicate entries (43% reduction)
Domain breakdown: 2 Product, 2 Infra

⚠️  Systemic Patterns Detected:
   ⚠️  Multiple network errors suggests possible systemic regression

╭────────────────┬────────────┬──────────────────────────────────────────────┬─────────┬─────────────────────────╮
│ Severity       │ Domain     │ Root Cause                                   │   Count │ Affected Tests          │
├────────────────┼────────────┼──────────────────────────────────────────────┼─────────┼─────────────────────────┤
│ ⚠️  HIGH       │ 🔧 INFRA   │ cy.visit() failed 404 Not Found              │       3 │ smoke/homepage, +2 more │
│ ⚠️  HIGH       │ 🐛 PROD    │ Timed out retrying after 4000ms              │       2 │ login-flow, dashboard   │
│ ⚠️  MEDIUM     │ 🐛 PROD    │ expected <button> to be 'visible'            │       1 │ ui/button-states        │
│ ⚠️  MEDIUM     │ 🔧 INFRA   │ Network request failed - ECONNREFUSED        │       1 │ api/health-check        │
╰────────────────┴────────────┴──────────────────────────────────────────────┴─────────┴─────────────────────────╯

━━━ Detailed Failure Analysis ━━━

1. ⚠️  HIGH - cy.visit() failed 404 Not Found
   Occurrences: 3
   Affected Tests:
      • smoke/homepage.spec.js › should load homepage
      • integration/auth.spec.js › should redirect after login
      • e2e/checkout.spec.js › should complete purchase flow
   💡 Suggested Fix:
      Check application availability and routing configuration

2. ⚠️  HIGH - Timed out retrying after 4000ms
   Occurrences: 2
   Affected Tests:
      • login-flow.spec.js › should authenticate user
      • dashboard.spec.js › should display widgets
   💡 Suggested Fix:
      Review test expectations and actual application behavior

⏱️  Slowest Tests (Top 5):
╭─────────────────────────────────────────┬──────────────╮
│ Test Case                               │     Duration │
├─────────────────────────────────────────┼──────────────┤
│ e2e/checkout-flow.spec.js › full flow   │           45s│
│ integration/dashboard.spec.js › widgets │           32s│
│ e2e/user-registration.spec.js › signup  │           28s│
│ smoke/search.spec.js › advanced filters │           22s│
│ integration/api-mocking.spec.js › POST  │           18s│
╰─────────────────────────────────────────┴──────────────╯
```

**Features:**
- ✅ Mochawesome and native Cypress JSON result parsing
- ✅ Intelligent failure clustering with deduplication (powered by `core.log_analysis.clustering`)
- ✅ Domain classification (Product, Infrastructure, Environment, Test)
- ✅ Network error detection and categorization
- ✅ Timeout analysis and suggested fixes
- ✅ Slowest tests profiling for performance optimization
- ✅ Retry attempt tracking
- ✅ Screenshot and video artifact references (when available)

#### Behave Enhanced Output Example

**Python BDD Testing with Scenario-Level Analysis:**

```bash
crossbridge log behave-results.json
```

**Output:**
```
           Behave Test Results
=========================================

Status: FAIL

Scenario Statistics:
  Total:    28
  Passed:   22
  Failed:   6
  Pass Rate: 78.6%
  Duration: 1m 45s

Root Cause Analysis: 3 unique issues (deduplicated from 6 failures)
Deduplication saved 3 duplicate entries (50% reduction)
Domain breakdown: 2 Product, 1 Infra

⚠️  Systemic Patterns Detected:
   ⚠️  Multiple step failures suggests possible systemic regression

╭────────────────┬────────────┬──────────────────────────────────────────────┬─────────┬─────────────────────────╮
│ Severity       │ Domain     │ Root Cause                                   │   Count │ Affected Scenarios      │
├────────────────┼────────────┼──────────────────────────────────────────────┼─────────┼─────────────────────────┤
│ ⚠️  HIGH       │ 🔧 INFRA   │ selenium.common.exceptions.TimeoutException  │       3 │ User Login, +2 more     │
│ ⚠️  HIGH       │ 🐛 PROD    │ AssertionError: expected 'Success', got 404  │       2 │ API Health, Status      │
│ ⚠️  MEDIUM     │ 🐛 PROD    │ NoSuchElementException: element not found    │       1 │ Search Functionality    │
╰────────────────┴────────────┴──────────────────────────────────────────────┴─────────┴─────────────────────────╯

━━━ Detailed Failure Analysis ━━━

1. ⚠️  HIGH - selenium.common.exceptions.TimeoutException
   Occurrences: 3
   Affected Scenarios:
      • features/authentication.feature › User Login Scenario
      • features/profile.feature › Profile Update Scenario
      • features/checkout.feature › Complete Purchase Scenario
   💡 Suggested Fix:
      Check WebDriver/browser compatibility and driver version

2. ⚠️  HIGH - AssertionError: expected 'Success', got 404
   Occurrences: 2
   Affected Scenarios:
      • features/api.feature › API Health Check
      • features/status.feature › Service Status Verification
   💡 Suggested Fix:
      Review test expectations and actual application behavior

⏱️  Slowest Scenarios (Top 5):
╭─────────────────────────────────────────────────────────────┬──────────────╮
│ Scenario                                                    │     Duration │
├─────────────────────────────────────────────────────────────┼──────────────┤
│ features/checkout.feature › Complete Multi-Step Purchase    │           38s│
│ features/reporting.feature › Generate Comprehensive Report  │           29s│
│ features/integration.feature › End-to-End Workflow Test     │           24s│
│ features/data-processing.feature › Bulk Data Import         │           19s│
│ features/authentication.feature › OAuth2 Login Flow         │           15s│
╰─────────────────────────────────────────────────────────────┴──────────────╯
```

**Features:**
- ✅ Behave JSON result parsing with feature/scenario structure
- ✅ Intelligent failure clustering at scenario level (powered by `core.log_analysis.clustering`)
- ✅ Domain classification (Product, Infrastructure, Environment, Test)
- ✅ Step definition failure mapping
- ✅ Tag-based test categorization (@smoke, @regression, @wip)
- ✅ Slowest scenarios profiling for performance optimization
- ✅ Multi-line string (docstring) and table parameter support
- ✅ Gherkin syntax validation and parsing

**All Frameworks - Common Benefits:**
- ✅ **Unified Interface**: Consistent CLI for all frameworks (`crossbridge log <result-file>`)
- ✅ **Zero Code Changes**: Works with existing test frameworks as-is
- ✅ **Smart Clustering**: Reduces duplicate failure noise by 40-60%
- ✅ **Actionable Insights**: Suggested fixes for common failure patterns
- ✅ **CI/CD Ready**: JSON output for pipeline integration
- ✅ **Modular Architecture**: Reuses `core.log_analysis.clustering` module across all frameworks

#### Multi-File Log Analysis 🆕

**Analyze multiple test result files in a single command!**

CrossBridge now supports analyzing multiple log files simultaneously with unified clustering, per-file JSON outputs, and merged results. Perfect for distributed test execution across multiple VMs, containers, or CI/CD nodes.

**CLI Usage:**

```bash
# Analyze multiple files from the same framework
crossbridge log testng-vm1.xml testng-vm2.xml testng-vm3.xml --enable-ai

# Mixed frameworks (TestNG, Cypress, Behave, etc.)
crossbridge log testng-results.xml cypress-results.json behave-output.json

# Specify custom merged output file
crossbridge log output1.xml output2.xml output3.xml --output merged-analysis.json

# With all analysis features
crossbridge log vm1.xml vm2.xml vm3.xml --enable-ai --triage --max-ai-clusters 10
```

**Console Output - Per-File Segregation:**

```
============================================================
  📊 Multi-File Log Analysis (3 files)
============================================================

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  File 1/3: testng-vm1.xml                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

[OK] Detected framework: testng

           TestNG Test Results
=========================================

Status: FAIL

Test Statistics:
  Total:    45
  Passed:   38
  Failed:   7
  Pass Rate: 84.4%

Root Cause Analysis: 3 unique issues (deduplicated from 7 failures)
...

Results saved to: testng-vm1.parsed.20260215_143028.json

────────────────────────────────────────────────────────────

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  File 2/3: testng-vm2.xml                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

[OK] Detected framework: testng

           TestNG Test Results
=========================================
...

Results saved to: testng-vm2.parsed.20260215_143029.json

────────────────────────────────────────────────────────────

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  File 3/3: testng-vm3.xml                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

[OK] Detected framework: testng
...

============================================================
  📊 Multi-File Analysis Summary
============================================================

✅ Successfully processed: 3 file(s)

📁 Output Files:
   Merged results: Testng_Full_Log_Analyze.20260215_143030.json
   Per-file results: 3 individual files

📈 Aggregate Statistics:
   Total tests:  120
   Passed:       102 (85.0%)
   Failed:       18 (15.0%)

============================================================
[OK] Multi-file parsing complete!
```

**JSON Output Structure:**

**Per-File JSONs** (automatically named with source filename):
```
testng-vm1.parsed.20260215_143028.json  ← Full analysis for VM1
testng-vm2.parsed.20260215_143029.json  ← Full analysis for VM2
testng-vm3.parsed.20260215_143030.json  ← Full analysis for VM3
```

Each per-file JSON contains complete analysis identical to single-file mode:
- Full test results
- Failure clustering
- Root cause analysis
- Confidence scores
- AI analysis (if enabled)

**Merged JSON** (combined results):
```json
{
  "analysis_type": "multi-file",
  "timestamp": "2026-02-15T14:30:30.123456",
  "total_files": 3,
  "files": [
    {
      "path": "/path/to/testng-vm1.xml",
      "framework": "testng",
      "output_file": "/path/to/testng-vm1.parsed.json",
      "statistics": {
        "total_tests": 45,
        "passed_tests": 38,
        "failed_tests": 7,
        "skipped_tests": 0
      }
    },
    {
      "path": "/path/to/testng-vm2.xml",
      "framework": "testng",
      "output_file": "/path/to/testng-vm2.parsed.json",
      "statistics": {
        "total_tests": 40,
        "passed_tests": 35,
        "failed_tests": 5,
        "skipped_tests": 0
      }
    },
    {
      "path": "/path/to/testng-vm3.xml",
      "framework": "testng",
      "output_file": "/path/to/testng-vm3.parsed.json",
      "statistics": {
        "total_tests": 35,
        "passed_tests": 29,
        "failed_tests": 6,
        "skipped_tests": 0
      }
    }
  ],
  "aggregate_statistics": {
    "total_tests": 120,
    "passed_tests": 102,
    "failed_tests": 18,
    "skipped_tests": 0
  },
  "unified_failure_clusters": [
    {
      "root_cause": "Connection timeout",
      "count": 8,
      "severity": "HIGH",
      "domain": "INFRA",
      "failures": [
        {
          "test_name": "LoginTest.testValidCredentials",
          "source_file": "/path/to/testng-vm1.xml",
          "error_message": "Connection timeout after 30s",
          "test_file": "LoginTest.java"
        },
        {
          "test_name": "ApiTest.testEndpoint",
          "source_file": "/path/to/testng-vm2.xml",
          "error_message": "Connection timeout after 30s",
          "test_file": "ApiTest.java"
        }
        // ... 6 more failures from all 3 files
      ]
    },
    {
      "root_cause": "AssertionError: expected 200 but was 500",
      "count": 5,
      "severity": "HIGH",
      "domain": "PRODUCT",
      "failures": [
        // Failures from multiple files
      ]
    }
  ],
  "unified_cluster_summary": {
    "total_clusters": 5,
    "total_failures": 18,
    "deduplication_rate": 0.61,
    "original_failure_count": 18
  },
  "per_file_results": [
    { /* Full VM1 analysis */ },
    { /* Full VM2 analysis */ },
    { /* Full VM3 analysis */ }
  ]
}
```

**Key Features:**

1. **Unified Clustering Across All Files**
   - Failures from all files are clustered together
   - Eliminates duplicate root causes across VMs/nodes
   - Higher deduplication rate (up to 70% for distributed tests)
   - Single view of all systemic issues

2. **Per-File Analysis**
   - Each file gets individual detailed analysis
   - Separate JSON outputs preserve full context
   - File names automatically embedded in output filenames
   - Easy to trace failures back to specific execution node

3. **Framework Agnostic**
   - Mix TestNG, Cypress, Behave, Robot, Playwright in one command
   - Each file automatically detected and parsed appropriately
   - Unified clustering works across framework boundaries

4. **Error Handling**
   - Skips unsupported/corrupted files gracefully
   - Shows clear warnings for failed files
   - Continues processing remaining files
   - Summary shows success/failure breakdown

5. **CI/CD Integration**
```yaml
# GitHub Actions example
- name: Collect test results from all nodes
  run: |
    crossbridge log \
      node1/testng-results.xml \
      node2/testng-results.xml \
      node3/testng-results.xml \
      --output ci-merged-results.json \
      --enable-ai \
      --triage
    
- name: Upload merged analysis
  uses: actions/upload-artifact@v3
  with:
    name: test-analysis
    path: |
      ci-merged-results.json
      *.parsed.*.json
```

**Benefits:**

- 🎯 **70% Reduced Analysis Time**: Single command vs. running separately
- 🔍 **Higher Deduplication**: Unified clustering across all files (40-70% noise reduction)
- 📊 **Aggregate Insights**: See overall test health across all execution nodes
- 🔗 **Traceability**: Per-file outputs preserve node-specific context
- 🚀 **CI/CD Native**: Perfect for distributed test execution pipelines
- ✅ **Zero Configuration**: Works with existing test outputs as-is

#### Detailed Logging & Observability 🆕

**Comprehensive logging throughout the analysis workflow for production troubleshooting and debugging.**

CrossBridge now provides enterprise-grade detailed logging across all operations, giving complete visibility into validation, parsing, sidecar communication, intelligence analysis, and file operations.

**What's Logged:**

```
2026-02-15 12:56:53 | INFO | Starting log parsing for: TestNG-VM1.xml (framework: auto-detect)
2026-02-15 12:56:53 | INFO | Options: AI=True, no_analyze=False, triage=False
2026-02-15 12:56:53 | INFO | Starting validation for file: TestNG-VM1.xml
2026-02-15 12:56:53 | DEBUG | ✓ File exists: TestNG-VM1.xml
2026-02-15 12:56:53 | DEBUG | ✓ Path is a file (not directory)
2026-02-15 12:56:53 | DEBUG | ✓ File is readable (permissions OK)
2026-02-15 12:56:53 | INFO | File size: 2.45 MB (2,569,834 bytes)
2026-02-15 12:56:53 | INFO | Auto-detected framework: testng
2026-02-15 12:56:53 | DEBUG | Running XML validation for testng
2026-02-15 12:56:53 | DEBUG | XML parsed successfully, root element: <testng-results>
2026-02-15 12:56:53 | DEBUG | Found 5 suite(s) in TestNG XML
2026-02-15 12:56:53 | INFO | ✓ All validation checks passed (framework: testng, size: 2.45 MB)
2026-02-15 12:56:53 | INFO | Sending parse request to sidecar: http://localhost:8000/parse/testng
2026-02-15 12:56:53 | INFO | File: TestNG-VM1.xml, Size: 2.45 MB, Framework: testng
2026-02-15 12:56:53 | DEBUG | Uploading file to sidecar endpoint...
2026-02-15 12:56:56 | INFO | Sidecar response received: HTTP 200 (took 3s)
2026-02-15 12:56:56 | INFO | Parsing successful - Total: 150, Passed: 115, Failed: 35
2026-02-15 12:56:56 | INFO | Starting intelligence analysis (AI: True)
2026-02-15 12:58:45 | INFO | Intelligence analysis request completed: HTTP 200
2026-02-15 12:58:45 | INFO | Clustering analysis complete: 12 unique issue(s) from 35 failure(s)
2026-02-15 12:58:45 | DEBUG | Cluster 1: [critical/product] NullPointerException (count: 8)
2026-02-15 12:58:45 | DEBUG | Cluster 2: [high/infrastructure] DB connection timeout (count: 5)
2026-02-15 12:58:45 | DEBUG | Cluster 3: [medium/product] Invalid API response (count: 4)
2026-02-15 12:58:45 | INFO | AI analysis complete: 15 insights generated
2026-02-15 12:58:45 | INFO | Results saved to: TestNG-VM1.parsed.json (347.2 KB)
```

**Logging Categories:**

1. **Validation Logging**
   - File existence, readability, size checks
   - Framework auto-detection process
   - XML/JSON/Java schema validation details
   - Validation failures with specific errors

2. **Framework Detection**
   - Filename pattern matching attempts
   - Content inspection findings
   - Detection method used (filename vs content)
   - Failures when framework unknown

3. **Sidecar Communication**
   - Parse request details (endpoint, file size)
   - HTTP response codes and timing
   - Test counts (total/passed/failed)
   - Connection errors and timeouts

4. **Intelligence Analysis**
   - Clustering results and deduplication stats
   - Top cluster details (severity, domain, root cause)
   - AI insights generation
   - Analysis timing and performance

5. **File Operations**
   - Output file paths (specified vs auto-generated)
   - JSON content sizes
   - Per-file and merged output writing

**Log Files Location:**

```bash
# Default log location
~/.crossbridge/logs/

# Typical log files
run-20260215_125653.log      # Detailed operation logs
run-20260215_121204.log      # Previous runs
```

**View Logs:**

```bash
# Live tail during analysis
tail -f ~/.crossbridge/logs/run-$(date +%Y%m%d)*.log

# Search for errors
grep "ERROR" ~/.crossbridge/logs/run-*.log

# Filter sidecar communication
grep "Sidecar" ~/.crossbridge/logs/run-*.log

# View clustering results
grep "Clustering analysis" ~/.crossbridge/logs/run-*.log
```

**Benefits:**

- 🔍 **Complete Audit Trail**: Every operation logged with timing
- 🐛 **Easy Troubleshooting**: Identify exact failure points
- ⚡ **Performance Monitoring**: Track file sizes, HTTP response times
- 🔗 **Sidecar Visibility**: Full API request/response details
- 📊 **Analysis Insights**: See clustering and AI results in logs
- 🏢 **Enterprise Ready**: Production-grade logging for monitoring

**Debugging Examples:**

```bash
# Why did validation fail?
grep "Validation failed" ~/.crossbridge/logs/run-*.log

# Sidecar connection issues?
grep -E "Sidecar.*(timeout|connection)" ~/.crossbridge/logs/run-*.log

# How many clusters were identified?
grep "unique issue" ~/.crossbridge/logs/run-*.log

# Which files were processed?
grep "Starting log parsing" ~/.crossbridge/logs/run-*.log
```

📖 **See Also:** [Logging Framework Documentation](core/logging/README.md) | [Troubleshooting Guide](docs/configuration/TROUBLESHOOTING.md)

---

### 🔹 5. **Intelligent Parsers & Unified Embeddings** ⭐
**Released: January 2026**

CrossBridge now includes advanced parsing capabilities and a unified embeddings system:

**Intelligent Parsers:**
- 🔍 **Java Step Definition Parser** - Parse Cucumber/BDD step definitions with AST-level analysis
- 📊 **Robot Framework Log Parser** - Analyze Robot output.xml for keywords, tags, and performance metrics
- 🧪 **Pytest Intelligence Plugin** - Extract execution signals and test metadata at runtime

**Unified Embeddings System:**
- 🎯 Framework-agnostic embedding interface for semantic search across all test types
- 🔌 Support for OpenAI, Anthropic, HuggingFace, Ollama, and custom embedding providers
- 💾 Vector stores: FAISS, pgvector, ChromaDB, Pinecone
- 🔎 Semantic test similarity and intelligent test matching

**Test Coverage:**
- ✅ 32/32 comprehensive parser tests (100% passing)
- ✅ 174/184 total tests passing (94.6% pass rate)
- ✅ Performance: 50 steps parsed in <1s, 30 Robot tests in <1s

📖 **Documentation:** [Feature Guide](docs/releases/historical/intelligence_features.md) | [QA Report](docs/releases/historical/intelligence_qa_report.md)

---

### 🔹 5. **Sidecar Observer** ⭐ NEW
**Zero-impact test observability without code changes**

Monitor and analyze tests without modifying a single line of test code:

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Test Execution    │         │   Sidecar        │         │   Observability     │
│   (No Changes!)     │         │   Runtime        │         │                     │
│                     │         │                  │         │                     │
│  • Existing tests   │────────▶│  • Sampler       │────────▶│  • Prometheus       │
│  • Any framework    │  events │  • Observer      │ metrics │  • Grafana          │
│  • Zero impact      │         │  • Profiler      │         │  • Health checks    │
│                     │         │  • <5% CPU       │         │  • Alerts           │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

**Key Features:**
- ⚡ **Fail-open execution** - Never blocks test runs (catches all exceptions)
- 📦 **Bounded queues** - Load shedding with 5000-10000 event capacity
- 🎲 **Smart sampling** - Configurable rates (1-100%, default: 10% events, 5% logs, 1% profiling)
- 🔄 **Adaptive sampling** - Auto-boost 5x for 60s on anomalies
- 💾 **Resource budgets** - Auto-throttles at 5% CPU / 100MB RAM limits
- 🏥 **Health endpoints** - `/health`, `/ready`, `/metrics` for monitoring
- 📊 **Prometheus metrics** - Production-grade observability with Grafana dashboards
- 🔧 **Runtime configurable** - No rebuild/redeploy required

**Quick Start:**
```yaml
# crossbridge.yml
runtime:
  sidecar:
    enabled: true
    sampling:
      events: 0.1          # 10% sampling rate
      adaptive: enabled    # Auto-boost on anomalies
    resources:
      max_queue_size: 10000
      max_cpu_percent: 5.0
      max_memory_mb: 100
```

**Usage Example:**
```python
from core.sidecar import SidecarRuntime

with SidecarRuntime() as sidecar:
    # Observe events
    sidecar.observe('test_event', {'test_id': 'test_123', 'status': 'passed'})
    
    # Get health status
    health = sidecar.get_health()  # {'status': 'healthy', 'components': {...}}
    
    # Export metrics (Prometheus format)
    metrics = sidecar.export_metrics()
```

Works with all 12+ frameworks. 

📖 **Learn More**:
- [Sidecar Runtime Guide](docs/sidecar/SIDECAR_RUNTIME.md)
- [Sidecar Integration Guide](docs/quick-start/SIDECAR_INTEGRATION_GUIDE.md) ⭐ **NEW**
- [Test Infrastructure & Hardening](docs/TEST_INFRASTRUCTURE_AND_SIDECAR_HARDENING.md)
- [Configuration Reference](crossbridge.yml)
- [Usage Examples](examples/sidecar_examples.py)

---

### 🔹 6. **AI Semantic Engine**
Advanced semantic intelligence for test discovery, duplicate detection, and smart test selection:

- 🔍 **Semantic Search** - Natural language search across tests, scenarios, and failures
- 🔄 **Duplicate Detection** - Automatic identification of duplicate test cases (threshold: similarity ≥ 0.9, confidence ≥ 0.8)
- 📊 **Clustering** - DBSCAN-based grouping of similar entities
- 🎯 **Smart Test Selection** - AI-powered test selection for code changes using multi-signal scoring:
  - 40% Semantic similarity (code/test relationship)
  - 30% Coverage relevance (code coverage mapping)
  - 20% Failure history (historical patterns)
  - 10% Flakiness penalty
- 📐 **Confidence Calibration** - Logarithmic confidence scoring for reliable results
- 💬 **Explainability** - Every result includes human-readable reasons

**Framework Compatibility:** Works with all 13 frameworks (pytest, selenium, Robot, Cypress, Playwright, JUnit, TestNG, RestAssured, Cucumber, NUnit, SpecFlow, Behave, BDD)

**Quick Start:**
```yaml
# crossbridge.yml
ai:
  semantic_engine:
    enabled: true
    embedding:
      provider: openai
      model: text-embedding-3-large
    test_selection:
      weights:
        semantic_similarity: 0.4
        coverage_relevance: 0.3
        failure_history: 0.2
        flakiness_penalty: 0.1
```

See [Semantic Engine Guide](docs/SEMANTIC_ENGINE.md) for details.

---

### 🔹 7. **Framework-Agnostic Plugin Architecture**
CrossBridge implements a clean plugin architecture through its Execution Orchestration layer:

**KEY INSIGHT:** Execution Orchestration IS the plugin architecture.
- **ExecutionOrchestrator** = Plugin Host
- **Execution Strategies** = Decision Plugins (WHAT to run)
- **Framework Adapters** = Execution Plugins (HOW to run)

**Plugin System Features:**
- 🧩 **Pluggable Strategies**: Smoke, Impacted, Risk-Based, Full (extensible)
- 🔌 **Pluggable Adapters**: 12+ framework adapters (extensible)
- 🔧 **Dynamic Registration**: Third-party plugins via PluginRegistry
- 🚀 **Non-Invasive**: Frameworks unchanged, CLI-level integration
- 🔄 **Sidecar-Compatible**: Works in both observer and orchestration modes

See [Plugin Architecture Guide](docs/architecture/PLUGIN_ARCHITECTURE.md) for complete design philosophy and extension points.

**Supported Frameworks (12+ adapters):**

| Framework | Language | Type | Status | Completeness |
|-----------|----------|------|--------|--------------|
| **pytest** | Python | Unit/Integration | ✅ Production | 98% |
| **Selenium Python** | Python | UI Automation | ✅ Production | 95% |
| **Selenium Java** | Java | UI Automation | ✅ Production | 96% |
| **Cucumber/JBehave (Java BDD)** | Java | BDD | ✅ Production | 95% |
| **Selenium .NET** | C# | UI Automation | ✅ Production | 98% |
| **Cypress** | JavaScript/TS | E2E | ✅ Production | 98% |
| **Robot Framework** | Robot | Keyword-Driven | ✅ Production | 98% |
| **JUnit/TestNG** | Java | Unit/Enterprise | ✅ Production | 95% |
| **NUnit/SpecFlow** | C# / .NET | Unit/BDD | ✅ Production | 96% |
| **Playwright** | JavaScript/TS/Python | E2E | ✅ Production | 96% |
| **RestAssured** | Java | API | ✅ Production | 95% |
| **Cucumber/Behave** | Gherkin | BDD | ✅ Production | 96% |

**Average Completeness: 96%** ✅ (Up from 88%)

**BDD Framework Support:** CrossBridge now includes comprehensive BDD adapters for Cucumber Java, Robot Framework BDD, and JBehave with full feature parsing, step definition mapping, and execution report analysis. See [BDD Implementation Summary](docs/pillars/framework-support/BDD_IMPLEMENTATION_SUMMARY.md) for complete details.

**Recent Framework Enhancements (Sprints 1-3):**
- 🆕 **Robot Framework**: Advanced failure classification, comprehensive metadata extraction, and fast static test discovery
- 🆕 **Selenium .NET**: Full adapter with NUnit/MSTest/xUnit support and intelligent failure classification
- 📖 See [Framework Gap Analysis](docs/pillars/framework-support/FRAMEWORK_GAP_ANALYSIS.md) and [Sprint Implementation Summary](docs/pillars/framework-support/SPRINT_IMPLEMENTATION_SUMMARY.md) for complete details

**Advanced Framework Features:**

*BDD Framework Support:*
- 🔹 **Multi-line String Handler** (Behave): Docstring and text block extraction
- 🔹 **Behave-pytest Bridge**: Hybrid testing with context fixture integration
- 🔹 **Step Parameters**: Behave regex group and parameter extraction
- 🔹 **Custom Matchers**: Behave custom step matcher detection
- 🔹 **DI Container Support** (SpecFlow): Microsoft.Extensions.DependencyInjection integration
- 🔹 **ScenarioContext Handler**: Context state management and pytest conversion
- 🔹 **Table Conversion Handler**: SpecFlow table transformations and TableConverter support

---

### 🔹 8. **Execution Orchestration** 🆕
Intelligent test execution that determines **WHAT**, **WHEN**, and **HOW** to run tests:

**Key Features:**
- **4 Execution Strategies**: Smoke (fast), Impacted (changes), Risk-based (quality), Full (comprehensive)
- **60-80% Test Reduction**: Smart selection reduces CI/CD time significantly
- **Framework-Agnostic**: Works with TestNG, Robot, Pytest, Cypress, Playwright, and more
- **Non-Invasive**: Zero test code changes - invokes frameworks via CLI
- **CI/CD Native**: Designed for Jenkins, GitHub Actions, GitLab CI, Azure DevOps, etc.

**Execution Strategies:**

| Strategy | Purpose | Selection Criteria | Reduction | Use Case |
|----------|---------|-------------------|-----------|----------|
| **Smoke** | Fast signal | Tagged smoke/critical tests | 80-95% | PR validation, quick checks |
| **Impacted** | Code changes | Git diff + coverage mapping + semantic | 60-80% | Feature dev, targeted regression |
| **Risk** | Historical risk | Failure rate + churn + criticality | 40-60% | Release pipelines, high-confidence |
| **Full** | Comprehensive | All tests | 0% | Baseline, nightly regression |

**CLI Examples:**
```bash
# Quick smoke test
crossbridge exec run --framework pytest --strategy smoke

# Impacted tests (PR validation)
crossbridge exec run --framework testng --strategy impacted --base-branch origin/main --ci

# Risk-based with budget (release)
crossbridge exec run --framework robot --strategy risk --max-tests 100 --env prod

# Dry-run to see plan
crossbridge exec plan --framework pytest --strategy impacted --json
```

**How It Works:**
```
┌─────────────────────────────────────────────────┐
│ Crossbridge (Orchestrator)                      │
│  • Decides WHAT to run  (Strategy)              │
│  • Decides HOW to invoke (Adapter)              │
└──────────────────┬──────────────────────────────┘
                   │ CLI Invocation
                   ▼
┌─────────────────────────────────────────────────┐
│ Test Framework (Unchanged)                      │
│  TestNG | Robot | Pytest | Cypress | etc.      │
└─────────────────────────────────────────────────┘
```

**Supported Frameworks (13 Total):** 
- **Java**: TestNG, JUnit 4/5, RestAssured, Cucumber
- **Python**: Robot Framework, Pytest, Behave
- **JavaScript/TypeScript**: Cypress, Playwright
- **.NET**: SpecFlow, NUnit

See [Execution Orchestration Guide](docs/EXECUTION_ORCHESTRATION.md) for complete documentation.

*Web Framework Support:*
- 🔹 **Component Testing** (Cypress): React and Vue component test detection
- 🔹 **Multi-Config Handler**: Environment-specific Cypress configurations
- 🔹 **TypeScript Types**: Cypress custom command type generation

*API Testing Support:*
- 🔹 **Request Filter Chains** (RestAssured): Filter chain extraction and Python conversion
- 🔹 **Enhanced POJO Mapping**: Jackson/Gson annotations and Python dataclass generation
- 🔹 **Fluent API Chains**: RestAssured method chaining analysis

*Enterprise Features:*
- 🔹 **Dependency Injection Support**: Guice, Spring DI extraction for Java
- 🔹 **Reporting Integration**: Allure & ExtentReports integration
- 🔹 **.NET Version Handler**: .NET Core/5/6/8 version detection and compatibility

*pytest Advanced Features:*
- 🔹 **Autouse Fixture Chains**: Complex pytest fixture dependency handling
- 🔹 **Custom Hooks**: pytest_configure, pytest_collection_modifyitems support
- 🔹 **Plugin Detection**: Automatic pytest plugin discovery and analysis
- 🔹 **Enhanced Logging**: Framework-specific loggers with comprehensive support

📖 See [MULTI_FRAMEWORK_SUPPORT.md](docs/frameworks/MULTI_FRAMEWORK_SUPPORT.md) for complete details

### 🔹 9. **Execution Intelligence Engine** 🆕
Framework-agnostic log analyzer that intelligently classifies test failures:

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Raw Logs          │         │   Intelligence   │         │   Classification    │
│  (All Frameworks)   │────────▶│   Engine         │────────▶│   + CI Actions      │
│                     │         │                  │         │                     │
│  • JUnit XML        │         │  • Extract       │         │  • Product Defect   │
│  • pytest output    │         │  • Normalize     │         │  • Locator Issue    │
│  • Robot logs       │         │  • Classify      │         │  • Environment      │
│  • App logs         │         │  • Resolve code  │         │  • Flaky Test       │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

**Features:**
- 🎯 **Intelligent Classification** - 5 failure types: Product Defect, Automation Issue, Locator Issue, Environment, Flaky
- 🔧 **Works Without AI** - Deterministic, explainable, rule-based classification (AI optional for enhancement)
- 📊 **Dual Log Support** - Analyze automation logs + application logs together
- 🔍 **Code Resolution** - Pinpoints exact test file/line causing automation failures
- 🚦 **CI/CD Integration** - Fail builds only on product defects, ignore flaky/env issues
- 📈 **Confidence Scoring** - Provides confidence levels for each classification
- 🌐 **Framework-Agnostic** - Supports all 13 frameworks with unified interface

**Quick Usage:**
```bash
# Analyze single test log
crossbridge analyze logs --log-file test_output.log --test-name test_login --framework pytest

# Analyze with application logs for correlation
crossbridge analyze-logs --framework selenium --logs-automation target/surefire-reports --logs-application app/logs/

# Batch analyze directory
crossbridge analyze directory --log-dir ./test-output --pattern "*.log"
```

**Failure Classification Categories:**
1. **PRODUCT_DEFECT** 🐛 - Real bugs in application code → Fail CI/CD
2. **AUTOMATION_ISSUE** 🔧 - Test code problems (syntax, imports, setup)
3. **LOCATOR_ISSUE** 🎯 - UI element selectors broken/changed
4. **ENVIRONMENT_ISSUE** 🌐 - Infrastructure failures (network, DB, timeouts)
5. **FLAKY_TEST** 🔀 - Intermittent failures, timing issues

**Use Cases:**
1. **Automated Triage** - Classify 100s of failures in seconds
2. **Smart CI/CD** - Fail pipeline only for real product defects
3. **Team Routing** - Send automation issues to QA, product bugs to dev
4. **Failure Analysis** - "Find similar timeout failures"
5. **Root Cause** - Trace failure to exact test file and line number

📖 See [EXECUTION_INTELLIGENCE.md](docs/EXECUTION_INTELLIGENCE.md) for complete documentation

### 🔹 10. **Application Log Integration** 🆕
**Released: January 30, 2026**

Universal JSON log adapter for correlating test failures with application behavior:

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Application Logs  │         │   JSON Adapter   │         │  Test Correlation   │
│  (JSON/ELK/K8s)     │────────▶│  + Sampling      │────────▶│  + Root Cause       │
│                     │         │  + Signal Extract│         │  + Context Analysis │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

**Features:**
- 🔍 **Universal JSON Support** - ELK, Fluentd, Kubernetes, CloudWatch, custom formats
- 🎯 **Auto Signal Extraction** - Errors, timeouts, retries, circuit breakers
- 🔗 **Multi-Strategy Correlation** - Trace ID (1.0), execution ID (0.9), timestamp (0.7), service (0.5)
- 📊 **Intelligent Sampling** - Level-based (DEBUG: 1%, ERROR: 100%), rate limiting, adaptive
- 💾 **PostgreSQL Storage** - JSONB for flexible querying, batch inserts, indexed fields
- 🎭 **Framework Compatible** - Works with all 13 CrossBridge frameworks
- 🔄 **Retry & Circuit Breaker** - Resilient error handling and storage protection
- 📈 **Health Monitoring** - Integrated with CrossBridge health status framework

**Quick Start:**
```yaml
# crossbridge.yml
execution:
  log_ingestion:
    enabled: true
    adapters:
      json:
        enabled: true
    sampling:
      rates:
        debug: 0.01    # 1% of DEBUG logs
        error: 1.0     # 100% of ERROR logs
    correlation:
      strategies: [trace_id, execution_id, timestamp, service]
```

**Example Usage:**
```python
from core.execution.intelligence.log_adapters import get_registry
from core.execution.intelligence.log_adapters.correlation import LogCorrelator

# Parse application logs
registry = get_registry()
adapter = registry.get_adapter('application.log')
app_logs = [adapter.parse(line) for line in log_file]

# Correlate with test failures
correlator = LogCorrelator()
result = correlator.correlate(test_event, app_logs)

print(f"Found {len(result.correlated_logs)} related logs")
print(f"Correlation confidence: {result.correlation_confidence}")
```

**Supported Log Formats:**
- Standard JSON logs
- ELK/Elasticsearch (@timestamp, severity)
- Fluentd/FluentBit (time, msg)
- Kubernetes container logs (JSON)
- CloudWatch logs (JSON)
- Custom JSON formats (configurable field mapping)

**Use Cases:**
- Correlate test failures with application errors
- Trace distributed transaction failures
- Identify root causes in microservices
- Detect timeout and retry patterns
- Analyze circuit breaker events
- Performance bottleneck detection

📖 See [JSON_LOG_ADAPTER.md](docs/log_analysis/JSON_LOG_ADAPTER.md) for complete documentation

### 🔹 11. **Semantic Search & Test Intelligence**
Unified system combining test normalization, AST extraction, and AI-powered semantic search:

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Test Files        │         │  Normalization   │         │  UnifiedTestMemory  │
│  (All Frameworks)   │────────▶│  + AST Extract   │────────▶│  + Structural Sigs  │
└─────────────────────┘         └──────────────────┘         └──────────┬──────────┘
                                                                          │
                                                                          ▼
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Similar Tests     │         │   Embedding API  │         │   Text Builder      │
│  + Recommendations  │◀────────│  Vector Search   │◀────────│  (Domain Context)   │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

**Features:**
- 🔄 **Universal Normalization** - Convert all frameworks to UnifiedTestMemory format
- 🌳 **AST Extraction** - Structural signals (imports, functions, assertions, API calls, UI interactions)
- 🔍 **Natural Language Search** - Find tests using plain English queries
- 🧠 **Multi-Provider Support** - OpenAI, Anthropic (Voyage AI), or local sentence-transformers
- 📊 **Vector Database** - PostgreSQL + pgvector for production-scale similarity search
- 🔄 **Versioned Embeddings** - Reindex with new models without losing old data
- 🚀 **Auto-Enable in Migration** - Automatically enabled during framework migration

**Quick Usage**:
```bash
# Index your tests (auto-normalizes + extracts AST)
crossbridge semantic index -f pytest -p ./tests

# Search using natural language
crossbridge semantic search "login timeout error"

# Find similar tests
crossbridge semantic similar test_user_login

# View statistics
crossbridge semantic stats
```

**Use Cases:**
- Find similar test failures to identify patterns
- Discover tests affected by code changes
- Map legacy tests to modern equivalents during migration
- Recommend new tests based on existing patterns
- Detect duplicate or redundant test coverage
- Analyze structural patterns across frameworks

**Configuration:**
All settings in one place under `runtime.semantic_search` in [crossbridge.yml](crossbridge.yml)

📖 See [SEMANTIC_SEARCH.md](docs/ai/SEMANTIC_SEARCH.md) and [Quick Start](docs/ai/SEMANTIC_SEARCH_QUICK_START.md)

### 🔹 12. **Unified Intelligence Configuration**
Centralize all framework-specific intelligence rules in one place:

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   crossbridge.yml   │         │   Rule Engine    │         │   All Frameworks    │
│                     │         │                  │         │                     │
│  intelligence:      │────────▶│  • Auto-detect   │────────▶│  • Selenium ✓      │
│    rules:           │         │  • Auto-load     │         │  • Pytest ✓        │
│      selenium: []   │         │  • Fallback      │         │  • Robot ✓         │
│      pytest: []     │         │  • Validation    │         │  • Playwright ✓    │
│      robot: []      │         │                  │         │  • +9 more ✓       │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

**Benefits:**
- 📦 **Single Source of Truth** - All 13 frameworks in one crossbridge.yml file
- 🔄 **Automatic Loading** - Framework detected, rules loaded automatically
- 🎯 **Priority System** - crossbridge.yml → framework.yaml → generic.yaml
- ⚡ **Zero Migration** - Existing YAML files work as templates/fallback
- 🧪 **Fully Tested** - 53 comprehensive tests covering all scenarios

**Quick Start:**
```yaml
# crossbridge.yml
crossbridge:
  intelligence:
    rules:
      selenium:
        - id: SEL001
          match_any: ["NoSuchElementException", "element not found"]
          failure_type: LOCATOR_ISSUE
          confidence: 0.9
      
      pytest:
        - id: PYT001
          match_any: ["AssertionError", "assert False"]
          failure_type: ASSERTION_FAILURE
          confidence: 0.95
      
      robot:
        - id: ROB001
          match_any: ["Element not found", "keyword failed"]
          failure_type: LOCATOR_ISSUE
          confidence: 0.85
```

**Supported Frameworks (13 Total):**
✅ Selenium • Pytest • Robot • Playwright • Cypress • RestAssured • Cucumber • Behave • JUnit • TestNG • SpecFlow • NUnit • Generic

📖 **Complete Guide**: [UNIFIED_CONFIGURATION_GUIDE.md](docs/configuration/UNIFIED_CONFIGURATION_GUIDE.md)

### 🔹 13. **Production Hardening & Runtime Protection**
Enterprise-grade production runtime features for resilient test execution:

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Test Execution    │         │   Runtime Layer  │         │   Protected Ops     │
│                     │         │                  │         │                     │
│  • AI generation    │────────▶│  • Rate limiting │────────▶│  • Fair throttling  │
│  • API calls        │         │  • Retry logic   │         │  • Auto-recovery    │
│  • Embeddings       │         │  • Health checks │         │  • Proactive detect │
│  • Database ops     │         │  • YAML config   │         │  • No manual retry  │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

**Features:**
- 🚦 **Rate Limiting** - Token bucket algorithm, per-user/org fair throttling
- 🔄 **Exponential Backoff Retry** - Intelligent retry with jitter for transient failures
- 🏥 **Health Checks** - Provider monitoring for AI, embeddings, database
- ⚙️ **YAML Configuration** - All settings in crossbridge.yml, no code changes
- 🪵 **Structured Logging** - Integrated with CrossBridgeLogger
- ⚡ **Performance** - <0.1ms per rate limit check, <1ms retry overhead
- 🧵 **Thread-Safe** - Production-ready concurrency handling

**Quick Enable**:
```yaml
# crossbridge.yml
runtime:
  rate_limiting:
    enabled: true
    defaults:
      search: {capacity: 30, window_seconds: 60}
      embed: {capacity: 60, window_seconds: 60}
  
  retry:
    enabled: true
    default_policy:
      max_attempts: 3
      base_delay: 0.5
      jitter: true
  
  health_checks:
    enabled: true
    interval: 30
    providers:
      ai_provider: {enabled: true}
      database: {enabled: true}
```

**Usage Example**:
```python
from core.runtime import retry_with_backoff, check_rate_limit, get_health_registry

# Automatic retry with exponential backoff
result = retry_with_backoff(lambda: ai_provider.generate(prompt))

# Rate limiting per user
if not check_rate_limit(key=f"user:{user_id}", operation="embed"):
    raise RateLimitExceeded("Too many requests")

# Health checks
registry = get_health_registry()
if not registry.is_healthy():
    logger.warning("Some providers degraded")
```

📖 **Learn More**: 
- [Production Hardening Guide](docs/hardening/PRODUCTION_HARDENING.md)
- [Quick Reference](docs/hardening/PRODUCTION_HARDENING_QUICK_REF.md)
- [All Gaps Fixed Summary](docs/hardening/PRODUCTION_HARDENING_ALL_GAPS_FIXED.md)
- [Module Documentation](core/runtime/README.md)

### 🔹 14. **Performance Profiling & Observability**
Passive, non-invasive performance profiling for all test executions:

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   Test Execution    │         │   Profiling      │         │   Observability     │
│                     │         │   (Background)   │         │                     │
│  • Test lifecycle   │────────▶│  • Event capture │────────▶│  • Grafana          │
│  • WebDriver calls  │         │  • Queue batch   │         │  • PostgreSQL       │
│  • HTTP requests    │         │  • Async write   │         │  • InfluxDB         │
│  • Setup/teardown   │         │  • <1% overhead  │         │  • Dashboards       │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

**Features:**
- 📊 **Test execution timing** - duration, setup, teardown
- 🌐 **HTTP request profiling** - API calls, status codes, latency
- 🖱️ **WebDriver command tracking** - clicks, navigations, waits
- 📈 **Performance regression detection** - historical trend analysis
- 🎯 **Framework-agnostic** - works with all 12 supported frameworks
- 💾 **Multiple storage backends** - PostgreSQL, InfluxDB, Local files
- 📉 **Grafana dashboards** - 12 pre-built panels + alerting
- 🚫 **Disabled by default** - zero impact unless enabled
- ⚡ **Non-blocking async** - never slows down test execution
- 🛡️ **Exception-safe** - profiling failures never fail tests

**Quick Enable**:
```yaml
# crossbridge.yml
crossbridge:
  profiling:
    enabled: true
    storage:
      backend: postgres
      postgres:
        host: 10.60.67.247
        port: 5432
        database: cbridge-unit-test-db
```

**Supported Frameworks** (All features: Profiling, Intelligence, Flaky Detection, Impact Analysis, Embeddings):
- ✅ **Python**: pytest, Robot Framework, Selenium Python, requests
- ✅ **Java**: TestNG, JUnit, RestAssured, Selenium Java
- ✅ **.NET/C#**: NUnit, SpecFlow, Selenium .NET (with or without test framework)
- ✅ **JavaScript**: Cypress, Playwright

📖 **Learn More**: [Performance Profiling Documentation](docs/profiling/README.md)

### 🔹 15. **AI Transformation Validation** 🆕
Never auto-merge AI-generated code again! Comprehensive validation system with confidence scoring, human review workflows, and audit trails:

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   AI Generation     │         │   Validation     │         │   Review & Apply    │
│                     │         │   System         │         │                     │
│  • Generate test    │────────▶│  • Confidence    │────────▶│  • Human review     │
│  • Modify code      │  output │  • Diff analysis │ score   │  • Approve/Reject   │
│  • Refactor         │         │  • Syntax check  │         │  • Apply to files   │
│  • Auto-complete    │         │  • Multi-signal  │         │  • Rollback ready   │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

**Key Principles:**
- 🚫 **Never Auto-Merge** - All AI output requires validation
- 🎯 **Numeric Confidence Scoring** - Multi-signal algorithm (0.0-1.0)
- 📸 **Full Snapshots** - Complete before/after state capture
- 👤 **Mandatory Review** - Low confidence (<0.8) requires human approval
- ↶ **Idempotent Rollback** - Safe, repeatable revert operations
- 📋 **Complete Audit Trail** - Track model, prompt, reviewer, timestamps

**Confidence Scoring Signals:**
| Signal | Impact | Description |
|--------|--------|-------------|
| Model Confidence | Base multiplier | AI model's self-reported confidence |
| Diff Size | -0.1 to -0.3 penalty | Lines changed (>100/-0.3, >50/-0.2, >20/-0.1) |
| Rule Violations | -0.1 per violation | Linting/style issues (max -0.3) |
| Similarity | -0.1 to -0.2 penalty | Cosine similarity to existing code |
| Historical Rate | Multiplier | Previous approval rate for similar changes |
| Syntax Valid | -0.4 penalty | Code parses successfully |
| Coverage | -0.2 penalty | Test coverage maintained |

**Confidence Levels:**
- 🟢 **HIGH (≥0.8)**: Optional review, can auto-apply
- 🟡 **MEDIUM (0.5-0.79)**: Requires human review
- 🔴 **LOW (<0.5)**: Requires human review

**Quick Enable:**
```python
from core.ai.transformation_service import AITransformationService
from core.ai.transformation_validation import ConfidenceSignals

# Initialize service
service = AITransformationService()

# Generate transformation with validation
transformation = service.generate(
    operation="generate",
    artifact_type="test",
    artifact_path="tests/test_login.py",
    before_content="",
    after_content=ai_generated_code,
    model="gpt-4",
    prompt="Generate login test",
    signals=ConfidenceSignals(
        model_confidence=0.92,
        diff_size=45,
        syntax_valid=True
    )
)

# Handle based on confidence
if transformation.requires_review:
    print(f"⚠ Review required: crossbridge ai-transform show {transformation.id}")
else:
    service.apply(transformation.id)
    print(f"✓ Applied automatically (confidence: {transformation.confidence})")
```

**CLI Workflow:**
```bash
# List transformations needing review
$ crossbridge ai-transform list --needs-review

# Review with diff
$ crossbridge ai-transform show ai-abc123 --show-diff

# Approve and apply
$ crossbridge ai-transform approve ai-abc123 \
    --reviewer john@example.com \
    --comments "Looks good" \
    --apply

# Rollback if needed
$ crossbridge ai-transform rollback ai-abc123

# View audit trail
$ crossbridge ai-transform audit ai-abc123

# System statistics
$ crossbridge ai-transform stats
```

**Features:**
- ✓ Multi-signal confidence computation
- ✓ Human review workflow (approve/reject)
- ✓ Unified diff generation
- ✓ Before/after snapshots
- ✓ Idempotent rollback
- ✓ Complete audit trail
- ✓ CLI commands (8 commands)
- ✓ JSON persistence
- ✓ Custom apply/rollback functions
- ✓ Analytics and statistics

📖 **Learn More**: 
- [AI Transformation Validation Guide](docs/ai/AI_TRANSFORMATION_VALIDATION.md)
- [Quick Start](docs/ai/QUICK_START_AI_TRANSFORM.md)
- [CLI Reference](docs/ai/AI_TRANSFORMATION_VALIDATION.md#cli-reference)

### 🔹 16. **Enhanced Health Monitoring & Observability** 🆕
Production-grade health monitoring with sub-component tracking, SLI/SLO support, and Prometheus integration:

```
┌─────────────────────┐         ┌──────────────────┐         ┌─────────────────────┐
│   CrossBridge       │         │   Health Monitor │         │   Observability     │
│   Components        │         │   (v2 API)       │         │                     │
│  • Database         │────────▶│  • Component     │────────▶│  • Prometheus       │
│  • AI Service       │  status │    Health        │ metrics │  • Grafana          │
│  • Embeddings       │         │  • SLI/SLO       │         │  • Alertmanager     │
│  • Sidecar          │         │  • History       │         │  • /health APIs     │
└─────────────────────┘         └──────────────────┘         └─────────────────────┘
```

**Key Features:**
- 🏥 **Versioned Health APIs** - v1 (simple) and v2 (detailed) endpoints with full backward compatibility
- 🔍 **Sub-Component Tracking** - Monitor database, AI service, embeddings, sidecar, execution engine individually
- 📊 **SLI/SLO Support** - Service Level Indicators with configurable targets (uptime ≥99%, latency ≤500ms, error rate ≤1%)
- 🔄 **Historical Health Data** - Track component health trends with 1-hour retention
- 🚨 **Prometheus Integration** - 20+ pre-configured alert rules for production monitoring
- ⚡ **Zero Impact** - Non-blocking health checks, never affect test execution
- 🎯 **Kubernetes-Ready** - `/ready`, `/live` endpoints for k8s liveness/readiness probes

**Health Endpoints:**

| Endpoint | Purpose | Response Time | Use Case |
|----------|---------|---------------|----------|
| `GET /health` | Overall system status | <10ms | Quick status check |
| `GET /health/v1` | Simple health (backward compatible) | <10ms | Legacy integrations |
| `GET /health/v2` | Detailed component health + SLI | <50ms | Production monitoring |
| `GET /ready` | Readiness check (Kubernetes) | <10ms | K8s readiness probe |
| `GET /live` | Liveness check (Kubernetes) | <5ms | K8s liveness probe |
| `GET /metrics` | Prometheus metrics export | <100ms | Metrics scraping |
| `GET /sli` | Service Level Indicators | <20ms | SLO monitoring |

**Health States:**
- 🟢 **HEALTHY**: All systems operational (SLI targets met)
- 🟡 **DEGRADED**: Partial functionality (some SLI targets missed, non-critical components down)
- 🔴 **UNHEALTHY**: Critical failure (database down, multiple SLI targets missed)

**Example v2 Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-31T10:30:00Z",
  "uptime_seconds": 86400,
  "version": "0.2.0",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 15,
      "details": {"connections": 5, "pool_size": 20}
    },
    "ai_service": {
      "status": "healthy",
      "response_time_ms": 245,
      "details": {"model": "gpt-4", "requests_today": 1523}
    },
    "embeddings": {
      "status": "healthy",
      "response_time_ms": 120,
      "details": {"vector_count": 15420, "index_size_mb": 234}
    }
  },
  "sli": {
    "uptime_percent": 99.95,
    "avg_latency_ms": 127,
    "error_rate_percent": 0.12,
    "targets_met": true
  }
}
```

**Prometheus Alerts (20+ Rules):**
- 🚨 CrossBridge Unhealthy (critical)
- ⚠️ CrossBridge Degraded (warning)
- 🔴 Component Down (critical: database, ai_service)
- 🟡 Component Degraded (warning: embeddings, sidecar)
- ⏱️ High Latency (>500ms for 5m)
- 💥 High Error Rate (>1% for 5m)
- 🎯 SLO Violation (uptime <99%, latency >500ms, errors >1%)
- 🗄️ Database Issues (connection failures, slow queries)
- 💾 Memory Pressure (>500MB for 5m)

**Quick Setup:**
```yaml
# crossbridge.yml
observability:
  health:
    enabled: true
    version: 2  # Use v2 API with SLI/SLO
    port: 9090  # Health endpoint port
    sli_targets:
      uptime_percent: 99.0    # 99% uptime SLO
      latency_ms: 500         # 500ms latency SLO
      error_rate_percent: 1.0 # 1% error rate SLO
  
  prometheus:
    enabled: true
    scrape_interval: 15s
    alert_rules: monitoring/prometheus/crossbridge-alerts.yml
```

**CI/CD Integration:**
```bash
# Wait for health before running tests
curl -f http://localhost:9090/health || exit 1

# Check readiness (Kubernetes)
curl -f http://localhost:9090/ready || exit 1

# Verify SLI targets met
curl http://localhost:9090/sli | jq '.targets_met' | grep true
```

**Alertmanager Integration:**
```yaml
# monitoring/prometheus/alertmanager.yml
route:
  receiver: crossbridge-team
  routes:
    - match:
        severity: critical
      receiver: pagerduty
    - match:
        severity: warning
      receiver: slack

receivers:
  - name: crossbridge-team
    email_configs:
      - to: team@example.com
  - name: pagerduty
    pagerduty_configs:
      - service_key: <YOUR_KEY>
  - name: slack
    slack_configs:
      - api_url: <WEBHOOK_URL>
        channel: '#alerts'
```

**Grafana Dashboards:**
- 📊 **CrossBridge Health Overview** - System-wide health status and trends
- 🔍 **Component Health Details** - Per-component metrics and history
- 🎯 **SLI/SLO Dashboard** - Track service level targets and violations
- 🚨 **Alert Dashboard** - Active alerts and alert history

📖 **Complete Documentation**: 
- [Enhanced Health Monitoring Guide](docs/observability/ENHANCED_HEALTH_MONITORING_GUIDE.md) (comprehensive 785-line guide)
- [Health Unhealthy Runbook](docs/runbooks/health-unhealthy.md) (troubleshooting)
- [Prometheus Configuration](monitoring/prometheus/)
- [Validation Report](docs/implementation/HEALTH_MONITORING_VALIDATION_REPORT.md)

---

## 🎯 Who Should Use CrossBridge AI

CrossBridge AI is ideal for:

✔ **QA Engineers** modernizing legacy Selenium test suites  
✔ **Test Architects** planning framework migrations and reducing technical debt  
✔ **DevOps Teams** optimizing CI/CD test validation pipelines  
✔ **Engineering Leaders** accelerating release cycles and improving quality  
✔ **QA Managers** seeking data-driven testing insights  
✔ **Organizations** embracing modern test ecosystems and AI-driven quality

### You Should Use CrossBridge If You:
- ✅ Have 100+ tests needing modernization
- ✅ Want intelligence on existing tests without migration
- ✅ Need automated failure triage and classification
- ✅ Need to migrate before losing team knowledge
- ✅ Require audit trails and reproducible transformations
- ✅ Value open-source and extensibility

### This May Not Be For You If:
- ❌ You have < 50 tests (manual rewrite may be faster)
- ❌ Your tests are already modern (Playwright/Cypress native)
- ❌ Your framework isn't supported yet (contributions welcome!)

---

## 💡 Why It Matters

Traditional test automation modernization is:
- ❌ **Expensive** — months of engineering effort
- ❌ **Risky** — potential loss of test coverage  
- ❌ **Slow** — manual rewrites delay delivery
- ❌ **Inconsistent** — varying quality across migrated tests

**CrossBridge AI** makes it:
- ✅ **Faster** — automated transformation in hours
- ✅ **Data-driven** — intelligence-based decisions
- ✅ **Scalable** — handles hundreds of tests
- ✅ **AI-enhanced** — smart insights and recommendations
- ✅ **Intelligent** — automated failure triage saves hours/week

**Result:** Teams get better maintainability and measurable ROI in weeks, not months.

---

## 🐳 Docker Quick Start

**Run CrossBridge as a Docker container for immediate use:**

### Pull and Run

```bash
# Pull the image
docker pull crossbridge/crossbridge:1.0.0

# Run a smoke test
docker run --rm \
  -v $(pwd)/test-repo:/workspace:ro \
  -v $(pwd)/crossbridge-data/logs:/data/logs \
  -v $(pwd)/crossbridge-data/reports:/data/reports \
  crossbridge/crossbridge:1.0.0 exec run \
  --framework pytest \
  --strategy smoke
```

### Using docker-compose

```bash
# Copy environment file
cp .env.docker.example .env

# Edit .env to customize

# Run tests
docker-compose up
```

### CI/CD Integration

**GitHub Actions:**
```yaml
- name: Run CrossBridge
  run: |
    docker run --rm \
      -v $(pwd):/workspace:ro \
      -v $(pwd)/crossbridge-data/logs:/data/logs \
      crossbridge/crossbridge:1.0.0 exec run \
      --framework pytest \
      --strategy impacted \
      --ci
```

### Available Tags
- `1.0.0` - Specific version (recommended for production)
- `1.0` - Minor version (gets patch updates)
- `1` - Major version (latest in v1.x)
- `latest` - Latest release

**Exit Codes** (CI/CD friendly):
- `0` - All tests passed ✅
- `1` - Test failures ❌
- `2` - Execution error ⚠️
- `3` - Configuration error 🔧

📖 **Complete Guide**: [Docker Guide](docs/DOCKER_GUIDE.md)

---

## 🎛️ CLI Commands

CrossBridge provides comprehensive CLI commands for all major features:

### 📊 Execution Intelligence & Log Analysis
```bash
# Analyze single test log
crossbridge analyze logs --log-file test_output.log --test-name test_login --framework pytest

# Analyze with application logs
crossbridge analyze-logs --framework selenium --logs-automation target/surefire-reports --logs-application app/logs/

# Batch analyze directory
crossbridge analyze directory --log-dir ./test-output --pattern "*.log"
```

### 🔄 Test Transformation & Migration
```bash
# Transform Selenium to Playwright
crossbridge transform --from selenium --to playwright --input tests/selenium/ --output tests/playwright/

# BDD transformation
crossbridge transform --from cucumber --to robot --input features/ --output robot/
```

### 🔍 Semantic Search & Intelligence
```bash
# Index tests for semantic search
crossbridge semantic index -f pytest -p ./tests

# Search using natural language
crossbridge semantic search "login timeout error"

# Find similar tests
crossbridge semantic similar test_user_login
```

### 🐛 Flaky Test Detection
```bash
# Detect flaky tests
crossbridge flaky detect --framework pytest --test-results ./results/

# Analyze flaky patterns
crossbridge flaky analyze --test-id test_checkout
```

### 🤖 AI Transformation Validation
```bash
# Generate with validation
crossbridge ai-transform generate --prompt "Create login test" --framework playwright

# Review pending transformations
crossbridge ai-transform review --id abc123

# Apply approved changes
crossbridge ai-transform apply --id abc123
```

### 📈 Coverage & Analysis
```bash
# Analyze test coverage
crossbridge coverage analyze --source-dir src/ --test-dir tests/

# Generate coverage report
crossbridge coverage report --format html
```

### ⚙️ Configuration & Setup
```bash
# Validate configuration
crossbridge config validate

# Initialize workspace
crossbridge init --framework pytest

# Check system status
crossbridge status
```

📖 **Full CLI Reference**: Run `crossbridge --help` or see [CLI Documentation](cli/README.md)

---

## 🚀 Quick Start

### 📥 Installation

```bash
# Clone the repository
git clone https://github.com/crossstack-ai/crossbridge.git
cd crossbridge

# Install dependencies
pip install -r requirements.txt
```

### ⚙️ Configuration

CrossBridge uses a single configuration file for all features:

**📄 Configuration File:**
- **`crossbridge.yml`** - Main configuration file with all options

**🔧 Setup:**
```bash
# Edit crossbridge.yml with your settings
nano crossbridge.yml

# Use environment variables for sensitive data
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export OPENAI_API_KEY="sk-..."
export CONFLUENCE_TOKEN="your-token"
```

**💡 Best Practice:** Use environment variables for secrets:
```yaml
database:
  url: "${DATABASE_URL}"  # Reads from environment
  
api_change:
  intelligence:
    ai:
      api_key: ${OPENAI_API_KEY}  # Secure!
```

### 🎯 Option 1: NO MIGRATION MODE (Recommended!)

Work with existing tests — **zero code changes required**.

**Step 1: Configure Environment**
```bash
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_DB_HOST=localhost
export CROSSBRIDGE_APPLICATION_VERSION=v2.0.0
```

**Step 2: Add Framework Listener/Plugin**

**For Selenium Java (TestNG):**
```xml
<!-- testng.xml -->
<listeners>
  <listener class-name="com.crossbridge.CrossBridgeListener"/>
</listeners>
```

**For Python pytest:**
```python
# conftest.py
pytest_plugins = ["crossbridge.pytest_plugin"]
```

**For Cypress:**
```javascript
// cypress.config.js
const crossbridge = require('crossbridge-cypress');
crossbridge.register(on, { enabled: true });
```

**Step 3: Run Tests Normally**
```bash
# Run your tests as you normally would
# CrossBridge observes and provides intelligence automatically
```

**That's it!** View insights in Grafana dashboards or via CLI.

📖 **Learn More**: [NO_MIGRATION_FRAMEWORK_SUPPORT.md](docs/sidecar/NO_MIGRATION_IMPLEMENTATION_COMPLETE.md)

### 🔄 Option 2: FULL MIGRATION MODE (Auto-Configured!)

Transform legacy tests to modern frameworks with **automatic configuration**:

```bash
# Start the interactive CLI
python -m cli.app

# Follow the prompts:
# 1. Select "Migration + Transformation"
# 2. Choose source framework (e.g., Selenium Java BDD)
# 3. Connect repository (GitHub/Bitbucket/Azure DevOps)
# 4. Configure paths
# 5. Run migration ✨
```

**Output**: Transformed tests + **Auto-configured CrossBridge features**:

#### ✅ Automatically Configured Features

When you migrate with CrossBridge, **all recent features are automatically set up**:

**Performance Profiling**:
- ✅ Framework-specific hooks (pytest conftest, Robot listener, TestNG listener, etc.)
- ✅ PostgreSQL storage configuration
- ✅ Grafana dashboard templates
- ✅ Environment variable templates

**Continuous Intelligence**:
- ✅ Database schema for test results
- ✅ Flaky test detection enabled
- ✅ Embedding/semantic search configured
- ✅ Test coverage tracking

**Configuration Files Created**:
- ✅ `crossbridge.yml` - Complete configuration with all features
- ✅ `.env.template` - Environment variables for database, AI, etc.
- ✅ `SETUP.md` - Step-by-step setup instructions
- ✅ Framework hooks (conftest.py, listeners, plugins)
- ✅ Database configuration
- ✅ CI/CD templates

#### 📋 What You Get

**For Robot Framework Migration**:
```
✅ tests/robot/libraries/crossbridge_listener.py  # Performance profiling + intelligence
✅ crossbridge.yml                                 # All features configured
✅ .env.template                                   # Database + AI settings
✅ SETUP.md                                        # Quick start guide
✅ robot.yaml                                      # Framework configuration
✅ requirements.txt                                # Dependencies with profiling
```

**For pytest/Playwright Migration**:
```
✅ tests/conftest.py                               # Profiling + intelligence hooks
✅ crossbridge.yml                                 # All features configured
✅ .env.template                                   # Database + AI settings
✅ SETUP.md                                        # Quick start guide
✅ pytest.ini                                      # Framework configuration
```

**For Java/TestNG Migration**:
```
✅ src/test/java/com/crossbridge/profiling/CrossBridgeProfilingListener.java
✅ testng.xml                                      # Listener configured
✅ crossbridge.yml                                 # All features configured
✅ .env.template                                   # Database + AI settings
✅ SETUP.md                                        # Environment setup
```

**For .NET/SpecFlow Migration**:
```
✅ CrossBridge.Profiling/CrossBridgeProfilingHook.cs  # NUnit/SpecFlow hook
✅ crossbridge.yml                                     # All features configured
✅ .env.template                                       # Database + AI settings
✅ SETUP.md                                            # Environment setup
✅ AssemblyInfo.cs                                     # Profiling attribute configured
```

> **Note**: .NET Selenium works with or without NUnit/SpecFlow. The profiling hook uses direct PostgreSQL connection via Npgsql.

#### 🚀 Ready to Use

After migration, simply:

```bash
# 1. Configure database
cp .env.template .env
# Edit .env with your database credentials

# 2. Enable profiling
export CROSSBRIDGE_PROFILING=true

# 3. Run tests - profiling and intelligence work automatically!
robot tests/  # or pytest tests/  # or mvn test
```

**No manual configuration needed!** All hooks and listeners are pre-configured.

📖 **Learn More**: 
- [AI Transformation Validation](docs/ai/AI_TRANSFORMATION_VALIDATION.md)
- [Performance Profiling Setup](docs/profiling/QUICK_REFERENCE.md)
- [Framework Integration Guide](docs/profiling/FRAMEWORK_INTEGRATION.md)

---

## 🎛️ Core Features

### 1. Migration Modes

```
Manual Mode         → Creates placeholders with TODOs (fast, requires review)
Enhanced Mode       → Smart extraction with pattern matching (recommended)
Hybrid Mode         → AI-enhanced with human review markers (best quality)
```

**🤖 AI-Powered Enhancement** (Optional):
- Enable OpenAI/Anthropic integration for intelligent transformation
- Supports **step definitions**, **page objects**, and **locators**
- Better Cucumber pattern recognition and Playwright action generation
- **Self-healing locator strategies** - prioritizes data-testid > id > CSS > XPath
- **Locator extraction tracking** - counts and reports all locators extracted from page objects
- **AI metrics & cost analysis** - detailed token usage, cost per file, and transformation statistics
- **Confidence Scoring & Validation** - comprehensive quality checks with automated validation 🆕
- **Human-in-the-Loop Feedback** - review integration with continuous improvement tracking 🆕
- **Rollback & Diff Reporting** - detailed transformation reports for audit trails 🆕
- Natural language documentation and best practice implementations
- Automatic fallback to pattern-based if AI unavailable
- See [`docs/ai/AI_TRANSFORMATION_VALIDATION.md`](docs/ai/AI_TRANSFORMATION_VALIDATION.md) for setup

```python
# Enable AI transformation for all file types
request.use_ai = True
request.ai_config = {
    'provider': 'openai',  # or 'anthropic'
    'api_key': 'sk-...',
    'model': 'gpt-3.5-turbo'  # or 'gpt-4', 'claude-3-sonnet'
}

# AI will transform:
# • Step Definitions: Cucumber → Robot Framework with smart pattern matching
# • Page Objects: Selenium → Playwright with locator extraction (tracked!)
# • Locators: Quality analysis + self-healing recommendations
# • Generates comprehensive AI summary with cost breakdown and metrics
```

**📊 AI Transformation Summary** (displayed after migration):
```
🤖 AI Transformation Statistics:
  ✓ Total Files Transformed: 50
  ✓ Step Definitions: 35
  ✓ Page Objects: 15
  ✓ Standalone Locator Files: 0
  ✓ Locators Extracted from Page Objects: 243  ← NEW!

🛡️  Self-Healing Locator Strategy Applied:  ← NEW!
  ✓ Priority: data-testid > id > CSS > XPath
  ✓ Text-based matching for visible elements
  ✓ Avoided brittle positional XPath selectors
  ✓ Modern Playwright locator best practices

💰 Token Usage & Cost:
  • Total Tokens: 125,430
  • Total Cost: $0.1254
  • Avg Tokens/File: 2,508
  • Avg Cost/File: $0.0025
```

### 2. Transformation Tiers

```
Tier 1: Quick Refresh     → Syntax updates only
Tier 2: Content Validation → Parse + validate structure  
Tier 3: Deep Regeneration → Full AI-powered rewrite
```

### 3. Repository Integration

- **Direct Git Operations**: Read from and write to repositories
- **Branch Management**: Automatic PR/MR creation
- **Batch Commits**: Configurable commit sizes for large migrations
- **Credential Caching**: Secure storage of API tokens

### 4. API Change Intelligence 🆕

**Automatic API change detection and documentation** for OpenAPI/Swagger specifications:

```bash
# Run API diff analysis
crossbridge api-diff run

# With AI-enhanced recommendations
crossbridge api-diff run --ai

# Check if oasdiff is installed
crossbridge api-diff check-deps
```

**Key Features:**
- ✅ **Automatic Change Detection**: Compare OpenAPI specs (file/URL/Git)
- ✅ **Breaking Change Analysis**: Identify backward-incompatible changes
- ✅ **Risk Classification**: Low/Medium/High/Critical risk levels
- ✅ **Test Recommendations**: Rule-based + AI-powered test suggestions
- ✅ **Incremental Documentation**: Auto-generated Markdown change logs
- ✅ **Grafana Dashboards**: 8 panels for API change monitoring
- ✅ **CI/CD Integration**: GitHub Actions, GitLab CI ready
- ✅ **PostgreSQL Storage**: Full change history and analytics

**Configuration Example:**
```yaml
crossbridge:
  api_change:
    enabled: true
    spec_source:
      type: file  # file | url | git
      current: specs/openapi-v2.yaml
      previous: specs/openapi-v1.yaml
    
    intelligence:
      mode: hybrid  # rules | hybrid | ai-only
      ai:
        enabled: false  # Optional AI enhancement
        provider: openai
        model: gpt-4.1-mini
    
    documentation:
      enabled: true
      output_dir: docs/api-changes
```

**Output Example:**
```markdown
## API Changes – 2026-01-29

**Summary:**
- Total Changes: 5
- Breaking Changes: 1  
- High Risk: 2

### ➕ Added
#### `POST /api/v1/backup/jobs`
- Risk: MEDIUM
- Recommended Tests:
  - Create positive test for POST /api/v1/backup/jobs
  - Verify authentication/authorization
  - Test error responses (400, 401, 403, 500)
```

📄 **Documentation**: [API Change Intelligence Spec](docs/implementation/API_CHANGE_INTELLIGENCE_SPEC.md) | [Setup Guide](docs/api-change/API_CHANGE_SETUP_GUIDE.md)

---

### 5. Flaky Test Detection 🎯

**Machine Learning-powered flaky test detection** with comprehensive analytics:

```bash
# Detect flaky tests using ML (Isolation Forest)
crossbridge flaky detect --db-url postgresql://user:pass@host:5432/db

# List flaky tests with severity filtering
crossbridge flaky list --severity critical

# Get detailed report for a specific test
crossbridge flaky report test_user_login

# Export flaky test data
crossbridge flaky export --format json --output flaky_tests.json
```

**Key Features:**
- ✅ **ML-Based Detection**: Isolation Forest algorithm with 200 decision trees
- ✅ **10 Feature Analysis**: Failure rate, pass/fail switching, timing variance, error diversity, retry patterns
- ✅ **Severity Classification**: Critical, High, Medium, Low based on failure rate and confidence
- ✅ **PostgreSQL Persistence**: 3 database tables (test_execution, flaky_test, flaky_test_history)
- ✅ **Grafana Dashboards**: 9 interactive panels for real-time monitoring
- ✅ **CI/CD Integration**: GitHub Actions, GitLab CI, Jenkins, Azure DevOps, CircleCI
- ✅ **External Test IDs**: TestRail, Zephyr, qTest integration

**Grafana Dashboard Panels:**
1. 📊 Flaky Test Summary - Total count with color-coded thresholds
2. 🍩 Flaky Tests by Severity - Donut chart (Critical/High/Medium/Low)
3. 📏 Average Flaky Score - Gauge visualization (0-1 scale)
4. 📈 Flaky Test Trend - 30-day historical trend
5. 📋 Top 10 Flaky Tests - Table with scores and external test IDs
6. 📊 Flaky Tests by Framework - Bar chart (pytest, junit, etc.)
7. 📊 Test Execution Status - Stacked timeseries (Passed/Failed/Skipped)
8. 📊 Confidence Score Distribution - Bar chart grouped by confidence levels
9. 🔍 Recent Test Failures - Table with timestamps and error types

**Database Setup:**
```bash
# Option 1: Using environment variables
export CROSSBRIDGE_DB_URL="postgresql://postgres:admin@10.55.12.99:5432/your-database"
python tests/populate_flaky_test_db.py

# Option 2: Using crossbridge.yml (automatic)
# Configure database in crossbridge.yml:
crossbridge:
  database:
    enabled: true
    host: ${CROSSBRIDGE_DB_HOST:-localhost}
    port: ${CROSSBRIDGE_DB_PORT:-5432}
    database: ${CROSSBRIDGE_DB_NAME:-crossbridge}
    user: ${CROSSBRIDGE_DB_USER:-postgres}
    password: ${CROSSBRIDGE_DB_PASSWORD:-admin}

# Run population script (reads config automatically)
python tests/populate_flaky_test_db.py
```

**Grafana Integration:**
1. Import dashboard: `grafana/flaky_dashboard_fixed.json`
2. Configure PostgreSQL datasource
3. View real-time flaky test analytics

**CI/CD Pipeline Example (GitHub Actions):**
```yaml
- name: Detect Flaky Tests
  run: |
    python scripts/store_test_results.py \
      --format pytest-json \
      --input results.json \
      --db-url ${{ secrets.CROSSBRIDGE_DB_URL }}
    
    crossbridge flaky detect \
      --db-url ${{ secrets.CROSSBRIDGE_DB_URL }} \
      --threshold 0.7 \
      --fail-on-flaky
```

📖 **See [FLAKY_DETECTION_IMPLEMENTATION_SUMMARY.md](docs/flaky-detection/FLAKY_DETECTION_IMPLEMENTATION_SUMMARY.md) and [CI_CD_FLAKY_INTEGRATION.md](docs/ci-cd/CI_CD_FLAKY_INTEGRATION.md)**

### 5. Memory & Embeddings System 🎯 NEW!

**Semantic memory for intelligent test discovery and AI-powered search:**

```bash
# Ingest tests into memory system
crossbridge memory ingest --source discovery.json

# Natural language search
crossbridge search query "tests covering login timeout"

# Find similar tests
crossbridge search similar test_login_valid

# Check memory statistics
crossbridge memory stats
```

**Key Features:**
- ✅ **Semantic Search**: Find tests by intent, not keywords - "timeout handling tests" vs "test_timeout"
- ✅ **Pluggable Embeddings**: OpenAI (text-embedding-3-large/small), local Ollama, HuggingFace
- ✅ **Vector Storage**: PostgreSQL + pgvector (production) or FAISS (local development)
- ✅ **Entity Types**: Tests, scenarios, steps, page objects, failures, assertions, locators
- ✅ **Similarity Detection**: Find duplicates (>0.9), related tests (0.7-0.9), complementary tests (0.5-0.7)
- ✅ **AI Integration**: Memory-augmented prompts for intelligent test generation
- ✅ **Production Ready**: Full embedding pipeline with standardized persistence schema
- ✅ **Regression Testing**: Comprehensive similarity regression test suite

**What Gets Stored:**
| Entity Type | Example | Use Case |
|-------------|---------|----------|
| `test` | `LoginTest.testValidLogin` | Find tests by behavior/intent |
| `scenario` | `Scenario: Valid Login` | Search BDD scenarios |
| `step` | `When user enters valid credentials` | Find step definitions |
| `page` | `LoginPage.login()` | Locate page objects |
| `failure` | `TimeoutException during login` | Pattern matching for failures |

**Semantic Search Examples:**

```bash
# Find timeout-related tests
crossbridge search query "tests covering login timeout" --type test

# Find duplicate tests (>0.9 similarity)
crossbridge search similar test_login_valid --top 10

# Search with framework filter
crossbridge search query "authentication tests" --framework pytest

# Explain top match
crossbridge search query "flaky auth tests" --explain
```

**Configuration (crossbridge.yml):**
```yaml
memory:
  enabled: true
  
  embedding_provider:
    type: openai                        # or 'local', 'huggingface'
    model: text-embedding-3-large       # 3072 dimensions
    api_key: ${OPENAI_API_KEY}
  
  vector_store:
    type: pgvector                      # or 'faiss'
    connection_string: postgresql://...
    dimension: 3072                     # Must match embedding model
  
  auto_ingest_on_discovery: true       # Ingest after test discovery
  update_on_change: true               # Re-embed when tests change
```

**Supported Embedding Providers:**
| Provider | Model | Dimension | Cost | Best For |
|----------|-------|-----------|------|----------|
| OpenAI | text-embedding-3-large | 3072 | $0.13/1M tokens | Production, highest quality |
| OpenAI | text-embedding-3-small | 1536 | $0.02/1M tokens | Fast, cost-effective |
| Ollama | nomic-embed-text | 768 | Free | Private, no API calls |
| HuggingFace | all-MiniLM-L6-v2 | 384 | Free | Air-gapped environments |

**Cost Example (OpenAI):**
- 1,000 tests @ ~100 tokens each = 100K tokens
- **Cost: $0.002 - $0.013** (less than a penny!)

**Use Cases:**
1. **Duplicate Detection**: Find tests with >90% similarity
2. **Test Discovery**: "Find all payment-related tests"
3. **Coverage Gaps**: "Which areas lack timeout handling tests?"
4. **Failure Analysis**: "Find similar timeout failures"
5. **AI Context**: Memory-augmented prompts for intelligent test generation

**Setup:**
```bash
# 1. Install pgvector extension in PostgreSQL
CREATE EXTENSION IF NOT EXISTS vector;

# 2. Run setup script
python scripts/setup_memory_db.py --dimension 3072

# 3. Set API key (if using OpenAI)
export OPENAI_API_KEY=sk-your-key-here

# 4. Ingest tests
crossbridge discover --framework pytest --output discovery.json
crossbridge memory ingest --source discovery.json

# 5. Search!
crossbridge search query "authentication timeout tests"
```

**Programmatic Usage:**
```python
from core.memory import (
    MemoryIngestionPipeline,
    SemanticSearchEngine,
    create_embedding_provider,
    create_vector_store,
)

# Setup
provider = create_embedding_provider('openai', model='text-embedding-3-large')
store = create_vector_store('pgvector', connection_string='postgresql://...', dimension=3072)

# Search
engine = SemanticSearchEngine(provider, store)
results = engine.search("login timeout tests", top_k=10)

for result in results:
    print(f"{result.rank}. {result.record.id} (score: {result.score:.3f})")

# Find duplicates
similar = engine.find_similar("test_login_valid", top_k=5)
duplicates = [r for r in similar if r.score > 0.9]
```

📖 **See [MEMORY_EMBEDDINGS_SYSTEM.md](docs/memory/MEMORY_EMBEDDINGS_SYSTEM.md) and [MEMORY_QUICK_START.md](docs/memory/MEMORY_QUICK_START.md)**

### 6. Impact Analysis

```bash
# Discover which tests use specific page objects
crossbridge impact --page-object LoginPage

# Find tests affected by code changes
crossbridge analyze-impact --changed-files src/pages/HomePage.java
```

### 6. Post-Migration Testing

- **Validation Reports**: Syntax checks, missing imports, undefined keywords
- **Execution Readiness**: Verify tests can run in Robot Framework
- **Documentation**: Auto-generated setup guides per repository

---

## 🏗️ Architecture

### Core Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI / Interactive Menu                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴──────────────┐
        │   Core Orchestrator         │
        │   - Migration Pipeline      │
        │   - Transformation Engine   │
        │   - Validation Framework    │
        └─────────────┬───────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼────┐      ┌────▼─────┐     ┌────▼─────┐
│Adapters│      │Generators│     │Connectors│
│        │      │          │     │          │
│Selenium│      │Robot FW  │     │Git/BB/ADO│
│Pytest  │      │pytest-bdd│     │Local FS  │
│SpecFlow│      │          │     │          │
└────────┘      └──────────┘     └──────────┘
```

### Plugin Architecture

CrossBridge uses a **formal plugin architecture** through Execution Orchestration:

```
┌─────────────────────────────────────────────────────────────────┐
│                      CROSSBRIDGE PLUGIN HOST                     │
│                    (ExecutionOrchestrator)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   Strategy   │───▶│    Plan      │───▶│   Adapter    │     │
│  │  (Decision)  │    │              │    │ (Execution)  │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│   WHAT to run      Framework-Agnostic     HOW to run          │
│                    Boundary Layer                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │  TEST FRAMEWORKS       │
                │  (Unchanged)           │
                ├────────────────────────┤
                │ • pytest               │
                │ • TestNG               │
                │ • Robot Framework      │
                │ • Cypress              │
                │ • Playwright           │
                │ • JUnit                │
                │ • And more...          │
                └────────────────────────┘
```

**Key Principles:**
- 🧩 **Orchestrator = Plugin Host**: Coordinates all plugin interactions
- 🎯 **Strategies = Decision Plugins**: Determine WHAT tests to run
- 🔌 **Adapters = Execution Plugins**: Determine HOW to invoke frameworks
- 🚫 **Non-Invasive**: Frameworks remain unchanged, CLI-level integration
- 🔄 **Extensible**: Third-party plugins via PluginRegistry

See [Plugin Architecture Guide](docs/architecture/PLUGIN_ARCHITECTURE.md) for complete design philosophy.

---

## 📊 Project Maturity & Limitations

### Current Status: **v0.2.0 - Production Ready**

**What Works Well:**
- ✅ Selenium Java + Cucumber → Robot Framework migrations
- ✅ Step definition parsing and transformation
- ✅ Bitbucket/GitHub/Azure DevOps integration
- ✅ Plugin-based execution orchestration
- ✅ 12+ framework adapters (96% average completeness)
- ✅ Sidecar integration for Java and Robot Framework
- ✅ Page object extraction and locator migration
- ✅ Impact analysis and coverage mapping
- ✅ Multi-threaded processing for large repositories
- ✅ **Flaky test detection with ML-based analysis** 🎯 NEW!
- ✅ **PostgreSQL persistence and Grafana dashboards** 🎯 NEW!
- ✅ **CI/CD integration for automated flaky detection** 🎯 NEW!
- ✅ **Memory & Embeddings System with semantic search** 🎯 NEW!
- ✅ **AI-powered test discovery and duplicate detection** 🎯 NEW!
- ✅ **Pluggable embedding providers (OpenAI, Ollama, HuggingFace)** 🎯 NEW!
- ✅ **Semantic memory and embeddings system** 🎯 NEW!
- ✅ **AI-powered semantic search for tests** 🎯 NEW!
- ✅ **Intelligent duplicate detection and similarity analysis** 🎯 NEW!

**Known Limitations:**
- ⚠️ **Parser Coverage**: Complex Java patterns may not parse (fallback generates TODOs)
- ⚠️ **Manual Review Required**: Output needs human validation before production use
- ⚠️ **AI Features**: Optional and require API keys (Azure OpenAI)
- ⚠️ **Error Handling**: Large repos may hit API rate limits
- ⚠️ **Documentation**: Some advanced features lack complete docs
- ⚠️ **Windows Paths**: Primary development on Windows; Unix path handling improving

**Not Yet Supported:**
- ❌ Dynamic locators or runtime-generated selectors
- ❌ Custom Selenium extensions or third-party frameworks
- ❌ Non-English test files (internationalization planned)
- ❌ Parallel test execution during validation

### Production Readiness

| Use Case | Readiness | Recommendation |
|----------|-----------|----------------|
| Personal projects | ✅ Ready | Great for experimentation |
| Internal tools/POCs | 🟡 Use with caution | Review output carefully |
| Production test suites | ❌ Not recommended | Wait for beta/v1.0 or contribute! |
| Enterprise deployments | ❌ Not recommended | Pilot programs only |

**Expected Timeline:**
- **Beta (v0.5)**: Q2 2026 (improved stability, more adapters)
- **v1.0 (Stable)**: Q4 2026 (production-ready, comprehensive testing)

---

## � AI Monetization & Cost Management

CrossBridge provides transparent AI cost tracking to help you optimize your migration budget:

### Cost Transparency Features
- **Real-time cost tracking** - See token usage and costs during transformation
- **Per-file cost breakdown** - Identify expensive files (complex step definitions, large page objects)
- **Model comparison** - Compare costs between GPT-3.5-turbo, GPT-4, Claude, etc.
- **Cost savings calculator** - Shows potential savings with different models
- **Budget-friendly defaults** - Uses GPT-3.5-turbo by default (~15x cheaper than GPT-4)

### Typical Migration Costs

| Project Size | Files | Estimated Tokens | GPT-3.5-turbo | GPT-4 |
|--------------|-------|------------------|---------------|-------|
| Small (50 files) | 50 | ~125K tokens | $0.12 | $1.80 |
| Medium (200 files) | 200 | ~500K tokens | $0.50 | $7.20 |
| Large (500 files) | 500 | ~1.25M tokens | $1.25 | $18.00 |
| Enterprise (2000 files) | 2000 | ~5M tokens | $5.00 | $72.00 |

**💡 Cost Optimization Tips:**
- Use **GPT-3.5-turbo** for initial migrations (93% cost savings vs GPT-4)
- Enable AI only for **complex files** (step definitions, page objects)
- Use **pattern-based transformation** for simple utility files (free!)
- Set **batch limits** to control spending per run
- Review **top cost files** in AI summary to optimize retry strategies

**🎯 Hybrid Approach** (Recommended):
```python
# Use pattern-based for utilities (free)
# Use AI for complex logic (paid)
transformation_mode: "hybrid"

# Result: ~60% cost savings while maintaining quality
```

### AI Summary Cost Breakdown
After each migration, CrossBridge displays:
- **Total cost and token usage**
- **Cost per file type** (step definitions vs page objects vs locators)
- **Top 5 most expensive files** - helps identify optimization opportunities
- **Model comparison** - shows savings with alternative models

Example:
```
💵 Top Cost Files:
  1. DataStoreSteps.robot (Step Definition): $0.0234 (5,430 tokens)
  2. BackUpJobStep.robot (Step Definition): $0.0198 (4,102 tokens)
  3. AddPolicies.robot (Step Definition): $0.0187 (3,988 tokens)

💡 Cost Savings:
  • Using gpt-3.5-turbo: $1.25
  • Same with gpt-4: ~$18.00
  • Savings: ~$16.75 (93% reduction)
```

---
## 🔌 Model Context Protocol (MCP) Integration

CrossBridge is **both an MCP Client and MCP Server**, enabling seamless integration with AI agents and external tools.

### 🖥️ MCP Server: Expose CrossBridge as Tools

CrossBridge exposes its capabilities as MCP tools that AI agents (Claude, GPT-4, etc.) can consume:

**Available Tools:**
- `run_tests` - Execute tests in any project (pytest, junit, robot)
- `analyze_flaky_tests` - Detect flaky tests from execution history
- `migrate_tests` - Convert tests between frameworks
- `analyze_coverage` - Generate coverage reports and impact analysis
- `analyze_impact` - Analyze code changes and recommend affected tests
- `analyze_bdd_features` - Analyze BDD features (Cucumber, Robot BDD, JBehave) ⭐ NEW
- `orchestrate_execution` - Intelligent test execution with strategy selection (smoke, impacted, risk, full) ⭐ NEW
- `semantic_search_tests` - Search tests using natural language queries ⭐ NEW
- `classify_failure` - Classify test failures (product defect, locator issue, environment, flaky) ⭐ NEW
- `sidecar_status` - Get sidecar runtime health and metrics ⭐ NEW
- `get_profiling_report` - Get performance profiling report for test execution ⭐ NEW
- `validate_transformation` - Validate AI-generated code with confidence scoring ⭐ NEW

**Starting the MCP Server:**
```python
from core.ai.mcp.server import MCPServer, MCPServerConfig

# Configure server
config = MCPServerConfig(
    host="localhost",
    port=8080,
    auth_enabled=True,
    api_key="your-api-key"
)

# Start server
server = MCPServer(config)
server.start()

# AI agents can now call CrossBridge tools via MCP!
```

**Example: AI Agent Using CrossBridge**
```json
{
  "tool": "orchestrate_execution",
  "inputs": {
    "project_path": "/path/to/project",
    "framework": "pytest",
    "strategy": "impacted",
    "base_branch": "origin/main"
  }
}
```

**Example: Semantic Search**
```json
{
  "tool": "semantic_search_tests",
  "inputs": {
    "query": "tests covering login timeout handling",
    "framework": "pytest",
    "top_k": 5
  }
}
```

**Example: BDD Analysis**
```json
{
  "tool": "analyze_bdd_features",
  "inputs": {
    "project_path": "/path/to/project",
    "framework": "cucumber-java",
    "features_dir": "src/test/resources/features",
    "step_definitions_dir": "src/test/java"
  }
}
```

### 🔄 MCP Client: Consume External Tools

CrossBridge can connect to external MCP servers (Jira, GitHub, CI/CD) to enhance workflows:

**Supported External Tools:**
- **Jira**: Create issues, search, update
- **GitHub**: Create PRs, get status, merge
- **CI/CD**: Trigger builds, get status

**Using External Tools:**
```python
from core.ai.mcp.client import MCPClient, MCPToolRegistry

# Discover tools from Jira server
registry = MCPToolRegistry(config_path="config/mcp_servers.json")
tools = registry.discover_tools("jira_server")

# Use MCP client to call tool
client = MCPClient(registry)
result = client.call_tool(
    "jira_create_issue",
    inputs={
        "project": "TEST",
        "summary": "Migration failed for LoginTest.java",
        "description": "AI transformation returned empty content",
        "issue_type": "Bug"
    }
)
```

**Configuration (config/mcp_servers.json):**
```json
{
  "servers": {
    "jira_server": {
      "url": "https://jira.example.com",
      "authentication": {
        "type": "bearer",
        "token": "your-jira-token"
      }
    },
    "github_server": {
      "url": "https://api.github.com",
      "authentication": {
        "type": "token",
        "token": "ghp_your-token"
      }
    }
  }
}
```

### 🎯 MCP Use Cases

**1. AI-Driven Workflows:**
```
AI Agent → CrossBridge MCP Server → Run tests → Create Jira issue (MCP Client)
```

**2. Automated Test Intelligence:**
```
Claude detects flaky test → CrossBridge analyzes → GitHub PR created → CI triggered
```

**3. Self-Service Test Migration:**
```
AI Agent → CrossBridge migrate_framework → PR opened → Slack notification
```

### 📚 MCP Documentation

- **[MCP Client Implementation](core/ai/mcp/client.py)** - Connect to external tools
- **[MCP Server Implementation](core/ai/mcp/server.py)** - Expose CrossBridge tools
- **[Unit Tests](tests/unit/core/ai/test_mcp_and_memory.py)** - Comprehensive test coverage

---
## �🛠️ Configuration Example

```yaml
# Example: Selenium Java BDD migration
migration:
  source_framework: selenium_bdd_java
  target_framework: robot_playwright
  
  paths:
    features: "src/test/resources/features"
    step_definitions: "src/main/java/com/example/stepdefinition"
    page_objects: "src/main/java/com/example/pagefactory"
  
  transformation:
    mode: enhanced  # manual | enhanced | hybrid
    tier: 2  # 1 (quick) | 2 (standard) | 3 (deep)
    batch_size: 10
  
  repository:
    type: bitbucket
    workspace: your-workspace
    repo: your-repo
    branch: feature/robot-migration
```

---

---

## 🤝 Contributing

We welcome contributions! This project needs help with:

- 🔧 **Adapters**: Support for new frameworks (Cypress, Katalon, etc.)
- 🐛 **Bug Fixes**: Parser improvements, edge case handling
- 📖 **Documentation**: Tutorials, examples, API docs
- 🧪 **Testing**: Unit tests, integration tests, real-world validations
- 🌍 **Internationalization**: Non-English test support

**See [CONTRIBUTING.md](docs/community/CONTRIBUTING.md)** for guidelines and [CLA.md](docs/community/CLA.md) for contributor license agreement.

### Quick Contribution Guide

```bash
# Fork and clone
git clone https://github.com/yourusername/crossbridge.git

# Create a feature branch
git checkout -b feature/my-adapter

# Make changes and test
pytest tests/

# Submit a pull request
```

---

## 📚 Documentation

### 🚀 Getting Started
- **[Quick Start Guide](docs/QUICKSTART.md)** - Get up and running in 5 minutes
- **[Unified CLI Guide](docs/UNIFIED_CLI.md)** - Complete reference for the crossbridge command
- **[Migration Guide](docs/MIGRATION_GUIDE.md)** - Migrate from bash scripts to unified CLI
- **[Installation](docs/INSTALLATION.md)** - Detailed setup instructions

### 🔧 Core Features
- **[Test Execution](docs/UNIFIED_CLI.md#crossbridge-run)** - Run tests with monitoring
- **[Log Parsing](docs/UNIFIED_CLI.md#crossbridge-log)** - Analyze test results
- **[Intelligence Engine](docs/intelligence/README.md)** - AI-powered failure analysis
- **[Flaky Detection](docs/flaky-detection/README.md)** - Identify unstable tests

### 📖 Advanced Topics
- **[Sidecar Architecture](docs/REMOTE_SIDECAR_README.md)** - Understanding the sidecar
- **[Adapter Development](docs/adapters/README.md)** - Create custom adapters
- **[CI/CD Integration](docs/ci-cd/README.md)** - Jenkins, GitHub Actions, GitLab
- **[API Reference](docs/api/README.md)** - REST API documentation

### 🔌 Integrations
- **[MCP (Model Context Protocol)](docs/mcp/README.md)** - AI agent integration
- **[GitHub Integration](docs/integrations/github.md)** - PR automation
- **[Jira Integration](docs/integrations/jira.md)** - Issue tracking

### 🏗️ Architecture
- **[System Design](docs/architecture/OVERVIEW.md)** - High-level architecture
- **[Data Flow](docs/architecture/DATA_FLOW.md)** - How data moves through the system
- **[Security](docs/architecture/SECURITY.md)** - Security considerations

### 📦 Framework Support
- **[Robot Framework](docs/frameworks/robot.md)** - Robot Framework integration
- **[Pytest](docs/frameworks/pytest.md)** - Pytest integration
- **[Jest](docs/frameworks/jest.md)** - Jest integration
- **[Java/Maven](docs/frameworks/java.md)** - Java testing frameworks
- **[All Frameworks](docs/frameworks/README.md)** - Complete list

---

**📖 [Full Documentation Hub](docs/README.md)** - Complete documentation organized by pillar

### 🚀 Getting Started
- **[5-Minute Quickstart Guide](docs/pillars/getting-started/getting-started.md)** - Installation, setup, and first transformation
- **[Configuration Guide](docs/config/CONFIG.md)** - All configuration options

### 🧱 Core Pillars
- **[Framework Support](docs/pillars/framework-support/framework-support.md)** - 13+ frameworks (Selenium, Cypress, Robot, pytest, Playwright, JUnit, TestNG, and more)
- **[AI Capabilities](docs/pillars/ai-capabilities/ai-capabilities.md)** - Intelligent failure classification, flaky detection, semantic search, smart test selection
- **[Embeddings & Semantics](docs/pillars/embeddings-semantics/embeddings-semantics.md)** - Semantic understanding, duplicate detection, test clustering
- **[Framework Migration](docs/pillars/migration/framework-migration.md)** - AI-powered migration workflows and validation
- **[Observability Stack](docs/pillars/observability/observability.md)** - Sidecar runtime profiling, Grafana dashboards, Prometheus metrics
- **[Plugin Ecosystem](docs/pillars/plugins/plugin-ecosystem.md)** - Custom adapters and extensions
- **[Enterprise Readiness](docs/pillars/enterprise/enterprise-readiness.md)** - CI/CD, Docker, Kubernetes, production deployment

### 📖 Additional Resources
- **[FAQ](docs/pillars/other/faq.md)** - Frequently asked questions
- **[Architecture](docs/pillars/other/architecture.md)** - System architecture overview
- **[Competitive Edge](docs/pillars/other/competitor-edge.md)** - How CrossBridge compares to alternatives
- **[Complete Documentation Index](docs/project/DOCUMENTATION_INDEX.md)** - Legacy documentation index

---

## 🤝 Get Involved