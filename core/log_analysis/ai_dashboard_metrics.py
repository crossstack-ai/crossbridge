"""
AI Dashboard Metrics Module

Provides dashboard-friendly metrics and visualizations for AI-enhanced analysis.
Tracks AI performance, costs, confidence scores, and quality metrics over time.

Features:
- AI confidence score trends and distributions
- Token usage and cost tracking per analysis
- AI response time and performance metrics
- Quality metrics (acceptance rate, feedback scores)
- Time-series aggregation for Grafana/Prometheus
- Dashboard query helpers for common visualizations

Integrates with:
- core.log_analysis.regression (confidence scoring)
- core.log_analysis.clustering (failure analysis)
- persistence layer (ai_transformation, ai_confidence_feedback tables)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

from core.logging import get_logger, LogCategory

# Get logger with EXECUTION category for dashboard metrics
logger = get_logger(__name__, category=LogCategory.EXECUTION)


class AIMetricType(str, Enum):
    """Types of AI metrics for dashboard tracking."""
    CONFIDENCE_SCORE = "confidence_score"
    TOKEN_USAGE = "token_usage"
    COST = "cost"
    RESPONSE_TIME = "response_time"
    ACCEPTANCE_RATE = "acceptance_rate"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"


class TimeGranularity(str, Enum):
    """Time granularity for aggregation."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class AIAnalysisMetrics:
    """
    Metrics for a single AI analysis run.
    
    Attributes:
        run_id: Unique identifier for the analysis run
        timestamp: When the analysis was performed
        framework: Test framework analyzed
        total_failures: Total failures analyzed
        ai_clusters_analyzed: Number of clusters that received AI analysis
        confidence_scores: List of confidence scores for AI-analyzed clusters
        tokens_used: Total tokens consumed (input + output)
        cost: Estimated cost in USD
        response_time_ms: Total AI response time in milliseconds
        model: AI model used (e.g., "gpt-4", "claude-3-sonnet")
        provider: AI provider (openai, anthropic, ollama, etc.)
        error_count: Number of errors encountered
        cache_hits: Number of cache hits (if caching enabled)
        suggestions_provided: Number of fix suggestions generated
    """
    run_id: str
    timestamp: datetime
    framework: str
    total_failures: int
    ai_clusters_analyzed: int = 0
    confidence_scores: List[float] = field(default_factory=list)
    tokens_used: int = 0
    cost: float = 0.0
    response_time_ms: int = 0
    model: Optional[str] = None
    provider: Optional[str] = None
    error_count: int = 0
    cache_hits: int = 0
    suggestions_provided: int = 0


@dataclass
class AIMetricsSummary:
    """
    Aggregated AI metrics summary for dashboard display.
    
    Attributes:
        time_period: Time period covered (e.g., "last_24h", "last_7d")
        total_analyses: Total number of AI analyses performed
        total_clusters_analyzed: Total clusters analyzed with AI
        avg_confidence_score: Average confidence score across all analyses
        confidence_score_distribution: Distribution buckets (0-0.2, 0.2-0.4, etc.)
        total_tokens: Total tokens consumed
        total_cost: Total cost in USD
        avg_response_time_ms: Average AI response time
        error_rate: Percentage of failed AI requests
        cache_hit_rate: Percentage of cache hits
        top_models: Most frequently used AI models
        cost_by_model: Cost breakdown by AI model
        daily_trend: Daily metrics for trend visualization
    """
    time_period: str
    total_analyses: int
    total_clusters_analyzed: int
    avg_confidence_score: float
    confidence_score_distribution: Dict[str, int] = field(default_factory=dict)
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_response_time_ms: float = 0.0
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0
    top_models: List[Dict[str, Any]] = field(default_factory=list)
    cost_by_model: Dict[str, float] = field(default_factory=dict)
    daily_trend: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PrometheusMetric:
    """
    Prometheus-compatible metric for export.
    
    Attributes:
        name: Metric name (e.g., "crossbridge_ai_confidence_score")
        metric_type: Metric type (counter, gauge, histogram, summary)
        value: Current metric value
        labels: Key-value labels for the metric
        help_text: Description of the metric
        timestamp: Unix timestamp in milliseconds
    """
    name: str
    metric_type: str  # counter, gauge, histogram, summary
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    help_text: str = ""
    timestamp: Optional[int] = None


def calculate_confidence_distribution(confidence_scores: List[float]) -> Dict[str, int]:
    """
    Calculate confidence score distribution for visualization.
    
    Groups scores into buckets: Very Low (0-0.4), Low (0.4-0.6), 
    Medium (0.6-0.8), High (0.8-0.9), Very High (0.9-1.0)
    
    Args:
        confidence_scores: List of confidence scores (0.0 - 1.0)
        
    Returns:
        Dictionary with bucket names and counts
    """
    distribution = {
        "very_low (0.0-0.4)": 0,
        "low (0.4-0.6)": 0,
        "medium (0.6-0.8)": 0,
        "high (0.8-0.9)": 0,
        "very_high (0.9-1.0)": 0
    }
    
    for score in confidence_scores:
        if score < 0.4:
            distribution["very_low (0.0-0.4)"] += 1
        elif score < 0.6:
            distribution["low (0.4-0.6)"] += 1
        elif score < 0.8:
            distribution["medium (0.6-0.8)"] += 1
        elif score < 0.9:
            distribution["high (0.8-0.9)"] += 1
        else:
            distribution["very_high (0.9-1.0)"] += 1
    
    return distribution


def aggregate_metrics_by_time(
    metrics_list: List[AIAnalysisMetrics],
    granularity: TimeGranularity = TimeGranularity.DAY
) -> List[Dict[str, Any]]:
    """
    Aggregate AI metrics by time period for trend visualization.
    
    Groups metrics into time buckets and aggregates key metrics:
    - Total analyses per period
    - Average confidence score
    - Total tokens and cost
    - Average response time
    - Error rate
    
    Args:
        metrics_list: List of AI analysis metrics
        granularity: Time granularity (HOUR, DAY, WEEK, MONTH)
        
    Returns:
        List of dictionaries with aggregated metrics per time period
    """
    if not metrics_list:
        return []
    
    # Group by time period
    time_buckets = defaultdict(list)
    
    for metric in metrics_list:
        # Round timestamp to granularity
        if granularity == TimeGranularity.HOUR:
            bucket_key = metric.timestamp.replace(minute=0, second=0, microsecond=0)
        elif granularity == TimeGranularity.DAY:
            bucket_key = metric.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        elif granularity == TimeGranularity.WEEK:
            # Round to start of week (Monday)
            days_since_monday = metric.timestamp.weekday()
            bucket_key = (metric.timestamp - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:  # MONTH
            bucket_key = metric.timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        time_buckets[bucket_key].append(metric)
    
    # Aggregate within each bucket
    aggregated = []
    for timestamp, bucket_metrics in sorted(time_buckets.items()):
        total_analyses = len(bucket_metrics)
        total_clusters = sum(m.ai_clusters_analyzed for m in bucket_metrics)
        all_confidence_scores = [score for m in bucket_metrics for score in m.confidence_scores]
        avg_confidence = sum(all_confidence_scores) / len(all_confidence_scores) if all_confidence_scores else 0.0
        total_tokens = sum(m.tokens_used for m in bucket_metrics)
        total_cost = sum(m.cost for m in bucket_metrics)
        total_response_time = sum(m.response_time_ms for m in bucket_metrics)
        avg_response_time = total_response_time / total_analyses if total_analyses > 0 else 0
        total_errors = sum(m.error_count for m in bucket_metrics)
        error_rate = (total_errors / total_analyses) if total_analyses > 0 else 0.0
        
        aggregated.append({
            "timestamp": timestamp.isoformat(),
            "total_analyses": total_analyses,
            "total_clusters_analyzed": total_clusters,
            "avg_confidence_score": round(avg_confidence, 3),
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "avg_response_time_ms": round(avg_response_time, 0),
            "error_rate": round(error_rate, 3)
        })
    
    return aggregated


def create_metrics_summary(
    metrics_list: List[AIAnalysisMetrics],
    time_period_label: str = "last_7d"
) -> AIMetricsSummary:
    """
    Create comprehensive metrics summary for dashboard display.
    
    Aggregates all metrics into a single summary object with:
    - Overall statistics
    - Distribution analysis
    - Model-specific breakdowns
    - Time-series trends
    
    Args:
        metrics_list: List of AI analysis metrics
        time_period_label: Human-readable time period label
        
    Returns:
        AIMetricsSummary with aggregated dashboard metrics
    """
    if not metrics_list:
        return AIMetricsSummary(
            time_period=time_period_label,
            total_analyses=0,
            total_clusters_analyzed=0,
            avg_confidence_score=0.0
        )
    
    # Overall statistics
    total_analyses = len(metrics_list)
    total_clusters = sum(m.ai_clusters_analyzed for m in metrics_list)
    all_confidence_scores = [score for m in metrics_list for score in m.confidence_scores]
    avg_confidence = sum(all_confidence_scores) / len(all_confidence_scores) if all_confidence_scores else 0.0
    
    # Token and cost aggregation
    total_tokens = sum(m.tokens_used for m in metrics_list)
    total_cost = sum(m.cost for m in metrics_list)
    
    # Response time
    total_response_time = sum(m.response_time_ms for m in metrics_list)
    avg_response_time = total_response_time / total_analyses if total_analyses > 0 else 0.0
    
    # Error rate
    total_errors = sum(m.error_count for m in metrics_list)
    total_requests = sum(m.ai_clusters_analyzed + m.error_count for m in metrics_list)
    error_rate = (total_errors / total_requests) if total_requests > 0 else 0.0
    
    # Cache hit rate
    total_cache_hits = sum(m.cache_hits for m in metrics_list)
    cache_hit_rate = (total_cache_hits / total_requests) if total_requests > 0 else 0.0
    
    # Confidence distribution
    distribution = calculate_confidence_distribution(all_confidence_scores)
    
    # Model usage breakdown
    model_usage = defaultdict(int)
    cost_by_model = defaultdict(float)
    for metric in metrics_list:
        if metric.model:
            model_usage[metric.model] += 1
            cost_by_model[metric.model] += metric.cost
    
    top_models = [
        {"model": model, "usage_count": count, "percentage": round((count / total_analyses) * 100, 1)}
        for model, count in sorted(model_usage.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    # Daily trend (last 7 days by default)
    daily_trend = aggregate_metrics_by_time(metrics_list, TimeGranularity.DAY)
    
    return AIMetricsSummary(
        time_period=time_period_label,
        total_analyses=total_analyses,
        total_clusters_analyzed=total_clusters,
        avg_confidence_score=round(avg_confidence, 3),
        confidence_score_distribution=distribution,
        total_tokens=total_tokens,
        total_cost=round(total_cost, 4),
        avg_response_time_ms=round(avg_response_time, 0),
        error_rate=round(error_rate, 3),
        cache_hit_rate=round(cache_hit_rate, 3),
        top_models=top_models,
        cost_by_model=dict(cost_by_model),
        daily_trend=daily_trend[-7:]  # Last 7 days
    )


def export_prometheus_metrics(metrics: AIAnalysisMetrics) -> List[PrometheusMetric]:
    """
    Export AI metrics in Prometheus format for monitoring.
    
    Converts AI analysis metrics into Prometheus-compatible metrics
    that can be scraped by Prometheus and visualized in Grafana.
    
    Metrics exported:
    - crossbridge_ai_confidence_score (gauge)
    - crossbridge_ai_tokens_used (counter)
    - crossbridge_ai_cost_usd (counter)
    - crossbridge_ai_response_time_ms (histogram)
    - crossbridge_ai_errors_total (counter)
    - crossbridge_ai_cache_hits_total (counter)
    
    Args:
        metrics: AI analysis metrics to export
        
    Returns:
        List of Prometheus-compatible metrics
    """
    prom_metrics = []
    labels = {
        "framework": metrics.framework,
        "model": metrics.model or "unknown",
        "provider": metrics.provider or "unknown"
    }
    
    # Confidence score (gauge - latest value)
    if metrics.confidence_scores:
        avg_confidence = sum(metrics.confidence_scores) / len(metrics.confidence_scores)
        prom_metrics.append(PrometheusMetric(
            name="crossbridge_ai_confidence_score",
            metric_type="gauge",
            value=avg_confidence,
            labels=labels,
            help_text="Average AI confidence score for analysis",
            timestamp=int(metrics.timestamp.timestamp() * 1000)
        ))
    
    # Tokens used (counter - cumulative)
    prom_metrics.append(PrometheusMetric(
        name="crossbridge_ai_tokens_used_total",
        metric_type="counter",
        value=float(metrics.tokens_used),
        labels=labels,
        help_text="Total tokens consumed by AI analysis",
        timestamp=int(metrics.timestamp.timestamp() * 1000)
    ))
    
    # Cost (counter - cumulative)
    prom_metrics.append(PrometheusMetric(
        name="crossbridge_ai_cost_usd_total",
        metric_type="counter",
        value=metrics.cost,
        labels=labels,
        help_text="Total cost in USD for AI analysis",
        timestamp=int(metrics.timestamp.timestamp() * 1000)
    ))
    
    # Response time (gauge - latest measurement)
    prom_metrics.append(PrometheusMetric(
        name="crossbridge_ai_response_time_ms",
        metric_type="gauge",
        value=float(metrics.response_time_ms),
        labels=labels,
        help_text="AI response time in milliseconds",
        timestamp=int(metrics.timestamp.timestamp() * 1000)
    ))
    
    # Errors (counter - cumulative)
    prom_metrics.append(PrometheusMetric(
        name="crossbridge_ai_errors_total",
        metric_type="counter",
        value=float(metrics.error_count),
        labels=labels,
        help_text="Total number of AI errors",
        timestamp=int(metrics.timestamp.timestamp() * 1000)
    ))
    
    # Cache hits (counter - cumulative)
    prom_metrics.append(PrometheusMetric(
        name="crossbridge_ai_cache_hits_total",
        metric_type="counter",
        value=float(metrics.cache_hits),
        labels=labels,
        help_text="Total number of AI cache hits",
        timestamp=int(metrics.timestamp.timestamp() * 1000)
    ))
    
    # Clusters analyzed (counter - cumulative)
    prom_metrics.append(PrometheusMetric(
        name="crossbridge_ai_clusters_analyzed_total",
        metric_type="counter",
        value=float(metrics.ai_clusters_analyzed),
        labels=labels,
        help_text="Total number of failure clusters analyzed with AI",
        timestamp=int(metrics.timestamp.timestamp() * 1000)
    ))
    
    logger.debug(f"Exported {len(prom_metrics)} Prometheus metrics for run {metrics.run_id}")
    return prom_metrics


def format_prometheus_text(metrics: List[PrometheusMetric]) -> str:
    """
    Format Prometheus metrics as text for /metrics endpoint.
    
    Converts PrometheusMetric objects into the Prometheus text exposition format
    that can be scraped by Prometheus.
    
    Format:
    ```
    # HELP metric_name Description
    # TYPE metric_name metric_type
    metric_name{label1="value1",label2="value2"} value timestamp
    ```
    
    Args:
        metrics: List of Prometheus metrics to format
        
    Returns:
        Formatted Prometheus text output
    """
    lines = []
    
    # Group by metric name to consolidate HELP and TYPE
    metrics_by_name = defaultdict(list)
    for metric in metrics:
        metrics_by_name[metric.name].append(metric)
    
    for name, metric_list in sorted(metrics_by_name.items()):
        # Write HELP and TYPE once per metric name
        if metric_list[0].help_text:
            lines.append(f"# HELP {name} {metric_list[0].help_text}")
        lines.append(f"# TYPE {name} {metric_list[0].metric_type}")
        
        # Write all samples for this metric
        for metric in metric_list:
            labels_str = ",".join([f'{k}="{v}"' for k, v in sorted(metric.labels.items())])
            if labels_str:
                labels_str = f"{{{labels_str}}}"
            
            timestamp_str = f" {metric.timestamp}" if metric.timestamp else ""
            lines.append(f"{name}{labels_str} {metric.value}{timestamp_str}")
        
        lines.append("")  # Blank line between metrics
    
    return "\n".join(lines)


def create_grafana_dashboard_data(summary: AIMetricsSummary) -> Dict[str, Any]:
    """
    Create Grafana-compatible dashboard data structure.
    
    Transforms AI metrics summary into a format optimized for Grafana panels:
    - Time series data for graph panels
    - Single stat data for stat panels
    - Table data for table panels
    - Pie chart data for distribution panels
    
    Args:
        summary: AI metrics summary
        
    Returns:
        Dictionary with Grafana-compatible data structures
    """
    grafana_data = {
        "single_stats": {
            "total_analyses": {
                "value": summary.total_analyses,
                "unit": "analyses",
                "description": "Total AI Analyses"
            },
            "avg_confidence": {
                "value": summary.avg_confidence_score,
                "unit": "percent",
                "description": "Avg Confidence Score",
                "decimals": 2,
                "thresholds": {
                    "green": 0.8,
                    "yellow": 0.6,
                    "red": 0.4
                }
            },
            "total_cost": {
                "value": summary.total_cost,
                "unit": "USD",
                "description": "Total AI Cost",
                "decimals": 2
            },
            "error_rate": {
                "value": summary.error_rate * 100,  # Convert to percentage
                "unit": "percent",
                "description": "Error Rate",
                "decimals": 1,
                "thresholds": {
                    "green": 5,
                    "yellow": 10,
                    "red": 20
                }
            }
        },
        "time_series": {
            "confidence_trend": [
                {"time": day["timestamp"], "value": day["avg_confidence_score"]}
                for day in summary.daily_trend
            ],
            "cost_trend": [
                {"time": day["timestamp"], "value": day["total_cost"]}
                for day in summary.daily_trend
            ],
            "analyses_trend": [
                {"time": day["timestamp"], "value": day["total_analyses"]}
                for day in summary.daily_trend
            ]
        },
        "pie_chart": {
            "confidence_distribution": [
                {"label": k, "value": v}
                for k, v in summary.confidence_score_distribution.items()
            ]
        },
        "table": {
            "model_usage": summary.top_models,
            "cost_by_model": [
                {"model": k, "cost": v}
                for k, v in sorted(summary.cost_by_model.items(), key=lambda x: x[1], reverse=True)
            ]
        }
    }
    
    logger.info(f"Created Grafana dashboard data for {summary.time_period}")
    return grafana_data
