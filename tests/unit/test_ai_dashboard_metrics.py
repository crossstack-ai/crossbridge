"""
Unit Tests for AI Dashboard Metrics Module

Tests the AI metrics tracking, aggregation, and export functionality
for dashboard visualizations and monitoring.

Test Coverage:
- AI metrics dataclasses and validation
- Confidence score distribution calculation
- Time-series aggregation (hourly, daily, weekly, monthly)
- Metrics summary generation
- Prometheus metrics export
- Grafana dashboard data formatting
- Metrics store (in-memory and persistence)
- Dashboard service API

Framework: pytest
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import json
import tempfile

from core.log_analysis.ai_dashboard_metrics import (
    AIAnalysisMetrics,
    AIMetricsSummary,
    PrometheusMetric,
    AIMetricType,
    TimeGranularity,
    calculate_confidence_distribution,
    aggregate_metrics_by_time,
    create_metrics_summary,
    export_prometheus_metrics,
    format_prometheus_text,
    create_grafana_dashboard_data
)

from services.ai_dashboard_service import (
    AIMetricsStore,
    AIDashboardService
)


class TestAIAnalysisMetrics:
    """Test AIAnalysisMetrics dataclass."""
    
    def test_create_basic_metrics(self):
        """Test creating metrics with required fields only."""
        metrics = AIAnalysisMetrics(
            run_id="run-123",
            timestamp=datetime.now(),
            framework="robot",
            total_failures=10
        )
        
        assert metrics.run_id == "run-123"
        assert metrics.framework == "robot"
        assert metrics.total_failures == 10
        assert metrics.ai_clusters_analyzed == 0
        assert metrics.tokens_used == 0
        assert metrics.cost == 0.0
    
    def test_create_full_metrics(self):
        """Test creating metrics with all fields."""
        metrics = AIAnalysisMetrics(
            run_id="run-456",
            timestamp=datetime.now(),
            framework="cypress",
            total_failures=20,
            ai_clusters_analyzed=5,
            confidence_scores=[0.85, 0.92, 0.78],
            tokens_used=1500,
            cost=0.045,
            response_time_ms=3200,
            model="gpt-4",
            provider="openai",
            error_count=1,
            cache_hits=2,
            suggestions_provided=5
        )
        
        assert metrics.ai_clusters_analyzed == 5
        assert len(metrics.confidence_scores) == 3
        assert metrics.tokens_used == 1500
        assert metrics.cost == 0.045
        assert metrics.model == "gpt-4"
        assert metrics.provider == "openai"


class TestConfidenceDistribution:
    """Test confidence score distribution calculations."""
    
    def test_distribution_empty_list(self):
        """Test distribution with empty confidence scores."""
        distribution = calculate_confidence_distribution([])
        
        assert all(count == 0 for count in distribution.values())
        assert len(distribution) == 5
    
    def test_distribution_all_ranges(self):
        """Test distribution covers all ranges."""
        scores = [0.1, 0.5, 0.7, 0.85, 0.95]
        distribution = calculate_confidence_distribution(scores)
        
        assert distribution["very_low (0.0-0.4)"] == 1
        assert distribution["low (0.4-0.6)"] == 1
        assert distribution["medium (0.6-0.8)"] == 1
        assert distribution["high (0.8-0.9)"] == 1
        assert distribution["very_high (0.9-1.0)"] == 1
    
    def test_distribution_boundary_values(self):
        """Test distribution with boundary values."""
        scores = [0.0, 0.4, 0.6, 0.8, 0.9, 1.0]
        distribution = calculate_confidence_distribution(scores)
        
        # Boundary values should fall into lower bucket
        assert distribution["very_low (0.0-0.4)"] == 1  # 0.0
        assert distribution["low (0.4-0.6)"] == 1  # 0.4
        assert distribution["medium (0.6-0.8)"] == 1  # 0.6
        assert distribution["high (0.8-0.9)"] == 1  # 0.8
        assert distribution["very_high (0.9-1.0)"] == 2  # 0.9, 1.0
    
    def test_distribution_multiple_scores(self):
        """Test distribution with multiple scores in same range."""
        scores = [0.91, 0.92, 0.93, 0.94, 0.95]
        distribution = calculate_confidence_distribution(scores)
        
        assert distribution["very_high (0.9-1.0)"] == 5
        assert sum(v for k, v in distribution.items() if k != "very_high (0.9-1.0)") == 0


class TestTimeAggregation:
    """Test time-series aggregation."""
    
    def test_aggregate_by_day(self):
        """Test daily aggregation."""
        now = datetime.now()
        metrics_list = [
            AIAnalysisMetrics(
                run_id=f"run-{i}",
                timestamp=now - timedelta(days=i),
                framework="robot",
                total_failures=10,
                ai_clusters_analyzed=5,
                confidence_scores=[0.85],
                tokens_used=1000,
                cost=0.03
            )
            for i in range(3)
        ]
        
        aggregated = aggregate_metrics_by_time(metrics_list, TimeGranularity.DAY)
        
        assert len(aggregated) == 3
        assert all("timestamp" in day for day in aggregated)
        assert all("total_analyses" in day for day in aggregated)
        assert aggregated[0]["total_analyses"] == 1
    
    def test_aggregate_by_hour(self):
        """Test hourly aggregation."""
        now = datetime.now()
        metrics_list = [
            AIAnalysisMetrics(
                run_id=f"run-{i}",
                timestamp=now - timedelta(hours=i),
                framework="robot",
                total_failures=10,
                ai_clusters_analyzed=3,
                confidence_scores=[0.75]
            )
            for i in range(5)
        ]
        
        aggregated = aggregate_metrics_by_time(metrics_list, TimeGranularity.HOUR)
        
        assert len(aggregated) == 5
    
    def test_aggregate_empty_list(self):
        """Test aggregation with empty metrics list."""
        aggregated = aggregate_metrics_by_time([], TimeGranularity.DAY)
        
        assert aggregated == []
    
    def test_aggregate_by_week(self):
        """Test weekly aggregation."""
        now = datetime.now()
        metrics_list = [
            AIAnalysisMetrics(
                run_id=f"run-{i}",
                timestamp=now - timedelta(days=i*7),  # Different weeks
                framework="robot",
                total_failures=10,
                confidence_scores=[0.8]
            )
            for i in range(3)
        ]
        
        aggregated = aggregate_metrics_by_time(metrics_list, TimeGranularity.WEEK)
        
        assert len(aggregated) == 3
    
    def test_aggregate_by_month(self):
        """Test monthly aggregation."""
        now = datetime.now()
        metrics_list = [
            AIAnalysisMetrics(
                run_id=f"run-{i}",
                timestamp=now - timedelta(days=i*3) - timedelta(days=15*i),
                framework="robot",
                total_failures=10,
                confidence_scores=[0.8]
            )
            for i in range(12)
        ]
        
        aggregated = aggregate_metrics_by_time(metrics_list, TimeGranularity.MONTH)
        
        assert len(aggregated) >= 1
        # Should group by month


class TestMetricsSummary:
    """Test metrics summary generation."""
    
    def test_create_summary_empty_list(self):
        """Test summary with no metrics."""
        summary = create_metrics_summary([], "test_period")
        
        assert summary.total_analyses == 0
        assert summary.avg_confidence_score == 0.0
        assert summary.time_period == "test_period"
    
    def test_create_summary_single_metric(self):
        """Test summary with single metric."""
        metrics_list = [
            AIAnalysisMetrics(
                run_id="run-1",
                timestamp=datetime.now(),
                framework="robot",
                total_failures=10,
                ai_clusters_analyzed=5,
                confidence_scores=[0.85, 0.92],
                tokens_used=1500,
                cost=0.045,
                response_time_ms=3000
            )
        ]
        
        summary = create_metrics_summary(metrics_list, "last_24h")
        
        assert summary.total_analyses == 1
        assert summary.total_clusters_analyzed == 5
        assert summary.avg_confidence_score == pytest.approx(0.885, rel=0.01)
        assert summary.total_tokens == 1500
        assert summary.total_cost == 0.045
        assert summary.avg_response_time_ms == 3000
    
    def test_create_summary_multiple_metrics(self):
        """Test summary with multiple metrics."""
        now = datetime.now()
        metrics_list = [
            AIAnalysisMetrics(
                run_id=f"run-{i}",
                timestamp=now - timedelta(hours=i),
                framework="robot",
                total_failures=10,
                ai_clusters_analyzed=5,
                confidence_scores=[0.8 + i*0.05],
                tokens_used=1000,
                cost=0.03,
                response_time_ms=2000,
                model="gpt-4",
                provider="openai"
            )
            for i in range(3)
        ]
        
        summary = create_metrics_summary(metrics_list, "last_24h")
        
        assert summary.total_analyses == 3
        assert summary.total_clusters_analyzed == 15
        assert summary.total_tokens == 3000
        assert summary.total_cost == pytest.approx(0.09, rel=0.01)
        assert len(summary.top_models) >= 1
        assert summary.top_models[0]["model"] == "gpt-4"
    
    def test_summary_includes_distribution(self):
        """Test summary includes confidence distribution."""
        metrics_list = [
            AIAnalysisMetrics(
                run_id="run-1",
                timestamp=datetime.now(),
                framework="robot",
                total_failures=10,
                confidence_scores=[0.2, 0.5, 0.7, 0.85, 0.95]
            )
        ]
        
        summary = create_metrics_summary(metrics_list)
        
        assert "confidence_score_distribution" in dict(summary.__dict__)
        assert summary.confidence_score_distribution["very_low (0.0-0.4)"] == 1
        assert summary.confidence_score_distribution["very_high (0.9-1.0)"] == 1
    
    def test_summary_error_rate_calculation(self):
        """Test error rate calculation in summary."""
        metrics_list = [
            AIAnalysisMetrics(
                run_id="run-1",
                timestamp=datetime.now(),
                framework="robot",
                total_failures=10,
                ai_clusters_analyzed=10,
                error_count=2  # 2 errors out of 10 requests
            ),
            AIAnalysisMetrics(
                run_id="run-2",
                timestamp=datetime.now(),
                framework="robot",
                total_failures=10,
                ai_clusters_analyzed=10,
                error_count=0  # 0 errors out of 10 requests
            )
        ]
        
        summary = create_metrics_summary(metrics_list)
        
        # Error rate should be 2/(10+10+2+0) = 2/22 = 0.091 (9.1%)
        # (total errors / total requests where requests = ai_clusters_analyzed + error_count)
        assert summary.error_rate == pytest.approx(0.091, rel=0.02)


class TestPrometheusExport:
    """Test Prometheus metrics export."""
    
    def test_export_basic_metrics(self):
        """Test exporting basic Prometheus metrics."""
        metrics = AIAnalysisMetrics(
            run_id="run-1",
            timestamp=datetime.now(),
            framework="robot",
            total_failures=10,
            ai_clusters_analyzed=5,
            confidence_scores=[0.85],
            tokens_used=1500,
            cost=0.045,
            model="gpt-4",
            provider="openai"
        )
        
        prom_metrics = export_prometheus_metrics(metrics)
        
        assert len(prom_metrics) >= 5
        metric_names = [m.name for m in prom_metrics]
        assert "crossbridge_ai_confidence_score" in metric_names
        assert "crossbridge_ai_tokens_used_total" in metric_names
        assert "crossbridge_ai_cost_usd_total" in metric_names
    
    def test_prometheus_metric_labels(self):
        """Test Prometheus metrics include correct labels."""
        metrics = AIAnalysisMetrics(
            run_id="run-1",
            timestamp=datetime.now(),
            framework="cypress",
            total_failures=10,
            confidence_scores=[0.9],
            model="claude-3-sonnet",
            provider="anthropic"
        )
        
        prom_metrics = export_prometheus_metrics(metrics)
        
        for metric in prom_metrics:
            assert "framework" in metric.labels
            assert metric.labels["framework"] == "cypress"
            assert "model" in metric.labels
            assert metric.labels["model"] == "claude-3-sonnet"
    
    def test_format_prometheus_text(self):
        """Test formatting Prometheus metrics as text."""
        prom_metric = PrometheusMetric(
            name="test_metric",
            metric_type="gauge",
            value=42.5,
            labels={"framework": "robot", "model": "gpt-4"},
            help_text="Test metric for validation"
        )
        
        text = format_prometheus_text([prom_metric])
        
        assert "# HELP test_metric Test metric for validation" in text
        assert "# TYPE test_metric gauge" in text
        assert 'test_metric{framework="robot",model="gpt-4"} 42.5' in text
    
    def test_format_prometheus_multiple_metrics(self):
        """Test formatting multiple Prometheus metrics."""
        metrics = [
            PrometheusMetric(
                name="metric_a",
                metric_type="counter",
                value=100,
                help_text="First metric"
            ),
            PrometheusMetric(
                name="metric_b",
                metric_type="gauge",
                value=50,
                help_text="Second metric"
            )
        ]
        
        text = format_prometheus_text(metrics)
        
        assert "# HELP metric_a" in text
        assert "# HELP metric_b" in text
        assert "metric_a" in text
        assert "metric_b" in text


class TestGrafanaDataFormat:
    """Test Grafana dashboard data formatting."""
    
    def test_create_grafana_data_basic(self):
        """Test creating basic Grafana dashboard data."""
        summary = AIMetricsSummary(
            time_period="last_24h",
            total_analyses=10,
            total_clusters_analyzed=50,
            avg_confidence_score=0.85,
            total_cost=0.5,
            error_rate=0.05
        )
        
        grafana_data = create_grafana_dashboard_data(summary)
        
        assert "single_stats" in grafana_data
        assert "time_series" in grafana_data
        assert "pie_chart" in grafana_data
        assert "table" in grafana_data
    
    def test_grafana_single_stats(self):
        """Test Grafana single stat panels."""
        summary = AIMetricsSummary(
            time_period="last_24h",
            total_analyses=10,
            total_clusters_analyzed=50,
            avg_confidence_score=0.85,
            total_cost=1.25,
            error_rate=0.05
        )
        
        grafana_data = create_grafana_dashboard_data(summary)
        single_stats = grafana_data["single_stats"]
        
        assert "total_analyses" in single_stats
        assert single_stats["total_analyses"]["value"] == 10
        assert "avg_confidence" in single_stats
        assert single_stats["avg_confidence"]["value"] == 0.85
        assert "total_cost" in single_stats
        assert single_stats["total_cost"]["value"] == 1.25
    
    def test_grafana_thresholds(self):
        """Test Grafana includes thresholds for alerting."""
        summary = AIMetricsSummary(
            time_period="last_24h",
            total_analyses=10,
            total_clusters_analyzed=50,
            avg_confidence_score=0.85,
            error_rate=0.15  # 15% error rate
        )
        
        grafana_data = create_grafana_dashboard_data(summary)
        error_stat = grafana_data["single_stats"]["error_rate"]
        
        assert "thresholds" in error_stat
        assert "green" in error_stat["thresholds"]
        assert "yellow" in error_stat["thresholds"]
        assert "red" in error_stat["thresholds"]


class TestMetricsStore:
    """Test AI metrics store (in-memory and persistence)."""
    
    def test_store_initialization(self):
        """Test metrics store initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            store = AIMetricsStore(storage_path)
            
            assert len(store.metrics) == 0
            assert store.storage_path == storage_path
    
    def test_add_metric(self):
        """Test adding metric to store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            store = AIMetricsStore(storage_path)
            
            metric = AIAnalysisMetrics(
                run_id="run-1",
                timestamp=datetime.now(),
                framework="robot",
                total_failures=10
            )
            store.add_metric(metric)
            
            assert len(store.metrics) == 1
            assert store.metrics[0].run_id == "run-1"
    
    def test_get_recent_metrics(self):
        """Test retrieving recent metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            store = AIMetricsStore(storage_path)
            
            now = datetime.now()
            # Add recent metric
            store.add_metric(AIAnalysisMetrics(
                run_id="run-recent",
                timestamp=now - timedelta(hours=1),
                framework="robot",
                total_failures=10
            ))
            
            # Add old metric
            store.add_metric(AIAnalysisMetrics(
                run_id="run-old",
                timestamp=now - timedelta(hours=48),
                framework="robot",
                total_failures=10
            ))
            
            recent = store.get_recent_metrics(hours=24)
            
            assert len(recent) == 1
            assert recent[0].run_id == "run-recent"
    
    def test_get_metrics_by_framework(self):
        """Test filtering metrics by framework."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            store = AIMetricsStore(storage_path)
            
            store.add_metric(AIAnalysisMetrics(
                run_id="run-1",
                timestamp=datetime.now(),
                framework="robot",
                total_failures=10
            ))
            
            store.add_metric(AIAnalysisMetrics(
                run_id="run-2",
                timestamp=datetime.now(),
                framework="cypress",
                total_failures=5
            ))
            
            robot_metrics = store.get_metrics_by_framework("robot")
            
            assert len(robot_metrics) == 1
            assert robot_metrics[0].framework == "robot"
    
    def test_persistence(self):
        """Test metrics persistence to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            
            # Create store and add metric
            store1 = AIMetricsStore(storage_path)
            metric = AIAnalysisMetrics(
                run_id="run-1",
                timestamp=datetime.now(),
                framework="robot",
                total_failures=10,
                confidence_scores=[0.85]
            )
            store1.add_metric(metric)
            
            # Create new store instance - should load from disk
            store2 = AIMetricsStore(storage_path)
            
            assert len(store2.metrics) == 1
            assert store2.metrics[0].run_id == "run-1"
    
    def test_clear_old_metrics(self):
        """Test clearing old metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            store = AIMetricsStore(storage_path)
            
            now = datetime.now()
            # Add recent metric
            store.add_metric(AIAnalysisMetrics(
                run_id="run-recent",
                timestamp=now,
                framework="robot",
                total_failures=10
            ))
            
            # Add old metric
            store.add_metric(AIAnalysisMetrics(
                run_id="run-old",
                timestamp=now - timedelta(days=40),
                framework="robot",
                total_failures=10
            ))
            
            removed = store.clear_old_metrics(days=30)
            
            assert removed == 1
            assert len(store.metrics) == 1
            assert store.metrics[0].run_id == "run-recent"


class TestDashboardService:
    """Test AI Dashboard Service."""
    
    def test_service_initialization(self):
        """Test dashboard service initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            service = AIDashboardService(storage_path)
            
            assert service.store is not None
    
    def test_record_analysis(self):
        """Test recording AI analysis metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            service = AIDashboardService(storage_path)
            
            service.record_analysis(
                run_id="test-run",
                framework="robot",
                total_failures=10,
                ai_clusters_analyzed=5,
                confidence_scores=[0.85, 0.92],
                tokens_used=1500,
                cost=0.045,
                model="gpt-4"
            )
            
            assert len(service.store.metrics) == 1
            assert service.store.metrics[0].run_id == "test-run"
    
    def test_get_summary(self):
        """Test getting metrics summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            service = AIDashboardService(storage_path)
            
            service.record_analysis(
                run_id="test-run",
                framework="robot",
                total_failures=10,
                ai_clusters_analyzed=5,
                confidence_scores=[0.85]
            )
            
            summary = service.get_summary(hours=24)
            
            assert summary["total_analyses"] == 1
            assert summary["total_clusters_analyzed"] == 5
    
    def test_get_summary_no_metrics(self):
        """Test getting summary with no metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            service = AIDashboardService(storage_path)
            
            summary = service.get_summary(hours=24)
            
            assert summary["total_analyses"] == 0
            assert "message" in summary
    
    def test_get_prometheus_metrics(self):
        """Test getting Prometheus-formatted metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            service = AIDashboardService(storage_path)
            
            service.record_analysis(
                run_id="test-run",
                framework="robot",
                total_failures=10,
                confidence_scores=[0.85],
                tokens_used=1000
            )
            
            prom_text = service.get_prometheus_metrics()
            
            assert isinstance(prom_text, str)
            assert "crossbridge_ai" in prom_text or prom_text.startswith("#")
    
    def test_get_grafana_data(self):
        """Test getting Grafana dashboard data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            service = AIDashboardService(storage_path)
            
            service.record_analysis(
                run_id="test-run",
                framework="robot",
                total_failures=10,
                ai_clusters_analyzed=5,
                confidence_scores=[0.85]
            )
            
            grafana_data = service.get_grafana_data(hours=168)
            
            assert isinstance(grafana_data, dict)
            # Should have data or message
            assert len(grafana_data) > 0
    
    def test_get_framework_metrics(self):
        """Test getting framework-specific metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "metrics.json"
            service = AIDashboardService(storage_path)
            
            service.record_analysis(
                run_id="run-1",
                framework="robot",
                total_failures=10
            )
            
            service.record_analysis(
                run_id="run-2",
                framework="cypress",
                total_failures=5
            )
            
            robot_metrics = service.get_framework_metrics("robot", hours=24)
            
            assert robot_metrics["framework"] == "robot"
            assert robot_metrics["total_analyses"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
