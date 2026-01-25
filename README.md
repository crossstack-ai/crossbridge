# CrossBridge AI

> **AI-Powered Test Automation Modernization & Transformation Platform**  
> Reduce test automation debt, unlock legacy test value, and accelerate delivery with AI-guided modernization.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Development Status](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/crossstack-ai/crossbridge)
[![CrossStack AI](https://img.shields.io/badge/by-CrossStack%20AI-blue)](https://crossstack.ai)

CrossBridge AI is an open-source platform by **CrossStack AI** that helps organizations and teams **modernize, analyze, and optimize test automation** in a framework-agnostic way.

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

### 🔹 3. **AI-Powered Test Intelligence**
Reduce maintenance costs with intelligent insights:

- 🔍 **Flaky test detection** with ML-based analysis
- 📊 **Coverage analysis** across behavioral and functional dimensions
- 🎯 **Test risk insight and prioritization**
- 🔧 **Self-healing locator suggestions**
- 📈 **Impact analysis** linking tests to code changes

### 🔹 4. **Framework-Agnostic Architecture**
Plugin-based ecosystem supports 12+ existing frameworks:

| Framework | Language | Type | Status | Completeness |
|-----------|----------|------|--------|--------------|
| **pytest** | Python | Unit/Integration | ✅ Production | 98% |
| **Selenium Python** | Python | UI Automation | ✅ Stable | 92% |
| **Selenium Java** | Java | UI Automation | ✅ Production | 98% |
| **Selenium .NET** | C# | UI Automation | ✅ Stable | 85% |
| **Cypress** | JavaScript/TS | E2E | ✅ Production | 95% |
| **Robot Framework** | Robot | Keyword-Driven | ✅ Production | 88% |
| **JUnit/TestNG** | Java | Unit/Enterprise | ✅ Production | 98% |
| **NUnit/SpecFlow** | C# / .NET | Unit/BDD | ✅ Stable | 88% |
| **Playwright** | JavaScript/TS/Python | E2E | ✅ Stable | 88% |
| **RestAssured** | Java | API | ✅ Production | 95% |
| **Cucumber/Behave** | Gherkin | BDD | ✅ Stable | 90% |

**Average Completeness: 93%** ✅ (Up from 88%)

**Phase 3 Advanced Features (January 2026):**
- 🔹 **Multi-line String Handler** (Behave): Docstring and text block extraction
- 🔹 **Behave-pytest Bridge**: Hybrid testing with context fixture integration
- 🔹 **DI Container Support** (SpecFlow): Microsoft.Extensions.DependencyInjection integration
- 🔹 **ScenarioContext Handler**: Context state management and pytest conversion
- 🔹 **Table Conversion Handler**: SpecFlow table transformations and TableConverter support
- 🔹 **Component Testing** (Cypress): React and Vue component test detection
- 🔹 **Multi-Config Handler**: Environment-specific Cypress configurations
- 🔹 **Request Filter Chains** (RestAssured): Filter chain extraction and Python conversion
- 🔹 **Enhanced POJO Mapping**: Jackson/Gson annotations and Python dataclass generation
- 🔹 **Enhanced Logging**: Framework-specific loggers with Phase 3 support

**Phase 2 Advanced Features (January 2026):**
- 🔹 **Dependency Injection Support**: Guice, Spring DI extraction for Java
- 🔹 **Reporting Integration**: Allure & ExtentReports integration
- 🔹 **Autouse Fixture Chains**: Complex pytest fixture dependency handling
- 🔹 **Custom Hooks**: pytest_configure, pytest_collection_modifyitems support
- 🔹 **Plugin Detection**: Automatic pytest plugin discovery and analysis
- 🔹 **Step Parameters**: Behave regex group and parameter extraction
- 🔹 **Custom Matchers**: Behave custom step matcher detection
- 🔹 **.NET Version Handler**: .NET Core/5/6/8 version detection and compatibility
- 🔹 **TypeScript Types**: Cypress custom command type generation
- 🔹 **Fluent API Chains**: RestAssured method chaining analysis

📖 See [MULTI_FRAMEWORK_SUPPORT.md](docs/frameworks/MULTI_FRAMEWORK_SUPPORT.md) for complete details

### 🔹 5. **Production Hardening & Runtime Protection** 🆕
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

### 🔹 6. **Performance Profiling & Observability**
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

**Result:** Teams get better maintainability and measurable ROI in weeks, not months.

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
- [AI Transformation Usage](docs/ai/AI_TRANSFORMATION_USAGE.md)
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
- Natural language documentation and best practice implementations
- Automatic fallback to pattern-based if AI unavailable
- See [`docs/ai/AI_TRANSFORMATION_USAGE.md`](docs/ai/AI_TRANSFORMATION_USAGE.md) for setup

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

### 4. Flaky Test Detection 🎯 NEW!

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

📖 **See [FLAKY_DETECTION_IMPLEMENTATION_SUMMARY.md](FLAKY_DETECTION_IMPLEMENTATION_SUMMARY.md) and [docs/CI_CD_FLAKY_INTEGRATION.md](docs/CI_CD_FLAKY_INTEGRATION.md)**

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

📖 **See [docs/MEMORY_EMBEDDINGS_SYSTEM.md](docs/MEMORY_EMBEDDINGS_SYSTEM.md) and [docs/MEMORY_QUICK_START.md](docs/MEMORY_QUICK_START.md)**

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

**Plugin Architecture**: Add new frameworks by implementing adapter interfaces.

---

## 📊 Project Maturity & Limitations

### Current Status: **Alpha (v0.1.0)**

**What Works Well:**
- ✅ Selenium Java + Cucumber → Robot Framework migrations
- ✅ Step definition parsing and transformation
- ✅ Bitbucket/GitHub/Azure DevOps integration
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
- `migrate_framework` - Convert tests between frameworks
- `analyze_coverage` - Generate coverage reports and impact analysis
- `generate_tests` - AI-powered test generation from requirements

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
  "tool": "migrate_framework",
  "inputs": {
    "source_framework": "selenium_java_bdd",
    "target_framework": "robot_playwright",
    "repository_url": "https://github.com/org/repo",
    "branch": "main"
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

## 📚 Documentation

- **[Getting Started Guide](docs/usage/)** - Step-by-step tutorials
- **[Architecture Overview](docs/architecture/)** - System design and components
- **[Flaky Detection Quick Start](docs/FLAKY_DETECTION_QUICK_START.md)** - 5-minute setup guide 🎯 NEW!
- **[CI/CD Flaky Integration](docs/CI_CD_FLAKY_INTEGRATION.md)** - Automated detection in pipelines 🎯 NEW!
- **[Adapter Development](docs/contributing/ADAPTER_DEVELOPMENT.md)** - Build your own adapters
- **[Migration Strategies](docs/migration/)** - Best practices for large migrations
- **[API Reference](docs/vision/)** - Future roadmap and APIs

---

## 🤝 Contributing

We welcome contributions! This project needs help with:

- 🔧 **Adapters**: Support for new frameworks (Cypress, Katalon, etc.)
- 🐛 **Bug Fixes**: Parser improvements, edge case handling
- 📖 **Documentation**: Tutorials, examples, API docs
- 🧪 **Testing**: Unit tests, integration tests, real-world validations
- 🌍 **Internationalization**: Non-English test support

**See [CONTRIBUTING.md](CONTRIBUTING.md)** for guidelines and [CLA.md](CLA.md) for contributor license agreement.

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

Comprehensive guides for test automation modernization and AI-powered transformation:

### 🚀 Getting Started
- **[Quick Start Guide](#-quick-start)** - Get started in 5 minutes
- **[API Documentation](docs/api/API.md)** - Complete API reference
- **[Configuration Guide](docs/config/CONFIG.md)** - All configuration options
- **[Contributing Guide](CONTRIBUTING.md)** - Join the community

### 🔧 Framework Integration
- **[Multi-Framework Support](docs/frameworks/MULTI_FRAMEWORK_SUPPORT.md)** - 12+ supported frameworks
- **[No-Migration Mode](docs/sidecar/NO_MIGRATION_IMPLEMENTATION_COMPLETE.md)** - Sidecar observer setup
- **[Framework Adapters](docs/frameworks/FRAMEWORK_ADAPTERS_REFERENCE.md)** - Custom adapter development

### 🤖 AI & Intelligence
- **[AI Transformation](docs/ai/AI_TRANSFORMATION_USAGE.md)** - AI-powered test migration
- **[Memory & Embeddings](docs/memory/MEMORY_EMBEDDINGS_SYSTEM.md)** - Semantic search and intelligent test discovery
- **[Intelligent Assistance](docs/intelligence/INTELLIGENT_TEST_ASSISTANCE.md)** - AI-powered insights

### 📊 Quality & Observability
- **[Flaky Test Detection](docs/flaky-detection/FLAKY_DETECTION_QUICK_START.md)** - ML-based detection and CI/CD integration
- **[Coverage Tracking](docs/coverage/FUNCTIONAL_COVERAGE_QUICKSTART.md)** - Behavioral & functional coverage
- **[Grafana Dashboards](docs/observability/CONTINUOUS_INTELLIGENCE_README.md)** - Real-time monitoring

### 📖 Complete Documentation
For full documentation index, visit: **[docs/INDEX.md](docs/INDEX.md)**

---

## 🤝 Get Involved

CrossBridge AI is **open source and community-driven**.  
We welcome contributions from developers, QA engineers, and organizations worldwide.

### How to Contribute
- 📝 **Read** [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
- 🔑 **Sign** [Contributor License Agreement](CLA.md)
- 💻 **Submit** pull requests for features or fixes
- 🐛 **Report** bugs and issues
- 📢 **Share** your experience

### Author & Maintainer
- **Vikas Verma** - Creator & Lead Developer
- **Email**: vikas.sdet@gmail.com
- **Organization**: CrossStack AI

See [AUTHORS.md](AUTHORS.md) and [GOVERNANCE.md](GOVERNANCE.md) for details.

---

## 🏆 Why Choose CrossBridge AI

### ✅ Framework Agnostic
Work with any testing framework — Selenium, Cypress, pytest, Robot, and more.

### ✅ Zero Lock-In
Use sidecar mode with existing tests — no migration required.

### ✅ AI-Enhanced
Optional AI features for smarter transformation and insights.

### ✅ Open Source
Apache 2.0 license — free forever, transparent, community-driven.

### ✅ Proven Architecture
Plugin-based design supports extensibility and custom integrations.

---

## 📜 License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

**Commercial Use**: Allowed under the terms of the Apache 2.0 license. 
**Attribution**: Required as per Apache 2.0 terms.
**Patent Grant**: Includes explicit patent protection for contributors and users.

---

## 🙏 Acknowledgments

Built by **CrossStack AI** for the global QA and DevOps community. Special thanks to:
- Robot Framework and Playwright communities
- Contributors to Selenium and Cucumber projects
- Early adopters providing feedback and bug reports

---

## 📞 Support & Community

- **Issues**: [GitHub Issues](https://github.com/yourusername/crossbridge/issues)
- **Email**: vikas.sdet@gmail.com (for sensitive topics)

**Response Time**: This is a volunteer project. Please be patient! 🙂

---

## 🗺️ Roadmap

### ✅ Completed (Q4 2025 - Q1 2026)
- [x] Core Selenium Java migration
- [x] Multi-framework intelligence (12+ frameworks)
- [x] Bitbucket/GitHub/Azure DevOps integration
- [x] Impact analysis and coverage mapping
- [x] **Flaky test detection with ML**
- [x] **PostgreSQL persistence + Grafana dashboards**
- [x] **Memory & Embeddings with semantic search**
- [x] **No-Migration sidecar mode**

### 🚀 In Progress (Q1 2026)
- [ ] Improved error handling and logging
- [ ] Comprehensive test coverage (>80%)
- [ ] Enhanced documentation and examples

### 📅 Planned (Q2 2026)
- [ ] Beta release (v0.5)
- [ ] Enhanced AI features (GPT-4, Claude 3.5 support)
- [ ] Web UI for migrations
- [ ] Docker containerization
- [ ] Playwright Java/Python adapters

### 🔮 Future (Q3-Q4 2026)
- [ ] v1.0 Stable release
- [ ] Enterprise features (LDAP, SSO)
- [ ] Cloud-hosted service option
- [ ] Plugin marketplace
- [ ] Internationalization support
- [ ] Certification program

---

## 📈 SEO Keywords

`test automation modernization` • `AI test transformation` • `legacy test migration` • `framework agnostic testing` • `test automation platform` • `selenium migration` • `flaky test detection` • `test intelligence` • `automated test migration` • `test framework conversion` • `AI-powered testing` • `test optimization` • `qa automation` • `devops testing` • `continuous testing`

---

## 💬 Testimonials

*Coming soon! We'd love to hear about your experience with CrossBridge.*

---

## ⭐ Show Your Support

If CrossBridge AI helps your team modernize test automation, please:

- ⭐ **Star this repository** to increase visibility
- 📢 **Share on LinkedIn** and social media
- 🐛 **Report issues** to improve quality
- 💻 **Contribute code** via pull requests
- 💬 **Join discussions** to share experiences

**Together, we can eliminate test automation debt worldwide.**

---

## 📞 Support & Community

### Get Help
- **📖 Documentation**: [docs/INDEX.md](docs/INDEX.md)
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/crossstack-ai/crossbridge/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/crossstack-ai/crossbridge/discussions)
- **📧 Email**: vikas.sdet@gmail.com

### Stay Connected
- **Organization**: CrossStack AI
- **Website**: https://crossstack.ai (coming soon)
- **Repository**: https://github.com/crossstack-ai/crossbridge

**Response Time**: This is a community-driven project. Please be patient! 🙂

---

## ⚖️ Legal & License

### License
CrossBridge AI is licensed under the [Apache License 2.0](LICENSE).

**Copyright (c) 2025 Vikas Verma**

- ✅ **Commercial use allowed**
- ✅ **Modification and distribution permitted**  
- ✅ **Patent grant included**
- ✅ **Attribution required**

### Disclaimer
**CrossBridge AI is an independent open-source project** developed by Vikas Verma in a personal capacity.

This project is:
- ✅ NOT affiliated with any employer
- ✅ Developed using personal time and resources
- ✅ Open-source for the testing community

For details, see [AUTHORS.md](AUTHORS.md) and [CLA.md](CLA.md).

---

**Built with ❤️ by [CrossStack AI](https://crossstack.ai) for the global test automation community.**

*Bridging Legacy Test Systems to AI-Powered Quality Engineering*
