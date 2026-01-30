"""
Confidence Drift Detection System.

Monitors confidence score changes over time to detect:
- Significant drift (>10% change)
- Trend patterns (upward/downward)
- Sudden changes vs gradual shifts
- Per-test and per-category drift
- Recalibration needs

Usage:
    from core.intelligence.confidence_drift import DriftDetector
    
    detector = DriftDetector()
    detector.record_confidence("test_login", 0.85, category="flaky")
    detector.record_confidence("test_login", 0.72, category="flaky")
    
    drift = detector.detect_drift("test_login")
    if drift.is_drifting:
        print(f"Alert: {drift.severity} drift detected!")
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
import statistics
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

class DriftSeverity(Enum):
    """Severity levels for confidence drift."""
    NONE = "none"
    LOW = "low"           # 5-10% change
    MODERATE = "moderate" # 10-20% change
    HIGH = "high"         # 20-30% change
    CRITICAL = "critical" # >30% change


class DriftDirection(Enum):
    """Direction of confidence drift."""
    STABLE = "stable"
    INCREASING = "increasing"
    DECREASING = "decreasing"
    VOLATILE = "volatile"  # Frequent up/down changes


@dataclass
class ConfidenceRecord:
    """Single confidence measurement."""
    test_name: str
    confidence: float
    category: str
    timestamp: datetime
    failure_id: Optional[str] = None
    rule_score: Optional[float] = None
    signal_score: Optional[float] = None
    
    def __post_init__(self):
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")


@dataclass
class DriftAnalysis:
    """Analysis of confidence drift for a test."""
    test_name: str
    current_confidence: float
    baseline_confidence: float
    drift_percentage: float
    drift_absolute: float
    severity: DriftSeverity
    direction: DriftDirection
    is_drifting: bool
    measurements_count: int
    time_span: timedelta
    trend: str
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __str__(self) -> str:
        """Human-readable drift summary."""
        direction_symbol = {
            DriftDirection.STABLE: "→",
            DriftDirection.INCREASING: "↑",
            DriftDirection.DECREASING: "↓",
            DriftDirection.VOLATILE: "↕"
        }
        
        symbol = direction_symbol.get(self.direction, "?")
        return (
            f"{symbol} {self.test_name}: "
            f"{self.baseline_confidence:.1%} → {self.current_confidence:.1%} "
            f"({self.drift_percentage:+.1%}) - {self.severity.value.upper()}"
        )


@dataclass
class CategoryDriftSummary:
    """Drift summary for a category (e.g., all flaky tests)."""
    category: str
    tests_analyzed: int
    drifting_tests: int
    avg_drift_percentage: float
    max_drift_test: Optional[str]
    max_drift_percentage: float
    drift_distribution: Dict[str, int]  # severity -> count
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ============================================================================
# DRIFT DETECTION THRESHOLDS
# ============================================================================

class DriftThresholds:
    """Configurable thresholds for drift detection."""
    
    # Drift severity thresholds (absolute percentage change)
    LOW_DRIFT = 0.05      # 5%
    MODERATE_DRIFT = 0.10 # 10%
    HIGH_DRIFT = 0.20     # 20%
    CRITICAL_DRIFT = 0.30 # 30%
    
    # Minimum measurements for drift detection
    MIN_MEASUREMENTS = 3
    
    # Volatility threshold (standard deviation)
    VOLATILITY_THRESHOLD = 0.15
    
    # Time windows for analysis
    SHORT_TERM_WINDOW = timedelta(days=7)
    MEDIUM_TERM_WINDOW = timedelta(days=30)
    LONG_TERM_WINDOW = timedelta(days=90)


# ============================================================================
# DRIFT DETECTOR
# ============================================================================

class DriftDetector:
    """
    Detects confidence drift over time.
    
    Features:
    - Per-test drift tracking
    - Per-category aggregation
    - Multiple time windows
    - Trend analysis
    - Alert generation
    """
    
    def __init__(self, thresholds: Optional[DriftThresholds] = None):
        """Initialize drift detector."""
        self.thresholds = thresholds or DriftThresholds()
        self._history: Dict[str, List[ConfidenceRecord]] = {}
        logger.info("DriftDetector initialized")
    
    def record_confidence(
        self,
        test_name: str,
        confidence: float,
        category: str,
        timestamp: Optional[datetime] = None,
        failure_id: Optional[str] = None,
        rule_score: Optional[float] = None,
        signal_score: Optional[float] = None
    ) -> None:
        """
        Record a confidence measurement.
        
        Args:
            test_name: Test identifier
            confidence: Confidence score (0.0-1.0)
            category: Classification category
            timestamp: Measurement time (default: now)
            failure_id: Optional failure ID
            rule_score: Optional rule score
            signal_score: Optional signal score
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        record = ConfidenceRecord(
            test_name=test_name,
            confidence=confidence,
            category=category,
            timestamp=timestamp,
            failure_id=failure_id,
            rule_score=rule_score,
            signal_score=signal_score
        )
        
        if test_name not in self._history:
            self._history[test_name] = []
        
        self._history[test_name].append(record)
        logger.debug(f"Recorded confidence {confidence:.2f} for {test_name}")
    
    def detect_drift(
        self,
        test_name: str,
        window: Optional[timedelta] = None
    ) -> Optional[DriftAnalysis]:
        """
        Detect drift for a specific test.
        
        Args:
            test_name: Test to analyze
            window: Time window (default: all history)
            
        Returns:
            DriftAnalysis if sufficient data, None otherwise
        """
        if test_name not in self._history:
            logger.warning(f"No history for test: {test_name}")
            return None
        
        records = self._history[test_name]
        
        # Filter by time window
        if window:
            cutoff = datetime.utcnow() - window
            records = [r for r in records if r.timestamp >= cutoff]
        
        if len(records) < self.thresholds.MIN_MEASUREMENTS:
            logger.debug(
                f"Insufficient measurements for {test_name}: "
                f"{len(records)} < {self.thresholds.MIN_MEASUREMENTS}"
            )
            return None
        
        # Sort by timestamp
        records = sorted(records, key=lambda r: r.timestamp)
        
        # Calculate baseline (earliest measurements)
        baseline_size = max(1, len(records) // 3)
        baseline_records = records[:baseline_size]
        baseline_confidence = statistics.mean(r.confidence for r in baseline_records)
        
        # Calculate current (latest measurements)
        current_size = max(1, len(records) // 3)
        current_records = records[-current_size:]
        current_confidence = statistics.mean(r.confidence for r in current_records)
        
        # Calculate drift
        drift_absolute = current_confidence - baseline_confidence
        drift_percentage = drift_absolute / baseline_confidence if baseline_confidence > 0 else 0.0
        
        # Determine severity
        severity = self._classify_severity(abs(drift_percentage))
        
        # Determine direction
        direction = self._classify_direction(records)
        
        # Is drifting?
        is_drifting = severity != DriftSeverity.NONE
        
        # Time span
        time_span = records[-1].timestamp - records[0].timestamp
        
        # Trend analysis
        trend = self._analyze_trend(records)
        
        # Recommendations
        recommendations = self._generate_recommendations(
            severity, direction, drift_percentage, trend
        )
        
        analysis = DriftAnalysis(
            test_name=test_name,
            current_confidence=current_confidence,
            baseline_confidence=baseline_confidence,
            drift_percentage=drift_percentage,
            drift_absolute=drift_absolute,
            severity=severity,
            direction=direction,
            is_drifting=is_drifting,
            measurements_count=len(records),
            time_span=time_span,
            trend=trend,
            recommendations=recommendations
        )
        
        if is_drifting:
            logger.warning(f"Drift detected: {analysis}")
        
        return analysis
    
    def detect_category_drift(self, category: str) -> CategoryDriftSummary:
        """
        Detect drift across all tests in a category.
        
        Args:
            category: Category to analyze
            
        Returns:
            CategoryDriftSummary with aggregate statistics
        """
        # Find all tests in this category
        category_tests = set()
        for test_name, records in self._history.items():
            if any(r.category == category for r in records):
                category_tests.add(test_name)
        
        if not category_tests:
            return CategoryDriftSummary(
                category=category,
                tests_analyzed=0,
                drifting_tests=0,
                avg_drift_percentage=0.0,
                max_drift_test=None,
                max_drift_percentage=0.0,
                drift_distribution={}
            )
        
        # Analyze each test
        analyses: List[DriftAnalysis] = []
        for test_name in category_tests:
            analysis = self.detect_drift(test_name)
            if analysis:
                analyses.append(analysis)
        
        # Calculate aggregates
        drifting_tests = sum(1 for a in analyses if a.is_drifting)
        avg_drift = statistics.mean(a.drift_percentage for a in analyses) if analyses else 0.0
        
        # Find max drift
        max_drift_analysis = max(analyses, key=lambda a: abs(a.drift_percentage)) if analyses else None
        max_drift_test = max_drift_analysis.test_name if max_drift_analysis else None
        max_drift_percentage = max_drift_analysis.drift_percentage if max_drift_analysis else 0.0
        
        # Drift distribution
        drift_distribution = {
            "none": sum(1 for a in analyses if a.severity == DriftSeverity.NONE),
            "low": sum(1 for a in analyses if a.severity == DriftSeverity.LOW),
            "moderate": sum(1 for a in analyses if a.severity == DriftSeverity.MODERATE),
            "high": sum(1 for a in analyses if a.severity == DriftSeverity.HIGH),
            "critical": sum(1 for a in analyses if a.severity == DriftSeverity.CRITICAL)
        }
        
        return CategoryDriftSummary(
            category=category,
            tests_analyzed=len(analyses),
            drifting_tests=drifting_tests,
            avg_drift_percentage=avg_drift,
            max_drift_test=max_drift_test,
            max_drift_percentage=max_drift_percentage,
            drift_distribution=drift_distribution
        )
    
    def get_all_drifting_tests(
        self,
        min_severity: DriftSeverity = DriftSeverity.LOW
    ) -> List[DriftAnalysis]:
        """
        Get all tests with detected drift.
        
        Args:
            min_severity: Minimum severity to include
            
        Returns:
            List of DriftAnalysis for drifting tests
        """
        drifting = []
        severity_order = {
            DriftSeverity.NONE: 0,
            DriftSeverity.LOW: 1,
            DriftSeverity.MODERATE: 2,
            DriftSeverity.HIGH: 3,
            DriftSeverity.CRITICAL: 4
        }
        min_level = severity_order[min_severity]
        
        for test_name in self._history.keys():
            analysis = self.detect_drift(test_name)
            if analysis and severity_order[analysis.severity] >= min_level:
                drifting.append(analysis)
        
        # Sort by severity (critical first)
        drifting.sort(key=lambda a: severity_order[a.severity], reverse=True)
        
        return drifting
    
    def get_confidence_history(
        self,
        test_name: str,
        window: Optional[timedelta] = None
    ) -> List[Tuple[datetime, float]]:
        """
        Get confidence history for a test.
        
        Args:
            test_name: Test to query
            window: Time window (default: all)
            
        Returns:
            List of (timestamp, confidence) tuples
        """
        if test_name not in self._history:
            return []
        
        records = self._history[test_name]
        
        if window:
            cutoff = datetime.utcnow() - window
            records = [r for r in records if r.timestamp >= cutoff]
        
        return [(r.timestamp, r.confidence) for r in sorted(records, key=lambda r: r.timestamp)]
    
    def clear_history(self, test_name: Optional[str] = None) -> None:
        """
        Clear confidence history.
        
        Args:
            test_name: Test to clear (None = clear all)
        """
        if test_name:
            if test_name in self._history:
                del self._history[test_name]
                logger.info(f"Cleared history for {test_name}")
        else:
            self._history.clear()
            logger.info("Cleared all history")
    
    # Private helper methods
    
    def _classify_severity(self, drift_percentage: float) -> DriftSeverity:
        """Classify drift severity based on percentage change."""
        if drift_percentage >= self.thresholds.CRITICAL_DRIFT:
            return DriftSeverity.CRITICAL
        elif drift_percentage >= self.thresholds.HIGH_DRIFT:
            return DriftSeverity.HIGH
        elif drift_percentage >= self.thresholds.MODERATE_DRIFT:
            return DriftSeverity.MODERATE
        elif drift_percentage >= self.thresholds.LOW_DRIFT:
            return DriftSeverity.LOW
        else:
            return DriftSeverity.NONE
    
    def _classify_direction(self, records: List[ConfidenceRecord]) -> DriftDirection:
        """Classify drift direction."""
        if len(records) < 3:
            return DriftDirection.STABLE
        
        confidences = [r.confidence for r in records]
        
        # Check volatility
        std_dev = statistics.stdev(confidences) if len(confidences) > 1 else 0.0
        if std_dev > self.thresholds.VOLATILITY_THRESHOLD:
            return DriftDirection.VOLATILE
        
        # Check trend
        first_third = statistics.mean(confidences[:len(confidences)//3])
        last_third = statistics.mean(confidences[-len(confidences)//3:])
        
        change = last_third - first_third
        
        if abs(change) < self.thresholds.LOW_DRIFT:
            return DriftDirection.STABLE
        elif change > 0:
            return DriftDirection.INCREASING
        else:
            return DriftDirection.DECREASING
    
    def _analyze_trend(self, records: List[ConfidenceRecord]) -> str:
        """Analyze confidence trend over time."""
        if len(records) < 3:
            return "insufficient_data"
        
        confidences = [r.confidence for r in records]
        
        # Simple linear regression
        n = len(confidences)
        x = list(range(n))
        y = confidences
        
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Classify trend
        if abs(slope) < 0.001:
            return "stable"
        elif slope > 0.005:
            return "strongly_increasing"
        elif slope > 0.001:
            return "gradually_increasing"
        elif slope < -0.005:
            return "strongly_decreasing"
        else:
            return "gradually_decreasing"
    
    def _generate_recommendations(
        self,
        severity: DriftSeverity,
        direction: DriftDirection,
        drift_percentage: float,
        trend: str
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if severity == DriftSeverity.NONE:
            recommendations.append("No action needed - confidence is stable")
            return recommendations
        
        # Severity-based recommendations
        if severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
            recommendations.append("🚨 URGENT: Investigate root cause immediately")
            recommendations.append("Consider disabling test until investigation complete")
        
        # Direction-based recommendations
        if direction == DriftDirection.DECREASING:
            recommendations.append("⚠️ Confidence is decreasing")
            recommendations.append("Check for: signal quality degradation, rule changes, test instability")
        elif direction == DriftDirection.INCREASING:
            recommendations.append("✓ Confidence is improving")
            recommendations.append("Validate: Are test conditions more stable? Have signals improved?")
        elif direction == DriftDirection.VOLATILE:
            recommendations.append("⚡ High volatility detected")
            recommendations.append("Review: signal consistency, environmental factors, test reliability")
        
        # Trend-based recommendations
        if "strongly" in trend:
            recommendations.append(f"Strong trend detected: {trend.replace('_', ' ')}")
            recommendations.append("Consider recalibration if trend continues")
        
        # Magnitude-based recommendations
        if abs(drift_percentage) > 0.20:
            recommendations.append("Large confidence change (>20%)")
            recommendations.append("Review classification rules and signal weights")
        
        # General recommendations
        severity_order = {
            DriftSeverity.NONE: 0,
            DriftSeverity.LOW: 1,
            DriftSeverity.MODERATE: 2,
            DriftSeverity.HIGH: 3,
            DriftSeverity.CRITICAL: 4
        }
        if severity_order[severity] >= severity_order[DriftSeverity.MODERATE]:
            recommendations.append("Run additional test cycles to gather more data")
            recommendations.append("Compare signal quality scores over time")
            recommendations.append("Review recent code changes affecting this test")
        
        return recommendations


# ============================================================================
# ALERT SYSTEM
# ============================================================================

@dataclass
class DriftAlert:
    """Alert for confidence drift."""
    test_name: str
    severity: DriftSeverity
    drift_percentage: float
    message: str
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "test_name": self.test_name,
            "severity": self.severity.value,
            "drift_percentage": self.drift_percentage,
            "message": self.message,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat()
        }


class DriftAlertManager:
    """Manages drift alerts and notifications."""
    
    def __init__(self, detector: DriftDetector):
        """Initialize alert manager."""
        self.detector = detector
        self.alerts: List[DriftAlert] = []
    
    def check_for_alerts(
        self,
        min_severity: DriftSeverity = DriftSeverity.MODERATE
    ) -> List[DriftAlert]:
        """
        Check all tests and generate alerts.
        
        Args:
            min_severity: Minimum severity for alerts
            
        Returns:
            List of new alerts
        """
        new_alerts = []
        drifting = self.detector.get_all_drifting_tests(min_severity)
        
        for analysis in drifting:
            message = str(analysis)
            alert = DriftAlert(
                test_name=analysis.test_name,
                severity=analysis.severity,
                drift_percentage=analysis.drift_percentage,
                message=message,
                recommendations=analysis.recommendations
            )
            new_alerts.append(alert)
            self.alerts.append(alert)
        
        return new_alerts
    
    def get_recent_alerts(
        self,
        hours: int = 24
    ) -> List[DriftAlert]:
        """Get alerts from last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [a for a in self.alerts if a.timestamp >= cutoff]
    
    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts.clear()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def detect_drift_from_explanations(
    explanations: List,
    detector: Optional[DriftDetector] = None
) -> DriftDetector:
    """
    Build drift detector from confidence explanations.
    
    Args:
        explanations: List of ConfidenceExplanation objects
        detector: Existing detector (creates new if None)
        
    Returns:
        DriftDetector with recorded confidences
    """
    if detector is None:
        detector = DriftDetector()
    
    for exp in explanations:
        detector.record_confidence(
            test_name=exp.failure_id,
            confidence=exp.final_confidence,
            category=exp.category,
            timestamp=datetime.fromisoformat(exp.timestamp),
            failure_id=exp.failure_id,
            rule_score=exp.confidence_breakdown.rule_score,
            signal_score=exp.confidence_breakdown.signal_score
        )
    
    return detector
