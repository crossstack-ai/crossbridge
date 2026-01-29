# Config-Driven Profiling - Implementation Guide

> **🎉 NOW PART OF UNIFIED PROFILING SYSTEM**
>
> This document describes the original Runtime Profiling implementation.  
> **For the complete consolidated system, see [UNIFIED_PROFILING.md](UNIFIED_PROFILING.md)**
>
> The unified system now includes:
> - ✅ Runtime Profiling (this document)
> - ✅ Test Execution Profiling (replaces legacy `MetricsCollector`)
> - ✅ System Profiling (replaces sidecar `LightweightProfiler`)
> - ✅ Benchmarking (replaces `PerformanceBenchmark`)

**Date**: January 30, 2026  
**Status**: ✅ COMPLETE (Enhanced with unified system)  
**Total Code**: 2,000+ lines (unified system)

---

## Overview

Config-Driven Profiling enables runtime-controllable performance monitoring that can be:
- **Turned ON/OFF via config** - No code changes required
- **Scoped** - Global, module, or request-level profiling
- **Safe for production** - Rate limiting, sampling, zero cost when disabled
- **Low overhead** - NoOp profiler when disabled, sampling mode available
- **Extensible** - Easy to add new profilers (CPU, network, custom metrics)

### Design Principles

1. **Profiling must be config-driven** - All behavior controlled via YAML
2. **Disabled by default** - Zero cost in production
3. **No profiling logic in business code** - Clean separation of concerns
4. **Centralized control** - Single source of truth for profiling behavior
5. **Production safety** - Rate limiting, sampling, error handling
6. **Structured output** - JSON for machine parsing

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Config-Driven Profiling                  │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                  │
    ┌───▼───┐                          ┌───▼───┐
    │ Config│                          │Factory│
    └───┬───┘                          └───┬───┘
        │                                  │
        │     ┌─────────────┬──────────────┤
        │     │             │              │
    ┌───▼─────▼──┐      ┌──▼──┐       ┌───▼────┐
    │ NoOpProfiler│      │Timing│       │Memory  │
    │  (disabled) │      │      │       │        │
    └─────────────┘      └──┬───┘       └───┬────┘
                            │               │
                   ┌────────▼───────────────▼─────┐
                   │    Context Managers          │
                   │  profile() / @profiled()     │
                   └──────────────────────────────┘
```

---

## Configuration

### Location
**File**: `crossbridge.yml`  
**Section**: `runtime.profiling`

### Configuration Schema

```yaml
runtime:
  profiling:
    # Enable/disable profiling (disabled by default)
    enabled: false
    
    # Profiling mode
    mode: sampling  # sampling | full
    
    # Detail level
    level: basic  # basic (timing only) | detailed (timing + memory)
    
    # Targets to profile (empty = all)
    targets:
      - semantic_search
      - embedding_provider
      - vector_store
    
    # Thresholds for alerting
    thresholds:
      slow_call_ms: 500  # Alert if call takes > 500ms
      memory_mb: 50  # Alert if memory usage > 50MB
    
    # Sampling configuration (for sampling mode)
    sample_rate: 0.1  # Profile 10% of requests
    
    # Output configuration
    output:
      type: log  # log | file | prometheus | none
      path: ./data/profiling/profile.jsonl  # File path (if type=file)
    
    # Production safety limits
    max_records_per_minute: 100  # Rate limit profiling records
    include_metadata: true  # Include metadata in records
    include_stack_trace: false  # Include stack traces (expensive)
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `false` | Enable/disable profiling |
| `mode` | string | `sampling` | `sampling` or `full` |
| `level` | string | `basic` | `basic` (timing) or `detailed` (timing + memory) |
| `targets` | list | `[]` | Target modules to profile (empty = all) |
| `thresholds.slow_call_ms` | float | `500.0` | Slow call threshold in ms |
| `thresholds.memory_mb` | float | `50.0` | High memory threshold in MB |
| `sample_rate` | float | `0.1` | Sampling rate (0.0-1.0) |
| `output.type` | string | `log` | Output type: `log`, `file`, `prometheus`, `none` |
| `output.path` | string | `null` | File path (if type=file) |
| `max_records_per_minute` | int | `100` | Rate limit |
| `include_metadata` | bool | `true` | Include metadata in records |
| `include_stack_trace` | bool | `false` | Include stack traces |

---

## Usage

### 1. Context Manager (Recommended)

Profile a code section using context manager:

```python
from core.profiling.context import profile

def semantic_search(query):
    with profile("semantic_search.search", {"query_len": len(query)}):
        # Your code here
        results = do_search(query)
        return results
```

**Advantages:**
- Clean, Pythonic syntax
- Automatic start/stop
- Exception safe

### 2. Decorator

Profile a function using decorator:

```python
from core.profiling.context import profiled

@profiled("embedding_provider.embed")
def embed_text(text):
    # Your code here
    return generate_embedding(text)

# Or auto-name from function
@profiled()
def embed_text(text):  # Will use "embed_text" as profile name
    return generate_embedding(text)
```

**Advantages:**
- Clean, declarative
- Works with existing code
- Auto-naming option

### 3. Manual Start/Stop

For more control:

```python
from core.profiling.factory import get_profiler

profiler = get_profiler()

profiler.start("custom_operation", {"user_id": user_id})
try:
    # Your code here
    result = process_data()
finally:
    profiler.stop("custom_operation", {"rows_processed": len(result)})
```

### 4. Async Support

Profile async functions:

```python
from core.profiling.context import profile_async, profiled_async

# Context manager
async def async_search(query):
    async with profile_async("async_search"):
        results = await do_async_search(query)
        return results

# Decorator
@profiled_async("async_embed")
async def async_embed(text):
    return await async_generate_embedding(text)
```

---

## Integration Examples

### Semantic Search Service

Already integrated in `core/ai/embeddings/semantic_service.py`:

```python
def search(self, query: str, top_k: int = 10) -> List[SimilarityResult]:
    with profile("semantic_search.search", {"query_len": len(query), "top_k": top_k}):
        # Generate embedding
        embedding = self.provider.embed(query)
        
        # Search vector store
        results = self.vector_store.search(embedding, top_k)
        
        return results
```

### Embedding Provider

```python
def embed(self, texts: List[str]) -> List[List[float]]:
    with profile("embedding_provider.embed", {"batch_size": len(texts)}):
        # Call API
        response = self.client.embeddings.create(input=texts, model=self.model)
        return [d.embedding for d in response.data]
```

### Vector Store

```python
def search(self, query_embedding: List[float], top_k: int) -> List[SimilarityResult]:
    with profile("vector_store.search", {"top_k": top_k}):
        # Perform similarity search
        results = self._similarity_search(query_embedding, top_k)
        return results
```

---

## Output Formats

### Log Output (type: log)

Structured JSON to logs:

```json
{
  "name": "semantic_search.search",
  "duration_ms": 523.45,
  "timestamp": 1706630400.0,
  "metadata": {
    "query_len": 42,
    "top_k": 10
  }
}
```

### File Output (type: file)

JSONL (newline-delimited JSON):

```json
{"name": "semantic_search.search", "duration_ms": 523.45, "timestamp": 1706630400.0}
{"name": "embedding_provider.embed", "duration_ms": 312.78, "timestamp": 1706630401.0}
```

### Prometheus Output (type: prometheus)

*Coming in Phase-2*

Metrics exported to Prometheus:
- `profiling_duration_seconds{name="semantic_search"}`
- `profiling_memory_bytes{name="vector_store"}`

---

## Production Usage

### Enable Profiling in Production

1. **Edit `crossbridge.yml`:**
```yaml
runtime:
  profiling:
    enabled: true
    mode: sampling  # ⚠️ Use sampling in production
    sample_rate: 0.05  # Profile 5% of requests
    level: basic  # Avoid detailed (memory tracking has overhead)
```

2. **Restart application** (or reload config if hot-reload supported)

3. **Monitor output** via logs or files

### Production Safety Checklist

✅ **Use sampling mode** - `mode: sampling`  
✅ **Low sample rate** - `sample_rate: 0.05` (5%)  
✅ **Basic level only** - `level: basic` (avoid memory profiling)  
✅ **Rate limiting enabled** - `max_records_per_minute: 100`  
✅ **Target filtering** - Only profile critical paths  
✅ **No stack traces** - `include_stack_trace: false`

### Disable Profiling

```yaml
runtime:
  profiling:
    enabled: false  # Zero cost
```

---

## Profiler Types

### NoOpProfiler (Default)

**When used**: `enabled: false`  
**Overhead**: Zero - all methods are no-ops  
**Use case**: Production default, testing

```python
profiler = NoOpProfiler()
profiler.start("test")  # Does nothing
profiler.stop("test")   # Does nothing
```

### TimingProfiler

**When used**: `enabled: true, level: basic`  
**Overhead**: Minimal (~1-2% for instrumented code)  
**Measures**: Execution duration  
**Features**:
- Slow call detection
- Target filtering
- Sampling support
- Rate limiting

### MemoryProfiler

**When used**: `enabled: true, level: detailed`  
**Overhead**: Moderate (~10-20% due to tracemalloc)  
**Measures**: Execution duration + memory usage  
**Features**:
- Everything in TimingProfiler
- Peak memory tracking
- Memory threshold alerts

⚠️ **Warning**: Only use MemoryProfiler in development/staging

---

## Target Filtering

### Profile All (Default)

```yaml
targets: []  # Empty list = profile all
```

### Profile Specific Modules

```yaml
targets:
  - semantic_search
  - embedding_provider
```

Matches:
- ✅ `semantic_search`
- ✅ `semantic_search.index_entity`
- ✅ `semantic_search.search`
- ✅ `embedding_provider.embed`
- ❌ `vector_store` (not in targets)

### Best Practices

1. **Start broad, narrow down**: Begin with `targets: []`, then add specific targets
2. **Profile critical paths**: Focus on slow or high-volume operations
3. **Avoid hot loops**: Don't profile code called thousands of times per second
4. **Use hierarchical names**: `module.class.method` for clarity

---

## Sampling Mode

### How It Works

```yaml
mode: sampling
sample_rate: 0.1  # 10%
```

- Profiler randomly selects ~10% of requests
- Reduces overhead in high-traffic scenarios
- Statistical sampling provides representative data

### When to Use

- ✅ **Production** - Always use sampling
- ✅ **High throughput** - > 100 req/sec
- ❌ **Development** - Use full mode for debugging

### Sample Rate Guidelines

| Environment | Sample Rate | Use Case |
|-------------|-------------|----------|
| Production | 0.01 - 0.05 (1-5%) | Normal operation |
| Staging | 0.1 - 0.2 (10-20%) | Pre-release testing |
| Development | 1.0 (100%) | Full profiling |

---

## Rate Limiting

### Configuration

```yaml
max_records_per_minute: 100
```

### Behavior

- Profiler tracks records emitted per minute
- Once limit reached, profiling stops until next minute
- Prevents profiling from overwhelming logs/storage

### Tuning

| Traffic Level | Recommended Limit |
|---------------|-------------------|
| Low (< 10 req/sec) | 100 |
| Medium (10-100 req/sec) | 500 |
| High (> 100 req/sec) | 1000 |

---

## Extending Profiling

### Add Custom Profiler

```python
from core.profiling.timing import TimingProfiler

class CPUProfiler(TimingProfiler):
    """Profile CPU usage"""
    
    def start(self, name, metadata=None):
        super().start(name, metadata)
        self.cpu_start[name] = psutil.cpu_percent()
    
    def stop(self, name, metadata=None):
        start_time = self.active.pop(name, None)
        if not start_time:
            return
        
        duration_ms = (time.time() - start_time) * 1000
        cpu_usage = psutil.cpu_percent() - self.cpu_start.pop(name)
        
        record = ProfileRecord(
            name=name,
            duration_ms=duration_ms,
            timestamp=time.time(),
            cpu_percent=cpu_usage,
            metadata=metadata
        )
        self.emit(record)
```

### Register in Factory

```python
# core/profiling/factory.py
from .cpu import CPUProfiler

def create_profiler(config):
    if not config.enabled:
        return NoOpProfiler()
    
    if config.level == ProfilingLevel.CPU:
        return CPUProfiler(config)
    elif config.level == ProfilingLevel.DETAILED:
        return MemoryProfiler(config)
    else:
        return TimingProfiler(config)
```

---

## Troubleshooting

### Profiling Not Working

**Check 1: Is profiling enabled?**
```yaml
runtime:
  profiling:
    enabled: true  # Must be true
```

**Check 2: Are you above thresholds?**
```yaml
thresholds:
  slow_call_ms: 500  # Calls < 500ms won't be emitted
```

**Check 3: Target filtering**
```yaml
targets:
  - semantic_search  # Must match your profile name
```

**Check 4: Rate limiting**
```yaml
max_records_per_minute: 100  # May be limiting you
```

### High Overhead

**Symptom**: Application slower with profiling enabled

**Solutions:**
1. Use sampling mode: `mode: sampling, sample_rate: 0.05`
2. Use basic level: `level: basic` (not detailed)
3. Filter targets: Only profile critical paths
4. Increase thresholds: `slow_call_ms: 1000`

### Memory Issues

**Symptom**: High memory usage with MemoryProfiler

**Cause**: `tracemalloc` has overhead

**Solution**: Use `level: basic` in production

---

## Testing

### Run Unit Tests

```bash
python -m pytest tests/test_config_driven_profiling.py -v
```

### Test Coverage

- ✅ ProfilerConfig
- ✅ NoOpProfiler
- ✅ TimingProfiler
- ✅ MemoryProfiler
- ✅ Profiler factory
- ✅ Context managers
- ✅ Decorators
- ✅ Target filtering
- ✅ Rate limiting
- ✅ Sampling mode

---

## Roadmap

### Phase-2 Enhancements

1. **Prometheus Integration** - Export metrics to Prometheus
2. **Flamegraphs** - Generate flamegraphs with py-spy
3. **Request Correlation** - Link profiling to request IDs
4. **Auto-Profiling** - Auto-enable on SLA breach
5. **CPU Profiling** - Track CPU usage
6. **Network Profiling** - Track API calls and network I/O
7. **Database Profiling** - Track query performance

---

## Summary

✅ **Config-driven** - All behavior controlled via YAML  
✅ **Zero cost when disabled** - NoOpProfiler is default  
✅ **Production safe** - Sampling, rate limiting, error handling  
✅ **Easy to use** - Context managers and decorators  
✅ **Extensible** - Add custom profilers easily  
✅ **Integrated** - Already integrated with semantic search  

**Next Steps:**
1. Enable profiling in `crossbridge.yml`
2. Add profiling to critical paths
3. Monitor output and adjust thresholds
4. Optimize based on profiling data

**Questions?** See tests in `tests/test_config_driven_profiling.py` for examples.
