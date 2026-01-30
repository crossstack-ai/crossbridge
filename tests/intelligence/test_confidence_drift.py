"""
Tests for Confidence Drift Detection System.

Covers:
- Drift detection (low, moderate, high, critical)
- Direction classification (increasing, decreasing, volatile, stable)
- Trend analysis
- Category-level drift
- Alert generation
- Time window filtering
"""

import pytest
from datetime import datetime, timedelta
import statistics

from core.intelligence.confidence_drift import (
    DriftDetector,
    DriftSeverity,
    DriftDirection,
    DriftThresholds,
    DriftAlertManager,
    ConfidenceRecord,
    detect_drift_from_explanations
)


class TestConfidenceRecord:
    """Test confidence record validation."""
    
    def test_valid_confidence(self):
        """Test valid confidence range."""
        record = ConfidenceRecord(
            test_name="test_example",
            confidence=0.5,
            category="flaky",
            timestamp=datetime.utcnow()
        )
        assert record.confidence == 0.5
    
    def test_invalid_confidence_high(self):
        """Test that confidence > 1.0 raises error."""
        with pytest.raises(ValueError):
            ConfidenceRecord(
                test_name="test_example",
                confidence=1.5,
                category="flaky",
                timestamp=datetime.utcnow()
            )
    
    def test_invalid_confidence_low(self):
        """Test that confidence < 0.0 raises error."""
        with pytest.raises(ValueError):
            ConfidenceRecord(
                test_name="test_example",
                confidence=-0.1,
                category="flaky",
                timestamp=datetime.utcnow()
            )


class TestDriftDetector:
    """Test drift detection functionality."""
    
    def test_record_confidence(self):
        """Test recording confidence measurements."""
        detector = DriftDetector()
        
        detector.record_confidence("test_login", 0.85, "flaky")
        detector.record_confidence("test_login", 0.82, "flaky")
        
        history = detector.get_confidence_history("test_login")
        assert len(history) == 2
        assert history[0][1] == 0.85
        assert history[1][1] == 0.82
    
    def test_insufficient_measurements(self):
        """Test that drift detection requires minimum measurements."""
        detector = DriftDetector()
        
        detector.record_confidence("test_new", 0.80, "stable")
        detector.record_confidence("test_new", 0.78, "stable")
        
        # Only 2 measurements, need 3
        analysis = detector.detect_drift("test_new")
        assert analysis is None
    
    def test_no_drift_stable(self):
        """Test detection when confidence is stable."""
        detector = DriftDetector()
        
        # Record stable confidence (~85%)
        for i in range(10):
            detector.record_confidence("test_stable", 0.85 + i*0.001, "stable")
        
        analysis = detector.detect_drift("test_stable")
        
        assert analysis is not None
        assert analysis.severity == DriftSeverity.NONE
        assert not analysis.is_drifting
        assert analysis.direction == DriftDirection.STABLE
    
    def test_low_drift(self):
        """Test detection of low drift (5-10%)."""
        detector = DriftDetector()
        
        # Start at 0.80, drift to 0.86 (7.5% increase)
        for i in range(5):
            detector.record_confidence("test_low", 0.80, "flaky")
        for i in range(5):
            detector.record_confidence("test_low", 0.86, "flaky")
        
        analysis = detector.detect_drift("test_low")
        
        assert analysis is not None
        assert analysis.severity == DriftSeverity.LOW
        assert analysis.is_drifting
        assert 0.05 <= abs(analysis.drift_percentage) < 0.10
    
    def test_moderate_drift(self):
        """Test detection of moderate drift (10-20%)."""
        detector = DriftDetector()
        
        # Start at 0.80, drift to 0.92 (15% increase)
        for i in range(5):
            detector.record_confidence("test_moderate", 0.80, "flaky")
        for i in range(5):
            detector.record_confidence("test_moderate", 0.92, "flaky")
        
        analysis = detector.detect_drift("test_moderate")
        
        assert analysis is not None
        assert analysis.severity == DriftSeverity.MODERATE
        assert analysis.is_drifting
        assert 0.10 <= abs(analysis.drift_percentage) < 0.20
    
    def test_high_drift(self):
        """Test detection of high drift (20-30%)."""
        detector = DriftDetector()
        
        # Start at 0.80, drift to 1.00 (25% increase)
        for i in range(5):
            detector.record_confidence("test_high", 0.80, "unstable")
        for i in range(5):
            detector.record_confidence("test_high", 1.00, "unstable")
        
        analysis = detector.detect_drift("test_high")
        
        assert analysis is not None
        assert analysis.severity == DriftSeverity.HIGH
        assert analysis.is_drifting
        assert 0.20 <= abs(analysis.drift_percentage) < 0.30
    
    def test_critical_drift(self):
        """Test detection of critical drift (>30%)."""
        detector = DriftDetector()
        
        # Start at 0.60, drift to 0.90 (50% increase)
        for i in range(5):
            detector.record_confidence("test_critical", 0.60, "regression")
        for i in range(5):
            detector.record_confidence("test_critical", 0.90, "regression")
        
        analysis = detector.detect_drift("test_critical")
        
        assert analysis is not None
        assert analysis.severity == DriftSeverity.CRITICAL
        assert analysis.is_drifting
        assert abs(analysis.drift_percentage) >= 0.30
    
    def test_decreasing_drift(self):
        """Test detection of decreasing confidence."""
        detector = DriftDetector()
        
        # Start at 0.90, drift down to 0.70 (22% decrease)
        for i in range(5):
            detector.record_confidence("test_decreasing", 0.90, "flaky")
        for i in range(5):
            detector.record_confidence("test_decreasing", 0.70, "flaky")
        
        analysis = detector.detect_drift("test_decreasing")
        
        assert analysis is not None
        assert analysis.severity == DriftSeverity.HIGH
        assert analysis.direction == DriftDirection.DECREASING
        assert analysis.drift_percentage < 0  # Negative = decreasing
    
    def test_increasing_drift(self):
        """Test detection of increasing confidence."""
        detector = DriftDetector()
        
        # Start at 0.70, drift up to 0.84 (20% increase)
        for i in range(5):
            detector.record_confidence("test_increasing", 0.70, "unstable")
        for i in range(5):
            detector.record_confidence("test_increasing", 0.84, "unstable")
        
        analysis = detector.detect_drift("test_increasing")
        
        assert analysis is not None
        assert analysis.severity == DriftSeverity.HIGH  # 20% is HIGH threshold
        assert analysis.direction == DriftDirection.INCREASING
        assert analysis.drift_percentage > 0  # Positive = increasing
    
    def test_volatile_drift(self):
        """Test detection of volatile confidence (frequent changes)."""
        detector = DriftDetector()
        
        # Alternating high/low confidence
        values = [0.5, 0.9, 0.4, 0.85, 0.45, 0.88, 0.5, 0.9, 0.4, 0.85]
        for value in values:
            detector.record_confidence("test_volatile", value, "flaky")
        
        analysis = detector.detect_drift("test_volatile")
        
        assert analysis is not None
        assert analysis.direction == DriftDirection.VOLATILE
        
        # Calculate standard deviation
        std_dev = statistics.stdev(values)
        assert std_dev > 0.15  # High volatility


class TestTrendAnalysis:
    """Test trend analysis functionality."""
    
    def test_gradually_increasing_trend(self):
        """Test detection of gradual upward trend."""
        detector = DriftDetector()
        
        # Gradual increase from 0.70 to 0.80
        for i in range(10):
            confidence = 0.70 + i * 0.01
            detector.record_confidence("test_trend", confidence, "stable")
        
        analysis = detector.detect_drift("test_trend")
        
        assert analysis is not None
        assert "increasing" in analysis.trend
    
    def test_strongly_increasing_trend(self):
        """Test detection of strong upward trend."""
        detector = DriftDetector()
        
        # Strong increase from 0.50 to 0.90
        for i in range(10):
            confidence = 0.50 + i * 0.04
            detector.record_confidence("test_trend", confidence, "stable")
        
        analysis = detector.detect_drift("test_trend")
        
        assert analysis is not None
        assert "strongly_increasing" in analysis.trend
    
    def test_gradually_decreasing_trend(self):
        """Test detection of gradual downward trend."""
        detector = DriftDetector()
        
        # Gradual decrease from 0.80 to 0.70
        for i in range(10):
            confidence = 0.80 - i * 0.01
            detector.record_confidence("test_trend", confidence, "flaky")
        
        analysis = detector.detect_drift("test_trend")
        
        assert analysis is not None
        assert "decreasing" in analysis.trend
    
    def test_stable_trend(self):
        """Test detection of stable trend."""
        detector = DriftDetector()
        
        # Stable at 0.85
        for i in range(10):
            confidence = 0.85 + (i % 2) * 0.001  # Minimal variation
            detector.record_confidence("test_trend", confidence, "stable")
        
        analysis = detector.detect_drift("test_trend")
        
        assert analysis is not None
        assert analysis.trend == "stable"


class TestCategoryDrift:
    """Test category-level drift detection."""
    
    def test_category_drift_summary(self):
        """Test drift summary for a category."""
        detector = DriftDetector()
        
        # Test 1: Critical drift (70 -> 95 = 35.7% increase)
        for i in range(5):
            detector.record_confidence("test1", 0.70, "flaky")
        for i in range(5):
            detector.record_confidence("test1", 0.95, "flaky")
        
        # Test 2: Moderate drift (80 -> 92 = 15% increase)
        for i in range(5):
            detector.record_confidence("test2", 0.80, "flaky")
        for i in range(5):
            detector.record_confidence("test2", 0.92, "flaky")
        
        # Test 3: No drift
        for i in range(10):
            detector.record_confidence("test3", 0.85, "flaky")
        
        summary = detector.detect_category_drift("flaky")
        
        assert summary.category == "flaky"
        assert summary.tests_analyzed == 3
        assert summary.drifting_tests == 2  # test1 and test2
        assert summary.drift_distribution["critical"] >= 1  # test1 is critical
        assert summary.drift_distribution["moderate"] >= 1
        assert summary.max_drift_test in ["test1", "test2"]
    
    def test_category_no_tests(self):
        """Test category drift when no tests in category."""
        detector = DriftDetector()
        
        summary = detector.detect_category_drift("nonexistent")
        
        assert summary.category == "nonexistent"
        assert summary.tests_analyzed == 0
        assert summary.drifting_tests == 0


class TestTimeWindows:
    """Test time window filtering."""
    
    def test_time_window_filtering(self):
        """Test that only measurements within window are considered."""
        detector = DriftDetector()
        
        now = datetime.utcnow()
        
        # Old measurements (outside 7-day window)
        for i in range(5):
            timestamp = now - timedelta(days=10 + i)
            detector.record_confidence("test_window", 0.70, "stable", timestamp=timestamp)
        
        # Recent measurements (within 7-day window)
        for i in range(5):
            timestamp = now - timedelta(days=i)
            detector.record_confidence("test_window", 0.90, "stable", timestamp=timestamp)
        
        # Detect drift with 7-day window
        analysis = detector.detect_drift("test_window", window=timedelta(days=7))
        
        # Should only see recent measurements (all ~0.90)
        assert analysis is not None
        assert analysis.severity == DriftSeverity.NONE  # Recent measurements are stable
    
    def test_get_history_with_window(self):
        """Test retrieving history within time window."""
        detector = DriftDetector()
        
        now = datetime.utcnow()
        
        # Record measurements over 30 days
        for i in range(30):
            timestamp = now - timedelta(days=29-i)
            detector.record_confidence("test_history", 0.80 + i*0.001, "stable", timestamp=timestamp)
        
        # Get last 7 days
        history = detector.get_confidence_history("test_history", window=timedelta(days=7))
        
        assert len(history) == 7


class TestDriftAlerts:
    """Test drift alert system."""
    
    def test_alert_generation(self):
        """Test generating alerts for drifting tests."""
        detector = DriftDetector()
        alert_manager = DriftAlertManager(detector)
        
        # Create critical drift (70 -> 95 = 35.7% increase)
        for i in range(5):
            detector.record_confidence("test_alert", 0.70, "flaky")
        for i in range(5):
            detector.record_confidence("test_alert", 0.95, "flaky")
        
        # Check for alerts
        alerts = alert_manager.check_for_alerts(min_severity=DriftSeverity.LOW)
        
        assert len(alerts) > 0
        alert = alerts[0]
        assert alert.test_name == "test_alert"
        assert alert.severity == DriftSeverity.CRITICAL  # 35.7% is critical
        assert len(alert.recommendations) > 0
    
    def test_alert_filtering_by_severity(self):
        """Test filtering alerts by severity."""
        detector = DriftDetector()
        alert_manager = DriftAlertManager(detector)
        
        # Create low drift (should not alert with MODERATE threshold)
        for i in range(5):
            detector.record_confidence("test_low", 0.80, "stable")
        for i in range(5):
            detector.record_confidence("test_low", 0.86, "stable")
        
        # Check for alerts with MODERATE threshold
        alerts = alert_manager.check_for_alerts(min_severity=DriftSeverity.MODERATE)
        
        # Should not generate alerts for low drift
        assert len(alerts) == 0
    
    def test_get_recent_alerts(self):
        """Test retrieving recent alerts."""
        detector = DriftDetector()
        alert_manager = DriftAlertManager(detector)
        
        # Generate alerts
        for i in range(5):
            detector.record_confidence("test_recent", 0.70, "flaky")
        for i in range(5):
            detector.record_confidence("test_recent", 0.95, "flaky")
        
        alerts = alert_manager.check_for_alerts(min_severity=DriftSeverity.LOW)
        
        # Get recent alerts (last 24 hours)
        recent = alert_manager.get_recent_alerts(hours=24)
        
        assert len(recent) == len(alerts)


class TestRecommendations:
    """Test recommendation generation."""
    
    def test_critical_drift_recommendations(self):
        """Test that critical drift generates urgent recommendations."""
        detector = DriftDetector()
        
        # Create critical drift
        for i in range(5):
            detector.record_confidence("test_critical", 0.50, "flaky")
        for i in range(5):
            detector.record_confidence("test_critical", 0.80, "flaky")
        
        analysis = detector.detect_drift("test_critical")
        
        assert analysis is not None
        assert any("URGENT" in r or "urgent" in r.lower() for r in analysis.recommendations)
    
    def test_decreasing_drift_recommendations(self):
        """Test recommendations for decreasing confidence."""
        detector = DriftDetector()
        
        # Create decreasing drift
        for i in range(5):
            detector.record_confidence("test_dec", 0.90, "stable")
        for i in range(5):
            detector.record_confidence("test_dec", 0.65, "stable")
        
        analysis = detector.detect_drift("test_dec")
        
        assert analysis is not None
        assert any("decreasing" in r.lower() for r in analysis.recommendations)
    
    def test_volatile_recommendations(self):
        """Test recommendations for volatile confidence."""
        detector = DriftDetector()
        
        # Create volatile pattern
        values = [0.5, 0.9, 0.4, 0.85, 0.45, 0.88, 0.5, 0.9, 0.4, 0.85]
        for value in values:
            detector.record_confidence("test_vol", value, "flaky")
        
        analysis = detector.detect_drift("test_vol")
        
        assert analysis is not None
        assert any("volatil" in r.lower() for r in analysis.recommendations)


class TestDriftFromExplanations:
    """Test building drift detector from confidence explanations."""
    
    def test_detect_drift_from_explanations(self):
        """Test creating detector from explanation objects."""
        from core.intelligence.explainability import (
            ConfidenceExplanation,
            ConfidenceBreakdown
        )
        
        # Create mock explanations
        explanations = []
        for i in range(10):
            exp = ConfidenceExplanation(
                failure_id="F-TEST-" + str(i),
                final_confidence=0.80 + i * 0.02,
                category="flaky",
                primary_rule="flaky_retry",
                rule_influence=[],
                signal_quality=[],
                evidence_context=None,
                confidence_breakdown=ConfidenceBreakdown(
                    rule_score=0.85,
                    signal_score=0.75,
                    final_confidence=0.80 + i * 0.02
                )
            )
            explanations.append(exp)
        
        # Build detector
        detector = detect_drift_from_explanations(explanations)
        
        # Should have 10 measurements
        for i in range(10):
            history = detector.get_confidence_history(f"F-TEST-{i}")
            assert len(history) == 1


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_get_all_drifting_tests(self):
        """Test getting all drifting tests."""
        detector = DriftDetector()
        
        # Test 1: High drift
        for i in range(5):
            detector.record_confidence("test_drift1", 0.70, "flaky")
        for i in range(5):
            detector.record_confidence("test_drift1", 0.95, "flaky")
        
        # Test 2: Moderate drift
        for i in range(5):
            detector.record_confidence("test_drift2", 0.80, "stable")
        for i in range(5):
            detector.record_confidence("test_drift2", 0.92, "stable")
        
        # Test 3: No drift
        for i in range(10):
            detector.record_confidence("test_no_drift", 0.85, "stable")
        
        drifting = detector.get_all_drifting_tests(min_severity=DriftSeverity.LOW)
        
        assert len(drifting) == 2
        # Should be sorted by severity (high first)
        assert drifting[0].severity.value in ["high", "critical", "moderate"]
    
    def test_clear_history(self):
        """Test clearing history."""
        detector = DriftDetector()
        
        detector.record_confidence("test1", 0.85, "stable")
        detector.record_confidence("test2", 0.80, "flaky")
        
        # Clear specific test
        detector.clear_history("test1")
        
        assert len(detector.get_confidence_history("test1")) == 0
        assert len(detector.get_confidence_history("test2")) == 1
        
        # Clear all
        detector.clear_history()
        
        assert len(detector.get_confidence_history("test2")) == 0
    
    def test_drift_analysis_string_representation(self):
        """Test drift analysis string formatting."""
        detector = DriftDetector()
        
        for i in range(5):
            detector.record_confidence("test_str", 0.80, "flaky")
        for i in range(5):
            detector.record_confidence("test_str", 0.92, "flaky")
        
        analysis = detector.detect_drift("test_str")
        
        assert analysis is not None
        str_repr = str(analysis)
        
        assert "test_str" in str_repr
        assert "%" in str_repr
        assert any(symbol in str_repr for symbol in ["↑", "↓", "→", "↕"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
