# Execution Intelligence Engine

**Framework-agnostic execution log analyzer** that converts raw automation logs into structured failure signals with explainable, deterministic classification.

## Overview

The Execution Intelligence Engine solves a critical pain point in test automation: **intelligently classifying test failures** to route them to the right team and make CI/CD decisions.

### The Problem

When tests fail, teams face:
- ❌ Manual triage of failures (hours per week)
- ❌ All failures treated equally (blocks PRs)
- ❌ No distinction between product bugs vs test issues
- ❌ Environment failures mistaken for product defects
- ❌ Difficult to pinpoint root cause in logs

### The Solution

Crossbridge's Execution Intelligence Engine:
- ✅ Automatically classifies failures into 5 categories
- ✅ Works **without AI** (deterministic, explainable)
- ✅ Resolves code references for automation failures
- ✅ Fails CI only for product defects (configurable)
- ✅ Framework-agnostic (Selenium, Pytest, Robot, Playwright, etc.)
- ✅ Optional AI enhancement for deeper insights

## Architecture

```
Raw Logs
   ↓
Framework Adapters (Normalization)
   ↓
Failure Signal Extraction (Deterministic)
   ↓
Rule-Based Classification (No AI)
   ↓
Code Reference Resolution
   ↓
Optional AI Enhancement
   ↓
Structured Output (CI/CD Ready)
```

### Key Principles

1. **Deterministic First**: Works perfectly without AI
2. **AI as Enhancement**: Optional layer that never overrides
3. **Framework Agnostic**: Single interface for all frameworks
4. **Explainable**: Every classification has evidence
5. **Production Safe**: Designed for CI/CD pipelines

## Failure Taxonomy

| Type | Description | Typical Causes | CI Action |
|------|-------------|---------------|-----------|
| **PRODUCT_DEFECT** | Application bug | Assertion failures, unexpected values, API errors | **Fail build** |
| **AUTOMATION_DEFECT** | Test code issue | Locator not found, stale elements, test syntax errors | Warning |
| **ENVIRONMENT_ISSUE** | Infrastructure problem | Timeouts, connection refused, DNS errors, out of memory | Retry/Warning |
| **CONFIGURATION_ISSUE** | Config/setup problem | Missing files, wrong credentials, import errors | Warning |
| **UNKNOWN** | Unable to classify | Insufficient information | Configurable |

## Quick Start

### Installation

```bash
pip install crossbridge
```

### Basic Usage

```python
from core.execution.intelligence import ExecutionAnalyzer

# Initialize analyzer
analyzer = ExecutionAnalyzer(workspace_root="/path/to/project")

# Analyze a test failure
result = analyzer.analyze(
    raw_log=log_content,
    test_name="test_login",
    framework="pytest"
)

# Check classification
if result.is_product_defect():
    print(f"Product bug: {result.classification.reason}")
    print(f"Confidence: {result.classification.confidence}")
    
    # Get code reference
    if result.classification.code_reference:
        ref = result.classification.code_reference
        print(f"Failed at: {ref.file}:{ref.line}")
        print(f"Snippet:\n{ref.snippet}")
```

### CLI Usage

```bash
# Analyze single log file
crossbridge analyze logs \
  --log-file test-output.log \
  --test-name test_login \
  --framework pytest \
  --fail-on product

# Analyze directory
crossbridge analyze directory \
  --log-dir ./test-results \
  --pattern "*.log" \
  --output analysis.json
```

## Components

### 1. Models ([models.py](../core/execution/intelligence/models.py))

Core data structures:

- **ExecutionEvent**: Normalized log entry
- **FailureSignal**: Extracted failure indicator
- **FailureClassification**: Classification result
- **CodeReference**: Code path and snippet
- **AnalysisResult**: Complete analysis output

### 2. Framework Adapters ([adapters.py](../core/execution/intelligence/adapters.py))

Convert framework-specific logs to ExecutionEvent:

- `SeleniumLogAdapter`: Selenium WebDriver logs
- `PytestLogAdapter`: Pytest output
- `RobotFrameworkLogAdapter`: Robot Framework logs
- `PlaywrightLogAdapter`: Playwright logs
- `GenericLogAdapter`: Fallback for unknown formats

**No classification happens here** - only normalization.

### 3. Signal Extractors ([extractor.py](../core/execution/intelligence/extractor.py))

Extract failure signals from events:

- `TimeoutExtractor`: Timeout-related failures
- `AssertionExtractor`: Assertion failures
- `LocatorExtractor`: Element locator issues
- `HttpErrorExtractor`: HTTP/API errors
- `InfraErrorExtractor`: Infrastructure errors

All **deterministic** - no AI, pure pattern matching.

### 4. Rule-Based Classifier ([classifier.py](../core/execution/intelligence/classifier.py))

Maps signals to failure types:

- **30+ classification rules**
- Priority-based matching
- Confidence scoring
- Evidence extraction
- 100% explainable

Example rule:

```python
ClassificationRule(
    name="locator_not_found",
    conditions=["NoSuchElementException", "locator", "selector"],
    failure_type=FailureType.AUTOMATION_DEFECT,
    confidence=0.92,
    priority=95
)
```

### 5. Code Reference Resolver ([resolver.py](../core/execution/intelligence/resolver.py))

Pinpoints test code location:

- Parses stack traces (Python, Java, JavaScript)
- Finds first non-framework frame
- Reads code snippet (±5 lines)
- Extracts function/class context
- Resolves repository info

**Killer feature**: Shows *exactly* where test failed.

### 6. Main Analyzer ([analyzer.py](../core/execution/intelligence/analyzer.py))

Orchestrates the pipeline:

```python
analyzer = ExecutionAnalyzer(workspace_root=".", enable_ai=False)

# Single test
result = analyzer.analyze(raw_log, test_name, framework)

# Batch analysis
results = analyzer.analyze_batch(test_logs)

# Get summary
summary = analyzer.get_summary(results)
```

### 7. AI Enhancement (Optional) ([ai_enhancement.py](../core/execution/intelligence/ai_enhancement.py))

Optional AI layer that:
- Adjusts confidence (±0.1 max)
- Provides detailed explanations
- Suggests potential fixes
- **Never overrides** failure type

## Usage Examples

### Example 1: Product Defect Detection

```python
analyzer = ExecutionAnalyzer()

result = analyzer.analyze(
    raw_log="""
    test_checkout.py::test_payment FAILED
    AssertionError: assert 'Payment Successful' == 'Payment Failed'
    Expected: Payment Successful
    Actual: Payment Failed
    """,
    test_name="test_payment",
    framework="pytest"
)

print(result.classification.failure_type)  # PRODUCT_DEFECT
print(result.classification.confidence)     # 0.88
print(result.classification.reason)         
# "Product defect: Assertion failed - expected 'Payment Successful' 
#  but got 'Payment Failed'"
```

### Example 2: Automation Defect Detection

```python
result = analyzer.analyze(
    raw_log="""
    selenium.common.exceptions.NoSuchElementException: 
    Message: Unable to locate element: {"method":"xpath","selector":"//button[@id='submit']"}
    """,
    test_name="test_submit_form",
    framework="selenium"
)

print(result.classification.failure_type)  # AUTOMATION_DEFECT
print(result.classification.confidence)     # 0.92

# Get code reference
ref = result.classification.code_reference
print(f"{ref.file}:{ref.line}")  # tests/test_forms.py:42
print(ref.snippet)
# >>> 42 | driver.find_element(By.XPATH, "//button[@id='submit']").click()
```

### Example 3: Environment Issue Detection

```python
result = analyzer.analyze(
    raw_log="""
    requests.exceptions.ConnectionError: HTTPSConnectionPool(host='api.example.com', port=443): 
    Max retries exceeded with url: /v1/users (Caused by NewConnectionError(
    '<urllib3.connection.HTTPSConnection object at 0x7f8b1c2d4e10>: 
    Failed to establish a new connection: [Errno 111] Connection refused'))
    """,
    test_name="test_api_call",
    framework="pytest"
)

print(result.classification.failure_type)  # ENVIRONMENT_ISSUE
print(result.classification.confidence)     # 0.92
print(result.classification.reason)
# "Environment issue: Connection refused - check network connectivity"
```

### Example 4: Batch Analysis

```python
# Analyze multiple test logs
test_logs = [
    {"raw_log": log1, "test_name": "test_login", "framework": "pytest"},
    {"raw_log": log2, "test_name": "test_checkout", "framework": "selenium"},
    {"raw_log": log3, "test_name": "test_api", "framework": "pytest"},
]

results = analyzer.analyze_batch(test_logs)

# Get summary statistics
summary = analyzer.get_summary(results)
print(f"Product defects: {summary['product_defects']}")
print(f"Automation defects: {summary['automation_defects']}")
print(f"Average confidence: {summary['average_confidence']:.2f}")

# CI decision
if analyzer.should_fail_ci(results, [FailureType.PRODUCT_DEFECT]):
    sys.exit(1)  # Fail CI
else:
    sys.exit(0)  # Pass CI
```

### Example 5: Custom Rules

```python
from core.execution.intelligence.classifier import ClassificationRule

# Add custom rule for your application
rule = ClassificationRule(
    name="database_connection_pool_exhausted",
    conditions=["connection pool", "exhausted", "timeout"],
    failure_type=FailureType.ENVIRONMENT_ISSUE,
    confidence=0.90,
    priority=90,
    exclude_patterns=[r'test.*timeout']  # Don't match test timeouts
)

analyzer.classifier.add_rule(rule)
```

## Configuration

### Enable AI Enhancement

```python
from core.ai.providers import OpenAIProvider

# Initialize with AI provider
ai_provider = OpenAIProvider(api_key="your-key")

analyzer = ExecutionAnalyzer(
    workspace_root=".",
    enable_ai=True,
    ai_provider=ai_provider
)

result = analyzer.analyze(...)

if result.classification.ai_enhanced:
    print(f"AI insights: {result.classification.ai_reasoning}")
```

### Custom Workspace Root

```python
# For code reference resolution
analyzer = ExecutionAnalyzer(
    workspace_root="/path/to/your/project"
)
```

## CLI Reference

### Commands

#### `analyze logs`

Analyze a single log file.

```bash
crossbridge analyze logs \
  --log-file test-output.log \
  --test-name test_login \
  --framework pytest \
  --workspace . \
  --format json \
  --enable-ai \
  --fail-on product
```

#### `analyze directory`

Analyze all logs in a directory.

```bash
crossbridge analyze directory \
  --log-dir ./test-results \
  --pattern "*.log" \
  --framework pytest \
  --output analysis.json \
  --fail-on product
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--log-file` | Path to log file | Required |
| `--test-name` | Test name | Required |
| `--framework` | Framework (selenium/pytest/robot/playwright/generic) | generic |
| `--workspace` | Workspace root | Current directory |
| `--format` | Output format (json/text/summary) | text |
| `--enable-ai` | Enable AI enhancement | false |
| `--fail-on` | Exit with error if type matches (product/automation/all/none) | none |
| `--output` | Output file for results | stdout |

## CI/CD Integration

See [CI/CD Integration Guide](./EXECUTION_INTELLIGENCE_CI_INTEGRATION.md) for:
- GitHub Actions examples
- GitLab CI configuration
- Jenkins pipeline
- Azure Pipelines
- Custom integration patterns

## Performance

| Operation | Time | Scale |
|-----------|------|-------|
| Parse logs | ~100ms | Per log file |
| Extract signals | ~50ms | Per failure |
| Classify | ~50ms | Per failure |
| Resolve code | ~20ms | Per stacktrace |
| **Total (no AI)** | **~220ms** | Per test failure |
| With AI enhancement | ~500ms | Per failure (if enabled) |

**Recommendation**: Use batch analysis for >10 log files.

## Testing

Run tests:

```bash
pytest tests/test_execution_intelligence.py -v
```

Coverage:

```bash
pytest tests/test_execution_intelligence.py --cov=core.execution.intelligence
```

## Roadmap

### Phase 1 (Current)
- ✅ Framework-agnostic log parsing
- ✅ Deterministic classification
- ✅ Code reference resolution
- ✅ CLI commands
- ✅ CI/CD integration

### Phase 2 (Next)
- [ ] Historical correlation
- [ ] Flaky test detection integration
- [ ] Custom framework adapters
- [ ] Confidence calibration
- [ ] Classification rule tuning

### Phase 3 (Future)
- [ ] Real-time streaming analysis
- [ ] Visual failure reports
- [ ] Automatic PR annotations
- [ ] Dashboard integration
- [ ] Machine learning model training

## FAQ

**Q: Does this require AI?**
A: No. The system is fully deterministic and works perfectly without AI. AI is an optional enhancement layer.

**Q: What frameworks are supported?**
A: Selenium, Pytest, Robot Framework, Playwright, and generic formats. Custom adapters can be added.

**Q: How accurate is the classification?**
A: 85-95% confidence for most common failure patterns. Unknown failures are explicitly marked.

**Q: Can I customize classification rules?**
A: Yes! Add custom rules via `classifier.add_rule()`.

**Q: Does this work offline?**
A: Yes, when AI enhancement is disabled (default).

**Q: How do I add my custom framework?**
A: Implement `LogAdapter` interface and register via `register_custom_adapter()`.

## Contributing

Contributions welcome! Focus areas:
- New framework adapters
- Additional classification rules
- Improved signal extractors
- Documentation improvements

## License

Apache 2.0

## Support

- Issues: https://github.com/crossstack-ai/crossbridge/issues
- Docs: https://docs.crossbridge.dev
- Email: support@crossbridge.dev
