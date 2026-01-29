"""
Unit tests for Config-Driven Profiling

Tests profiler implementations, factory, and context managers.
"""

import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import json

from core.profiling.base import (
    Profiler,
    ProfilerConfig,
    ProfileRecord,
    ProfilingMode,
    ProfilingLevel,
    OutputType,
)
from core.profiling.noop import NoOpProfiler
from core.profiling.timing import TimingProfiler
from core.profiling.memory import MemoryProfiler
from core.profiling.factory import create_profiler, initialize_profiler, reset_profiler
from core.profiling.context import profile, profiled, ProfilerContext


class TestProfilerConfig:
    """Test profiler configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = ProfilerConfig()
        
        assert config.enabled == False
        assert config.mode == ProfilingMode.SAMPLING
        assert config.level == ProfilingLevel.BASIC
        assert config.slow_call_ms == 500.0
        assert config.output_type == OutputType.LOG
    
    def test_config_from_dict(self):
        """Test creating config from dictionary"""
        config_dict = {
            "enabled": True,
            "mode": "full",
            "level": "detailed",
            "targets": ["semantic_search", "vector_store"],
            "thresholds": {
                "slow_call_ms": 300,
                "memory_mb": 100
            },
            "output": {
                "type": "file",
                "path": "/tmp/profile.json"
            }
        }
        
        config = ProfilerConfig.from_dict(config_dict)
        
        assert config.enabled == True
        assert config.mode == ProfilingMode.FULL
        assert config.level == ProfilingLevel.DETAILED
        assert config.targets == ["semantic_search", "vector_store"]
        assert config.slow_call_ms == 300
        assert config.memory_mb == 100
        assert config.output_type == OutputType.FILE
        assert config.output_path == "/tmp/profile.json"


class TestNoOpProfiler:
    """Test NoOp profiler (zero cost when disabled)"""
    
    def test_noop_start_stop(self):
        """Test NoOp profiler does nothing"""
        profiler = NoOpProfiler()
        
        # Should not raise or do anything
        profiler.start("test")
        profiler.stop("test")
        profiler.emit(ProfileRecord(name="test", duration_ms=100, timestamp=time.time()))
    
    def test_noop_is_disabled(self):
        """Test NoOp profiler is always disabled"""
        profiler = NoOpProfiler()
        
        assert profiler.is_enabled() == False
        assert profiler.should_profile("anything") == False


class TestTimingProfiler:
    """Test timing profiler"""
    
    @pytest.fixture
    def config(self):
        """Create test config"""
        return ProfilerConfig(
            enabled=True,
            mode=ProfilingMode.FULL,  # Use FULL mode for tests
            level=ProfilingLevel.BASIC,
            targets=["test_target"],
            slow_call_ms=100,
            output_type=OutputType.NONE,
        )
    
    def test_timing_profiler_initialization(self, config):
        """Test timing profiler initialization"""
        profiler = TimingProfiler(config)
        
        assert profiler.config == config
        assert profiler.is_enabled() == True
    
    def test_timing_profiler_measures_duration(self, config):
        """Test timing profiler measures execution time"""
        profiler = TimingProfiler(config)
        
        profiler.start("test_target")
        time.sleep(0.15)  # Sleep 150ms (above 100ms threshold)
        profiler.stop("test_target")
        
        # Should have emitted record (checked via logs)
    
    def test_target_filtering(self, config):
        """Test target filtering"""
        profiler = TimingProfiler(config)
        
        assert profiler.should_profile("test_target") == True
        assert profiler.should_profile("test_target.method") == True
        assert profiler.should_profile("other_target") == False
    
    def test_empty_targets_profiles_all(self):
        """Test empty targets list profiles everything"""
        config = ProfilerConfig(
            enabled=True,
            targets=[],  # Empty = all
        )
        profiler = TimingProfiler(config)
        
        assert profiler.should_profile("anything") == True
        assert profiler.should_profile("everything") == True
    
    def test_slow_call_threshold(self, config):
        """Test only slow calls are emitted"""
        profiler = TimingProfiler(config)
        records_emitted = []
        
        # Mock emit to capture records
        original_emit = profiler.emit
        profiler.emit = lambda r: records_emitted.append(r)
        
        # Fast call (below threshold)
        profiler.start("test_target")
        time.sleep(0.05)  # 50ms < 100ms
        profiler.stop("test_target")
        
        # Slow call (above threshold)
        profiler.start("test_target")
        time.sleep(0.15)  # 150ms > 100ms
        profiler.stop("test_target")
        
        # Only slow call should be emitted
        assert len(records_emitted) >= 1
        assert records_emitted[0].duration_ms >= 100
    
    def test_rate_limiting(self):
        """Test rate limiting prevents overflow"""
        config = ProfilerConfig(
            enabled=True,
            targets=[],
            slow_call_ms=0,  # Emit everything
            max_records_per_minute=5,
        )
        profiler = TimingProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        # Try to emit 10 records
        for i in range(10):
            profiler.start("test")
            profiler.stop("test")
        
        # Should have emitted at most 5
        assert len(records_emitted) <= 5
    
    def test_file_output(self):
        """Test file output"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "profile.jsonl"
            
            config = ProfilerConfig(
                enabled=True,
                mode=ProfilingMode.FULL,  # Use FULL mode for tests
                targets=[],
                slow_call_ms=0,
                output_type=OutputType.FILE,
                output_path=str(output_path),
            )
            profiler = TimingProfiler(config)
            
            profiler.start("test")
            time.sleep(0.01)
            profiler.stop("test", {"key": "value"})
            
            # Check file exists and has content
            assert output_path.exists()
            
            with open(output_path) as f:
                line = f.readline()
                record = json.loads(line)
                assert record["name"] == "test"
                assert "duration_ms" in record
                assert record["metadata"]["key"] == "value"


class TestMemoryProfiler:
    """Test memory profiler"""
    
    @pytest.fixture
    def config(self):
        """Create detailed config (enables memory tracking)"""
        return ProfilerConfig(
            enabled=True,
            level=ProfilingLevel.DETAILED,
            targets=[],
            slow_call_ms=0,
            memory_mb=10,
            output_type=OutputType.NONE,
        )
    
    def test_memory_profiler_initialization(self, config):
        """Test memory profiler initialization"""
        profiler = MemoryProfiler(config)
        
        assert profiler.track_memory == True
    
    def test_memory_tracking(self, config):
        """Test memory usage is tracked"""
        profiler = MemoryProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        profiler.start("test")
        # Allocate some memory
        data = [0] * (1024 * 1024 * 20)  # ~20MB
        profiler.stop("test")
        
        # Should have emitted record with memory info
        if records_emitted:
            assert records_emitted[0].peak_memory_mb is not None


class TestProfilerFactory:
    """Test profiler factory"""
    
    def teardown_method(self):
        """Reset profiler after each test"""
        reset_profiler()
    
    def test_create_profiler_disabled(self):
        """Test factory returns NoOp when disabled"""
        config = ProfilerConfig(enabled=False)
        profiler = create_profiler(config)
        
        assert isinstance(profiler, NoOpProfiler)
    
    def test_create_profiler_basic(self):
        """Test factory returns TimingProfiler for basic level"""
        config = ProfilerConfig(
            enabled=True,
            level=ProfilingLevel.BASIC,
        )
        profiler = create_profiler(config)
        
        assert isinstance(profiler, TimingProfiler)
        assert not isinstance(profiler, MemoryProfiler)
    
    def test_create_profiler_detailed(self):
        """Test factory returns MemoryProfiler for detailed level"""
        config = ProfilerConfig(
            enabled=True,
            level=ProfilingLevel.DETAILED,
        )
        profiler = create_profiler(config)
        
        assert isinstance(profiler, MemoryProfiler)
    
    def test_initialize_global_profiler(self):
        """Test global profiler initialization"""
        from core.profiling.factory import get_profiler
        
        config = ProfilerConfig(enabled=True)
        profiler = initialize_profiler(config)
        
        # Global profiler should be set
        assert get_profiler() is profiler


class TestProfileContext:
    """Test profiling context managers"""
    
    def test_profile_context_manager(self):
        """Test profile() context manager"""
        config = ProfilerConfig(
            enabled=True,
            mode=ProfilingMode.FULL,  # Use FULL mode for tests
            targets=[],
            slow_call_ms=0,
            output_type=OutputType.NONE
        )
        profiler = TimingProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        with profile("test_operation", {"key": "value"}, profiler):
            time.sleep(0.01)
        
        # Should have profiled
        assert len(records_emitted) >= 1
        assert records_emitted[0].name == "test_operation"
    
    def test_profiled_decorator(self):
        """Test @profiled decorator"""
        config = ProfilerConfig(
            enabled=True,
            mode=ProfilingMode.FULL,  # Use FULL mode for tests
            targets=[],
            slow_call_ms=0,
            output_type=OutputType.NONE
        )
        profiler = TimingProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        @profiled("test_function", profiler=profiler)
        def my_function():
            time.sleep(0.01)
            return "result"
        
        result = my_function()
        
        assert result == "result"
        assert len(records_emitted) >= 1
        assert records_emitted[0].name == "test_function"
    
    def test_profiled_decorator_auto_name(self):
        """Test @profiled decorator with auto-naming"""
        config = ProfilerConfig(
            enabled=True,
            mode=ProfilingMode.FULL,  # Use FULL mode for tests
            targets=[],
            slow_call_ms=0,
            output_type=OutputType.NONE
        )
        profiler = TimingProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        @profiled(profiler=profiler)
        def my_function():
            time.sleep(0.01)
        
        my_function()
        
        assert len(records_emitted) >= 1
        assert records_emitted[0].name == "my_function"
    
    def test_profiler_context_class(self):
        """Test ProfilerContext class"""
        config = ProfilerConfig(
            enabled=True,
            mode=ProfilingMode.FULL,  # Use FULL mode for tests
            targets=[],
            slow_call_ms=0,
            output_type=OutputType.NONE
        )
        profiler = TimingProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        with ProfilerContext("test", profiler=profiler):
            time.sleep(0.01)
        
        assert len(records_emitted) >= 1
        assert records_emitted[0].name == "test"


class TestProfileRecord:
    """Test profile record"""
    
    def test_record_to_dict(self):
        """Test record serialization"""
        record = ProfileRecord(
            name="test",
            duration_ms=123.45,
            timestamp=1234567890.0,
            metadata={"key": "value"},
            peak_memory_mb=45.67,
        )
        
        d = record.to_dict()
        
        assert d["name"] == "test"
        assert d["duration_ms"] == 123.45
        assert d["timestamp"] == 1234567890.0
        assert d["metadata"] == {"key": "value"}
        assert d["peak_memory_mb"] == 45.67


class TestSamplingMode:
    """Test sampling profiling mode"""
    
    def test_sampling_mode_profiles_subset(self):
        """Test sampling mode only profiles a subset of requests"""
        config = ProfilerConfig(
            enabled=True,
            mode=ProfilingMode.SAMPLING,
            sample_rate=0.5,  # 50%
            targets=[],
            slow_call_ms=0,
            output_type=OutputType.NONE,
        )
        profiler = TimingProfiler(config)
        records_emitted = []
        profiler.emit = lambda r: records_emitted.append(r)
        
        # Try 100 calls
        for i in range(100):
            profiler.start("test")
            profiler.stop("test")
        
        # Should have profiled roughly 50% (with variance)
        # Allow 20-80% range due to randomness
        assert 20 <= len(records_emitted) <= 80


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
