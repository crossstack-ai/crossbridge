"""
Confidence Calibration System

Calibrates confidence scores across different frameworks and signal types
to ensure consistent reliability of failure classifications.

Ensures:
- Same failure type yields comparable confidence across frameworks
- Historical accuracy improves confidence over time
- Confidence reflects true probability of correct classification
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

from core.logging import get_logger
from core.execution.intelligence.models import (
    FailureSignal,
    SignalType,
    FailureType,
    ExecutionSignal,
    EntityType,
)

logger = get_logger(__name__)


@dataclass
class ConfidenceRecord:
    """
    Record of a confidence prediction and its outcome.
    
    Used for calibration and evaluation.
    """
    signal_type: str
    framework: str
    predicted_confidence: float
    was_correct: bool
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CalibrationStats:
    """
    Calibration statistics for a signal type.
    """
    signal_type: str
    framework: Optional[str] = None
    
    # Prediction counts
    total_predictions: int = 0
    correct_predictions: int = 0
    
    # Confidence statistics
    avg_confidence_when_correct: float = 0.0
    avg_confidence_when_incorrect: float = 0.0
    
    # Calibration metrics
    calibration_error: float = 0.0  # How far off confidence is from accuracy
    
    def accuracy(self) -> float:
        """Calculate prediction accuracy"""
        if self.total_predictions == 0:
            return 0.0
        return self.correct_predictions / self.total_predictions
    
    def confidence_bias(self) -> float:
        """
        Calculate confidence bias.
        
        Positive = overconfident
        Negative = underconfident
        """
        return self.avg_confidence_when_correct - self.accuracy()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'signal_type': self.signal_type,
            'framework': self.framework,
            'total_predictions': self.total_predictions,
            'correct_predictions': self.correct_predictions,
            'accuracy': self.accuracy(),
            'avg_confidence_when_correct': self.avg_confidence_when_correct,
            'avg_confidence_when_incorrect': self.avg_confidence_when_incorrect,
            'calibration_error': self.calibration_error,
            'confidence_bias': self.confidence_bias(),
        }


class ConfidenceCalibrator:
    """
    Calibrates confidence scores based on historical accuracy.
    
    Uses empirical Bayes approach:
    - Track prediction accuracy by signal type and framework
    - Adjust confidence scores to match historical accuracy
    - Apply smoothing for low-sample scenarios
    """
    
    def __init__(self, calibration_file: Optional[str] = None):
        """
        Initialize calibrator.
        
        Args:
            calibration_file: Path to calibration data file (JSON)
        """
        self.calibration_file = calibration_file
        self.records: List[ConfidenceRecord] = []
        self.stats_cache: Dict[Tuple[str, str], CalibrationStats] = {}
        
        # Load existing calibration data
        if calibration_file and Path(calibration_file).exists():
            self.load(calibration_file)
    
    def record_prediction(
        self,
        signal_type: SignalType,
        framework: str,
        predicted_confidence: float,
        was_correct: bool,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a confidence prediction and its outcome.
        
        Args:
            signal_type: Type of signal predicted
            framework: Framework (cucumber, robot, pytest)
            predicted_confidence: Original confidence score (0.0-1.0)
            was_correct: Whether prediction was correct
            metadata: Optional additional context
        """
        record = ConfidenceRecord(
            signal_type=signal_type.value,
            framework=framework,
            predicted_confidence=predicted_confidence,
            was_correct=was_correct,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        self.records.append(record)
        
        # Invalidate stats cache
        cache_key = (signal_type.value, framework)
        if cache_key in self.stats_cache:
            del self.stats_cache[cache_key]
    
    def calculate_stats(
        self,
        signal_type: str,
        framework: Optional[str] = None
    ) -> CalibrationStats:
        """
        Calculate calibration statistics.
        
        Args:
            signal_type: Signal type to calculate for
            framework: Optional framework filter
            
        Returns:
            CalibrationStats object
        """
        # Check cache
        cache_key = (signal_type, framework or "all")
        if cache_key in self.stats_cache:
            return self.stats_cache[cache_key]
        
        # Filter records
        filtered_records = [
            r for r in self.records
            if r.signal_type == signal_type and (framework is None or r.framework == framework)
        ]
        
        if not filtered_records:
            return CalibrationStats(signal_type=signal_type, framework=framework)
        
        # Calculate statistics
        total = len(filtered_records)
        correct = sum(1 for r in filtered_records if r.was_correct)
        
        correct_records = [r for r in filtered_records if r.was_correct]
        incorrect_records = [r for r in filtered_records if not r.was_correct]
        
        avg_conf_correct = (
            sum(r.predicted_confidence for r in correct_records) / len(correct_records)
            if correct_records else 0.0
        )
        
        avg_conf_incorrect = (
            sum(r.predicted_confidence for r in incorrect_records) / len(incorrect_records)
            if incorrect_records else 0.0
        )
        
        # Calculate calibration error (ECE - Expected Calibration Error)
        # Group predictions into bins and compare confidence to accuracy
        calibration_error = self._calculate_ece(filtered_records)
        
        stats = CalibrationStats(
            signal_type=signal_type,
            framework=framework,
            total_predictions=total,
            correct_predictions=correct,
            avg_confidence_when_correct=avg_conf_correct,
            avg_confidence_when_incorrect=avg_conf_incorrect,
            calibration_error=calibration_error,
        )
        
        # Cache result
        self.stats_cache[cache_key] = stats
        
        return stats
    
    def _calculate_ece(self, records: List[ConfidenceRecord], num_bins: int = 10) -> float:
        """
        Calculate Expected Calibration Error.
        
        Measures how well confidence scores match actual accuracy.
        """
        if not records:
            return 0.0
        
        # Create bins
        bins = [[] for _ in range(num_bins)]
        for record in records:
            bin_idx = min(int(record.predicted_confidence * num_bins), num_bins - 1)
            bins[bin_idx].append(record)
        
        # Calculate ECE
        ece = 0.0
        total_samples = len(records)
        
        for bin_records in bins:
            if not bin_records:
                continue
            
            # Average confidence in this bin
            avg_confidence = sum(r.predicted_confidence for r in bin_records) / len(bin_records)
            
            # Actual accuracy in this bin
            accuracy = sum(1 for r in bin_records if r.was_correct) / len(bin_records)
            
            # Weighted contribution to ECE
            weight = len(bin_records) / total_samples
            ece += weight * abs(avg_confidence - accuracy)
        
        return ece
    
    def calibrate_confidence(
        self,
        signal_type: SignalType,
        framework: str,
        original_confidence: float,
        min_samples: int = 10
    ) -> float:
        """
        Calibrate confidence score based on historical accuracy.
        
        Args:
            signal_type: Type of signal
            framework: Framework
            original_confidence: Original confidence score (0.0-1.0)
            min_samples: Minimum samples needed for calibration
            
        Returns:
            Calibrated confidence score (0.0-1.0)
        """
        stats = self.calculate_stats(signal_type.value, framework)
        
        # Not enough data - return original
        if stats.total_predictions < min_samples:
            return original_confidence
        
        # Calculate calibration factor
        accuracy = stats.accuracy()
        
        # If we have good accuracy, adjust confidence toward accuracy
        # Use a weighted average: 80% historical accuracy, 20% original confidence
        # (This prevents over-correction)
        calibrated = 0.8 * accuracy + 0.2 * original_confidence
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, calibrated))
    
    def get_framework_comparison(self, signal_type: str) -> Dict[str, CalibrationStats]:
        """
        Compare calibration across frameworks for a signal type.
        
        Args:
            signal_type: Signal type to compare
            
        Returns:
            Dictionary of framework → CalibrationStats
        """
        frameworks = set(r.framework for r in self.records if r.signal_type == signal_type)
        
        return {
            framework: self.calculate_stats(signal_type, framework)
            for framework in frameworks
        }
    
    def save(self, file_path: str):
        """Save calibration data to file"""
        data = {
            'records': [
                {
                    'signal_type': r.signal_type,
                    'framework': r.framework,
                    'predicted_confidence': r.predicted_confidence,
                    'was_correct': r.was_correct,
                    'timestamp': r.timestamp,
                    'metadata': r.metadata,
                }
                for r in self.records
            ]
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(self.records)} calibration records to {file_path}")
    
    def load(self, file_path: str):
        """Load calibration data from file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        self.records = [
            ConfidenceRecord(**record_data)
            for record_data in data['records']
        ]
        
        logger.info(f"Loaded {len(self.records)} calibration records from {file_path}")
    
    def report(self) -> Dict[str, Any]:
        """
        Generate calibration report.
        
        Returns:
            Dictionary with calibration statistics
        """
        # Get all unique signal types
        signal_types = set(r.signal_type for r in self.records)
        
        report = {
            'total_records': len(self.records),
            'signal_types': {},
            'overall_accuracy': sum(1 for r in self.records if r.was_correct) / len(self.records) if self.records else 0.0,
        }
        
        for signal_type in signal_types:
            # Overall stats for this signal type
            overall_stats = self.calculate_stats(signal_type)
            
            # Per-framework stats
            framework_stats = self.get_framework_comparison(signal_type)
            
            report['signal_types'][signal_type] = {
                'overall': overall_stats.to_dict(),
                'by_framework': {
                    framework: stats.to_dict()
                    for framework, stats in framework_stats.items()
                }
            }
        
        return report


class CrossFrameworkCalibrator:
    """
    Ensures consistency across frameworks.
    
    Adjusts confidence scores so that:
    - Similar failures have similar confidence across frameworks
    - Framework-specific biases are corrected
    """
    
    def __init__(self, calibrator: ConfidenceCalibrator):
        self.calibrator = calibrator
    
    def normalize_across_frameworks(
        self,
        signals: List[ExecutionSignal]
    ) -> List[ExecutionSignal]:
        """
        Normalize confidence scores across frameworks.
        
        Args:
            signals: List of ExecutionSignal objects
            
        Returns:
            Signals with normalized confidence scores
        """
        # Group signals by failure type
        by_failure_type: Dict[str, List[ExecutionSignal]] = {}
        
        for signal in signals:
            if signal.failure_type:
                if signal.failure_type not in by_failure_type:
                    by_failure_type[signal.failure_type] = []
                by_failure_type[signal.failure_type].append(signal)
        
        # Normalize each group
        normalized_signals = []
        
        for failure_type, group in by_failure_type.items():
            # Calculate average confidence across frameworks
            avg_confidence = sum(s.confidence for s in group) / len(group)
            
            # Adjust each signal's confidence toward the average
            for signal in group:
                # Get framework-specific stats
                try:
                    signal_type = SignalType(failure_type)
                    stats = self.calibrator.calculate_stats(
                        signal_type.value,
                        signal.framework
                    )
                    
                    # If framework is under/overconfident, adjust
                    if stats.total_predictions >= 10:
                        bias = stats.confidence_bias()
                        
                        # Correct for bias
                        adjusted_confidence = signal.confidence - bias
                        
                        # Blend with average (50/50)
                        signal.confidence = 0.5 * adjusted_confidence + 0.5 * avg_confidence
                        
                        # Clamp to [0, 1]
                        signal.confidence = max(0.0, min(1.0, signal.confidence))
                
                except ValueError:
                    # Unknown signal type, keep original
                    pass
                
                normalized_signals.append(signal)
        
        return normalized_signals


# Example usage
if __name__ == "__main__":
    # Initialize calibrator
    calibrator = ConfidenceCalibrator("calibration_data.json")
    
    # Record some predictions (in production, this happens during test execution)
    calibrator.record_prediction(
        signal_type=SignalType.TIMEOUT,
        framework="cucumber",
        predicted_confidence=0.9,
        was_correct=True
    )
    
    calibrator.record_prediction(
        signal_type=SignalType.TIMEOUT,
        framework="robot",
        predicted_confidence=0.85,
        was_correct=True
    )
    
    calibrator.record_prediction(
        signal_type=SignalType.ASSERTION,
        framework="pytest",
        predicted_confidence=0.95,
        was_correct=False  # Overconfident
    )
    
    # Generate report
    report = calibrator.report()
    print(f"Calibration Report:")
    print(f"  Total records: {report['total_records']}")
    print(f"  Overall accuracy: {report['overall_accuracy']:.2%}")
    
    for signal_type, stats in report['signal_types'].items():
        print(f"\n{signal_type}:")
        print(f"  Overall accuracy: {stats['overall']['accuracy']:.2%}")
        print(f"  Calibration error: {stats['overall']['calibration_error']:.3f}")
        print(f"  Confidence bias: {stats['overall']['confidence_bias']:.3f}")
        
        if stats['by_framework']:
            print(f"  By framework:")
            for framework, fw_stats in stats['by_framework'].items():
                print(f"    {framework}: {fw_stats['accuracy']:.2%} accuracy")
    
    # Calibrate a new prediction
    original_conf = 0.9
    calibrated_conf = calibrator.calibrate_confidence(
        signal_type=SignalType.TIMEOUT,
        framework="cucumber",
        original_confidence=original_conf
    )
    
    print(f"\nCalibration example:")
    print(f"  Original confidence: {original_conf:.2f}")
    print(f"  Calibrated confidence: {calibrated_conf:.2f}")
    
    # Save calibration data
    calibrator.save("calibration_data.json")
