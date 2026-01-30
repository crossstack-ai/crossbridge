"""
Observability and Metrics for Deterministic + AI System.

This module provides:
- Metrics collection for deterministic and AI paths
- Performance tracking
- Error monitoring
- Health checks
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import time
import logging
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class IntelligenceMetrics:
    """
    Metrics collector for intelligence system.
    
    Tracks:
    - Classification counts by label
    - AI enrichment success/failure rates
    - Latency percentiles
    - Error rates
    """
    
    def __init__(self, prefix: str = "crossbridge.intelligence"):
        """
        Initialize metrics collector.
        
        Args:
            prefix: Metric name prefix
        """
        self.prefix = prefix
        self._lock = Lock()
        
        # Counters
        self._counters: Dict[str, int] = defaultdict(int)
        
        # Histograms (for latency tracking)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Gauges (current values)
        self._gauges: Dict[str, float] = {}
        
        logger.info("IntelligenceMetrics initialized with prefix: %s", prefix)
    
    def increment(self, metric_name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """
        Increment a counter metric.
        
        Args:
            metric_name: Name of the metric
            value: Amount to increment (default 1)
            labels: Optional metric labels
        """
        full_name = self._build_metric_name(metric_name, labels)
        
        with self._lock:
            self._counters[full_name] += value
    
    def record_latency(self, metric_name: str, latency_ms: float, labels: Optional[Dict[str, str]] = None):
        """
        Record a latency measurement.
        
        Args:
            metric_name: Name of the metric
            latency_ms: Latency in milliseconds
            labels: Optional metric labels
        """
        full_name = self._build_metric_name(metric_name, labels)
        
        with self._lock:
            self._histograms[full_name].append(latency_ms)
            
            # Keep only last 1000 measurements to prevent memory growth
            if len(self._histograms[full_name]) > 1000:
                self._histograms[full_name] = self._histograms[full_name][-1000:]
    
    def set_gauge(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Set a gauge metric value.
        
        Args:
            metric_name: Name of the metric
            value: Current value
            labels: Optional metric labels
        """
        full_name = self._build_metric_name(metric_name, labels)
        
        with self._lock:
            self._gauges[full_name] = value
    
    def get_counter(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """Get current counter value."""
        full_name = self._build_metric_name(metric_name, labels)
        with self._lock:
            return self._counters.get(full_name, 0)
    
    def get_latency_percentile(
        self,
        metric_name: str,
        percentile: float,
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """
        Get latency percentile.
        
        Args:
            metric_name: Name of the metric
            percentile: Percentile to calculate (0-100)
            labels: Optional metric labels
            
        Returns:
            Percentile value in milliseconds or None if no data
        """
        full_name = self._build_metric_name(metric_name, labels)
        
        with self._lock:
            values = self._histograms.get(full_name, [])
            if not values:
                return None
            
            sorted_values = sorted(values)
            index = int(len(sorted_values) * (percentile / 100))
            return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics."""
        with self._lock:
            metrics = {
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'histograms': {}
            }
            
            # Calculate percentiles for histograms
            for name, values in self._histograms.items():
                if values:
                    sorted_values = sorted(values)
                    metrics['histograms'][name] = {
                        'count': len(values),
                        'p50': self._percentile(sorted_values, 50),
                        'p90': self._percentile(sorted_values, 90),
                        'p95': self._percentile(sorted_values, 95),
                        'p99': self._percentile(sorted_values, 99),
                        'min': sorted_values[0],
                        'max': sorted_values[-1],
                    }
            
            return metrics
    
    def reset(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()
    
    def _build_metric_name(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Build full metric name with prefix and labels."""
        full_name = f"{self.prefix}.{metric_name}"
        
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            full_name = f"{full_name}{{{label_str}}}"
        
        return full_name
    
    @staticmethod
    def _percentile(sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0
        
        index = int(len(sorted_values) * (percentile / 100))
        return sorted_values[min(index, len(sorted_values) - 1)]


# Standard metric names (for consistency)
class MetricNames:
    """Standard metric names for intelligence system."""
    
    # Deterministic classifier
    DETERMINISTIC_CLASSIFICATIONS_TOTAL = "deterministic.classifications_total"
    DETERMINISTIC_CLASSIFICATIONS_BY_LABEL = "deterministic.classifications_by_label"
    DETERMINISTIC_LATENCY = "deterministic.latency_ms"
    DETERMINISTIC_ERRORS = "deterministic.errors_total"
    
    # AI enrichment
    AI_ENRICHMENT_ATTEMPTED = "ai.enrichment.attempted"
    AI_ENRICHMENT_SUCCESS = "ai.enrichment.success"
    AI_ENRICHMENT_FAILED = "ai.enrichment.failed"
    AI_ENRICHMENT_TIMEOUT = "ai.enrichment.timeout"
    AI_ENRICHMENT_LOW_CONFIDENCE = "ai.enrichment.low_confidence"
    AI_ENRICHMENT_LATENCY = "ai.enrichment.latency_ms"
    
    # Combined results
    FINAL_RESULTS_WITH_AI = "final.results_with_ai"
    FINAL_RESULTS_WITHOUT_AI = "final.results_without_ai"
    FINAL_LATENCY = "final.latency_ms"


class MetricsTracker:
    """
    High-level metrics tracking for intelligence operations.
    
    This provides convenient methods for tracking common operations.
    """
    
    def __init__(self, metrics: Optional[IntelligenceMetrics] = None):
        """
        Initialize tracker.
        
        Args:
            metrics: Metrics collector instance
        """
        self.metrics = metrics or IntelligenceMetrics()
    
    def track_deterministic_classification(self, label: str, confidence: float, duration_ms: float):
        """Track a deterministic classification."""
        self.metrics.increment(MetricNames.DETERMINISTIC_CLASSIFICATIONS_TOTAL)
        self.metrics.increment(
            MetricNames.DETERMINISTIC_CLASSIFICATIONS_BY_LABEL,
            labels={'label': label}
        )
        self.metrics.record_latency(MetricNames.DETERMINISTIC_LATENCY, duration_ms)
        self.metrics.set_gauge(
            f"deterministic.confidence.{label}",
            confidence
        )
    
    def track_ai_enrichment_success(self, duration_ms: float, confidence: float):
        """Track successful AI enrichment."""
        self.metrics.increment(MetricNames.AI_ENRICHMENT_ATTEMPTED)
        self.metrics.increment(MetricNames.AI_ENRICHMENT_SUCCESS)
        self.metrics.record_latency(MetricNames.AI_ENRICHMENT_LATENCY, duration_ms)
        self.metrics.set_gauge("ai.enrichment.confidence", confidence)
    
    def track_ai_enrichment_failure(self, reason: str):
        """Track AI enrichment failure."""
        self.metrics.increment(MetricNames.AI_ENRICHMENT_ATTEMPTED)
        self.metrics.increment(MetricNames.AI_ENRICHMENT_FAILED, labels={'reason': reason})
    
    def track_ai_enrichment_timeout(self):
        """Track AI enrichment timeout."""
        self.metrics.increment(MetricNames.AI_ENRICHMENT_ATTEMPTED)
        self.metrics.increment(MetricNames.AI_ENRICHMENT_TIMEOUT)
    
    def track_ai_enrichment_low_confidence(self, confidence: float):
        """Track AI enrichment rejected due to low confidence."""
        self.metrics.increment(MetricNames.AI_ENRICHMENT_ATTEMPTED)
        self.metrics.increment(MetricNames.AI_ENRICHMENT_LOW_CONFIDENCE)
        self.metrics.set_gauge("ai.enrichment.rejected_confidence", confidence)
    
    def track_final_result(self, has_ai_enrichment: bool, total_duration_ms: float):
        """Track final combined result."""
        if has_ai_enrichment:
            self.metrics.increment(MetricNames.FINAL_RESULTS_WITH_AI)
        else:
            self.metrics.increment(MetricNames.FINAL_RESULTS_WITHOUT_AI)
        
        self.metrics.record_latency(MetricNames.FINAL_LATENCY, total_duration_ms)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        all_metrics = self.metrics.get_all_metrics()
        
        # Calculate derived metrics
        total_classifications = self.metrics.get_counter(
            MetricNames.DETERMINISTIC_CLASSIFICATIONS_TOTAL
        )
        
        ai_attempted = self.metrics.get_counter(MetricNames.AI_ENRICHMENT_ATTEMPTED)
        ai_success = self.metrics.get_counter(MetricNames.AI_ENRICHMENT_SUCCESS)
        ai_failed = self.metrics.get_counter(MetricNames.AI_ENRICHMENT_FAILED)
        
        ai_success_rate = (ai_success / ai_attempted * 100) if ai_attempted > 0 else 0
        
        return {
            'total_classifications': total_classifications,
            'ai_enrichment': {
                'attempted': ai_attempted,
                'success': ai_success,
                'failed': ai_failed,
                'success_rate_pct': round(ai_success_rate, 2),
            },
            'latency': {
                'deterministic_p95_ms': self.metrics.get_latency_percentile(
                    MetricNames.DETERMINISTIC_LATENCY, 95
                ),
                'ai_p95_ms': self.metrics.get_latency_percentile(
                    MetricNames.AI_ENRICHMENT_LATENCY, 95
                ),
                'final_p95_ms': self.metrics.get_latency_percentile(
                    MetricNames.FINAL_LATENCY, 95
                ),
            },
            'raw_metrics': all_metrics,
        }


# Global metrics instance
_metrics_instance: Optional[MetricsTracker] = None


def get_metrics_tracker() -> MetricsTracker:
    """Get global metrics tracker instance."""
    global _metrics_instance
    
    if _metrics_instance is None:
        _metrics_instance = MetricsTracker()
    
    return _metrics_instance


def reset_metrics():
    """Reset global metrics (useful for testing)."""
    global _metrics_instance
    _metrics_instance = None
