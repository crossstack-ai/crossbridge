# CrossBridge API Documentation

Copyright (c) 2025 Vikas Verma  
Licensed under the Apache License, Version 2.0

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Modules](#core-modules)
4. [Adapters API](#adapters-api)
5. [CLI API](#cli-api)
6. [Memory & Intelligence](#memory--intelligence)
7. [Configuration](#configuration)
8. [Integration Examples](#integration-examples)
9. [Extension Guide](#extension-guide)

---

## Overview

CrossBridge provides a comprehensive API for test automation transformation and intelligence. The API is organized into modular components that can be used independently or combined for end-to-end workflows.

### Key Design Principles

- **Framework-Agnostic**: Works with 13+ test frameworks
- **Modular Architecture**: Use only what you need
- **Python-First**: Native Python API with CLI wrapper
- **Type-Safe**: Full type hints throughout
- **Extensible**: Plugin architecture for custom adapters

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                             │
│  (cli/main.py, cli/commands/, cli/app.py)                   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Core Services                            │
│  • Orchestration  • Memory      • Intelligence               │
│  • Translation    • Coverage    • Flaky Detection            │
│  • Execution      • Governance  • Observability              │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Adapter Layer                            │
│  Selenium │ Cypress │ pytest │ Robot │ Java │ .NET │ BDD    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                  Storage & Persistence                       │
│  • PostgreSQL    • Vector Store    • File System            │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Modules

### 1. Orchestration (`core.orchestration`)

Main entry point for test transformation workflows.

#### MigrationOrchestrator

**Purpose**: Orchestrates end-to-end test migration and transformation.

```python
from core.orchestration.orchestrator import MigrationOrchestrator
from core.orchestration.models import MigrationRequest, MigrationMode

# Initialize orchestrator
orchestrator = MigrationOrchestrator(
    source_framework="selenium_java",
    target_framework="robot",
    config_path="crossbridge.yml"
)

# Create migration request
request = MigrationRequest(
    source_repo_path="/path/to/selenium/tests",
    target_repo_path="/path/to/output",
    source_framework="selenium_java",
    target_framework="robot",
    mode=MigrationMode.FULL,
    use_ai=True,
    validate=True
)

# Execute migration
result = await orchestrator.execute_migration(request)

print(f"Status: {result.status}")
print(f"Files migrated: {len(result.migrated_files)}")
print(f"Success rate: {result.success_rate}%")
```

**Key Methods:**

- `execute_migration(request)` - Full migration workflow
- `validate_transformation(file_path)` - Validate single file
- `batch_transform(files, batch_size=10)` - Batch processing
- `get_migration_status(migration_id)` - Check status

**Configuration:**

```yaml
orchestration:
  mode: full  # full, hybrid, validate_only
  batch_size: 10
  parallel_workers: 4
  use_ai: true
  validation_level: strict
```

---

### 2. Memory System (`core.memory`)

Intelligent memory and embedding management.

#### UniversalTestNormalizer

**Purpose**: Normalize test metadata across all frameworks.

```python
from adapters.common.normalizer import UniversalTestNormalizer
from adapters.common.memory_integration import TestMetadata

# Initialize normalizer
normalizer = UniversalTestNormalizer(
    config_path="crossbridge.yml",
    auto_normalize=True,
    generate_embeddings=True
)

# Create test metadata
metadata = TestMetadata(
    test_id="test_login_001",
    test_name="test_user_login_success",
    framework="pytest",
    file_path="tests/test_auth.py",
    description="Test successful user login flow",
    tags=["auth", "smoke", "p0"]
)

# Normalize to unified memory
unified_memory = await normalizer.normalize(metadata)

print(f"Test ID: {unified_memory.test_id}")
print(f"Embedding: {len(unified_memory.embedding)} dimensions")
print(f"Signals: {len(unified_memory.structural_signals)} extracted")
```

#### Semantic Search

```python
from core.memory.search import SemanticSearchEngine

# Initialize search engine
search_engine = SemanticSearchEngine(
    vector_store_path="data/vectors",
    embedding_provider="openai"
)

# Search for similar tests
results = await search_engine.search(
    query="login authentication tests",
    top_k=5,
    framework_filter="pytest",
    min_similarity=0.7
)

for result in results:
    print(f"{result.test_name} (similarity: {result.similarity:.2f})")
```

**Key Classes:**

- `UniversalTestNormalizer` - Framework-agnostic normalization
- `SemanticSearchEngine` - Embedding-based search
- `MemoryIngestion` - Bulk memory ingestion
- `EmbeddingProvider` - OpenAI/HuggingFace integration

---

### 3. Intelligence (`core.intelligence`)

AI-powered test analysis and recommendations.

#### Framework Adapters

```python
from core.intelligence.adapters import AdapterFactory

# Get adapter for any framework
adapter = AdapterFactory.get_adapter("pytest")

# Discover tests
tests = adapter.discover_tests("/path/to/tests")
print(f"Found {len(tests)} tests")

# Extract memory
memories = []
for test in tests:
    memory = adapter.extract_to_memory(test)
    memories.append(memory)
```

**Supported Frameworks:**

| Framework | Adapter Class | AST Support |
|-----------|--------------|-------------|
| pytest | `PytestAdapter` | ✅ Full |
| JUnit | `JUnitAdapter` | ⚠️ Partial |
| TestNG | `TestNGAdapter` | ⚠️ Partial |
| NUnit | `NUnitAdapter` | ⚠️ Partial |
| Robot | `RobotAdapter` | ⚠️ Basic |
| SpecFlow | `SpecFlowAdapter` | ✅ Gherkin |
| Selenium Java | `SeleniumJavaAdapter` | ⚠️ Partial |
| Selenium Python | `SeleniumPythonAdapter` | ✅ Full |
| Playwright | `PlaywrightAdapter` | ⚠️ Partial |
| Cucumber | `CucumberAdapter` | ✅ Gherkin |
| Behave | `BehaveAdapter` | ✅ Gherkin |
| Cypress | `CypressAdapter` | ⚠️ Partial |

#### RAG Engine

```python
from core.intelligence.rag_engine import RAGExplanationEngine

# Initialize RAG engine
rag_engine = RAGExplanationEngine(search_engine)

# Explain test coverage
explanation = await rag_engine.explain_coverage(
    query="What checkout scenarios are tested?",
    max_tests=10
)

print(f"Summary: {explanation.summary}")
print(f"Validated behaviors: {len(explanation.validated_behaviors)}")

for behavior in explanation.validated_behaviors:
    print(f"  • {behavior.behavior}")
    print(f"    Confidence: {behavior.confidence:.0%}")
    print(f"    Evidence: {len(behavior.supporting_tests)} tests")
```

#### Test Recommender

```python
from core.intelligence.recommender import TestRecommendationEngine

# Initialize recommender
recommender = TestRecommendationEngine(search_engine)

# Get recommendations based on code changes
recommendations = await recommender.recommend_for_changes(
    changed_files=["src/auth/login.py"],
    max_recommendations=5
)

for rec in recommendations:
    print(f"{rec.test_name} (score: {rec.relevance_score:.2f})")
    print(f"  Reason: {rec.reason}")
```

---

### 4. Coverage Analysis (`core.coverage`)

Functional and behavioral coverage tracking.

```python
from core.coverage.functional_repository import FunctionalCoverageRepository

# Initialize coverage repository
coverage_repo = FunctionalCoverageRepository(db_connection)

# Track coverage for a test
await coverage_repo.record_coverage(
    test_id="test_login_001",
    business_capability="user_authentication",
    user_action="successful_login",
    validation="session_token_created",
    coverage_type="functional"
)

# Query coverage
coverage_summary = await coverage_repo.get_capability_coverage(
    capability="user_authentication"
)

print(f"Total actions: {coverage_summary.total_actions}")
print(f"Covered actions: {coverage_summary.covered_actions}")
print(f"Coverage %: {coverage_summary.coverage_percentage:.1f}%")
```

---

### 5. Flaky Detection (`core.flaky_detection`)

ML-based flaky test detection.

```python
from core.flaky_detection.multi_framework_detector import MultiFrameworkFlakyDetector

# Initialize detector
detector = MultiFrameworkFlakyDetector(db_connection)

# Train models (per framework)
await detector.train_models(
    min_executions=10,
    frameworks=["pytest", "junit", "robot"]
)

# Detect flaky tests
flaky_tests = await detector.detect_flaky_tests(
    framework="pytest",
    confidence_threshold=0.7
)

for test in flaky_tests:
    print(f"{test.test_name}")
    print(f"  Confidence: {test.flaky_confidence:.2%}")
    print(f"  Pass rate: {test.pass_rate:.1f}%")
    print(f"  Reason: {test.explanation}")
```

---

## Adapters API

### Creating Custom Adapters

All adapters inherit from `FrameworkAdapter`:

```python
from core.intelligence.adapters import FrameworkAdapter
from core.intelligence.models import UnifiedTestMemory
from pathlib import Path
from typing import List

class MyCustomAdapter(FrameworkAdapter):
    """
    Custom adapter for MyFramework.
    """
    
    def __init__(self):
        super().__init__(
            framework_name="myframework",
            supported_extensions=[".mytest"],
            supports_ast=False
        )
    
    def discover_tests(self, directory: Path) -> List[Path]:
        """Discover test files."""
        return list(directory.rglob("*.mytest"))
    
    def extract_to_memory(self, test_path: Path) -> UnifiedTestMemory:
        """Extract test metadata to unified memory."""
        # Parse test file
        test_content = test_path.read_text()
        
        # Extract metadata
        test_name = self._extract_test_name(test_content)
        description = self._extract_description(test_content)
        
        # Create unified memory
        return UnifiedTestMemory(
            test_id=f"myframework_{test_name}",
            test_name=test_name,
            framework=self.framework_name,
            file_path=str(test_path),
            description=description,
            metadata=self._extract_metadata(test_content)
        )
    
    def _extract_test_name(self, content: str) -> str:
        """Extract test name from content."""
        # Implementation
        pass
```

**Register Custom Adapter:**

```python
from core.intelligence.adapters import AdapterFactory

# Register your adapter
AdapterFactory.register_adapter("myframework", MyCustomAdapter)

# Use it
adapter = AdapterFactory.get_adapter("myframework")
```

---

## CLI API

### Command Structure

```bash
# General format
crossbridge <command> <subcommand> [options]

# Get help
crossbridge --help
crossbridge translate --help
```

### Translation Commands

```bash
# Translate entire repository
crossbridge translate repo \
    --source /path/to/selenium/tests \
    --target /path/to/output \
    --source-framework selenium_java \
    --target-framework robot \
    --use-ai

# Translate single file
crossbridge translate file \
    --input tests/LoginTest.java \
    --output tests/login.robot \
    --source-framework selenium_java \
    --target-framework robot

# Batch translate with pattern
crossbridge translate batch \
    --source-dir tests/ \
    --pattern "**/*Test.java" \
    --target-framework robot \
    --workers 4
```

### Memory Commands

```bash
# Ingest tests into memory
crossbridge memory ingest \
    --directory tests/ \
    --framework pytest \
    --generate-embeddings

# Search tests
crossbridge memory search \
    --query "authentication tests" \
    --top-k 10 \
    --framework pytest

# Export memories
crossbridge memory export \
    --output memories.json \
    --framework all
```

### Coverage Commands

```bash
# Track coverage
crossbridge coverage track \
    --tests tests/ \
    --capabilities capabilities.yaml

# Generate report
crossbridge coverage report \
    --capability user_authentication \
    --output coverage_report.html

# Dashboard
crossbridge coverage dashboard \
    --port 3000
```

### Flaky Detection Commands

```bash
# Train flaky detection models
crossbridge flaky train \
    --frameworks pytest,junit \
    --min-executions 10

# Detect flaky tests
crossbridge flaky detect \
    --framework pytest \
    --confidence 0.7 \
    --output flaky_tests.json

# Analyze specific test
crossbridge flaky analyze \
    --test-id test_login_001 \
    --history 30
```

---

## Configuration

### crossbridge.yml Structure

```yaml
# Core configuration
crossbridge:
  version: "1.0"
  project_name: "my_project"
  
  # Memory settings
  memory:
    enabled: true
    auto_normalize: true
    generate_embeddings: true
    embedding_provider: "openai"  # openai, huggingface
    extract_structural_signals: true
    extract_ui_interactions: true
    
    # Per-framework settings
    frameworks:
      pytest: true
      junit: true
      robot: true
      # ... all frameworks
  
  # AI settings
  ai:
    enabled: true
    provider: "openai"  # openai, anthropic, azure
    model: "gpt-4"
    temperature: 0.3
    max_tokens: 2000
    fallback_to_pattern: true
  
  # Database
  database:
    enabled: true
    host: "localhost"
    port: 5432
    database: "crossbridge"
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"
  
  # Flaky detection
  flaky_detection:
    enabled: true
    confidence_threshold: 0.7
    min_executions: 10
    training_interval_days: 7
  
  # Coverage tracking
  coverage:
    enabled: true
    track_functional: true
    track_behavioral: true
    capabilities_file: "capabilities.yaml"
  
  # Framework adapters
  adapters:
    selenium_java:
      enabled: true
      test_paths: ["src/test/java"]
      pattern: "**/*Test.java"
    
    robot:
      enabled: true
      test_paths: ["tests"]
      pattern: "**/*.robot"
```

### Environment Variables

```bash
# AI API Keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Database
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="crossbridge"
export DB_USER="postgres"
export DB_PASSWORD="secure_password"

# Memory
export VECTOR_STORE_PATH="data/vectors"
export EMBEDDING_CACHE_DIR="cache/embeddings"

# Observability
export GRAFANA_URL="http://localhost:3000"
export GRAFANA_API_KEY="..."
```

---

## Integration Examples

### 1. CI/CD Integration

```python
# ci_integration.py
from core.orchestration.orchestrator import MigrationOrchestrator
from core.observability.metrics import MetricsCollector

async def run_migration_pipeline():
    """Run migration in CI/CD pipeline."""
    
    # Initialize
    orchestrator = MigrationOrchestrator(
        source_framework="selenium_java",
        target_framework="robot",
        config_path="crossbridge.yml"
    )
    
    metrics = MetricsCollector()
    
    # Execute migration
    result = await orchestrator.execute_migration(request)
    
    # Collect metrics
    metrics.record_migration(
        total_files=len(result.all_files),
        successful=len(result.migrated_files),
        failed=len(result.failed_files),
        duration=result.duration
    )
    
    # Validate results
    if result.success_rate < 95:
        raise Exception(f"Migration quality too low: {result.success_rate}%")
    
    return result

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(run_migration_pipeline())
    print(f"Migration complete: {result.success_rate}% success")
```

### 2. Custom Test Discovery

```python
# custom_discovery.py
from pathlib import Path
from core.intelligence.adapters import AdapterFactory

def discover_all_tests(root_dir: Path):
    """Discover tests across all frameworks."""
    
    all_tests = {}
    
    # Get all supported frameworks
    frameworks = AdapterFactory.list_supported_frameworks()
    
    for framework in frameworks:
        adapter = AdapterFactory.get_adapter(framework)
        tests = adapter.discover_tests(root_dir)
        
        if tests:
            all_tests[framework] = tests
            print(f"{framework}: {len(tests)} tests")
    
    return all_tests
```

### 3. Batch Memory Ingestion

```python
# batch_ingest.py
from adapters.common.normalizer import UniversalTestNormalizer
from core.memory.ingestion import MemoryIngestion
from pathlib import Path

async def ingest_test_suite(test_dir: Path, framework: str):
    """Ingest entire test suite into memory."""
    
    # Initialize
    normalizer = UniversalTestNormalizer()
    ingestion = MemoryIngestion(db_connection)
    
    # Get adapter
    adapter = AdapterFactory.get_adapter(framework)
    
    # Discover tests
    test_files = adapter.discover_tests(test_dir)
    
    # Process in batches
    batch_size = 10
    for i in range(0, len(test_files), batch_size):
        batch = test_files[i:i+batch_size]
        
        memories = []
        for test_file in batch:
            # Extract metadata
            metadata = adapter.extract_metadata(test_file)
            
            # Normalize
            memory = await normalizer.normalize(metadata)
            memories.append(memory)
        
        # Ingest batch
        await ingestion.ingest_batch(memories)
        
        print(f"Ingested {len(batch)} tests")
```

### 4. Flaky Test Monitoring

```python
# flaky_monitor.py
from core.flaky_detection.multi_framework_detector import MultiFrameworkFlakyDetector
from core.observability.alerts import AlertManager

async def monitor_flaky_tests():
    """Continuous flaky test monitoring."""
    
    detector = MultiFrameworkFlakyDetector(db_connection)
    alerts = AlertManager()
    
    while True:
        # Detect flaky tests
        flaky_tests = await detector.detect_flaky_tests(
            framework="pytest",
            confidence_threshold=0.7
        )
        
        # Send alerts for new flaky tests
        for test in flaky_tests:
            if test.is_new:
                await alerts.send_alert(
                    severity="warning",
                    message=f"New flaky test detected: {test.test_name}",
                    details={
                        "confidence": test.flaky_confidence,
                        "pass_rate": test.pass_rate,
                        "explanation": test.explanation
                    }
                )
        
        # Sleep for 1 hour
        await asyncio.sleep(3600)
```

---

## Extension Guide

### Adding New Framework Support

**Step 1: Create Adapter**

```python
# adapters/myframework/adapter.py
from core.intelligence.adapters import FrameworkAdapter

class MyFrameworkAdapter(FrameworkAdapter):
    def __init__(self):
        super().__init__(
            framework_name="myframework",
            supported_extensions=[".mytest"],
            supports_ast=True
        )
```

**Step 2: Register Adapter**

```python
# adapters/myframework/__init__.py
from core.intelligence.adapters import AdapterFactory
from .adapter import MyFrameworkAdapter

AdapterFactory.register_adapter("myframework", MyFrameworkAdapter)
```

**Step 3: Add Configuration**

```yaml
# crossbridge.yml
adapters:
  myframework:
    enabled: true
    test_paths: ["tests"]
    pattern: "**/*.mytest"
```

**Step 4: Add Tests**

```python
# tests/test_myframework_adapter.py
def test_myframework_discovery():
    adapter = AdapterFactory.get_adapter("myframework")
    tests = adapter.discover_tests(Path("tests"))
    assert len(tests) > 0
```

### Adding Custom AI Providers

```python
# core/ai/custom_provider.py
from core.ai.provider import AIProvider

class CustomAIProvider(AIProvider):
    """Custom AI provider implementation."""
    
    async def generate_transformation(
        self,
        source_code: str,
        source_framework: str,
        target_framework: str,
        context: dict
    ) -> str:
        """Generate transformation using custom AI."""
        # Implementation
        pass
```

---

## API Versioning

CrossBridge follows semantic versioning:

- **Major version** (1.x.x): Breaking API changes
- **Minor version** (x.1.x): New features, backward compatible
- **Patch version** (x.x.1): Bug fixes, backward compatible

**Current Version**: 0.1.0 (Alpha)

### Stability Guarantees

- ✅ **Stable**: `core.memory`, `core.intelligence`, CLI
- ⚠️ **Beta**: `core.flaky_detection`, `core.coverage`
- 🔬 **Experimental**: `core.observability`, Custom adapters

---

## Error Handling

### Common Exceptions

```python
from core.exceptions import (
    CrossBridgeException,      # Base exception
    AdapterNotFoundError,       # Framework not supported
    TransformationError,        # Transformation failed
    ValidationError,            # Validation failed
    ConfigurationError,         # Invalid configuration
    DatabaseError,              # Database operation failed
)

try:
    adapter = AdapterFactory.get_adapter("unknown_framework")
except AdapterNotFoundError as e:
    print(f"Framework not supported: {e}")
    # Handle gracefully
```

### Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("crossbridge")

# Use in your code
logger.info("Starting migration")
logger.warning("Low confidence transformation")
logger.error("Migration failed", exc_info=True)
```

---

## Performance Considerations

### Batch Processing

```python
# Good: Batch processing
memories = []
for test in tests:
    memory = await normalizer.normalize(test)
    memories.append(memory)

await ingestion.ingest_batch(memories, batch_size=100)

# Bad: Individual inserts
for test in tests:
    memory = await normalizer.normalize(test)
    await ingestion.ingest_single(memory)  # Slow!
```

### Async Operations

```python
import asyncio

# Good: Parallel execution
tasks = [
    normalizer.normalize(test1),
    normalizer.normalize(test2),
    normalizer.normalize(test3)
]
memories = await asyncio.gather(*tasks)

# Bad: Sequential execution
memory1 = await normalizer.normalize(test1)
memory2 = await normalizer.normalize(test2)
memory3 = await normalizer.normalize(test3)
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_adapter(framework: str):
    """Cached adapter retrieval."""
    return AdapterFactory.get_adapter(framework)
```

---

## Testing Your Integration

```python
# test_integration.py
import pytest
from core.orchestration.orchestrator import MigrationOrchestrator

@pytest.mark.asyncio
async def test_migration_workflow():
    """Test complete migration workflow."""
    
    orchestrator = MigrationOrchestrator(
        source_framework="selenium_java",
        target_framework="robot"
    )
    
    result = await orchestrator.execute_migration(request)
    
    assert result.status == "success"
    assert len(result.migrated_files) > 0
    assert result.success_rate > 90
```

---

## Support & Resources

- **Documentation**: [README.md](README.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: vikas.sdet@gmail.com

---

## License

Copyright (c) 2025 Vikas Verma

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
