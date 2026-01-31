# AI Capabilities

> **Intelligent test analysis, failure classification, and risk-based insights**

CrossBridge AI provides advanced AI-powered capabilities for test automation intelligence and optimization.

---

## 🧠 Core AI Features

### 1. **Failure Classification** 🎯
Automatically classify test failures into actionable categories:

**5 Failure Types**:
- **PRODUCT_DEFECT** 🐛 - Real bugs in application code → Fail CI/CD
- **AUTOMATION_ISSUE** 🔧 - Test code problems (syntax, imports, setup)
- **LOCATOR_ISSUE** 🎯 - UI element selectors broken/changed
- **ENVIRONMENT_ISSUE** 🌐 - Infrastructure failures (network, DB, timeouts)
- **FLAKY_TEST** 🔀 - Intermittent failures, timing issues

**How it works**:
```bash
# Analyze single test failure
crossbridge analyze logs --log-file test_output.log --framework pytest

# Output:
# Classification: LOCATOR_ISSUE
# Confidence: 0.89
# Reason: NoSuchElementException detected
# Code reference: tests/test_login.py:42
```

**Key benefits**:
- ✅ **Works without AI** - Deterministic, rule-based classification (85-95% accuracy)
- ✅ **Optional AI enhancement** - LLM provides deeper insights (never overrides deterministic)
- ✅ **Framework-agnostic** - Supports all 13 frameworks
- ✅ **CI/CD integration** - Fail builds only on PRODUCT_DEFECT

**Documentation**: [Execution Intelligence Guide](EXECUTION_INTELLIGENCE.md)

---

### 2. **Flaky Test Detection** 🔀
ML-powered detection of intermittent test failures:

**Detection Algorithm**:
- **Isolation Forest** ML model with 200 decision trees
- **10 feature analysis**: Failure rate, pass/fail switching, timing variance, error diversity, retry patterns
- **Severity classification**: Critical, High, Medium, Low

**Usage**:
```bash
# Detect flaky tests
crossbridge flaky detect --db-url postgresql://user:pass@host/db

# List by severity
crossbridge flaky list --severity critical

# Get detailed report
crossbridge flaky report test_user_login
```

**Grafana Dashboard**:
- 9 interactive panels
- Real-time flaky test monitoring
- Historical trend analysis
- Confidence score distribution

**Documentation**: [Flaky Detection Guide](flaky-detection/FLAKY_DETECTION_IMPLEMENTATION_SUMMARY.md)

---

### 3. **Semantic Test Understanding** 🔍
AI-powered semantic analysis of test intent and behavior:

**Capabilities**:
- **Natural language search**: "Find all login timeout tests"
- **Duplicate detection**: Identify tests with >90% similarity
- **Test clustering**: Group related tests by functional area
- **Intent extraction**: Understand what tests actually validate

**Embedding Providers**:
- **OpenAI**: text-embedding-3-large (3072 dim, $0.13/1M tokens)
- **OpenAI**: text-embedding-3-small (1536 dim, $0.02/1M tokens)
- **Ollama**: nomic-embed-text (768 dim, free, local)
- **HuggingFace**: all-MiniLM-L6-v2 (384 dim, free)

**Usage**:
```bash
# Index tests
crossbridge semantic index -f pytest -p ./tests

# Search semantically
crossbridge semantic search "authentication timeout handling"

# Find similar tests
crossbridge semantic similar test_login_valid
```

**Use cases**:
- Find tests affected by code changes
- Detect duplicate test coverage
- Map legacy tests to modern equivalents
- Discover coverage gaps

**Documentation**: [Semantic Engine Guide](SEMANTIC_ENGINE.md)

---

### 4. **Smart Test Selection** 🎯
AI-driven test selection using multi-signal scoring:

**Scoring Signals**:
- 40% Semantic similarity (code/test relationship)
- 30% Coverage relevance (code coverage mapping)
- 20% Failure history (historical patterns)
- 10% Flakiness penalty

**Execution Strategies**:
| Strategy | Selection Criteria | Reduction | Use Case |
|----------|-------------------|-----------|----------|
| **Smoke** | Tagged smoke/critical | 80-95% | PR validation |
| **Impacted** | Git diff + coverage + semantic | 60-80% | Feature dev |
| **Risk** | Failure rate + churn + criticality | 40-60% | Release pipeline |
| **Full** | All tests | 0% | Nightly regression |

**Usage**:
```bash
# Run impacted tests only
crossbridge exec run --framework pytest --strategy impacted --base-branch main

# Risk-based with budget
crossbridge exec run --framework robot --strategy risk --max-tests 100
```

**Documentation**: [Execution Orchestration Guide](EXECUTION_ORCHESTRATION.md)

---

### 5. **Risk Scoring & Prioritization** ⚠️
Calculate risk scores for tests and features:

**Risk Factors**:
- Historical failure rate
- Code churn in tested areas
- Criticality tags (business impact)
- Flakiness score
- Time since last execution

**Risk Levels**:
- 🔴 **Critical**: Frequent failures in critical paths
- 🟡 **High**: Unstable tests in important areas
- 🟢 **Medium**: Occasional failures
- ⚪ **Low**: Stable, non-critical tests

**Use cases**:
- Prioritize test maintenance
- Focus regression testing
- Allocate QA resources
- Risk-based release decisions

---

### 6. **AI-Assisted Test Generation** 🤖
Generate tests from requirements or existing patterns:

**Capabilities**:
- Convert requirements to test cases
- Generate test data variations
- Create similar tests based on patterns
- Auto-complete test implementations

**Validation System**:
- **Confidence scoring** (0.0-1.0)
- **Human review** required for <0.8 confidence
- **Diff analysis** before applying
- **Rollback support** for safety

**Usage**:
```bash
# Generate test with validation
crossbridge ai-transform generate \
  --prompt "Create login test with timeout handling" \
  --framework playwright

# Review transformation
crossbridge ai-transform show ai-abc123 --show-diff

# Apply if approved
crossbridge ai-transform approve ai-abc123 --apply
```

**Documentation**: [AI Transformation Validation](ai/AI_TRANSFORMATION_VALIDATION.md)

---

### 7. **Explainability & Confidence** 📊
All AI decisions include human-readable explanations:

**Confidence Calibration**:
- Logarithmic scoring for reliable results
- Multi-signal validation
- Explicit uncertainty markers
- Never auto-merge low-confidence results

**Explainability Features**:
- **Reasoning**: Why this classification?
- **Evidence**: What signals were detected?
- **Alternatives**: What else was considered?
- **Confidence**: How certain is this result?

**Example**:
```json
{
  "classification": "LOCATOR_ISSUE",
  "confidence": 0.89,
  "reasoning": "NoSuchElementException detected in Selenium logs",
  "evidence": [
    {"type": "exception_pattern", "weight": 0.9},
    {"type": "locator_keyword", "weight": 0.85}
  ],
  "alternatives": [
    {"type": "ENVIRONMENT_ISSUE", "confidence": 0.15}
  ]
}
```

---

## 🚦 AI Configuration

All AI features are configurable in `crossbridge.yml`:

```yaml
ai:
  # Semantic Engine
  semantic_engine:
    enabled: true
    embedding:
      provider: openai  # or anthropic, ollama, huggingface
      model: text-embedding-3-large
    
  # Failure Classification
  execution_intelligence:
    enabled: true
    ai_enhancement: false  # Optional, works without AI
    
  # Flaky Detection
  flaky_detection:
    enabled: true
    ml_model: isolation_forest
    
  # Smart Test Selection
  test_selection:
    enabled: true
    weights:
      semantic_similarity: 0.4
      coverage_relevance: 0.3
      failure_history: 0.2
      flakiness_penalty: 0.1
```

---

## 📊 AI Performance Metrics

**Failure Classification**:
- Accuracy: 85-95% (deterministic)
- Processing time: ~220ms per failure
- Framework coverage: 11 frameworks

**Flaky Detection**:
- Detection rate: ~85% of known flaky tests
- False positive rate: <5%
- Processing: 50 tests/second

**Semantic Search**:
- Search latency: <100ms
- Embedding cost: $0.002-$0.013 per 1000 tests
- Index time: 1000 tests in ~30 seconds

---

## 🔌 AI Provider Support

CrossBridge supports multiple AI providers:

| Provider | Use Case | Cost | Setup |
|----------|----------|------|-------|
| **OpenAI** | Embeddings, LLM | $$$ | API key required |
| **Anthropic (Voyage AI)** | Embeddings | $$ | API key required |
| **Ollama** | Local embeddings | Free | Local install |
| **HuggingFace** | Local embeddings | Free | Offline capable |

**Configuration**:
```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Ollama (local)
ollama pull nomic-embed-text
```

---

## ❓ AI vs Rule-Based

**When AI is used**:
- Semantic search and similarity
- Test generation and suggestions
- Natural language understanding

**When AI is NOT used**:
- Failure classification (rule-based primary)
- Flaky detection (ML, not LLM)
- Test execution and orchestration

**Philosophy**: AI enhances, never replaces, deterministic systems.

---

## 📚 Learn More

- [Execution Intelligence](EXECUTION_INTELLIGENCE.md) - Failure classification details
- [Semantic Engine](SEMANTIC_ENGINE.md) - Embedding system architecture
- [Flaky Detection](flaky-detection/) - ML-based flaky test detection
- [AI Transformation](ai/AI_TRANSFORMATION_VALIDATION.md) - Safe AI-generated code
- [Explainability System](EXPLAINABILITY_SYSTEM.md) - How explanations work

---

**Ready to enable AI features?** Check the [configuration guide](configuration/UNIFIED_CONFIGURATION_GUIDE.md).
