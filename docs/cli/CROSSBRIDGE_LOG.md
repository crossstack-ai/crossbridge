# CrossBridge Log Parser CLI

**Universal log parsing utility with automatic intelligence analysis**

## Overview

`crossbridge-log` is a command-line utility that provides intelligent log parsing and analysis for all test automation frameworks. It automatically applies execution intelligence to classify failures, extract signals, and provide actionable recommendations.

## Key Features

### 🎯 **Automatic Intelligence** (ENHANCED!)

#### **Advanced Failure Classification**
Automatically categorizes failures with 5 primary categories and 31 sub-categories:

**Primary Categories:**
- ✅ `PRODUCT_DEFECT` - Application bugs, API failures, business logic errors
- ✅ `AUTOMATION_DEFECT` - Test code issues, locator problems, assertion errors  
- ✅ `ENVIRONMENT_ISSUE` - Infrastructure failures, network issues, timeouts
- ✅ `CONFIGURATION_ISSUE` - Setup problems, dependency issues, credential errors
- ✅ `UNKNOWN` - Unclassifiable failures

**Sub-Categories (31 specialized classifications):**

*Product Defects:*
- `API_ERROR` - REST/GraphQL/SOAP API failures
- `ASSERTION_FAILURE` - Test assertions failed
- `BUSINESS_LOGIC_ERROR` - Application logic bugs
- `DATA_VALIDATION_ERROR` - Invalid data format/type
- `PERFORMANCE_ISSUE` - Slow response, high latency
- `SECURITY_ERROR` - Authentication/authorization failures

*Automation Defects:*
- `ELEMENT_NOT_FOUND` - UI element locator failed
- `LOCATOR_ISSUE` - Incorrect/brittle locator
- `STALE_ELEMENT` - Element no longer attached to DOM
- `TEST_CODE_ERROR` - Test script bugs
- `SYNCHRONIZATION_ERROR` - Timing/wait issues
- `TEST_DATA_ISSUE` - Test data problems

*Environment Issues:*
- `CONNECTION_TIMEOUT` - Network connection timeout
- `NETWORK_ERROR` - Network connectivity problems
- `DNS_ERROR` - DNS resolution failure
- `SSL_ERROR` - SSL/TLS certificate issues
- `RESOURCE_EXHAUSTION` - Out of memory/disk/CPU
- `INFRASTRUCTURE_FAILURE` - Server/database down

*Configuration Issues:*
- `MISSING_DEPENDENCY` - Library/package not found
- `WRONG_CREDENTIALS` - Invalid username/password
- `MISSING_FILE` - File/resource not found
- `INVALID_CONFIGURATION` - Config file errors
- `PERMISSION_ERROR` - Access denied
- `VERSION_MISMATCH` - Incompatible versions

**Classification Features:**
- 📊 Confidence scoring (0.0-1.0) for each classification
- 🔍 Evidence-based reasoning (specific patterns detected)
- 🎯 Multi-signal analysis (error messages, stack traces, test context)
- 🚀 Fast performance (<50ms per classification)

#### **Test Failure Correlation & Grouping** ⭐ NEW!
Intelligent correlation engine that groups related failures:

- ✅ **Error Pattern Matching** - Groups tests with similar error signatures
- ✅ **Root Cause Analysis** - Identifies common underlying issues
- ✅ **Failure Trend Detection** - Tracks patterns across test runs
- ✅ **Test Dependency Mapping** - Detects cascading failures
- ✅ **Temporal Correlation** - Groups failures in time windows

**Benefits:**
- 🎯 Reduce analysis time by 70% (analyze groups, not individual tests)
- 🔍 Identify systemic issues vs. isolated failures
- 📈 Prioritize fixes based on impact (# affected tests)
- 📊 Track failure patterns over time

#### **Failure Deduplication & Root Cause Clustering** 🔥 CRITICAL!
Advanced clustering algorithm that eliminates duplicate failures and identifies unique root causes:

**How It Works:**
- ✅ **Error Fingerprinting** - Generates MD5 hash of normalized error signatures
- ✅ **Smart Normalization** - Removes variable elements (timestamps, IDs, URLs, line numbers)
- ✅ **Stack Trace Analysis** - Incorporates call stack patterns for precision
- ✅ **HTTP Status Clustering** - Groups by HTTP error codes (4xx, 5xx)
- ✅ **Severity Detection** - Automatically assigns priority levels (Critical/High/Medium/Low)

**Normalization Patterns:**
```python
# These all cluster together:
"ElementNotFound: #btn-123"     → "elementnotfound: #<id>"
"ElementNotFound: #btn-456"     → "elementnotfound: #<id>"
"ElementNotFound: #btn-login"   → "elementnotfound: #<id>"

# Timestamps normalized:
"Error at 2024-01-15 10:30:45"  → "error at <timestamp>"
"Error at 2024-12-31 23:59:59"  → "error at <timestamp>"

# URLs normalized:
"Failed https://api.com/users"  → "failed <url>"
"Failed https://api.com/orders" → "failed <url>"
```

**Deduplication Logic:**
- Within same test: Only count first occurrence of identical error
- Across tests: Cluster similar errors together
- Results: Show "5 unique issues (deduplicated from 23 failures)"

**Output Format:**
```
Root Cause Analysis: 3 unique issues (deduplicated from 12 failures)
Deduplication saved 9 duplicate entries (75% reduction)

╒════════════╤═══════════════════════════════════════╤═══════╤════════════════════╕
│ Severity   │ Root Cause                             │ Count │ Affected           │
╞════════════╪═══════════════════════════════════════╪═══════╪════════════════════╡
│ HIGH       │ ElementNotFound: element missing       │     8 │ Test Login, +3 ... │
│ MEDIUM     │ TimeoutException: operation timed out  │     3 │ Test Checkout, ... │
│ HIGH       │ AssertionError: expected 5 but was 3   │     1 │ Test Validation    │
╘════════════╧═══════════════════════════════════════╧═══════╧════════════════════╛

[i] Suggested Fix for Top Issue:
Check if element locators are correct and elements are visible.
Consider adding explicit waits or updating selectors if page structure changed.
```

**Real-World Example:**
```
Before Clustering:
✗ Checking Instant VM Job Status → failed
✗ Checking Instant VM Job Status → failed
✗ Checking Instant VM Job Status → failed
✗ Verifying Cloud Resources → failed
✗ Validating Network Config → failed

After Clustering:
Root Cause Analysis: 2 unique issues (deduplicated from 5 failures)
  HIGH: Element not found (3 occurrences) → Instant VM Job Status
  HIGH: Connection timeout (2 occurrences) → Cloud Resources, Network Config
```

**Value Delivered:**
- ⚡ **Massive Triage Speedup** - 75-90% reduction in noise
- 🎯 **Focused Analysis** - "23 failures → 5 root issues"
- 📊 **Impact Visibility** - See which issue affects most tests
- 🔍 **Pattern Recognition** - Identify systemic vs. isolated failures

#### **Enhanced Signal Extraction**
Detects 20+ signal types across all categories:

- Timeout errors (connection, read, operation)
- Assertion failures (expected vs actual)
- Locator/element issues (not found, stale, ambiguous)
- Network/connection errors (DNS, SSL, firewall)
- Configuration problems (missing files, wrong credentials)
- API errors (4xx, 5xx status codes)
- Performance issues (slow response, high latency)
- Security errors (authentication, authorization)

#### **Code Reference Resolution**
Pinpoints exact test code location for automation defects:
- File path and line number
- Stack trace analysis
- Test method/function name
- Framework-specific context

#### **AI-Enhanced Analysis** 🤖 ENHANCED!
Optional AI-powered insights with cost transparency:

- ✅ **Root Cause Analysis** - AI explains "why" the test failed (with intelligent summarization)
- ✅ **Intelligent Summarization** 🆕 - AI condenses all verbose output
  * **Applies to both recommendations AND root cause analysis text**
  * Eliminates mid-sentence truncation (complete, actionable messages)
  * Automatically combines duplicate recommendations
  * Removes verbose explanations while maintaining technical accuracy
  * Smart sentence-boundary awareness (fallback without AI)
  * Uses dedicated `/summarize-recommendations` API endpoint
- ✅ **Fix Recommendations** - Specific code-level suggestions
- ✅ **Similar Failure Patterns** - Historical pattern matching
- ✅ **Business Impact Assessment** - Severity and urgency scoring
- ✅ **Cost Transparency** - Show costs before/after processing
- ✅ **License Management** - Tier-based token limits
- ✅ **Graceful Fallback** - Works without AI if license invalid

**AI Providers Supported:**
- OpenAI (GPT-3.5, GPT-4, GPT-4-turbo)
- Anthropic (Claude-3-Sonnet, Claude-3-Opus)
- Azure OpenAI (GPT models)
- Self-hosted: Ollama (deepseek-coder, llama3, mistral, etc.)

**Provider Detection at Startup:**
Sidecar shows clear status messages for each provider:
- ✅ AI AVAILABLE - OpenAI credentials configured (💰 Cost: ~$0.01-$0.10 per run)
- ✅ AI AVAILABLE - Anthropic Claude credentials configured (💰 Cost: ~$0.015-$0.15 per run)
- ✅ AI AVAILABLE - Self-hosted model: deepseek-coder:6.7b at http://... (💰 Cost: Free)
- ℹ️  AI NOT CONFIGURED - Will run rule-based analysis only

#### **Works Without AI**
Fully deterministic, rule-based analysis (no AI required for core features)

### 🔍 **Universal Parsing**
Supports all major frameworks:
- Robot Framework (`output.xml`)
- Cypress (`cypress-results.json`)
- Playwright (`playwright-trace.json`)
- Behave BDD (`behave-results.json`)
- Java Cucumber (`*Steps.java`)

### 🎛️ **Powerful Filtering**
- Filter by test name (with wildcards)
- Filter by test ID
- Filter by status (PASS/FAIL/SKIP)
- Filter by error code
- Filter by text pattern (case-insensitive)
- Filter by time range

### 💾 **Flexible Output**
- Console display (formatted, color-coded)
- JSON file export
- API upload (for remote access)

---

## Installation

```bash
# Clone repository
git clone https://github.com/crossstack-ai/crossbridge.git
cd crossbridge

# Make executable
chmod +x bin/crossbridge-log

# Add to PATH (optional)
export PATH=$PATH:$(pwd)/bin
```

---

## Quick Start

### Basic Usage (with automatic intelligence)

```bash
# Parse Robot Framework log
./bin/crossbridge-log output.xml

# Parse Cypress results
./bin/crossbridge-log cypress-results.json

# Parse with custom sidecar
CROSSBRIDGE_SIDECAR_HOST=remote-server ./bin/crossbridge-log output.xml
```

**Output includes:**
- Parsed test results
- **Intelligence Analysis Summary** (NEW!)
  - Failure classifications breakdown
  - Detected signals
  - Actionable recommendations
- Framework-specific statistics

---

## Usage Examples

### 1. Basic Parsing with Intelligence

```bash
./bin/crossbridge-log output.xml
```

**Output:**
```
Checking sidecar API...
✓ Detected framework: robot
Parsing log file: output.xml
Running intelligence analysis...
✓ Intelligence analysis complete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Intelligence Analysis Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Failure Classifications:
  • PRODUCT_DEFECT: 2
  • AUTOMATION_DEFECT: 1

Detected Signals:
  • assertion_failure: 2
  • locator_error: 1

Recommendations:
  ✓ Review application code for bugs
  ✓ Update test automation code/locators

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           Robot Framework Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
...
```

### 2. Filter Failed Tests Only

```bash
./bin/crossbridge-log output.xml --status FAIL
```

Shows only failed tests with intelligence analysis.

### 3. Filter by Test Name (Wildcards Supported)

```bash
# All login tests
./bin/crossbridge-log output.xml --test-name 'Login*'

# Tests containing "API"
./bin/crossbridge-log output.xml --test-name '*API*'
```

### 4. Filter by Error Code/Pattern

```bash
# Find all "Connection refused" errors
./bin/crossbridge-log output.xml --pattern "Connection refused"

# Find all timeout errors
./bin/crossbridge-log output.xml --error-code "TimeoutException"
```

### 5. Save to File

```bash
# Save to specific file
./bin/crossbridge-log output.xml --output results.json

# Auto-generated timestamped file
./bin/crossbridge-log output.xml
# Creates: output.xml.parsed.20260205_143022.json
```

### 6. Time-Based Filtering

```bash
# Tests after specific time
./bin/crossbridge-log output.xml --time-from '2026-02-05T10:00:00'

# Tests in time range
./bin/crossbridge-log output.xml \
  --time-from '2026-02-05T10:00:00' \
  --time-to '2026-02-05T12:00:00'
```

### 7. Combined Filters

```bash
# Failed login tests with assertion errors
./bin/crossbridge-log output.xml \
  --status FAIL \
  --test-name 'Login*' \
  --pattern 'AssertionError'
```

### 8. AI-Enhanced Analysis 🤖 NEW!

```bash
# Enable AI-powered insights (requires license for cloud providers)
./bin/crossbridge-log output.xml --enable-ai

# Banner varies by configured provider:
```

#### OpenAI / Cloud Providers
```bash
⚠️  AI-ENHANCED ANALYSIS ENABLED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Provider: Openai (gpt-3.5-turbo)
Using AI will incur costs:
  • Cost: ~$0.002 per 1000 tokens
  • Typical analysis: ~$0.01-$0.10 per run
  • Costs vary by log size and complexity

Checking AI configuration...
✓ OpenAI (gpt-3.5-turbo) validated successfully
```

#### Self-Hosted AI (Ollama/vLLM)
```bash
🤖  AI-ENHANCED ANALYSIS ENABLED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Provider: Self-hosted (deepseek-coder:6.7b)
Cost: No additional costs (local inference)
License: Not required for self-hosted AI

Checking AI configuration...
✓ Self-hosted AI configured (deepseek-coder:6.7b) - no license required
```

#### After Analysis - Smart Duration Formatting
```bash
🤖 AI LOG ANALYSIS SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AI Configuration:
  • Provider: Selfhosted
  • Model: deepseek-coder:6.7b

AI Analysis Statistics:
  ✓ Total Tests Analyzed: 78
  ✓ AI-Enhanced Classifications: 78
  ✓ Total Time Taken: 54h 2m  ← Smart formatting!

Token Usage & Cost:
  • Prompt Tokens: 12,708
  • Completion Tokens: 17,136
  • Total Tokens: 29,844
  • Total Cost: $0.0000  ← Zero cost for self-hosted!
  • Avg Tokens/Test: 382
  • Avg Cost/Test: $0.0000
```

**Duration Formatting Examples:**
- `45s` - Less than 1 minute
- `3m 25s` - Between 1-60 minutes
- `2h 15m` - Between 1-24 hours
- `3d 14h` - More than 24 hours

**Supported AI Providers:**

| Provider | Models | Cost | License Required | Setup |
|----------|--------|------|------------------|-------|
| **OpenAI** | gpt-3.5-turbo, gpt-4, gpt-4o | ~$0.002/1K tokens | ✅ Yes | API key |
| **Anthropic** | Claude 3.5 Sonnet, Opus, Haiku | ~$0.003/1K tokens | ✅ Yes | API key |
| **Azure OpenAI** | GPT-4, GPT-3.5 (Azure-hosted) | ~$0.002/1K tokens | ✅ Yes | API key + endpoint |
| **Ollama** | deepseek-coder, llama3, mistral | 💰 Free (self-hosted) | ❌ No | Local installation |
| **vLLM** | Any HuggingFace model | 💰 Free (self-hosted) | ❌ No | Self-hosted server |

**Provider-Specific Features:**
- ✅ **All providers** - Comprehensive request/response logging with timing, tokens, and costs
- ✅ **All providers** - Error tracking (timeouts, HTTP errors, auth failures)
- ✅ **All providers** - Request correlation via execution_id
- 🔍 **Ollama only** - Performance metrics (tokens/sec, eval duration)

**AI Enhancement Features:**
- Root cause analysis for each failure
- Specific fix recommendations
- Similar failure pattern detection
- Code-level debugging suggestions
- Business impact assessment

**AI-Enhanced Test Analysis Output:**

CrossBridge displays AI insights in a clean, structured format:

```bash
AI-Enhanced Test Analysis:

  ┌─────────────────────────────────────────┐
  │ test-001: User Login Authentication Test
  └─────────────────────────────────────────┘
  📊 Classification: PRODUCT > DEFECT > API > ERROR
  🎯 Confidence: 0.85
  
  💡 Root Cause Analysis:
  API authentication endpoint returned 500 error due to missing OAuth 
  token in request headers. Database connection pool exhausted after 
  30 seconds timeout.

  ┌─────────────────────────────────────────┐
  │ test-002: Payment Processing Flow
  └─────────────────────────────────────────┘
  📊 Classification: ENVIRONMENT > ISSUE > TIMEOUT
  🎯 Confidence: 0.92
  
  💡 Root Cause Analysis:
  Payment gateway response exceeded configured 10s timeout. Network 
  latency to external service averages 8.5s under load.
```

**Key Features:**
- ✅ **Structured Format** - TC ID, Name, Classification, Confidence clearly displayed
- ✅ **Clean Output** - No AI disclaimers like "I'm sorry, as an AI..."
- ✅ **Concise Analysis** - 2-3 sentences focused on technical root cause
- ✅ **Hierarchical Classification** - Easy-to-read format (PRODUCT > DEFECT > API > ERROR)
- ✅ **Actionable Insights** - Direct technical analysis without hedging

**License Tiers (Cloud Providers Only):**
- FREE: 1K daily / 10K monthly tokens (testing)
- BASIC: 10K daily / 100K monthly tokens (small teams)
- PROFESSIONAL: 50K daily / 1M monthly tokens (large teams)
- ENTERPRISE: 100K daily / 5M monthly tokens (enterprise)
- UNLIMITED: No limits (enterprise premium)

**Cost Transparency:**
- ⚠️ Warning displayed before processing
- 📊 Real-time token tracking
- 💰 Detailed cost breakdown after analysis
- 💡 Savings comparison (GPT-3.5 vs GPT-4)
- ✅ Graceful fallback if license invalid

### 9. Correlation Analysis NEW!

```bash
# Group related failures
./bin/crossbridge-log output.xml --correlation

# Shows correlation groups:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          Correlation Groups
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Group CG-001: Database connection timeout
  • Affected Tests: 15
  • Category: ENVIRONMENT_ISSUE
  • Sub-Category: CONNECTION_TIMEOUT
  • Confidence: 0.95
  • Root Cause: Database server overload
  • Recommendation: Scale database or add pooling

Group CG-002: Element not found errors
  • Affected Tests: 8
  • Category: AUTOMATION_DEFECT
  • Sub-Category: ELEMENT_NOT_FOUND
  • Confidence: 0.88
  • Root Cause: UI changes not reflected in tests
  • Recommendation: Update locators to match new UI
```

### 10. Filter by Category/Sub-Category NEW!

```bash
# Filter by primary category
./bin/crossbridge-log output.xml --category PRODUCT_DEFECT

# Filter by sub-category
./bin/crossbridge-log output.xml --sub-category API_ERROR

# Combine filters
./bin/crossbridge-log output.xml \
  --category AUTOMATION_DEFECT \
  --sub-category ELEMENT_NOT_FOUND
```

### 11. Disable Intelligence Analysis

```bash
# Use basic parsing only (faster for large logs)
./bin/crossbridge-log output.xml --no-analyze
```

---

## Command-Line Options

```
Usage: crossbridge-log <log-file> [OPTIONS]

Options:
  -o, --output FILE          Save parsed results to FILE (JSON format)
  -a, --app-logs FILE        Application logs for correlation (JSON format)
  --enable-ai                Enable AI-enhanced analysis (requires license, incurs cost)
  --correlation              Enable correlation analysis (group related failures)
  -t, --test-name PATTERN    Filter tests by name (supports wildcards)
  -i, --test-id ID           Filter by specific test ID
  -s, --status STATUS        Filter by status (PASS, FAIL, SKIP)
  -c, --category CATEGORY    Filter by primary category (PRODUCT_DEFECT, AUTOMATION_DEFECT, etc.)
  --sub-category SUBCATEGORY Filter by sub-category (API_ERROR, ELEMENT_NOT_FOUND, etc.)
  -e, --error-code CODE      Filter by error code in messages
  -p, --pattern PATTERN      Filter by text pattern (case-insensitive)
  --time-from DATETIME       Filter tests starting after DATETIME
  --time-to DATETIME         Filter tests ending before DATETIME
  --no-analyze               Disable automatic intelligence analysis
  -h, --help                 Show this help message

Environment Variables:
  CROSSBRIDGE_SIDECAR_HOST   - Sidecar API host (default: localhost)
  CROSSBRIDGE_SIDECAR_PORT   - Sidecar API port (default: 8765)

AI License Configuration:
  ~/.crossbridge/ai_license.json - AI license and usage tracking
  Use 'crossbridge configure ai' to set up AI credentials (coming soon)
```

---

## Intelligence Analysis Details

### How It Works

1. **Automatic Framework Detection**
   - Analyzes filename and content
   - Selects appropriate parser

2. **Log Parsing**
   - Uses framework-specific parser (Robot, Cypress, etc.)
   - Normalizes to standard format

3. **Intelligence Analysis** (Automatic, unless `--no-analyze`)
   - Calls sidecar `/analyze` endpoint
   - Uses `ExecutionAnalyzer` (deterministic, no AI)
   - Extracts failure signals
   - Classifies each failure
   - Resolves code references (for automation defects)
   - Generates recommendations

4. **Filtering**
   - Applies user-specified filters
   - Works on enriched data

5. **Display**
   - Shows intelligence summary
   - Shows filtered results
   - Saves to file/API

### Classification Logic

#### Primary Categories (5)

**PRODUCT_DEFECT:**
- Assertion failures (expected ≠ actual)
- Unexpected values/behavior
- API errors (4xx/5xx status codes)
- Business logic failures
- Data validation errors
- Performance issues (slow response)
- Security errors (auth/authorization)

**AUTOMATION_DEFECT:**
- Element not found (locator failed)
- Stale element references
- Incorrect/brittle locators
- Test syntax errors
- Synchronization errors (timing issues)
- Test data problems

**ENVIRONMENT_ISSUE:**
- Connection timeouts
- Network errors (connectivity lost)
- DNS failures (hostname resolution)
- SSL/TLS certificate errors
- Out of memory/disk space
- Infrastructure failures (server/database down)

**CONFIGURATION_ISSUE:**
- Missing files/resources
- Wrong credentials
- Import/dependency errors
- Invalid configuration
- Permission denied
- Version mismatches

**UNKNOWN:**
- Insufficient information to classify
- Novel failure patterns
- Complex multi-factor failures

#### Sub-Categories (31)

See **Command-Line Options** section above for complete list of 31 sub-categories.

**Classification Algorithm:**
1. Extract error message, stack trace, test context
2. Apply 50+ pattern-matching rules
3. Calculate confidence score (0.0-1.0)
4. Select best matching category + sub-category
5. Generate evidence-based reasoning

**Confidence Scoring:**
- `0.9-1.0` - High confidence (strong pattern match)
- `0.7-0.89` - Medium confidence (partial match)
- `0.5-0.69` - Low confidence (weak signals)
- `<0.5` - Very low confidence (classify as UNKNOWN)

### Signal Types (20+)

**Error Signals:**
- `assertion_failure` - Assert/expect statements failed
- `timeout` - Operation exceeded time limit (connection, read, operation)
- `locator_error` - Element locator not found
- `stale_element` - Element no longer attached to DOM
- `network_error` - Connection/network issues
- `dns_error` - DNS resolution failure
- `ssl_error` - SSL/TLS certificate problems
- `http_error` - HTTP status errors (4xx, 5xx)
- `api_error` - REST/GraphQL/SOAP failures
- `configuration_error` - Config/setup problems
- `permission_error` - Access denied
- `missing_dependency` - Library/package not found
- `missing_file` - File/resource not found
- `wrong_credentials` - Invalid username/password
- `version_mismatch` - Incompatible versions
- `resource_exhaustion` - Out of memory/disk/CPU
- `business_logic_error` - Application logic bugs
- `data_validation_error` - Invalid data format/type
- `performance_issue` - Slow response, high latency
- `security_error` - Authentication/authorization failures

### Correlation Algorithm

**Grouping Strategy:**
1. Calculate pairwise similarity between all failures
2. Use multiple similarity metrics:
   - Error message similarity (cosine similarity ≥ 0.8)
   - Stack trace pattern matching
   - Category/sub-category matching
   - Temporal proximity (within 5-minute windows)
   - Test context similarity (tags, suites, modules)
3. Apply clustering algorithm (DBSCAN)
4. Generate group metadata (pattern, root cause, recommendations)

**Correlation Metrics:**
- `affected_tests` - Number of tests in group
- `confidence` - Confidence that tests are truly related (0.0-1.0)
- `pattern` - Common error pattern description
- `root_cause` - Identified underlying issue
- `recommendation` - Suggested fix action

---

## API Access

### Upload to Sidecar (Automatic)

Results are automatically uploaded to sidecar (if < 10MB):

```bash
./bin/crossbridge-log output.xml

# Output:
✓ Results uploaded successfully
Access via API:
  GET  http://localhost:8765/logs/abc123
  GET  http://localhost:8765/logs/abc123/summary
  GET  http://localhost:8765/logs/abc123/failures
```

### API Endpoints

```bash
# Get full log
curl http://localhost:8765/logs/abc123

# Get summary only
curl http://localhost:8765/logs/abc123/summary

# Get failures only
curl http://localhost:8765/logs/abc123/failures

# List all logs
curl http://localhost:8765/logs

# Delete log
curl -X DELETE http://localhost:8765/logs/abc123
```

---

## Integration with Existing Components

### 1. Execution Intelligence Engine
**Location:** `core/execution/intelligence/`

- **ExecutionAnalyzer** - Main analysis engine
- **Signal Extractors** - Pattern-based signal detection
- **Rule-Based Classifier** - 30+ classification rules
- **Code Reference Resolver** - Stack trace parsing

**Usage:**
```python
from core.execution.intelligence.analyzer import ExecutionAnalyzer

analyzer = ExecutionAnalyzer(enable_ai=False)  # Works without AI
result = analyzer.analyze(raw_log, test_name, framework)
print(result.classification.failure_type)  # PRODUCT_DEFECT, etc.
```

### 2. JSON Log Adapter
**Location:** `core/execution/intelligence/log_adapters/`

- Parses application logs (JSON/ELK/Fluentd)
- Correlates with test execution logs
- Normalizes to canonical schema

**Complementary Use:**
- `crossbridge-log` → Test execution logs
- `JSON Log Adapter` → Application logs
- Correlate both for full-stack analysis

### 3. Framework Parsers
**Location:** `core/intelligence/`

- `RobotLogParser` - Robot Framework
- `CypressResultsParser` - Cypress
- `PlaywrightTraceParser` - Playwright
- `BehaveJSONParser` - Behave BDD
- `JavaStepDefinitionParser` - Java Cucumber

**Reuse:**
`crossbridge-log` uses same parsers as runtime execution.

---

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Parse logs | ~100ms | Per log file |
| Extract signals | ~50ms | Per failure |
| Classify (category + sub-category) | ~50ms | Per failure |
| Correlation grouping | ~200ms | For 1000 tests |
| Resolve code | ~20ms | Per stack trace |
| AI analysis (if enabled) | +120ms | Per failure (OpenAI GPT-3.5) |
| **Total (with intelligence)** | ~220ms | Per test failure (non-AI) |
| **Total (with AI)** | ~340ms | Per test failure (AI-enhanced) |
| Total (without intelligence) | ~100ms | Basic parsing only |

**Performance Tips:**
- Use `--no-analyze` for very large logs (>1000 tests)
- Use filtering to reduce dataset before analysis
- Enable intelligence for failure analysis (worth the 120ms overhead)
- Use `--correlation` to analyze groups instead of individual tests (70% faster)
- Use AI selectively (high-priority failures only) to minimize cost and latency

**Scalability:**
- Tested with logs containing 10,000+ tests
- Correlation scales linearly: O(n log n) with optimized clustering
- Memory usage: ~50MB for 1000 tests, ~500MB for 10,000 tests
- AI analysis: Scales based on failure count (only failed tests analyzed)

---

## Troubleshooting

### Issue: Sidecar not reachable

```
Error: Sidecar API not reachable at http://localhost:8765
```

**Solution:**
1. Start sidecar: `python -m services.sidecar_api`
2. Check `CROSSBRIDGE_SIDECAR_HOST` and `CROSSBRIDGE_SIDECAR_PORT`
3. Verify firewall allows connection

### Issue: Intelligence analysis not available

```
Note: Intelligence analysis not available (using basic parsing)
```

**Solution:**
1. Update sidecar to latest version (includes `/analyze` endpoint)
2. Restart sidecar
3. Intelligence analysis requires sidecar with ExecutionAnalyzer

### Issue: No failures to analyze

```
Recommendations:
  ✓ All tests passed - no analysis needed
```

**Solution:**
This is normal - intelligence only runs on failed tests.

---

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run tests and analyze
  run: |
    pytest tests/ --html=report.html
    ./bin/crossbridge-log pytest-output.log --status FAIL --output failures.json
    
- name: Check for product defects
  run: |
    if grep -q "PRODUCT_DEFECT" failures.json; then
      echo "Product defects found!"
      exit 1
    fi
```

### GitLab CI

```yaml
test:
  script:
    - robot tests/
    - ./bin/crossbridge-log output.xml --status FAIL --output failures.json
  artifacts:
    when: always
    paths:
      - failures.json
    reports:
      junit: failures.json
```

### Jenkins

```groovy
stage('Test Analysis') {
    steps {
        sh '''
            ./bin/crossbridge-log output.xml --status FAIL --output failures.json
            
            if grep -q "PRODUCT_DEFECT" failures.json; then
                currentBuild.result = 'FAILURE'
            fi
        '''
    }
}
```

---

## Advanced Usage

### Batch Processing

```bash
# Process all logs in directory
for log in logs/*.xml; do
  ./bin/crossbridge-log "$log" --status FAIL --output "analyzed_$(basename $log).json"
done
```

### Remote Sidecar

```bash
# Use remote sidecar server
export CROSSBRIDGE_SIDECAR_HOST=10.60.75.145
export CROSSBRIDGE_SIDECAR_PORT=8765

./bin/crossbridge-log output.xml
```

### Programmatic Access (Python)

```python
import subprocess
import json

# Run crossbridge-log
result = subprocess.run(
    ['./bin/crossbridge-log', 'output.xml', '--output', 'results.json'],
    capture_output=True
)

# Load results
with open('results.json') as f:
    data = json.load(f)
    
# Access intelligence summary
summary = data.get('intelligence_summary', {})
product_defects = summary.get('classifications', {}).get('PRODUCT_DEFECT', 0)

print(f"Found {product_defects} product defects")
```

---

## Related Documentation

- [Execution Intelligence](../EXECUTION_INTELLIGENCE.md) - Deep dive into analysis engine
- [JSON Log Adapter](../log_analysis/JSON_LOG_ADAPTER.md) - Application log correlation
- [Intelligence Features](../releases/historical/intelligence_features.md) - Parser details
- [Sidecar API](../sidecar/SIDECAR_API.md) - API reference

---

## Contributing

To add support for a new framework:

1. Implement parser in `core/intelligence/`
2. Register in sidecar API (`services/sidecar_api.py`)
3. Add detection logic in `crossbridge-log` (`detect_framework()`)
4. Add tests in `tests/unit/test_crossbridge_log.py`
5. Update this documentation

---

## License

Apache 2.0

---

## Support

- Issues: https://github.com/crossstack-ai/crossbridge/issues
- Docs: https://docs.crossbridge.dev
- Email: support@crossbridge.dev
