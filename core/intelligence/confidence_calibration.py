"""
Confidence Calibration for AI Enrichment.

This module provides confidence calibration to adjust AI confidence scores
based on historical accuracy, ensuring reliable confidence estimates.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging
import statistics

logger = logging.getLogger(__name__)


@dataclass
class CalibrationRecord:
    """Single calibration record tracking predicted vs actual confidence."""
    predicted_confidence: float
    actual_correct: bool
    classification_label: str
    timestamp: float


@dataclass
class CalibrationBucket:
    """Confidence bucket for calibration tracking."""
    min_confidence: float
    max_confidence: float
    predictions: int = 0
    correct: int = 0
    
    @property
    def accuracy(self) -> float:
        """Get accuracy for this bucket."""
        if self.predictions == 0:
            return 0.0
        return self.correct / self.predictions
    
    @property
    def calibration_error(self) -> float:
        """Get calibration error (difference between predicted and actual)."""
        if self.predictions == 0:
            return 0.0
        
        avg_predicted = (self.min_confidence + self.max_confidence) / 2
        return abs(avg_predicted - self.accuracy)


class ConfidenceCalibrator:
    """
    Confidence calibration system for AI enrichment.
    
    This tracks AI prediction accuracy across confidence levels and
    adjusts future confidence scores to be well-calibrated.
    
    Key concepts:
    - Confidence buckets: Group predictions by confidence range
    - Expected Calibration Error (ECE): Measure of calibration quality
    - Calibration curve: Plot of predicted vs actual confidence
    """
    
    def __init__(
        self,
        num_buckets: int = 10,
        min_samples_per_bucket: int = 10,
        history_size: int = 1000
    ):
        """
        Initialize confidence calibrator.
        
        Args:
            num_buckets: Number of confidence buckets (default 10)
            min_samples_per_bucket: Minimum samples needed for calibration
            history_size: Maximum history to keep
        """
        self.num_buckets = num_buckets
        self.min_samples_per_bucket = min_samples_per_bucket
        self.history_size = history_size
        
        # Initialize buckets
        self.buckets: List[CalibrationBucket] = []
        bucket_size = 1.0 / num_buckets
        for i in range(num_buckets):
            self.buckets.append(CalibrationBucket(
                min_confidence=i * bucket_size,
                max_confidence=(i + 1) * bucket_size
            ))
        
        # History of predictions
        self.history: deque = deque(maxlen=history_size)
        
        # Per-label calibration
        self.label_buckets: Dict[str, List[CalibrationBucket]] = defaultdict(
            lambda: [
                CalibrationBucket(
                    min_confidence=i / num_buckets,
                    max_confidence=(i + 1) / num_buckets
                )
                for i in range(num_buckets)
            ]
        )
    
    def record_prediction(
        self,
        predicted_confidence: float,
        actual_correct: bool,
        classification_label: str,
        timestamp: Optional[float] = None
    ):
        """
        Record a prediction for calibration tracking.
        
        Args:
            predicted_confidence: AI's predicted confidence (0.0 - 1.0)
            actual_correct: Whether the prediction was actually correct
            classification_label: The classification label
            timestamp: Optional timestamp (uses current time if None)
        """
        import time
        
        timestamp = timestamp or time.time()
        
        # Add to history
        record = CalibrationRecord(
            predicted_confidence=predicted_confidence,
            actual_correct=actual_correct,
            classification_label=classification_label,
            timestamp=timestamp
        )
        self.history.append(record)
        
        # Update global buckets
        bucket_idx = self._get_bucket_index(predicted_confidence)
        self.buckets[bucket_idx].predictions += 1
        if actual_correct:
            self.buckets[bucket_idx].correct += 1
        
        # Update label-specific buckets
        label_buckets = self.label_buckets[classification_label]
        label_buckets[bucket_idx].predictions += 1
        if actual_correct:
            label_buckets[bucket_idx].correct += 1
        
        logger.debug(
            "Recorded prediction: confidence=%.2f, correct=%s, label=%s",
            predicted_confidence, actual_correct, classification_label
        )
    
    def calibrate(
        self,
        predicted_confidence: float,
        classification_label: Optional[str] = None
    ) -> float:
        """
        Calibrate a predicted confidence score.
        
        This adjusts the raw AI confidence based on historical accuracy
        to produce a well-calibrated confidence estimate.
        
        Args:
            predicted_confidence: Raw AI confidence (0.0 - 1.0)
            classification_label: Optional label for label-specific calibration
            
        Returns:
            Calibrated confidence (0.0 - 1.0)
        """
        bucket_idx = self._get_bucket_index(predicted_confidence)
        
        # Use label-specific calibration if available and sufficient data
        if classification_label and classification_label in self.label_buckets:
            label_bucket = self.label_buckets[classification_label][bucket_idx]
            if label_bucket.predictions >= self.min_samples_per_bucket:
                calibrated = label_bucket.accuracy
                logger.debug(
                    "Label-specific calibration: %.2f -> %.2f (label=%s, n=%d)",
                    predicted_confidence, calibrated, classification_label,
                    label_bucket.predictions
                )
                return calibrated
        
        # Fall back to global calibration
        global_bucket = self.buckets[bucket_idx]
        if global_bucket.predictions >= self.min_samples_per_bucket:
            calibrated = global_bucket.accuracy
            logger.debug(
                "Global calibration: %.2f -> %.2f (n=%d)",
                predicted_confidence, calibrated, global_bucket.predictions
            )
            return calibrated
        
        # Not enough data, return original confidence
        logger.debug(
            "Insufficient calibration data (n=%d), returning original confidence",
            global_bucket.predictions
        )
        return predicted_confidence
    
    def get_expected_calibration_error(self) -> float:
        """
        Calculate Expected Calibration Error (ECE).
        
        ECE measures how well-calibrated the model is.
        Lower is better (0.0 = perfect calibration).
        
        Returns:
            ECE score (0.0 - 1.0)
        """
        total_predictions = sum(b.predictions for b in self.buckets)
        if total_predictions == 0:
            return 0.0
        
        weighted_errors = []
        for bucket in self.buckets:
            if bucket.predictions > 0:
                weight = bucket.predictions / total_predictions
                weighted_errors.append(weight * bucket.calibration_error)
        
        return sum(weighted_errors)
    
    def get_calibration_curve(self) -> List[Tuple[float, float, int]]:
        """
        Get calibration curve data.
        
        Returns:
            List of (predicted_confidence, actual_accuracy, sample_count) tuples
        """
        curve = []
        for bucket in self.buckets:
            avg_predicted = (bucket.min_confidence + bucket.max_confidence) / 2
            curve.append((avg_predicted, bucket.accuracy, bucket.predictions))
        
        return curve
    
    def get_calibration_stats(self) -> Dict[str, any]:
        """
        Get comprehensive calibration statistics.
        
        Returns:
            Dictionary with calibration metrics
        """
        total_predictions = sum(b.predictions for b in self.buckets)
        total_correct = sum(b.correct for b in self.buckets)
        
        # Get per-bucket stats
        bucket_stats = []
        for i, bucket in enumerate(self.buckets):
            if bucket.predictions > 0:
                bucket_stats.append({
                    "bucket": i,
                    "confidence_range": f"{bucket.min_confidence:.2f}-{bucket.max_confidence:.2f}",
                    "predictions": bucket.predictions,
                    "accuracy": bucket.accuracy,
                    "calibration_error": bucket.calibration_error
                })
        
        # Get per-label stats
        label_stats = {}
        for label, label_buckets in self.label_buckets.items():
            label_total = sum(b.predictions for b in label_buckets)
            label_correct = sum(b.correct for b in label_buckets)
            
            if label_total > 0:
                label_stats[label] = {
                    "predictions": label_total,
                    "accuracy": label_correct / label_total
                }
        
        return {
            "total_predictions": total_predictions,
            "overall_accuracy": total_correct / total_predictions if total_predictions > 0 else 0.0,
            "expected_calibration_error": self.get_expected_calibration_error(),
            "num_buckets": self.num_buckets,
            "history_size": len(self.history),
            "bucket_stats": bucket_stats,
            "label_stats": label_stats
        }
    
    def _get_bucket_index(self, confidence: float) -> int:
        """Get bucket index for a confidence value."""
        # Clamp confidence to [0, 1)
        confidence = max(0.0, min(0.999, confidence))
        return int(confidence * self.num_buckets)
    
    def reset(self):
        """Reset all calibration data."""
        for bucket in self.buckets:
            bucket.predictions = 0
            bucket.correct = 0
        
        self.history.clear()
        self.label_buckets.clear()
        
        logger.info("Confidence calibrator reset")


class CalibrationManager:
    """
    High-level manager for confidence calibration.
    
    This provides a convenient interface for:
    - Recording predictions and outcomes
    - Calibrating new predictions
    - Monitoring calibration quality
    """
    
    def __init__(self, calibrator: Optional[ConfidenceCalibrator] = None):
        """
        Initialize calibration manager.
        
        Args:
            calibrator: Optional calibrator instance (creates default if None)
        """
        self.calibrator = calibrator or ConfidenceCalibrator()
        self.enabled = True
    
    def record_and_calibrate(
        self,
        raw_confidence: float,
        classification_label: str,
        actual_correct: Optional[bool] = None
    ) -> float:
        """
        Record a prediction and return calibrated confidence.
        
        Args:
            raw_confidence: Raw AI confidence
            classification_label: Classification label
            actual_correct: Whether prediction was correct (if known)
            
        Returns:
            Calibrated confidence
        """
        # Record if we know the outcome
        if actual_correct is not None:
            self.calibrator.record_prediction(
                predicted_confidence=raw_confidence,
                actual_correct=actual_correct,
                classification_label=classification_label
            )
        
        # Calibrate and return
        if self.enabled:
            return self.calibrator.calibrate(raw_confidence, classification_label)
        else:
            return raw_confidence
    
    def get_quality_report(self) -> Dict[str, any]:
        """
        Get calibration quality report.
        
        Returns:
            Dictionary with quality metrics and recommendations
        """
        stats = self.calibrator.get_calibration_stats()
        ece = stats['expected_calibration_error']
        
        # Determine quality level
        if ece < 0.05:
            quality = "excellent"
            recommendation = "Calibration is excellent, no action needed"
        elif ece < 0.10:
            quality = "good"
            recommendation = "Calibration is good, continue monitoring"
        elif ece < 0.15:
            quality = "fair"
            recommendation = "Consider collecting more calibration data"
        else:
            quality = "poor"
            recommendation = "Calibration needs improvement, collect more data"
        
        return {
            "quality": quality,
            "expected_calibration_error": ece,
            "total_predictions": stats['total_predictions'],
            "overall_accuracy": stats['overall_accuracy'],
            "recommendation": recommendation,
            "detailed_stats": stats
        }


# Global calibration manager instance
_calibration_manager: Optional[CalibrationManager] = None


def get_calibration_manager() -> CalibrationManager:
    """Get global calibration manager instance."""
    global _calibration_manager
    
    if _calibration_manager is None:
        _calibration_manager = CalibrationManager()
    
    return _calibration_manager


def reset_calibration():
    """Reset global calibration manager."""
    global _calibration_manager
    
    if _calibration_manager:
        _calibration_manager.calibrator.reset()
