# Unified Performance Profiling System

## Overview

**CONSOLIDATED**: All profiling systems have been unified into a single config-driven framework.

### What Was Consolidated

| Legacy System | Purpose | Status | Replacement |
|--------------|---------|---------|-------------|
| **Legacy Profiling** (`collector.py`, `models.py`) | Test execution metrics | ✅ MIGRATED | `TestExecutionProfiler` |
| **Sidecar Profiler** (`sidecar/profiler.py`) | System monitoring | ✅ MIGRATED | `SystemProfiler` |
| **Performance Benchmark** (`benchmarking/performance.py`) | Adapter comparison | ✅ MIGRATED | `BenchmarkProfiler` |
| **Config-Driven Profiling** (`profiling/timing.py`, etc.) | Runtime profiling | ✅ ENHANCED | Unified foundation |

### Benefits of Consolidation

✅ **Single Configuration** - All profiling controlled via `crossbridge.yml`  
✅ **Consistent API** - Same interface for all profiler types  
✅ **Production Safe** - Zero cost when disabled, built-in rate limiting  
✅ **Easy Migration** - Automatic migration utilities included  
✅ **Backward Compatible** - Legacy APIs still work during transition  

---

## Profiler Types

The unified system supports 4 profiler types:

### 1. Runtime Profiling 🔧
**Purpose**: Profile internal CrossBridge operations  
**Use For**: Semantic search, embeddings, vector stores, AI operations  
**Output**: Timing, memory, slow calls  

```yaml
runtime:
  profiling:
    runtime:
      enabled: true
      type: runtime
      level: basic  # basic | detailed
      targets:
        - semantic_search
        - embedding_provider
```

### 2. Test Execution Profiling 🧪
**Purpose**: Profile test lifecycle and automation commands  
**Use For**: Test duration, driver commands, HTTP requests  
**Output**: Test metrics, command timing, HTTP performance  

```yaml
runtime:
  profiling:
    test_execution:
      enabled: true
      type: test_execution
      capture:
        test_lifecycle: true
        commands: true
        http: true
```

### 3. System Profiling 📊
**Purpose**: System-level monitoring  
**Use For**: CPU, memory, threads, garbage collection  
**Output**: System snapshots, resource trends  

```yaml
runtime:
  profiling:
    system:
      enabled: true
      type: system
      monitor:
        cpu: true
        memory: true
        threads: true
```

### 4. Benchmarking 🏁
**Purpose**: Adapter performance comparison  
**Use For**: Comparing selenium vs playwright vs cypress  
**Output**: Performance rankings, insights, recommendations  

```yaml
runtime:
  profiling:
    benchmarking:
      enabled: true
      type: benchmark
      iterations: 10
```

---

## Configuration

All profiling is controlled via `crossbridge.yml` under `runtime.profiling`.

### Full Configuration Example

```yaml
runtime:
  profiling:
    # ─────────────────────────────────────────────
    # RUNTIME PROFILING
    # ─────────────────────────────────────────────
    runtime:
      enabled: false
      type: runtime
      mode: sampling  # sampling | full
      level: basic  # basic | detailed
      
      targets:  # Empty = all
        - semantic_search
        - embedding_provider
      
      thresholds:
        slow_call_ms: 500
        memory_mb: 50
      
      sample_rate: 0.1  # 10%
      
      output:
        type: log  # log | file | prometheus | none
        path: ./data/profiling/runtime.jsonl
      
      max_records_per_minute: 100
    
    # ─────────────────────────────────────────────
    # TEST EXECUTION PROFILING
    # ─────────────────────────────────────────────
    test_execution:
      enabled: false
      type: test_execution
      mode: full
      
      capture:
        test_lifecycle: true
        commands: true
        http: true
        assertions: false
      
      thresholds:
        slow_call_ms: 100
      
      output:
        type: database
        database_path: ./data/profiling/test_execution.db
    
    # ─────────────────────────────────────────────
    # SYSTEM PROFILING
    # ─────────────────────────────────────────────
    system:
      enabled: false
      type: system
      level: system
      
      monitor:
        cpu: true
        memory: true
        threads: true
        gc: true
      
      sampling_interval: 1.0  # seconds
      max_snapshots: 1000
      
      thresholds:
        cpu_percent: 80.0
        memory_mb: 500
      
      output:
        type: log
    
    # ─────────────────────────────────────────────
    # BENCHMARKING
    # ─────────────────────────────────────────────
    benchmarking:
      enabled: false
      type: benchmark
      
      iterations: 10
      compare_baselines: true
      baseline_adapters:
        - selenium_python
        - playwright_python
      
      output:
        type: file
        path: ./data/profiling/benchmark_results.json
```

---

## Usage Examples

### Runtime Profiling

```python
from core.profiling import profile, profiled

# Context manager
with profile("semantic_search", {"query_len": len(query)}):
    results = search(query)

# Decorator
@profiled("embed_text")
def generate_embedding(text):
    return model.embed(text)

# Manual
from core.profiling import get_profiler

profiler = get_profiler()
profiler.start("custom_operation")
# ... operation ...
profiler.stop("custom_operation", {"status": "success"})
```

### Test Execution Profiling

```python
from core.profiling import TestExecutionProfiler, ProfilerConfig, ProfilerType

config = ProfilerConfig(
    enabled=True,
    profiler_type=ProfilerType.TEST_EXECUTION,
    capture_test_lifecycle=True,
    capture_commands=True,
)

profiler = TestExecutionProfiler(config)

# Record test lifecycle
profiler.start_test("test_login_001", "User Login Test", {"framework": "pytest"})
# ... test runs ...
profiler.end_test("test_login_001", "passed")

# Record driver commands
profiler.record_command("test_login_001", "click", 45.2, "selenium", {"selector": "#login-btn"})

# Record HTTP requests
profiler.record_http("test_login_001", "POST", "https://api.example.com/login", 200, 125.3)
```

### System Profiling

```python
from core.profiling import SystemProfiler, ProfilerConfig, ProfilerType

config = ProfilerConfig(
    enabled=True,
    profiler_type=ProfilerType.SYSTEM,
    sampling_interval=1.0,
    monitor_cpu=True,
    monitor_memory=True,
)

profiler = SystemProfiler(config)

# Start background monitoring
profiler.start("system")

# ... application runs ...

# Get summary
summary = profiler.get_summary(window_seconds=60)
print(f"Avg CPU: {summary['cpu']['avg']:.1f}%")
print(f"Peak Memory: {summary['memory']['max_mb']:.1f} MB")

# Stop monitoring
profiler.stop("system")
```

### Benchmarking

```python
from core.profiling import BenchmarkProfiler, ProfilerConfig, ProfilerType

config = ProfilerConfig(
    enabled=True,
    profiler_type=ProfilerType.BENCHMARK,
    benchmark_iterations=10,
)

profiler = BenchmarkProfiler(config)

# Benchmark operations
def selenium_operation():
    driver.find_element(By.ID, "test").click()

def playwright_operation():
    page.click("#test")

profiler.benchmark_operation("selenium", selenium_operation)
profiler.benchmark_operation("playwright", playwright_operation)

# Compare
comparison = profiler.compare_adapters()
print(f"Fastest: {comparison['fastest']}")
print(f"Slowest: {comparison['slowest']}")

# Get insights
for insight in profiler.get_insights():
    print(insight)

# Generate report
report = profiler.generate_report()
print(report)
```

---

## Migration Guide

### From Legacy MetricsCollector

**OLD CODE:**
```python
from core.profiling import ProfileConfig, MetricsCollector

config = ProfileConfig(enabled=True, storage_backend="sqlite")
collector = MetricsCollector(config)
collector.start()
```

**NEW CODE (Option 1 - Use YAML):**
```yaml
runtime:
  profiling:
    test_execution:
      enabled: true
      type: test_execution
```

```python
from core.profiling.migration import ProfilingMigration

# Automatic migration
ProfilingMigration.auto_migrate_and_initialize()
```

**NEW CODE (Option 2 - Manual):**
```python
from core.profiling import TestExecutionProfiler, ProfilerConfig, ProfilerType

config = ProfilerConfig(
    enabled=True,
    profiler_type=ProfilerType.TEST_EXECUTION,
    capture_test_lifecycle=True,
)

profiler = TestExecutionProfiler(config)
profiler.start_test("test_id", "test_name")
```

### From Sidecar LightweightProfiler

**OLD CODE:**
```python
from core.sidecar.profiler import LightweightProfiler

profiler = LightweightProfiler(sampling_interval=1.0)
profiler.start()
summary = profiler.get_summary()
```

**NEW CODE:**
```python
from core.profiling import SystemProfiler, ProfilerConfig, ProfilerType

config = ProfilerConfig(
    enabled=True,
    profiler_type=ProfilerType.SYSTEM,
    sampling_interval=1.0,
)

profiler = SystemProfiler(config)
profiler.start("system")
summary = profiler.get_summary()
```

### From PerformanceBenchmark

**OLD CODE:**
```python
from core.benchmarking import PerformanceBenchmark

benchmark = PerformanceBenchmark()
result = benchmark.benchmark_adapter('selenium', operation, iterations=10)
insights = benchmark.get_performance_insights()
```

**NEW CODE:**
```python
from core.profiling import BenchmarkProfiler, ProfilerConfig, ProfilerType

config = ProfilerConfig(
    enabled=True,
    profiler_type=ProfilerType.BENCHMARK,
    benchmark_iterations=10,
)

profiler = BenchmarkProfiler(config)
result = profiler.benchmark_operation('selenium', operation)
insights = profiler.get_insights()
```

---

## API Reference

### ProfilerConfig

Unified configuration for all profiler types.

```python
@dataclass
class ProfilerConfig:
    # Core
    enabled: bool = False
    profiler_type: ProfilerType = ProfilerType.RUNTIME
    mode: ProfilingMode = ProfilingMode.SAMPLING
    level: ProfilingLevel = ProfilingLevel.BASIC
    
    # Targets (runtime/test profiling)
    targets: List[str] = field(default_factory=list)
    
    # Thresholds
    slow_call_ms: float = 500.0
    memory_mb: float = 50.0
    cpu_percent: float = 80.0
    
    # Sampling
    sample_rate: float = 0.1
    sampling_interval: float = 1.0
    
    # Output
    output_type: OutputType = OutputType.LOG
    output_path: Optional[str] = None
    database_path: Optional[str] = None
    
    # Safety
    max_records_per_minute: int = 100
    max_snapshots: int = 1000
    
    # Test execution specific
    capture_test_lifecycle: bool = True
    capture_commands: bool = True
    capture_http: bool = True
    capture_assertions: bool = False
    
    # System profiling specific
    monitor_cpu: bool = True
    monitor_memory: bool = True
    monitor_threads: bool = True
    monitor_gc: bool = True
    
    # Benchmarking specific
    benchmark_iterations: int = 10
    compare_baselines: bool = True
    baseline_adapters: List[str] = field(default_factory=list)
```

### Profiler Types

```python
class ProfilerType(Enum):
    RUNTIME = "runtime"
    TEST_EXECUTION = "test_execution"
    SYSTEM = "system"
    BENCHMARK = "benchmark"
```

### Factory Functions

```python
def create_profiler(config: ProfilerConfig) -> Profiler:
    """Create profiler based on configuration"""

def get_profiler() -> Profiler:
    """Get global profiler instance"""

def initialize_profiler(config: ProfilerConfig) -> None:
    """Initialize global profiler"""

def reset_profiler() -> None:
    """Reset global profiler (for testing)"""
```

---

## Testing

Comprehensive test suite with 30 tests covering all profiler types:

```bash
# Run all profiling tests
pytest tests/test_unified_profiling.py -v

# Run specific profiler type tests
pytest tests/test_unified_profiling.py::TestRuntimeProfiling -v
pytest tests/test_unified_profiling.py::TestTestExecutionProfiling -v
pytest tests/test_unified_profiling.py::TestSystemProfiling -v
pytest tests/test_unified_profiling.py::TestBenchmarkProfiling -v
```

### Test Coverage

- ✅ Configuration (6 tests)
- ✅ Runtime Profiling (4 tests)
- ✅ Test Execution Profiling (4 tests)
- ✅ System Profiling (3 tests)
- ✅ Benchmarking (4 tests)
- ✅ Factory (7 tests)
- ✅ Backward Compatibility (2 tests)

**Total: 30/30 tests passing** ✅

---

## Production Deployment

### Enabling Runtime Profiling

```yaml
runtime:
  profiling:
    runtime:
      enabled: true
      mode: sampling  # Sample 10% of requests
      sample_rate: 0.1
      slow_call_ms: 500  # Only alert on slow calls
      max_records_per_minute: 100  # Rate limit
```

### Enabling Test Execution Profiling

```yaml
runtime:
  profiling:
    test_execution:
      enabled: true
      capture:
        test_lifecycle: true
        commands: true  # Record driver commands
        http: true  # Record HTTP requests
      output:
        type: database
        database_path: ./data/profiling/test_execution.db
```

### Safety Features

All profilers include production safety features:

1. **Zero Cost When Disabled** - NoOpProfiler has zero overhead
2. **Rate Limiting** - `max_records_per_minute` prevents flooding
3. **Sampling Mode** - Profile only a percentage of requests
4. **Threshold-Based Emission** - Only emit slow calls
5. **Error Handling** - Never crash on profiling errors
6. **Graceful Degradation** - Falls back to NoOp on errors

---

## Troubleshooting

### No Profiling Data

**Check:**
1. Is profiling enabled in config?
2. Are thresholds too high?
3. Is sampling rate too low?
4. Check logs for profiler initialization

```python
# Force full mode for debugging
config.mode = ProfilingMode.FULL
config.slow_call_ms = 0  # Emit all calls
```

### High Overhead

**Solutions:**
1. Use sampling mode instead of full
2. Increase thresholds to reduce emissions
3. Use basic level instead of detailed
4. Increase sampling_interval (system profiling)

### Migration Issues

**Use migration utility:**
```python
from core.profiling.migration import ProfilingMigration

# Automatic migration
ProfilingMigration.auto_migrate_and_initialize()

# Or manual migration
config = ProfilingMigration.migrate_legacy_profile_config(legacy_config)
```

---

## Roadmap

### Phase 2 (Future)
- [ ] Prometheus exporter implementation
- [ ] Flamegraph generation (py-spy integration)
- [ ] Request correlation across profilers
- [ ] Auto-profiling on SLA breach
- [ ] CPU profiling (cProfile integration)
- [ ] Network profiling
- [ ] Distributed tracing

### Deprecation Timeline

| Component | Deprecation Date | Removal Date |
|-----------|-----------------|--------------|
| Legacy `MetricsCollector` | v1.8.0 (Mar 2026) | v2.0.0 (Jun 2026) |
| Sidecar `LightweightProfiler` | v1.8.0 (Mar 2026) | v2.0.0 (Jun 2026) |
| `PerformanceBenchmark` | v1.8.0 (Mar 2026) | v2.0.0 (Jun 2026) |

**Action Required**: Migrate to unified profiling before v2.0.0 release.

---

## Support

For questions or issues:
1. Check this documentation
2. Review test examples in `tests/test_unified_profiling.py`
3. Use migration utilities in `core/profiling/migration.py`
4. Check logs for profiler initialization messages

**Legacy code still works during transition period** - no immediate action required, but migration recommended.
