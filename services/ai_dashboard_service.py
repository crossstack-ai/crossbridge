"""
AI Dashboard Service

Provides REST API endpoints for AI metrics and dashboard data.
Exposes Prometheus-compatible metrics and Grafana-friendly data structures.

Endpoints:
- GET /ai-metrics/summary - AI metrics summary for dashboard display
- GET /ai-metrics/prometheus - Prometheus-compatible metrics endpoint
- GET /ai-metrics/grafana - Grafana-optimized dashboard data
- GET /ai-metrics/trends - Time-series trend data
- POST /ai-metrics/record - Record new AI analysis metrics

Integrates with:
- core.log_analysis.ai_dashboard_metrics (metrics computation)
- persistence layer (metrics storage)
- services.sidecar_api (REST API integration)
"""

import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from core.logging import get_logger, LogCategory
from core.log_analysis.ai_dashboard_metrics import (
    AIAnalysisMetrics,
    AIMetricsSummary,
    PrometheusMetric,
    TimeGranularity,
    create_metrics_summary,
    export_prometheus_metrics,
    format_prometheus_text,
    create_grafana_dashboard_data,
    aggregate_metrics_by_time
)

# Get logger with ORCHESTRATION category for service layer
logger = get_logger(__name__, category=LogCategory.ORCHESTRATION)


class AIMetricsStore:
    """
    In-memory store for AI metrics with file-based persistence.
    
    Provides fast access to recent metrics while persisting to disk
    for long-term storage and analysis.
    
    Attributes:
        storage_path: Path to persist metrics as JSON
        metrics: In-memory list of AI analysis metrics
        max_memory_items: Maximum items to keep in memory (oldest evicted)
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize metrics store.
        
        Args:
            storage_path: Path for persistent storage (default: ./data/ai_metrics.json)
        """
        self.storage_path = storage_path or Path("data/ai_metrics.json")
        self.metrics: List[AIAnalysisMetrics] = []
        self.max_memory_items = 1000  # Keep last 1000 analyses in memory
        
        # Create storage directory if needed
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing metrics from file
        self._load_from_disk()
        logger.info(f"AI metrics store initialized with {len(self.metrics)} metrics")
    
    def add_metric(self, metric: AIAnalysisMetrics) -> None:
        """Add new metric to store and persist to disk."""
        self.metrics.append(metric)
        
        # Evict old metrics if exceeding memory limit
        if len(self.metrics) > self.max_memory_items:
            self.metrics = self.metrics[-self.max_memory_items:]
            logger.debug(f"Evicted old metrics, keeping last {self.max_memory_items}")
        
        # Persist to disk
        self._save_to_disk()
        logger.debug(f"Added metric for run {metric.run_id}")
    
    def get_recent_metrics(self, hours: int = 24) -> List[AIAnalysisMetrics]:
        """
        Get metrics from the last N hours.
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            List of metrics within the time window
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [m for m in self.metrics if m.timestamp >= cutoff]
        logger.debug(f"Retrieved {len(recent)} metrics from last {hours} hours")
        return recent
    
    def get_metrics_by_framework(self, framework: str, hours: int = 168) -> List[AIAnalysisMetrics]:
        """
        Get metrics for specific framework from the last N hours.
        
        Args:
            framework: Test framework name (robot, cypress, etc.)
            hours: Number of hours to look back (default: 168 = 1 week)
            
        Returns:
            List of metrics for the specified framework
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        framework_metrics = [
            m for m in self.metrics 
            if m.framework == framework and m.timestamp >= cutoff
        ]
        logger.debug(f"Retrieved {len(framework_metrics)} metrics for framework {framework}")
        return framework_metrics
    
    def get_all_metrics(self) -> List[AIAnalysisMetrics]:
        """Get all metrics from store."""
        return self.metrics.copy()
    
    def clear_old_metrics(self, days: int = 30) -> int:
        """
        Clear metrics older than N days.
        
        Args:
            days: Number of days to retain (default: 30)
            
        Returns:
            Number of metrics removed
        """
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self.metrics)
        self.metrics = [m for m in self.metrics if m.timestamp >= cutoff]
        removed_count = original_count - len(self.metrics)
        
        if removed_count > 0:
            self._save_to_disk()
            logger.info(f"Removed {removed_count} metrics older than {days} days")
        
        return removed_count
    
    def _load_from_disk(self) -> None:
        """Load metrics from persistent storage."""
        if not self.storage_path.exists():
            logger.debug("No existing metrics file found, starting fresh")
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                
            # Reconstruct AIAnalysisMetrics objects
            for item in data:
                # Convert timestamp string back to datetime
                item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                metric = AIAnalysisMetrics(**item)
                self.metrics.append(metric)
            
            logger.info(f"Loaded {len(self.metrics)} metrics from {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to load metrics from disk: {e}")
            # Continue with empty metrics list
    
    def _save_to_disk(self) -> None:
        """Save metrics to persistent storage."""
        try:
            # Convert metrics to JSON-serializable format
            data = []
            for metric in self.metrics[-self.max_memory_items:]:  # Only save recent metrics
                metric_dict = {
                    "run_id": metric.run_id,
                    "timestamp": metric.timestamp.isoformat(),
                    "framework": metric.framework,
                    "total_failures": metric.total_failures,
                    "ai_clusters_analyzed": metric.ai_clusters_analyzed,
                    "confidence_scores": metric.confidence_scores,
                    "tokens_used": metric.tokens_used,
                    "cost": metric.cost,
                    "response_time_ms": metric.response_time_ms,
                    "model": metric.model,
                    "provider": metric.provider,
                    "error_count": metric.error_count,
                    "cache_hits": metric.cache_hits,
                    "suggestions_provided": metric.suggestions_provided
                }
                data.append(metric_dict)
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(data)} metrics to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save metrics to disk: {e}")


class AIDashboardService:
    """
    Service for AI dashboard metrics and data export.
    
    Provides high-level operations for:
    - Recording AI analysis metrics
    - Generating dashboard summaries
    - Exporting Prometheus metrics
    - Creating Grafana-compatible data
    - Trend analysis and aggregation
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize AI dashboard service.
        
        Args:
            storage_path: Path for metrics persistence
        """
        self.store = AIMetricsStore(storage_path)
        logger.info("AI Dashboard Service initialized")
    
    def record_analysis(
        self,
        run_id: str,
        framework: str,
        total_failures: int,
        ai_clusters_analyzed: int = 0,
        confidence_scores: Optional[List[float]] = None,
        tokens_used: int = 0,
        cost: float = 0.0,
        response_time_ms: int = 0,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        error_count: int = 0,
        cache_hits: int = 0,
        suggestions_provided: int = 0
    ) -> None:
        """
        Record metrics for an AI-enhanced analysis run.
        
        Args:
            run_id: Unique identifier for the analysis run
            framework: Test framework analyzed
            total_failures: Total failures in the run
            ai_clusters_analyzed: Number of clusters analyzed with AI
            confidence_scores: List of confidence scores
            tokens_used: Total tokens consumed
            cost: Estimated cost in USD
            response_time_ms: Total AI response time
            model: AI model used
            provider: AI provider
            error_count: Number of errors
            cache_hits: Number of cache hits
            suggestions_provided: Number of fix suggestions
        """
        metric = AIAnalysisMetrics(
            run_id=run_id,
            timestamp=datetime.now(),
            framework=framework,
            total_failures=total_failures,
            ai_clusters_analyzed=ai_clusters_analyzed,
            confidence_scores=confidence_scores or [],
            tokens_used=tokens_used,
            cost=cost,
            response_time_ms=response_time_ms,
            model=model,
            provider=provider,
            error_count=error_count,
            cache_hits=cache_hits,
            suggestions_provided=suggestions_provided
        )
        self.store.add_metric(metric)
        logger.info(f"Recorded AI analysis metrics for run {run_id}")
    
    def get_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get AI metrics summary for dashboard display.
        
        Args:
            hours: Number of hours to include (default: 24)
            
        Returns:
            Dictionary with summary metrics
        """
        metrics_list = self.store.get_recent_metrics(hours)
        
        if not metrics_list:
            logger.warning(f"No metrics found for last {hours} hours")
            return {
                "time_period": f"last_{hours}h",
                "total_analyses": 0,
                "message": "No AI analyses recorded in this time period"
            }
        
        summary = create_metrics_summary(metrics_list, f"last_{hours}h")
        
        # Convert to dictionary for JSON serialization
        result = {
            "time_period": summary.time_period,
            "total_analyses": summary.total_analyses,
            "total_clusters_analyzed": summary.total_clusters_analyzed,
            "avg_confidence_score": summary.avg_confidence_score,
            "confidence_score_distribution": summary.confidence_score_distribution,
            "total_tokens": summary.total_tokens,
            "total_cost": summary.total_cost,
            "avg_response_time_ms": summary.avg_response_time_ms,
            "error_rate": summary.error_rate,
            "cache_hit_rate": summary.cache_hit_rate,
            "top_models": summary.top_models,
            "cost_by_model": summary.cost_by_model,
            "daily_trend": summary.daily_trend
        }
        
        logger.info(f"Generated summary for {hours} hours: {summary.total_analyses} analyses")
        return result
    
    def get_prometheus_metrics(self) -> str:
        """
        Get Prometheus-formatted metrics for scraping.
        
        Exports metrics from the most recent analysis run.
        
        Returns:
            Prometheus text exposition format
        """
        recent_metrics = self.store.get_recent_metrics(hours=1)
        
        if not recent_metrics:
            logger.warning("No recent metrics for Prometheus export")
            return "# No metrics available\n"
        
        # Export metrics from the most recent run
        latest_metric = recent_metrics[-1]
        prom_metrics = export_prometheus_metrics(latest_metric)
        text_output = format_prometheus_text(prom_metrics)
        
        logger.debug(f"Exported Prometheus metrics for run {latest_metric.run_id}")
        return text_output
    
    def get_grafana_data(self, hours: int = 168) -> Dict[str, Any]:
        """
        Get Grafana-optimized dashboard data.
        
        Args:
            hours: Number of hours to include (default: 168 = 1 week)
            
        Returns:
            Dictionary with Grafana-compatible data structures
        """
        metrics_list = self.store.get_recent_metrics(hours)
        
        if not metrics_list:
            logger.warning(f"No metrics found for Grafana export")
            return {"message": "No data available"}
        
        summary = create_metrics_summary(metrics_list, f"last_{hours}h")
        grafana_data = create_grafana_dashboard_data(summary)
        
        logger.info(f"Generated Grafana data for {hours} hours")
        return grafana_data
    
    def get_trends(
        self,
        granularity: str = "day",
        hours: int = 168
    ) -> List[Dict[str, Any]]:
        """
        Get time-series trend data.
        
        Args:
            granularity: Time granularity (hour, day, week, month)
            hours: Number of hours to include
            
        Returns:
            List of aggregated metrics by time period
        """
        metrics_list = self.store.get_recent_metrics(hours)
        
        if not metrics_list:
            logger.warning("No metrics found for trend analysis")
            return []
        
        # Convert string to enum
        granularity_enum = TimeGranularity[granularity.upper()]
        trends = aggregate_metrics_by_time(metrics_list, granularity_enum)
        
        logger.info(f"Generated {len(trends)} trend data points with {granularity} granularity")
        return trends
    
    def get_framework_metrics(
        self,
        framework: str,
        hours: int = 168
    ) -> Dict[str, Any]:
        """
        Get metrics for a specific test framework.
        
        Args:
            framework: Test framework name
            hours: Number of hours to include
            
        Returns:
            Framework-specific metrics summary
        """
        metrics_list = self.store.get_metrics_by_framework(framework, hours)
        
        if not metrics_list:
            return {
                "framework": framework,
                "message": f"No metrics found for {framework}"
            }
        
        summary = create_metrics_summary(metrics_list, f"last_{hours}h")
        
        result = {
            "framework": framework,
            "time_period": summary.time_period,
            "total_analyses": summary.total_analyses,
            "avg_confidence_score": summary.avg_confidence_score,
            "total_cost": summary.total_cost,
            "avg_response_time_ms": summary.avg_response_time_ms,
            "error_rate": summary.error_rate
        }
        
        logger.info(f"Generated metrics for framework {framework}: {summary.total_analyses} analyses")
        return result
    
    def cleanup_old_metrics(self, days: int = 30) -> int:
        """
        Clean up metrics older than specified days.
        
        Args:
            days: Number of days to retain
            
        Returns:
            Number of metrics removed
        """
        removed = self.store.clear_old_metrics(days)
        logger.info(f"Cleaned up {removed} old metrics (retention: {days} days)")
        return removed


# Global service instance
_dashboard_service: Optional[AIDashboardService] = None


def get_dashboard_service(storage_path: Optional[Path] = None) -> AIDashboardService:
    """
    Get or create global dashboard service instance.
    
    Args:
        storage_path: Path for metrics persistence
        
    Returns:
        AIDashboardService singleton instance
    """
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = AIDashboardService(storage_path)
    return _dashboard_service
