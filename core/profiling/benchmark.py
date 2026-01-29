"""
Benchmark Profiler

Adapter performance comparison and benchmarking.
Consolidates PerformanceBenchmark functionality with config-driven approach.
"""

import time
import tracemalloc
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
from core.profiling.base import Profiler, ProfilerConfig, ProfileRecord
from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.PERFORMANCE)


@dataclass
class BenchmarkResult:
    """Single benchmark result"""
    adapter_name: str
    iterations: int
    successful_runs: int
    failed_runs: int
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    avg_memory_mb: float
    peak_memory_mb: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "adapter": self.adapter_name,
            "iterations": self.iterations,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "avg_duration_ms": self.avg_duration_ms,
            "min_duration_ms": self.min_duration_ms,
            "max_duration_ms": self.max_duration_ms,
            "avg_memory_mb": self.avg_memory_mb,
            "peak_memory_mb": self.peak_memory_mb,
        }


class BenchmarkProfiler(Profiler):
    """
    Profiler for benchmarking and adapter comparison.
    
    Replaces PerformanceBenchmark with config-driven approach.
    """
    
    def __init__(self, config: ProfilerConfig):
        """Initialize benchmark profiler"""
        if not config.enabled:
            raise ValueError("BenchmarkProfiler requires enabled=True")
        
        self._config = config
        self._results: List[BenchmarkResult] = []
        
        logger.info(
            f"BenchmarkProfiler initialized: "
            f"iterations={config.benchmark_iterations}, "
            f"baselines={config.baseline_adapters}"
        )
    
    def start(self, name: str, metadata: Optional[Dict] = None) -> None:
        """Start not used for benchmarking"""
        pass
    
    def stop(self, name: str, metadata: Optional[Dict] = None) -> None:
        """Stop not used for benchmarking"""
        pass
    
    def emit(self, record: ProfileRecord) -> None:
        """Emit not used for benchmarking"""
        pass
    
    def benchmark_operation(
        self,
        adapter_name: str,
        operation: Callable,
        *args,
        iterations: Optional[int] = None,
        **kwargs
    ) -> BenchmarkResult:
        """
        Benchmark an operation.
        
        Args:
            adapter_name: Name of adapter being benchmarked
            operation: Operation to benchmark
            *args: Operation arguments
            iterations: Number of iterations (uses config if None)
            **kwargs: Operation keyword arguments
        
        Returns:
            Benchmark result
        """
        iterations = iterations or self._config.benchmark_iterations
        
        timing_results = []
        memory_results = []
        
        for i in range(iterations):
            try:
                # Measure timing
                start = time.perf_counter()
                result = operation(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                timing_results.append(duration_ms)
                
                # Measure memory (every 3rd iteration to reduce overhead)
                if i % 3 == 0:
                    tracemalloc.start()
                    try:
                        _ = operation(*args, **kwargs)
                        current, peak = tracemalloc.get_traced_memory()
                        memory_results.append({
                            "current_mb": current / 1024 / 1024,
                            "peak_mb": peak / 1024 / 1024
                        })
                    finally:
                        tracemalloc.stop()
                
            except Exception as e:
                logger.error(f"Benchmark iteration failed: {e}", exc_info=True)
        
        # Calculate statistics
        successful_runs = len(timing_results)
        failed_runs = iterations - successful_runs
        
        if timing_results:
            avg_duration_ms = sum(timing_results) / len(timing_results)
            min_duration_ms = min(timing_results)
            max_duration_ms = max(timing_results)
        else:
            avg_duration_ms = min_duration_ms = max_duration_ms = 0.0
        
        if memory_results:
            avg_memory_mb = sum(m["current_mb"] for m in memory_results) / len(memory_results)
            peak_memory_mb = max(m["peak_mb"] for m in memory_results)
        else:
            avg_memory_mb = peak_memory_mb = 0.0
        
        result = BenchmarkResult(
            adapter_name=adapter_name,
            iterations=iterations,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            avg_duration_ms=avg_duration_ms,
            min_duration_ms=min_duration_ms,
            max_duration_ms=max_duration_ms,
            avg_memory_mb=avg_memory_mb,
            peak_memory_mb=peak_memory_mb,
        )
        
        self._results.append(result)
        
        logger.info(
            f"Benchmark complete: {adapter_name} - "
            f"avg={avg_duration_ms:.2f}ms, "
            f"memory={avg_memory_mb:.2f}MB, "
            f"success_rate={successful_runs}/{iterations}"
        )
        
        return result
    
    def compare_adapters(self, adapter_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compare benchmark results across adapters.
        
        Args:
            adapter_names: List of adapter names to compare (None = all)
        
        Returns:
            Comparison results
        """
        results = self._results
        
        if adapter_names:
            results = [r for r in results if r.adapter_name in adapter_names]
        
        if not results:
            return {
                "adapters": adapter_names or [],
                "comparison": "No benchmark data available",
            }
        
        # Sort by duration
        sorted_results = sorted(results, key=lambda r: r.avg_duration_ms)
        
        # Calculate relative performance
        if self._config.compare_baselines and self._config.baseline_adapters:
            baseline_results = [r for r in sorted_results if r.adapter_name in self._config.baseline_adapters]
            baseline_avg = sum(r.avg_duration_ms for r in baseline_results) / len(baseline_results) if baseline_results else None
        else:
            baseline_avg = sorted_results[0].avg_duration_ms if sorted_results else None
        
        comparison = {
            "adapters": [r.adapter_name for r in sorted_results],
            "fastest": sorted_results[0].adapter_name if sorted_results else None,
            "slowest": sorted_results[-1].adapter_name if sorted_results else None,
            "results": [r.to_dict() for r in sorted_results],
        }
        
        if baseline_avg:
            comparison["relative_performance"] = {
                r.adapter_name: {
                    "speedup": baseline_avg / r.avg_duration_ms if r.avg_duration_ms > 0 else 0.0,
                    "slowdown": r.avg_duration_ms / baseline_avg if baseline_avg > 0 else 0.0,
                }
                for r in sorted_results
            }
        
        return comparison
    
    def get_insights(self) -> List[str]:
        """
        Get performance optimization insights.
        
        Returns:
            List of insights
        """
        insights = []
        
        if not self._results:
            return ["No benchmark data available"]
        
        # Check for slow adapters
        durations = [r.avg_duration_ms for r in self._results]
        mean_duration = sum(durations) / len(durations)
        
        for result in self._results:
            if result.avg_duration_ms > mean_duration * 2:
                insights.append(
                    f"⚠️ {result.adapter_name} is significantly slower than average "
                    f"({result.avg_duration_ms:.2f}ms vs {mean_duration:.2f}ms)"
                )
        
        # Check for high memory usage
        for result in self._results:
            if result.avg_memory_mb > 100:
                insights.append(
                    f"⚠️ {result.adapter_name} has high memory usage ({result.avg_memory_mb:.2f} MB)"
                )
        
        # Check for failures
        for result in self._results:
            if result.failed_runs > 0:
                failure_rate = (result.failed_runs / result.iterations) * 100
                insights.append(
                    f"❌ {result.adapter_name} has {failure_rate:.1f}% failure rate "
                    f"({result.failed_runs}/{result.iterations} failed)"
                )
        
        if not insights:
            insights.append("✅ All adapters performing within acceptable limits")
        
        return insights
    
    def generate_report(self) -> str:
        """
        Generate markdown benchmark report.
        
        Returns:
            Markdown report
        """
        lines = []
        lines.append("# Benchmark Report\n")
        lines.append(f"## Summary\n")
        lines.append(f"- Total benchmarks: {len(self._results)}\n")
        lines.append(f"- Iterations per benchmark: {self._config.benchmark_iterations}\n")
        
        if self._results:
            lines.append("\n## Results\n")
            lines.append("| Adapter | Avg (ms) | Min (ms) | Max (ms) | Memory (MB) | Success Rate |")
            lines.append("|---------|----------|----------|----------|-------------|--------------|")
            
            for result in sorted(self._results, key=lambda r: r.avg_duration_ms):
                success_rate = (result.successful_runs / result.iterations) * 100
                lines.append(
                    f"| {result.adapter_name} | "
                    f"{result.avg_duration_ms:.2f} | "
                    f"{result.min_duration_ms:.2f} | "
                    f"{result.max_duration_ms:.2f} | "
                    f"{result.avg_memory_mb:.2f} | "
                    f"{success_rate:.0f}% |"
                )
            
            lines.append("\n## Insights\n")
            for insight in self.get_insights():
                lines.append(f"- {insight}\n")
        
        return "\n".join(lines)
    
    def clear_results(self) -> None:
        """Clear all benchmark results"""
        self._results.clear()
        logger.info("Benchmark results cleared")
