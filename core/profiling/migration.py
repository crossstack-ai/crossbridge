"""
Profiling Migration Utility

Helps migrate from legacy profiling systems to unified config-driven profiling.

Migrations:
1. Legacy MetricsCollector → TestExecutionProfiler
2. Sidecar LightweightProfiler → SystemProfiler
3. PerformanceBenchmark → BenchmarkProfiler
"""

from typing import Dict, Any, Optional
import yaml
from pathlib import Path
from core.profiling.base import ProfilerConfig, ProfilerType, ProfilingMode, ProfilingLevel, OutputType
from core.profiling.factory import create_profiler, initialize_profiler
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


class ProfilingMigration:
    """Migration utility for profiling systems"""
    
    @staticmethod
    def migrate_legacy_profile_config(legacy_config: Dict[str, Any]) -> ProfilerConfig:
        """
        Migrate legacy ProfileConfig to new ProfilerConfig.
        
        Args:
            legacy_config: Legacy configuration dict
        
        Returns:
            New ProfilerConfig
        """
        logger.info("Migrating legacy ProfileConfig to new system")
        
        # Map legacy config to new config
        new_config = {
            "enabled": legacy_config.get("enabled", True),
            "type": "test_execution",  # Legacy was for test execution
            "mode": "full",  # Legacy always did full profiling
            "level": "basic",
            "thresholds": {
                "slow_call_ms": 100,  # Lower threshold for test commands
            },
            "test_execution": {
                "capture_lifecycle": True,
                "capture_commands": True,
                "capture_http": True,
                "capture_assertions": False,
            },
            "output": {
                "type": legacy_config.get("storage_backend", "database"),
                "database_path": legacy_config.get("storage_path", "./data/profiling/test_execution.db"),
            },
            "max_records_per_minute": 1000,  # Higher for test execution
        }
        
        return ProfilerConfig.from_dict(new_config)
    
    @staticmethod
    def migrate_sidecar_profiler_config(
        sampling_interval: float = 1.0,
        max_snapshots: int = 1000
    ) -> ProfilerConfig:
        """
        Create config for SystemProfiler (replaces sidecar LightweightProfiler).
        
        Args:
            sampling_interval: How often to sample (seconds)
            max_snapshots: Max snapshots to keep
        
        Returns:
            ProfilerConfig for system profiling
        """
        logger.info("Migrating sidecar profiler configuration")
        
        config = {
            "enabled": True,
            "type": "system",
            "level": "system",
            "sampling_interval": sampling_interval,
            "max_snapshots": max_snapshots,
            "system": {
                "monitor_cpu": True,
                "monitor_memory": True,
                "monitor_threads": True,
                "monitor_gc": True,
            },
            "thresholds": {
                "cpu_percent": 80.0,
                "memory_mb": 500,
            },
            "output": {
                "type": "log",
            },
        }
        
        return ProfilerConfig.from_dict(config)
    
    @staticmethod
    def migrate_benchmark_config(
        iterations: int = 10,
        baseline_adapters: Optional[list] = None
    ) -> ProfilerConfig:
        """
        Create config for BenchmarkProfiler (replaces PerformanceBenchmark).
        
        Args:
            iterations: Iterations per benchmark
            baseline_adapters: Baseline adapters for comparison
        
        Returns:
            ProfilerConfig for benchmarking
        """
        logger.info("Migrating benchmark configuration")
        
        config = {
            "enabled": True,
            "type": "benchmark",
            "benchmarking": {
                "iterations": iterations,
                "compare_baselines": bool(baseline_adapters),
                "baseline_adapters": baseline_adapters or [],
            },
            "output": {
                "type": "file",
                "path": "./data/profiling/benchmark_results.json",
            },
        }
        
        return ProfilerConfig.from_dict(config)
    
    @staticmethod
    def load_unified_config_from_yaml(
        yaml_path: str,
        profiler_type: str = "runtime"
    ) -> ProfilerConfig:
        """
        Load unified profiling config from crossbridge.yml.
        
        Args:
            yaml_path: Path to crossbridge.yml
            profiler_type: Type of profiler (runtime|test_execution|system|benchmark)
        
        Returns:
            ProfilerConfig
        """
        logger.info(f"Loading {profiler_type} config from {yaml_path}")
        
        with open(yaml_path, 'r') as f:
            yaml_config = yaml.safe_load(f)
        
        # Navigate to profiling config
        profiling_config = yaml_config.get("runtime", {}).get("profiling", {})
        
        # Get specific profiler type config
        type_config = profiling_config.get(profiler_type, {})
        
        if not type_config:
            logger.warning(f"No config found for {profiler_type}, using defaults")
            type_config = {"enabled": False}
        
        return ProfilerConfig.from_dict(type_config)
    
    @staticmethod
    def auto_migrate_and_initialize(yaml_path: str = "./crossbridge.yml") -> None:
        """
        Automatically migrate and initialize profiling from YAML.
        
        This is the main entry point for migration.
        
        Args:
            yaml_path: Path to crossbridge.yml
        """
        logger.info("Starting automatic profiling migration")
        
        if not Path(yaml_path).exists():
            logger.error(f"Config file not found: {yaml_path}")
            return
        
        try:
            # Load runtime profiling config (most common)
            config = ProfilingMigration.load_unified_config_from_yaml(yaml_path, "runtime")
            
            # Initialize global profiler
            profiler = create_profiler(config)
            initialize_profiler(config)
            
            logger.info(
                f"Profiling migration complete: "
                f"type={config.profiler_type.value}, "
                f"enabled={config.enabled}"
            )
            
        except Exception as e:
            logger.error(f"Profiling migration failed: {e}", exc_info=True)


# Example migration code for legacy users
def migrate_from_legacy_metrics_collector():
    """
    Example migration from MetricsCollector to TestExecutionProfiler.
    
    OLD CODE:
    ```python
    from core.profiling import ProfileConfig, MetricsCollector
    
    config = ProfileConfig(enabled=True, storage_backend="sqlite")
    collector = MetricsCollector(config)
    collector.start()
    ```
    
    NEW CODE:
    ```python
    from core.profiling import ProfilerConfig, TestExecutionProfiler, ProfilerType
    
    config = ProfilerConfig(
        enabled=True,
        profiler_type=ProfilerType.TEST_EXECUTION,
        output_type=OutputType.DATABASE,
        database_path="./data/profiling/test_execution.db"
    )
    profiler = TestExecutionProfiler(config)
    profiler.start_test(test_id="test_123", test_name="Login Test")
    ```
    
    OR use migration utility:
    ```python
    from core.profiling.migration import ProfilingMigration
    
    # Automatic migration
    ProfilingMigration.auto_migrate_and_initialize()
    ```
    """
    pass


def migrate_from_sidecar_profiler():
    """
    Example migration from LightweightProfiler to SystemProfiler.
    
    OLD CODE:
    ```python
    from core.sidecar.profiler import LightweightProfiler
    
    profiler = LightweightProfiler(sampling_interval=1.0)
    profiler.start()
    summary = profiler.get_summary()
    ```
    
    NEW CODE:
    ```python
    from core.profiling import SystemProfiler, ProfilerConfig, ProfilerType
    
    config = ProfilerConfig(
        enabled=True,
        profiler_type=ProfilerType.SYSTEM,
        sampling_interval=1.0
    )
    profiler = SystemProfiler(config)
    profiler.start("system")
    summary = profiler.get_summary()
    ```
    
    OR use YAML config:
    ```yaml
    runtime:
      profiling:
        system:
          enabled: true
          type: system
          sampling_interval: 1.0
    ```
    """
    pass


def migrate_from_performance_benchmark():
    """
    Example migration from PerformanceBenchmark to BenchmarkProfiler.
    
    OLD CODE:
    ```python
    from core.benchmarking import PerformanceBenchmark
    
    benchmark = PerformanceBenchmark()
    result = benchmark.benchmark_adapter('selenium', operation, iterations=10)
    insights = benchmark.get_performance_insights()
    ```
    
    NEW CODE:
    ```python
    from core.profiling import BenchmarkProfiler, ProfilerConfig, ProfilerType
    
    config = ProfilerConfig(
        enabled=True,
        profiler_type=ProfilerType.BENCHMARK,
        benchmark_iterations=10
    )
    profiler = BenchmarkProfiler(config)
    result = profiler.benchmark_operation('selenium', operation)
    insights = profiler.get_insights()
    ```
    
    OR use YAML config:
    ```yaml
    runtime:
      profiling:
        benchmarking:
          enabled: true
          type: benchmark
          iterations: 10
    ```
    """
    pass
