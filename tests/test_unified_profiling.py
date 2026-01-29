"""
Comprehensive Unit Tests for Unified Profiling System

Tests all 4 profiler types:
1. Runtime Profiling (TimingProfiler, MemoryProfiler)
2. Test Execution Profiling (TestExecutionProfiler)
3. System Profiling (SystemProfiler)
4. Benchmarking (BenchmarkProfiler)

Ensures no regression from consolidation.
"""

import time
import pytest
import tempfile
from pathlib import Path
from core.profiling import (
    ProfilerConfig,
    ProfilerType,
    ProfilingMode,
    ProfilingLevel,
    OutputType,
    NoOpProfiler,
    TimingProfiler,
    MemoryProfiler,
    TestExecutionProfiler,
    SystemProfiler,
    BenchmarkProfiler,
    create_profiler,
    initialize_profiler,
    reset_profiler,
    profile,
    profiled,
)


class TestUnifiedProfilingConfig:
    """Test unified profiler configuration"""
    
    def test_runtime_config(self):
        """Test runtime profiling config"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.RUNTIME,
            mode=ProfilingMode.FULL,
            level=ProfilingLevel.BASIC,
            targets=["semantic_search"],
            slow_call_ms=500,
        )
        
        assert config.enabled is True
        assert config.profiler_type == ProfilerType.RUNTIME
        assert config.mode == ProfilingMode.FULL
        assert config.level == ProfilingLevel.BASIC
        assert "semantic_search" in config.targets
    
    def test_test_execution_config(self):
        """Test test execution profiling config"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.TEST_EXECUTION,
            capture_test_lifecycle=True,
            capture_commands=True,
            capture_http=True,
        )
        
        assert config.profiler_type == ProfilerType.TEST_EXECUTION
        assert config.capture_test_lifecycle is True
        assert config.capture_commands is True
        assert config.capture_http is True
    
    def test_system_config(self):
        """Test system profiling config"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.SYSTEM,
            level=ProfilingLevel.SYSTEM,
            sampling_interval=1.0,
            monitor_cpu=True,
            monitor_memory=True,
        )
        
        assert config.profiler_type == ProfilerType.SYSTEM
        assert config.level == ProfilingLevel.SYSTEM
        assert config.sampling_interval == 1.0
        assert config.monitor_cpu is True
    
    def test_benchmark_config(self):
        """Test benchmarking config"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.BENCHMARK,
            benchmark_iterations=10,
            compare_baselines=True,
        )
        
        assert config.profiler_type == ProfilerType.BENCHMARK
        assert config.benchmark_iterations == 10
        assert config.compare_baselines is True
    
    def test_config_from_dict_runtime(self):
        """Test loading runtime config from dict"""
        config_dict = {
            "enabled": True,
            "type": "runtime",
            "mode": "full",
            "level": "basic",
            "targets": ["test"],
            "thresholds": {"slow_call_ms": 100},
        }
        
        config = ProfilerConfig.from_dict(config_dict)
        
        assert config.enabled is True
        assert config.profiler_type == ProfilerType.RUNTIME
        assert config.slow_call_ms == 100
    
    def test_config_from_dict_test_execution(self):
        """Test loading test execution config from dict"""
        config_dict = {
            "enabled": True,
            "type": "test_execution",
            "test_execution": {
                "capture_lifecycle": True,
                "capture_commands": False,
            },
        }
        
        config = ProfilerConfig.from_dict(config_dict)
        
        assert config.profiler_type == ProfilerType.TEST_EXECUTION
        assert config.capture_test_lifecycle is True
        assert config.capture_commands is False


class TestRuntimeProfiling:
    """Test runtime profiling (TimingProfiler, MemoryProfiler)"""
    
    def test_timing_profiler_basic(self):
        """Test basic timing profiler"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.RUNTIME,
            mode=ProfilingMode.FULL,
            level=ProfilingLevel.BASIC,
            targets=[],
            slow_call_ms=0,
            output_type=OutputType.NONE,
        )
        
        profiler = TimingProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        profiler.start("test_operation")
        time.sleep(0.01)
        profiler.stop("test_operation")
        
        assert len(records_emitted) >= 1
        assert records_emitted[0].name == "test_operation"
        assert records_emitted[0].duration_ms >= 10
    
    def test_memory_profiler(self):
        """Test memory profiler"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.RUNTIME,
            mode=ProfilingMode.FULL,
            level=ProfilingLevel.DETAILED,
            targets=[],
            slow_call_ms=0,
            output_type=OutputType.NONE,
        )
        
        profiler = MemoryProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        profiler.start("test_memory")
        # Allocate some memory
        data = [i for i in range(10000)]
        time.sleep(0.01)
        profiler.stop("test_memory")
        
        assert len(records_emitted) >= 1
        assert records_emitted[0].name == "test_memory"
        assert records_emitted[0].peak_memory_mb is not None
    
    def test_context_manager(self):
        """Test profile() context manager"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.RUNTIME,
            mode=ProfilingMode.FULL,
            targets=[],
            slow_call_ms=0,
            output_type=OutputType.NONE,
        )
        
        profiler = TimingProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        with profile("test_context", profiler=profiler):
            time.sleep(0.01)
        
        assert len(records_emitted) >= 1
        assert records_emitted[0].name == "test_context"
    
    def test_decorator(self):
        """Test @profiled decorator"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.RUNTIME,
            mode=ProfilingMode.FULL,
            targets=[],
            slow_call_ms=0,
            output_type=OutputType.NONE,
        )
        
        profiler = TimingProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        @profiled("test_func", profiler=profiler)
        def my_function():
            time.sleep(0.01)
            return "result"
        
        result = my_function()
        
        assert result == "result"
        assert len(records_emitted) >= 1
        assert records_emitted[0].name == "test_func"


class TestTestExecutionProfiling:
    """Test test execution profiling (TestExecutionProfiler)"""
    
    def test_test_lifecycle(self):
        """Test test lifecycle profiling"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.TEST_EXECUTION,
            mode=ProfilingMode.FULL,
            capture_test_lifecycle=True,
            slow_call_ms=0,
            output_type=OutputType.NONE,
        )
        
        profiler = TestExecutionProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        # Simulate test execution
        profiler.start_test("test_123", "Login Test", {"framework": "pytest"})
        time.sleep(0.02)
        profiler.end_test("test_123", "passed")
        
        # Should have start and end events
        assert len(records_emitted) >= 1
        test_records = [r for r in records_emitted if "test_123" in r.name]
        assert len(test_records) >= 1
    
    def test_command_recording(self):
        """Test driver command recording"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.TEST_EXECUTION,
            capture_commands=True,
            slow_call_ms=10,  # Only record slow commands
            output_type=OutputType.NONE,
        )
        
        profiler = TestExecutionProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        # Record fast command (should not emit)
        profiler.record_command("test_123", "click", 5.0, "selenium")
        assert len(records_emitted) == 0
        
        # Record slow command (should emit)
        profiler.record_command("test_123", "wait", 50.0, "selenium", {"selector": "#button"})
        assert len(records_emitted) == 1
        assert "selenium" in records_emitted[0].name
        assert records_emitted[0].metadata["test_id"] == "test_123"
    
    def test_http_recording(self):
        """Test HTTP request recording"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.TEST_EXECUTION,
            capture_http=True,
            slow_call_ms=10,
            output_type=OutputType.NONE,
        )
        
        profiler = TestExecutionProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        # Record HTTP request
        profiler.record_http(
            "test_123",
            "POST",
            "https://api.example.com/login",
            200,
            125.5,
            {"body_size": 1024}
        )
        
        assert len(records_emitted) == 1
        assert "http.POST" in records_emitted[0].name
        assert records_emitted[0].metadata["status_code"] == 200
    
    def test_assertion_recording(self):
        """Test assertion recording"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.TEST_EXECUTION,
            capture_assertions=True,  # Disabled by default
            output_type=OutputType.NONE,
        )
        
        profiler = TestExecutionProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        profiler.record_assertion("test_123", "equals", True, 0.5)
        
        assert len(records_emitted) == 1
        assert "assertion" in records_emitted[0].name
        assert records_emitted[0].metadata["passed"] is True


class TestSystemProfiling:
    """Test system profiling (SystemProfiler)"""
    
    def test_system_profiler_initialization(self):
        """Test system profiler initialization"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.SYSTEM,
            level=ProfilingLevel.SYSTEM,
            sampling_interval=0.1,  # Fast for testing
            max_snapshots=10,
            monitor_cpu=True,
            monitor_memory=True,
        )
        
        profiler = SystemProfiler(config)
        
        assert profiler._config.enabled is True
        assert profiler._config.sampling_interval == 0.1
    
    def test_system_profiler_sampling(self):
        """Test system profiler background sampling"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.SYSTEM,
            sampling_interval=0.1,
            max_snapshots=10,
        )
        
        profiler = SystemProfiler(config)
        
        # Start profiling
        profiler.start("system")
        time.sleep(0.3)  # Let it collect a few samples
        profiler.stop("system")
        
        # Should have collected snapshots
        snapshots = profiler.get_snapshots()
        assert len(snapshots) >= 2  # At least 2 samples in 0.3s
        assert snapshots[0].cpu_percent >= 0.0
        assert snapshots[0].memory_mb > 0.0
    
    def test_system_profiler_summary(self):
        """Test system profiler summary statistics"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.SYSTEM,
            sampling_interval=0.1,
        )
        
        profiler = SystemProfiler(config)
        
        profiler.start("system")
        time.sleep(0.3)
        profiler.stop("system")
        
        summary = profiler.get_summary()
        
        assert summary["count"] >= 2
        assert "cpu" in summary
        assert "memory" in summary
        assert summary["cpu"]["avg"] >= 0.0


class TestBenchmarkProfiling:
    """Test benchmarking (BenchmarkProfiler)"""
    
    def test_benchmark_operation(self):
        """Test benchmarking an operation"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.BENCHMARK,
            benchmark_iterations=5,
        )
        
        profiler = BenchmarkProfiler(config)
        
        def sample_operation():
            time.sleep(0.01)
            return sum(range(1000))
        
        result = profiler.benchmark_operation("test_adapter", sample_operation)
        
        assert result.adapter_name == "test_adapter"
        assert result.iterations == 5
        assert result.successful_runs == 5
        assert result.avg_duration_ms >= 10
    
    def test_benchmark_comparison(self):
        """Test adapter comparison"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.BENCHMARK,
            benchmark_iterations=3,
        )
        
        profiler = BenchmarkProfiler(config)
        
        # Benchmark multiple adapters
        def fast_operation():
            time.sleep(0.01)
        
        def slow_operation():
            time.sleep(0.03)
        
        profiler.benchmark_operation("fast_adapter", fast_operation)
        profiler.benchmark_operation("slow_adapter", slow_operation)
        
        comparison = profiler.compare_adapters()
        
        assert comparison["fastest"] == "fast_adapter"
        assert comparison["slowest"] == "slow_adapter"
        assert len(comparison["results"]) == 2
    
    def test_benchmark_insights(self):
        """Test performance insights"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.BENCHMARK,
            benchmark_iterations=3,
        )
        
        profiler = BenchmarkProfiler(config)
        
        def operation():
            time.sleep(0.01)
        
        profiler.benchmark_operation("adapter1", operation)
        
        insights = profiler.get_insights()
        
        assert len(insights) > 0
        # Should have at least one insight
        assert any("adapter" in insight.lower() or "acceptable" in insight.lower() for insight in insights)
    
    def test_benchmark_report(self):
        """Test markdown report generation"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.BENCHMARK,
            benchmark_iterations=3,
        )
        
        profiler = BenchmarkProfiler(config)
        
        def operation():
            time.sleep(0.01)
        
        profiler.benchmark_operation("test_adapter", operation)
        
        report = profiler.generate_report()
        
        assert "# Benchmark Report" in report
        assert "test_adapter" in report
        assert "Insights" in report


class TestProfilerFactory:
    """Test profiler factory"""
    
    def test_create_noop_profiler(self):
        """Test creating NoOp profiler when disabled"""
        config = ProfilerConfig(enabled=False)
        profiler = create_profiler(config)
        
        assert isinstance(profiler, NoOpProfiler)
    
    def test_create_timing_profiler(self):
        """Test creating timing profiler"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.RUNTIME,
            level=ProfilingLevel.BASIC,
        )
        profiler = create_profiler(config)
        
        assert isinstance(profiler, TimingProfiler)
    
    def test_create_memory_profiler(self):
        """Test creating memory profiler"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.RUNTIME,
            level=ProfilingLevel.DETAILED,
        )
        profiler = create_profiler(config)
        
        assert isinstance(profiler, MemoryProfiler)
    
    def test_create_test_execution_profiler(self):
        """Test creating test execution profiler"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.TEST_EXECUTION,
        )
        profiler = create_profiler(config)
        
        assert isinstance(profiler, TestExecutionProfiler)
    
    def test_create_system_profiler(self):
        """Test creating system profiler"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.SYSTEM,
        )
        profiler = create_profiler(config)
        
        assert isinstance(profiler, SystemProfiler)
    
    def test_create_benchmark_profiler(self):
        """Test creating benchmark profiler"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.BENCHMARK,
        )
        profiler = create_profiler(config)
        
        assert isinstance(profiler, BenchmarkProfiler)
    
    def test_global_profiler_initialization(self):
        """Test global profiler initialization"""
        config = ProfilerConfig(
            enabled=True,
            profiler_type=ProfilerType.RUNTIME,
            level=ProfilingLevel.BASIC,
        )
        
        # Initialize global profiler
        initialize_profiler(config)
        
        # Should be able to use context manager without passing profiler
        from core.profiling.factory import get_profiler
        profiler = get_profiler()
        
        assert profiler is not None
        assert isinstance(profiler, TimingProfiler)
        
        # Cleanup
        reset_profiler()


class TestBackwardCompatibility:
    """Test backward compatibility with legacy systems"""
    
    def test_noop_profiler_still_works(self):
        """Test NoOpProfiler still works as before"""
        profiler = NoOpProfiler()
        
        profiler.start("test")
        profiler.stop("test")
        
        # Should not raise any errors
        assert True
    
    def test_timing_profiler_still_works(self):
        """Test TimingProfiler still works with old interface"""
        config = ProfilerConfig(
            enabled=True,
            mode=ProfilingMode.FULL,
            level=ProfilingLevel.BASIC,
            targets=[],
            slow_call_ms=0,
            output_type=OutputType.NONE,
        )
        
        profiler = TimingProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        profiler.start("old_style_profiling")
        time.sleep(0.01)
        profiler.stop("old_style_profiling")
        
        assert len(records_emitted) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
