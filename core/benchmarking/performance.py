"""
Performance benchmarking for crossbridge adapters.

Provides performance profiling and optimization insights.
"""

from typing import List, Dict, Optional, Callable
from pathlib import Path
import time
import sys
import tracemalloc


class PerformanceBenchmark:
    """Benchmark adapter performance."""
    
    def __init__(self):
        """Initialize the benchmark."""
        self.benchmarks = []
        
    def measure_execution_time(self, func: Callable, *args, **kwargs) -> Dict:
        """
        Measure execution time of a function.
        
        Args:
            func: Function to measure
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Timing metrics
        """
        start_time = time.perf_counter()
        
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        return {
            'duration': duration,
            'success': success,
            'error': error,
            'result': result,
        }
    
    def measure_memory_usage(self, func: Callable, *args, **kwargs) -> Dict:
        """
        Measure memory usage of a function.
        
        Args:
            func: Function to measure
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Memory metrics
        """
        tracemalloc.start()
        
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return {
            'current_memory': current,
            'peak_memory': peak,
            'current_mb': current / (1024 * 1024),
            'peak_mb': peak / (1024 * 1024),
            'success': success,
            'error': error,
            'result': result,
        }
    
    def benchmark_adapter(
        self,
        adapter_name: str,
        operation: Callable,
        *args,
        iterations: int = 10,
        **kwargs
    ) -> Dict:
        """
        Benchmark adapter operation.
        
        Args:
            adapter_name: Name of adapter
            operation: Operation to benchmark
            *args: Operation arguments
            iterations: Number of iterations
            **kwargs: Operation keyword arguments
            
        Returns:
            Benchmark results
        """
        timing_results = []
        memory_results = []
        
        for i in range(iterations):
            # Measure time
            timing = self.measure_execution_time(operation, *args, **kwargs)
            timing_results.append(timing)
            
            # Measure memory (every 3rd iteration to reduce overhead)
            if i % 3 == 0:
                memory = self.measure_memory_usage(operation, *args, **kwargs)
                memory_results.append(memory)
        
        # Calculate statistics
        successful_timings = [t['duration'] for t in timing_results if t['success']]
        
        if successful_timings:
            avg_duration = sum(successful_timings) / len(successful_timings)
            min_duration = min(successful_timings)
            max_duration = max(successful_timings)
        else:
            avg_duration = 0
            min_duration = 0
            max_duration = 0
        
        successful_memory = [m['peak_mb'] for m in memory_results if m['success']]
        avg_memory = sum(successful_memory) / len(successful_memory) if successful_memory else 0
        
        benchmark_result = {
            'adapter': adapter_name,
            'iterations': iterations,
            'successful_runs': len(successful_timings),
            'failed_runs': iterations - len(successful_timings),
            'avg_duration': avg_duration,
            'min_duration': min_duration,
            'max_duration': max_duration,
            'avg_memory_mb': avg_memory,
        }
        
        self.benchmarks.append(benchmark_result)
        
        return benchmark_result
    
    def benchmark_file_processing(
        self,
        adapter_name: str,
        file_processor: Callable[[Path], any],
        test_files: List[Path],
    ) -> Dict:
        """
        Benchmark file processing performance.
        
        Args:
            adapter_name: Name of adapter
            file_processor: File processing function
            test_files: List of test files
            
        Returns:
            Benchmark results
        """
        file_results = []
        
        for test_file in test_files:
            if not test_file.exists():
                continue
            
            file_size = test_file.stat().st_size
            
            # Measure processing
            timing = self.measure_execution_time(file_processor, test_file)
            
            file_results.append({
                'file': str(test_file),
                'size_bytes': file_size,
                'size_kb': file_size / 1024,
                'duration': timing['duration'],
                'success': timing['success'],
            })
        
        # Calculate throughput
        successful_results = [r for r in file_results if r['success']]
        
        if successful_results:
            total_size = sum(r['size_kb'] for r in successful_results)
            total_time = sum(r['duration'] for r in successful_results)
            throughput_kb_s = total_size / total_time if total_time > 0 else 0
        else:
            throughput_kb_s = 0
        
        return {
            'adapter': adapter_name,
            'total_files': len(test_files),
            'successful': len(successful_results),
            'failed': len(file_results) - len(successful_results),
            'throughput_kb_per_sec': throughput_kb_s,
            'file_results': file_results,
        }
    
    def compare_adapters(self, adapter_names: List[str]) -> Dict:
        """
        Compare performance across adapters.
        
        Args:
            adapter_names: List of adapter names
            
        Returns:
            Comparison results
        """
        adapter_benchmarks = [
            b for b in self.benchmarks
            if b['adapter'] in adapter_names
        ]
        
        if not adapter_benchmarks:
            return {
                'adapters': adapter_names,
                'comparison': 'No benchmark data available',
            }
        
        # Sort by average duration
        sorted_benchmarks = sorted(
            adapter_benchmarks,
            key=lambda x: x['avg_duration']
        )
        
        return {
            'adapters': adapter_names,
            'fastest': sorted_benchmarks[0]['adapter'] if sorted_benchmarks else None,
            'slowest': sorted_benchmarks[-1]['adapter'] if sorted_benchmarks else None,
            'rankings': [b['adapter'] for b in sorted_benchmarks],
        }
    
    def generate_report(self) -> str:
        """
        Generate performance benchmark report.
        
        Returns:
            Report as markdown
        """
        lines = []
        lines.append("# Performance Benchmark Report\n")
        
        lines.append(f"## Summary\n")
        lines.append(f"- Total benchmarks: {len(self.benchmarks)}\n")
        
        if self.benchmarks:
            lines.append("## Benchmark Results\n")
            lines.append("| Adapter | Avg Duration (s) | Min (s) | Max (s) | Avg Memory (MB) |")
            lines.append("|---------|------------------|---------|---------|-----------------|")
            
            for benchmark in self.benchmarks:
                lines.append(
                    f"| {benchmark['adapter']} | "
                    f"{benchmark['avg_duration']:.4f} | "
                    f"{benchmark['min_duration']:.4f} | "
                    f"{benchmark['max_duration']:.4f} | "
                    f"{benchmark['avg_memory_mb']:.2f} |"
                )
        
        return '\n'.join(lines)
    
    def get_performance_insights(self) -> List[str]:
        """
        Get performance optimization insights.
        
        Returns:
            List of insights
        """
        insights = []
        
        if not self.benchmarks:
            return ["No benchmark data available"]
        
        # Check for slow adapters
        avg_durations = [b['avg_duration'] for b in self.benchmarks]
        mean_duration = sum(avg_durations) / len(avg_durations)
        
        for benchmark in self.benchmarks:
            if benchmark['avg_duration'] > mean_duration * 2:
                insights.append(
                    f"⚠️ {benchmark['adapter']} is significantly slower than average "
                    f"({benchmark['avg_duration']:.2f}s vs {mean_duration:.2f}s)"
                )
        
        # Check for high memory usage
        for benchmark in self.benchmarks:
            if benchmark['avg_memory_mb'] > 100:
                insights.append(
                    f"⚠️ {benchmark['adapter']} uses high memory ({benchmark['avg_memory_mb']:.1f} MB)"
                )
        
        # Check for failures
        for benchmark in self.benchmarks:
            if benchmark['failed_runs'] > 0:
                failure_rate = (benchmark['failed_runs'] / benchmark['iterations']) * 100
                insights.append(
                    f"⚠️ {benchmark['adapter']} has {failure_rate:.1f}% failure rate"
                )
        
        if not insights:
            insights.append("✅ All adapters performing within expected parameters")
        
        return insights
