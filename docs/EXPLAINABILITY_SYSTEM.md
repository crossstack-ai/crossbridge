# Explainability System for Deterministic Failure Classification

## Overview

The **Explainability System** provides comprehensive confidence explanations for test failure classifications. It decouples classification from explanation, tracks rule influence, assesses signal quality, and generates CI-ready artifacts.

**Status**: ✅ **Phase 1 Complete** - Core framework implemented and tested

---

## Features

### 1. Rule Influence Tracking
- **What**: Tracks which rules matched and their contribution to the final classification
- **Why**: Answers "Why did the classifier choose this category?"
- **How**: Each rule returns influence metadata with weight, matched status, and explanation
- **Output**: Normalized contributions that sum to 1.0

### 2. Signal Quality Assessment
- **What**: Evaluates reliability of input signals (stacktrace, error messages, retries, etc.)
- **Why**: Answers "How reliable is this classification?"
- **How**: 5 framework-agnostic signals evaluated with quality scores (0.0-1.0)
- **Output**: Quality scores with evidence strings

### 3. Evidence Extraction
- **What**: Summarizes supporting evidence (stacktraces, error messages, logs)
- **Why**: Provides context without overwhelming with raw data
- **How**: Smart summarization with size limits (max 150 chars)
- **Output**: Human-readable summaries (NO raw logs, NO full stacktraces)

### 4. Confidence Computation
- **What**: Standardized formula combining rule and signal scores
- **Why**: Consistent, explainable confidence across all frameworks
- **How**: `confidence = 0.7 × rule_score + 0.3 × signal_score`
- **Output**: Single confidence score (0.0-1.0) with breakdown

### 5. CI Integration
- **What**: Generates artifacts for CI systems and dashboards
- **Why**: Machine-readable output for automation
- **How**: JSON artifacts + text summaries + PR comments
- **Output**: Structured files in `ci-artifacts/failure_explanations/`

### 6. Framework-Agnostic Design
- **What**: Works consistently across all 13 supported frameworks
- **Why**: No framework-specific logic in explainability layer
- **How**: Maps framework-specific signals to standard signal names
- **Output**: Identical confidence for identical patterns across frameworks

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ExplainableClassifier                        │
│  (Extends DeterministicClassifier with explainability)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ├──► 1. Run Deterministic Classification
                              │      (Existing logic, returns label + confidence)
                              │
                              ├──► 2. Compute Rule Influences
                              │      (Track which rules matched, weights, contributions)
                              │
                              ├──► 3. Evaluate Signal Quality
                              │      (5 standard signals: stacktrace, error, retry, history, correlation)
                              │
                              ├──► 4. Extract Evidence Context
                              │      (Summarize stacktrace, error message, related tests)
                              │
                              ├──► 5. Generate Explanation
                              │      (Combine all data, compute final confidence)
                              │
                              └──► 6. Return (Result, Explanation)

┌─────────────────────────────────────────────────────────────────┐
│                    ConfidenceExplanation                        │
│  (Main output consumed by CI systems, dashboards, humans)      │
├─────────────────────────────────────────────────────────────────┤
│  • failure_id: str                                             │
│  • final_confidence: float                                     │
│  • category: str                                               │
│  • primary_rule: str                                           │
│  • rule_influence: List[RuleInfluence]                        │
│  • signal_quality: List[SignalQuality]                        │
│  • evidence_context: EvidenceContext                          │
│  • confidence_breakdown: ConfidenceBreakdown                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Data Models

### FailureClassification
Baseline classification output (framework-agnostic).

```python
@dataclass
class FailureClassification:
    failure_id: str          # Unique ID (e.g., "F-ABC123")
    category: str            # Classification category
    confidence: float        # Base confidence (0.0-1.0)
    primary_rule: str        # Primary rule that matched
    signals_used: List[str]  # Signals used in classification
    timestamp: str           # ISO timestamp
```

### RuleInfluence
Explains why a rule contributed to classification.

```python
@dataclass
class RuleInfluence:
    rule_name: str      # Rule identifier (e.g., "flaky_retry")
    weight: float       # Rule priority weight
    matched: bool       # Did rule match?
    contribution: float # Normalized contribution (0.0-1.0)
    explanation: str    # Human-readable reason
```

**Example**:
```python
RuleInfluence(
    rule_name="flaky_retry",
    weight=0.9,
    matched=True,
    contribution=0.65,
    explanation="Test required 2 retries before passing"
)
```

### SignalQuality
Reliability assessment of input signals.

```python
@dataclass
class SignalQuality:
    signal_name: str     # Standard signal name
    quality_score: float # Quality (0.0-1.0)
    evidence: str        # Supporting evidence
```

**Standard Signals**:
1. `stacktrace_presence` - Is stacktrace available?
2. `error_message_stability` - Is error consistent?
3. `retry_consistency` - Does failure reproduce?
4. `historical_frequency` - Historical data reliability
5. `cross_test_correlation` - Related test patterns

**Example**:
```python
SignalQuality(
    signal_name="retry_consistency",
    quality_score=0.90,
    evidence="Failure reproduced in all 3 retries"
)
```

### EvidenceContext
Supporting evidence (summaries only, NO raw data).

```python
@dataclass
class EvidenceContext:
    stacktrace_summary: Optional[str]  # Max 150 chars
    error_message_summary: Optional[str]  # Max 150 chars
    similar_failures: List[str]  # Related failure IDs
    related_tests: List[str]  # Related test names
    logs_summary: List[str]  # Max 5 lines, ERROR/WARN only
```

### ConfidenceBreakdown
Detailed confidence computation.

```python
@dataclass
class ConfidenceBreakdown:
    rule_score: float        # Aggregated rule score
    signal_score: float      # Average signal quality
    final_confidence: float  # Final computed confidence
    formula: str = "0.7 * rule_score + 0.3 * signal_score"
```

### ConfidenceExplanation
Main API output (combines all above).

```python
@dataclass
class ConfidenceExplanation:
    failure_id: str
    final_confidence: float
    category: str
    primary_rule: str
    rule_influence: List[RuleInfluence]
    signal_quality: List[SignalQuality]
    evidence_context: EvidenceContext
    confidence_breakdown: ConfidenceBreakdown
    timestamp: str
    framework: Optional[str]
```

---

## APIs

### Main Classification API

```python
from core.intelligence.explainable_classifier import classify_and_explain
from core.intelligence.deterministic_classifier import SignalData

# Prepare signal data
signal = SignalData(
    test_name="test_login",
    test_suite="auth.tests",
    framework="pytest",
    test_status="pass",
    final_status="pass",
    retry_count=2,
    total_runs=50,
    historical_failure_rate=0.12,
    consecutive_passes=0,
    consecutive_failures=0,
    code_changed=False,
    error_message="TimeoutException: Element not found"
)

# Classify with explanation
result, explanation = classify_and_explain(signal, failure_id="F-LOGIN-123")

# Access results
print(f"Category: {result.label.value}")
print(f"Confidence: {explanation.final_confidence:.1%}")
print(f"Primary Rule: {explanation.primary_rule}")
```

### CI Integration

```python
from core.intelligence.explainability import save_ci_artifacts, generate_pr_comment

# Save artifacts
artifact_path = save_ci_artifacts(explanation, output_dir=".")
# Creates:
#   ci-artifacts/failure_explanations/{failure_id}.json
#   ci-artifacts/failure_explanations/{failure_id}.txt

# Generate PR comment
pr_comment = generate_pr_comment(explanation)
# Post to GitHub/GitLab/etc.
```

### JSON Serialization

```python
# Serialize to JSON
json_str = explanation.to_json()

# Save to file
explanation.save_to_file("failure_explanation.json")

# Generate text summary
summary = explanation.to_ci_summary()
```

---

## Confidence Formula

### Standard Formula

```
confidence = 0.7 × rule_score + 0.3 × signal_score
```

**Why This Formula?**
- **70% weight on rules**: Deterministic logic is primary classification mechanism
- **30% weight on signals**: Data quality impacts confidence
- **Normalized**: Rule contributions sum to 1.0, signal quality averaged

### Example Computation

```python
# Rule influences (after normalization)
rules = [
    RuleInfluence("flaky_retry", 0.9, True, 0.8, "..."),  # 80%
    RuleInfluence("regression", 0.8, True, 0.2, "..."),   # 20%
]
rule_score = 0.8 + 0.2 = 1.0  # Sum of matched contributions

# Signal qualities
signals = [
    SignalQuality("retry_consistency", 0.90, "..."),
    SignalQuality("historical_frequency", 0.70, "..."),
    SignalQuality("stacktrace_presence", 0.50, "..."),
]
signal_score = (0.90 + 0.70 + 0.50) / 3 = 0.70  # Average

# Final confidence
confidence = 0.7 × 1.0 + 0.3 × 0.70 = 0.91 (91%)
```

---

## Rule Influence Tracking

### How Rules Are Evaluated

Each rule in `DeterministicClassifier` is enhanced to emit `RuleInfluence`:

```python
def _eval_flaky_retry_influence(self, signal: SignalData, result: DeterministicResult) -> RuleInfluence:
    """Evaluate flaky retry rule influence."""
    matched = signal.retry_count > 0 and signal.final_status == "pass"
    weight = 0.9  # High priority
    
    if matched:
        explanation = f"Test failed initially but passed after {signal.retry_count} retry(ies)"
    else:
        explanation = "Test was not retried" if signal.retry_count == 0 else "No flaky pattern"
    
    return RuleInfluence(
        rule_name="flaky_retry",
        weight=weight,
        matched=matched,
        contribution=weight if matched else 0.0,
        explanation=explanation
    )
```

### Rule Priority Weights

| Rule           | Weight | Description                          |
|----------------|--------|--------------------------------------|
| new_test       | 1.0    | Highest - limited execution history  |
| flaky_retry    | 0.9    | Very high - retry-based detection    |
| regression     | 0.85   | High - code change + failure         |
| unstable       | 0.8    | High - consistently high failure rate|
| flaky_history  | 0.7    | Medium - moderate failure rate       |
| stable         | 0.6    | Baseline - low failure rate          |

### Normalization

Rule contributions are normalized to sum to 1.0:

```python
def aggregate_rule_influence(influences: List[RuleInfluence]) -> List[RuleInfluence]:
    """Normalize rule contributions to sum to 1.0"""
    total = sum(r.contribution for r in influences if r.matched)
    if total > 0:
        for influence in influences:
            if influence.matched:
                influence.contribution = influence.contribution / total
    return influences
```

---

## Signal Quality Assessment

### Standard Signals (Framework-Agnostic)

#### 1. Stacktrace Presence

**Evaluates**: Availability and completeness of stacktrace

```python
quality = SignalEvaluator.evaluate_stacktrace_presence(
    has_stacktrace=True,
    stacktrace_lines=15
)
# Returns: 0.9 (complete stacktrace)
```

**Quality Mapping**:
- No stacktrace: 0.3
- Partial (1-5 lines): 0.5
- Moderate (6-10 lines): 0.7
- Complete (11+ lines): 0.9

#### 2. Error Message Stability

**Evaluates**: Consistency of error message

```python
quality = SignalEvaluator.evaluate_error_message_stability(
    error_message="TimeoutException: Element not found",
    is_consistent=True
)
# Returns: 0.85 (consistent error)
```

**Quality Mapping**:
- No error message: 0.2
- Inconsistent error: 0.4
- Consistent error: 0.85

#### 3. Retry Consistency

**Evaluates**: Reproducibility of failure

```python
quality = SignalEvaluator.evaluate_retry_consistency(
    retry_count=3,
    failure_reproduced=True
)
# Returns: 0.90 (consistent failure)
```

**Framework Mapping**:
- Selenium: `retries` → `retry_consistency`
- Pytest: `reruns` → `retry_consistency`
- Robot: `retry keyword` → `retry_consistency`

**Quality Mapping**:
- No retries: 0.5
- Inconsistent (flaky): 0.4
- Consistent reproduction: 0.9

#### 4. Historical Frequency

**Evaluates**: Reliability of historical data

```python
quality = SignalEvaluator.evaluate_historical_frequency(
    historical_failure_rate=0.15,
    total_runs=100
)
# Returns: 0.8 (large sample)
```

**Quality Mapping**:
- < 5 runs: 0.3
- 5-20 runs: 0.6
- 21-50 runs: 0.7
- 51+ runs: 0.8

#### 5. Cross-Test Correlation

**Evaluates**: Pattern detection across related tests

```python
quality = SignalEvaluator.evaluate_cross_test_correlation(
    similar_failure_count=8,
    related_test_count=10
)
# Returns: 0.85 (strong pattern)
```

**Quality Mapping**:
- No correlation: 0.4
- Weak (< 50%): 0.6
- Moderate (50-70%): 0.75
- Strong (> 70%): 0.85

---

## Evidence Extraction

### Summary-Only Approach

**NO raw logs, NO full stacktraces** - only human-readable summaries.

### Stacktrace Summarization

```python
EvidenceExtractor.summarize_stacktrace(stacktrace)
```

**Rules**:
- Extract last meaningful line
- Max 150 characters
- No full stack dumps

**Example**:
```
Input: "Traceback (most recent call last):\n  File test.py, line 42...\nTimeoutException: Element not found: LoginButton"
Output: "TimeoutException: Element not found: LoginButton"
```

### Error Message Summarization

```python
EvidenceExtractor.summarize_error_message(error_message)
```

**Rules**:
- Remove prefixes (ERROR:, FAIL:, etc.)
- Remove timestamps
- Max 150 characters
- Truncate with "..." if needed

**Example**:
```
Input: "ERROR: AssertionError: Expected total=100.00, got 95.00 - payment calculation failed"
Output: "AssertionError: Expected total=100.00, got 95.00 - payment calculation failed"
```

### Log Summarization

```python
EvidenceExtractor.summarize_logs(logs)
```

**Rules**:
- Only ERROR and WARN lines
- Max 5 lines
- Remove timestamps

**Example**:
```
Input: [
    "2024-01-15 INFO: Starting test",
    "2024-01-15 DEBUG: Navigating to page",
    "2024-01-15 ERROR: Element not found",
    "2024-01-15 WARN: Retry attempt 1",
    "2024-01-15 INFO: Test complete"
]
Output: [
    "Element not found",
    "Retry attempt 1"
]
```

---

## CI Integration

### Artifact Structure

```
ci-artifacts/
└── failure_explanations/
    ├── F-ABC123.json    # Structured data
    └── F-ABC123.txt     # Text summary
```

### JSON Artifact

**Location**: `ci-artifacts/failure_explanations/{failure_id}.json`

**Content**:
```json
{
  "failure_id": "F-ABC123",
  "final_confidence": 0.82,
  "category": "flaky",
  "primary_rule": "flaky_retry",
  "rule_influence": [
    {
      "rule_name": "flaky_retry",
      "weight": 0.9,
      "matched": true,
      "contribution": 0.65,
      "explanation": "Test required 2 retries before passing"
    }
  ],
  "signal_quality": [
    {
      "signal_name": "retry_consistency",
      "quality_score": 0.90,
      "evidence": "Failure reproduced in all retries"
    }
  ],
  "evidence_context": {
    "stacktrace_summary": "TimeoutException: Element not found",
    "error_message_summary": "Element not found: LoginButton",
    "similar_failures": ["F-ABC122", "F-ABC124"],
    "related_tests": ["test_login", "test_logout"]
  },
  "confidence_breakdown": {
    "rule_score": 0.65,
    "signal_score": 0.90,
    "final_confidence": 0.82,
    "formula": "0.7 * rule_score + 0.3 * signal_score"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "framework": "pytest"
}
```

### Text Summary

**Location**: `ci-artifacts/failure_explanations/{failure_id}.txt`

**Content**:
```
Failure: flaky (Confidence: 82%)

Primary Rule:
- flaky_retry (65%)

Strong Signals:
- Retry Consistency (90%)

Evidence:
- TimeoutException: Element not found
- Element not found: LoginButton
```

### PR Comment

**Markdown-formatted comment for GitHub/GitLab**:

```markdown
## 🔍 Failure Analysis: F-ABC123

**Category**: flaky  
**Confidence**: 82%

### Primary Contributing Rule
flaky_retry

### Rule Influence
- **flaky_retry**: 65% - Test required 2 retries before passing

### Signal Quality
- **retry_consistency**: 90% - Failure reproduced in all retries

### Evidence
Element not found: LoginButton

---
<details>
<summary>Detailed Breakdown</summary>

**Confidence Computation**:
- Rule Score: 0.65
- Signal Score: 0.90
- Formula: 0.7 * rule_score + 0.3 * signal_score

</details>
```

---

## Framework-Agnostic Behavior

### Design Principle

**Same signals → Same confidence**, regardless of framework.

### Signal Mapping

| Framework     | Retry Mechanism     | Maps To               |
|---------------|---------------------|-----------------------|
| Pytest        | `@pytest.mark.reruns` | `retry_consistency`  |
| Selenium      | `retry` decorator   | `retry_consistency`   |
| Robot         | `RETRY` keyword     | `retry_consistency`   |
| Playwright    | `retries` config    | `retry_consistency`   |
| Cypress       | `cypress-retry`     | `retry_consistency`   |

### Verification Test

```python
frameworks = ["pytest", "selenium_java", "robot", "playwright", "cypress"]
confidences = []

for framework in frameworks:
    signal = SignalData(
        framework=framework,
        retry_count=1,
        total_runs=30,
        historical_failure_rate=0.15,
        # ... (identical signals)
    )
    
    result, explanation = classify_and_explain(signal)
    confidences.append(explanation.final_confidence)

# All confidences should be identical
assert max(confidences) - min(confidences) < 0.001
```

---

## Testing

### Test Coverage

**36/36 tests passing** (100%)

```
TestConfidenceComputation (5 tests)
├── test_compute_confidence_basic
├── test_compute_confidence_max_capped
├── test_compute_confidence_min_values
├── test_aggregate_rule_influence_normalization
└── test_aggregate_rule_influence_no_matches

TestSignalEvaluator (8 tests)
├── test_evaluate_stacktrace_presence_none
├── test_evaluate_stacktrace_presence_complete
├── test_evaluate_error_message_stability_consistent
├── test_evaluate_retry_consistency_reproduced
├── test_evaluate_retry_consistency_flaky
├── test_evaluate_historical_frequency_large_sample
├── test_evaluate_historical_frequency_small_sample
└── test_evaluate_cross_test_correlation_strong

TestEvidenceExtractor (5 tests)
├── test_summarize_stacktrace_basic
├── test_summarize_stacktrace_none
├── test_summarize_error_message_basic
├── test_summarize_error_message_truncation
└── test_summarize_logs_filtering

TestExplainFailureAPI (2 tests)
├── test_explain_failure_complete
└── test_explain_failure_confidence_computation

TestExplainableClassifier (4 tests)
├── test_classify_with_explanation_flaky
├── test_classify_with_explanation_regression
├── test_classify_with_explanation_new_test
└── test_classify_and_explain_convenience_function

TestCIIntegration (4 tests)
├── test_save_ci_artifacts
├── test_generate_pr_comment
├── test_to_ci_summary
└── test_to_json

TestFrameworkAgnostic (8 tests)
├── test_classification_across_frameworks[pytest]
├── test_classification_across_frameworks[selenium_pytest]
├── test_classification_across_frameworks[selenium_java]
├── test_classification_across_frameworks[robot]
├── test_classification_across_frameworks[playwright]
├── test_classification_across_frameworks[cypress]
├── test_classification_across_frameworks[restassured_java]
└── test_confidence_formula_consistency
```

### Running Tests

```bash
# Run all explainability tests
python -m pytest tests/intelligence/test_explainability.py -v

# Run with coverage
python -m pytest tests/intelligence/test_explainability.py --cov=core.intelligence.explainability --cov-report=term-missing
```

---

## Demo

### Running the Demo

```bash
python demo_explainability.py
```

### Demo Scenarios

1. **Flaky Test** - Retry-based detection
2. **Regression** - Code change + failure
3. **New Test** - Limited execution history
4. **CI Integration** - Artifact generation
5. **Framework-Agnostic** - Cross-framework consistency
6. **Confidence Formula** - Computation breakdown
7. **Complete Explanation** - Full details

---

## Next Steps (Phase 2+)

### Phase 2: Visual Dashboards
- [ ] Grafana integration for confidence visualization
- [ ] Trend charts for confidence drift over time
- [ ] Rule contribution heatmaps

### Phase 3: Confidence Drift Monitoring
- [ ] Track confidence changes over time
- [ ] Alert on significant drift
- [ ] Historical confidence analysis

### Phase 4: Human Feedback Loop
- [ ] Collect human annotations ("I agree/disagree")
- [ ] Feed back into calibration
- [ ] Track agreement rates

### Phase 5: Advanced Analytics
- [ ] Identify low-confidence patterns
- [ ] Recommend test improvements
- [ ] Confidence prediction for new tests

---

## FAQ

### Q: Why decouple classification from explanation?

**A**: Classification needs to be fast and deterministic. Explanation is for humans and CI systems, generated after classification. This separation allows:
- Classification logic stays simple
- Explanation adds zero runtime overhead
- Different consumers can use same classification with different explanation detail levels

### Q: Why 0.7 × rule + 0.3 × signal formula?

**A**: Based on empirical observation:
- Rules are primary classification mechanism (70% weight)
- Signals indicate data quality (30% weight)
- This ratio balances deterministic logic with data reliability

### Q: Can I change the weights?

**A**: Yes, but keep formula consistent across all frameworks:

```python
# In explainability.py
def compute_confidence(rule_score: float, signal_score: float, 
                       rule_weight: float = 0.7,
                       signal_weight: float = 0.3) -> float:
    return min(1.0, rule_weight * rule_score + signal_weight * signal_score)
```

### Q: Why summary-only approach for evidence?

**A**: Raw logs/stacktraces are:
- Too large for CI artifacts
- Noisy and hard to read
- Not actionable

Summaries provide:
- Human-readable context
- Actionable information
- Consistent size (< 150 chars)

### Q: How does framework-agnostic mapping work?

**A**: `SignalEvaluator` maps framework-specific signals to standard names:

```python
# All these map to "retry_consistency"
selenium_retries → retry_consistency
pytest_reruns → retry_consistency
robot_retry_keyword → retry_consistency
```

This ensures identical confidence for identical patterns across frameworks.

---

## Contact & Support

**Documentation**: See [docs/intelligence/](../docs/intelligence/)  
**Tests**: See [tests/intelligence/test_explainability.py](../tests/intelligence/test_explainability.py)  
**Demo**: Run `python demo_explainability.py`  
**Issues**: Report at https://github.com/your-org/crossbridge/issues

---

**Last Updated**: 2024-01-30  
**Version**: 1.0.0  
**Status**: ✅ Production-Ready (Phase 1)
