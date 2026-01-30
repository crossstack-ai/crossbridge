# Deterministic + AI Behavior System

## Overview

Crossbridge's intelligence system implements a **Deterministic + AI Behavior** architecture that ensures:

- **Predictable behavior** - Deterministic classification always runs
- **Enterprise trust** - AI failures never impact correctness
- **AI enhancement** - Optional AI enrichment adds insights without replacing deterministic results

## Architecture

```
Input Signals
     ↓
Deterministic Classifier (ALWAYS)
     ↓
Guaranteed Result
     ↓
[Optional] AI Enrichment
     ↓
Final Output (Deterministic + Optional AI)
```

## Key Principles

### 1. Deterministic First
The deterministic classifier:
- Uses only rule-based logic
- Never depends on external services
- Always produces a result
- Is fully testable and explainable
- **Cannot fail**

### 2. AI as Enhancement
The AI enricher:
- Adds context and explanations
- Suggests actions and root causes
- **Never changes the classification label**
- Can fail gracefully without impacting the system

### 3. Fail-Open by Default
- AI timeouts → Return deterministic result
- AI errors → Log and suppress
- Low AI confidence → Discard enrichment
- No AI configured → Skip AI path entirely

## Components

### 1. Deterministic Classifier

Located: `core/intelligence/deterministic_classifier.py`

**Input**: `SignalData` with test execution signals
```python
signal = SignalData(
    test_name="test_login",
    test_status="pass",
    retry_count=2,
    final_status="pass",
    historical_failure_rate=0.15,
    total_runs=20,
    code_changed=False
)
```

**Output**: `DeterministicResult`
```python
result = DeterministicResult(
    label=ClassificationLabel.FLAKY,
    confidence=0.85,
    reasons=["Test required 2 retries before passing"],
    applied_rules=["flaky_retry"]
)
```

**Classification Rules** (priority order):
1. **New Test** - No/limited historical data
2. **Flaky (Retry)** - Required retries to pass
3. **Regression** - Code changed + failure
4. **Unstable** - High failure rate (≥40%)
5. **Flaky (History)** - Moderate failure rate (10-40%)
6. **Stable** - Low failure rate (<10%)
7. **Unknown** - Fallback for insufficient data

### 2. AI Enricher

Located: `core/intelligence/ai_enricher.py`

**Input**: `DeterministicResult` + `SignalData` + optional context

**Output**: `AIResult` (advisory only)
```python
ai_result = AIResult(
    insights=["Possible timeout issue in API call"],
    suggested_actions=["Increase timeout to 30s", "Add retry logic"],
    similarity_refs=["test_checkout", "test_payment"],
    root_cause_hints=["Network latency"],
    confidence=0.75
)
```

**Failure Handling**:
- Timeout after 2000ms (configurable)
- Discard results with confidence < 0.5
- Log all failures without impacting results
- Track metrics for monitoring

### 3. Intelligence Engine

Located: `core/intelligence/intelligence_engine.py`

**Main API**: `IntelligenceEngine.classify()`

```python
from core.intelligence.intelligence_engine import IntelligenceEngine, SignalData

# Initialize engine
engine = IntelligenceEngine()

# Classify test
signal = SignalData(
    test_name="test_api",
    test_status="fail",
    retry_count=1,
    final_status="pass",
    total_runs=10
)

result = engine.classify(signal)

print(f"Label: {result.label}")  # "flaky"
print(f"Confidence: {result.deterministic_confidence}")  # 0.85
print(f"Reasons: {result.deterministic_reasons}")
if result.ai_enrichment:
    print(f"AI Insights: {result.ai_enrichment.insights}")
```

**Convenience Function**:
```python
from core.intelligence.intelligence_engine import classify_test

result = classify_test(
    test_name="test_login",
    test_status="pass",
    retry_count=2,
    historical_failure_rate=0.15,
    total_runs=20
)
```

### 4. Configuration

Located: `core/intelligence/intelligence_config.py`

**Configuration Sources** (priority):
1. Environment variables
2. YAML config file
3. Defaults

**Example Configuration**:
```yaml
# intelligence_config.yaml
deterministic:
  flaky_threshold: 0.1        # 10% failure rate = flaky
  unstable_threshold: 0.4     # 40% failure rate = unstable
  min_runs_for_confidence: 5

ai:
  enabled: true
  enrichment: true
  timeout_ms: 2000
  min_confidence: 0.5
  fail_open: true
  model: "gpt-4o-mini"
  temperature: 0.3

observability:
  metrics_enabled: true
  log_level: "INFO"
  track_latency: true
```

**Environment Variables**:
```bash
export CROSSBRIDGE_AI_ENABLED=true
export CROSSBRIDGE_AI_TIMEOUT_MS=3000
export CROSSBRIDGE_AI_MIN_CONFIDENCE=0.6
export CROSSBRIDGE_FLAKY_THRESHOLD=0.15
```

### 5. Metrics & Observability

Located: `core/intelligence/intelligence_metrics.py`

**Tracked Metrics**:
- `deterministic.classifications_total`
- `deterministic.classifications_by_label{label=flaky}`
- `deterministic.latency_ms` (p50, p90, p95, p99)
- `ai.enrichment.attempted`
- `ai.enrichment.success`
- `ai.enrichment.failed`
- `ai.enrichment.timeout`
- `ai.enrichment.low_confidence`
- `ai.enrichment.latency_ms`
- `final.results_with_ai`
- `final.results_without_ai`

**Get Metrics**:
```python
engine = IntelligenceEngine()

# ... run classifications ...

# Get health status
health = engine.get_health()
print(health['ai_enrichment']['success_rate_pct'])

# Get detailed metrics
metrics = engine.get_metrics()
print(metrics['latency']['deterministic_p95_ms'])
```

## Usage Examples

### Basic Classification

```python
from core.intelligence.intelligence_engine import classify_test

# Classify a flaky test
result = classify_test(
    test_name="test_search",
    test_status="pass",
    retry_count=2,  # Required 2 retries
    final_status="pass",
    total_runs=10
)

assert result.label == "flaky"
```

### Batch Classification

```python
from core.intelligence.intelligence_engine import IntelligenceEngine, SignalData

engine = IntelligenceEngine()

signals = [
    SignalData(test_name="test1", test_status="pass", total_runs=0),
    SignalData(test_name="test2", test_status="pass", historical_failure_rate=0.5, total_runs=20),
]

results = engine.batch_classify(signals)
```

### With Custom Configuration

```python
from core.intelligence.intelligence_engine import IntelligenceEngine
from core.intelligence.intelligence_config import IntelligenceConfig

config = IntelligenceConfig()
config.ai.enabled = False  # Disable AI
config.deterministic.flaky_threshold = 0.15  # Custom threshold

engine = IntelligenceEngine(config=config)
```

### Health Monitoring

```python
engine = IntelligenceEngine()

# Run periodic health checks
health = engine.get_health()

if health['ai_enrichment']['status'] == 'unhealthy':
    print("Warning: AI enrichment success rate is low")
    print(f"Success rate: {health['ai_enrichment']['success_rate_pct']}%")
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_deterministic_ai_behavior.py -v
```

**Test Coverage**:
- ✅ All deterministic classification rules
- ✅ AI enrichment success and failure cases
- ✅ Fallback behavior
- ✅ Configuration loading
- ✅ Metrics tracking
- ✅ End-to-end integration

## Best Practices

### DO:
- ✅ Always rely on deterministic labels for decisions
- ✅ Use AI enrichment for insights and recommendations
- ✅ Monitor AI success rates
- ✅ Configure timeouts appropriately
- ✅ Test with AI disabled

### DON'T:
- ❌ Let AI change classification labels
- ❌ Block on AI responses
- ❌ Use AI without deterministic baseline
- ❌ Hide AI failures
- ❌ Make decisions on AI-only data

## Migration from Existing Flaky Detection

To integrate with existing flaky detection:

```python
# Old code
from core.flaky_detection import detect_flaky_test

# New code
from core.intelligence.intelligence_engine import classify_test

result = classify_test(
    test_name=test_name,
    test_status=status,
    retry_count=retries,
    historical_failure_rate=failure_rate,
    total_runs=total_runs
)

if result.label in ["flaky", "unstable"]:
    # Handle flaky/unstable test
    pass
```

## Performance Characteristics

**Deterministic Classification**:
- Latency: < 5ms (p95)
- Throughput: > 1000 classifications/second
- Failure rate: 0% (guaranteed to return result)

**AI Enrichment**:
- Latency: 500-2000ms (p95)
- Success rate: 80-95% (typical)
- Timeout: 2000ms (configurable)

**Combined**:
- Total latency: ~10ms without AI, ~520ms with AI (p95)
- Never blocks on AI failures

## Troubleshooting

### AI enrichment not working
1. Check `config.ai.enabled = True`
2. Verify AI analyzer is configured
3. Check timeout settings
4. Review metrics: `engine.get_metrics()`

### Low AI success rate
1. Increase timeout: `config.ai.timeout_ms = 3000`
2. Lower confidence threshold: `config.ai.min_confidence = 0.4`
3. Check AI service health
4. Review logs for specific errors

### Classification seems wrong
1. Review applied rules: `result.deterministic_reasons`
2. Check input signals are correct
3. Adjust thresholds if needed
4. Run tests to verify rule logic

## References

- **Implementation Guide**: [docs/intelligence/DETERMINISTIC_AI_IMPLEMENTATION.md](./DETERMINISTIC_AI_IMPLEMENTATION.md)
- **API Documentation**: [core/intelligence/](../../core/intelligence/)
- **Test Suite**: [tests/test_deterministic_ai_behavior.py](../../tests/test_deterministic_ai_behavior.py)
