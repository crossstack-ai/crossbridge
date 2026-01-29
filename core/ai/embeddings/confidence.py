"""
Confidence Calibration for Similarity Results

Every similarity result must have a trust score (0.0 – 1.0).
Never return raw similarity without confidence assessment.

Confidence inputs:
- Similarity score
- Number of historical samples
- Consistency over time
- Cross-signal agreement (text + AST + graph)
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.AI)


class ConfidenceLevel(Enum):
    """Confidence level categories for UX"""
    HIGH = "high"  # >= 0.8
    MEDIUM = "medium"  # 0.6 - 0.8
    LOW = "low"  # < 0.6


@dataclass
class SignalAgreement:
    """
    Agreement between different similarity signals.
    
    Signals:
    - text: Semantic similarity from embeddings
    - ast: Structural similarity from AST
    - graph: Relationship similarity from graph
    """
    text_score: float
    ast_score: Optional[float] = None
    graph_score: Optional[float] = None
    
    def agreement_score(self) -> float:
        """
        Calculate agreement between available signals.
        
        Agreement score:
        - 1.0: All available signals agree (within 0.1)
        - 0.7: Two signals agree
        - 0.4: Only one signal available
        - 0.0: Signals disagree significantly
        """
        available_scores = [s for s in [self.text_score, self.ast_score, self.graph_score] if s is not None]
        
        if len(available_scores) == 1:
            return 0.4  # Only one signal
        
        if len(available_scores) == 2:
            diff = abs(available_scores[0] - available_scores[1])
            if diff < 0.1:
                return 0.9  # Strong agreement
            elif diff < 0.2:
                return 0.7  # Moderate agreement
            else:
                return 0.5  # Weak agreement
        
        if len(available_scores) == 3:
            # Check if all three agree (within 0.1)
            max_score = max(available_scores)
            min_score = min(available_scores)
            if max_score - min_score < 0.1:
                return 1.0  # All agree strongly
            elif max_score - min_score < 0.2:
                return 0.8  # All agree moderately
            else:
                return 0.6  # Some disagreement
        
        return 0.0


@dataclass
class ConfidenceFactors:
    """Factors contributing to confidence score"""
    similarity_score: float
    sample_count: int = 1
    agreement_score: float = 0.4
    consistency_score: float = 1.0  # Future: track score variance over time
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dict for serialization"""
        return {
            "similarity_score": round(self.similarity_score, 3),
            "sample_count": self.sample_count,
            "agreement_score": round(self.agreement_score, 3),
            "consistency_score": round(self.consistency_score, 3)
        }


@dataclass
class CalibratedResult:
    """
    Similarity result with calibrated confidence.
    
    MANDATORY: Never return raw similarity without confidence.
    """
    entity_id: str
    similarity_score: float
    confidence_score: float
    confidence_level: ConfidenceLevel
    factors: ConfidenceFactors
    reasons: List[str]
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dict for API responses"""
        return {
            "entity_id": self.entity_id,
            "similarity_score": round(self.similarity_score, 3),
            "confidence_score": round(self.confidence_score, 3),
            "confidence_level": self.confidence_level.value,
            "factors": self.factors.to_dict(),
            "reasons": self.reasons,
            "metadata": self.metadata or {}
        }


class ConfidenceCalibrator:
    """
    Calibrates similarity scores with confidence assessment.
    
    Phase-1 Formula:
    confidence = min(1.0,
        similarity *
        log1p(sample_count) / log1p(30) *
        agreement_score *
        consistency_score
    )
    
    Phase-2: Adaptive calibration based on historical accuracy
    """
    
    def __init__(
        self,
        sample_threshold: int = 30,
        min_confidence: float = 0.1,
        enable_agreement: bool = True
    ):
        """
        Initialize confidence calibrator
        
        Args:
            sample_threshold: Sample count for full confidence (default: 30)
            min_confidence: Minimum confidence to return (default: 0.1)
            enable_agreement: Enable cross-signal agreement (default: True)
        """
        self.sample_threshold = sample_threshold
        self.min_confidence = min_confidence
        self.enable_agreement = enable_agreement
        
        logger.info(
            "Confidence calibrator initialized",
            sample_threshold=sample_threshold,
            min_confidence=min_confidence
        )
    
    def calculate_confidence(
        self,
        similarity_score: float,
        sample_count: int = 1,
        agreement: Optional[SignalAgreement] = None,
        consistency_score: float = 1.0
    ) -> float:
        """
        Calculate calibrated confidence score.
        
        Args:
            similarity_score: Raw similarity score (0.0 - 1.0)
            sample_count: Number of historical samples for this entity
            agreement: Cross-signal agreement (optional)
            consistency_score: Score consistency over time (0.0 - 1.0)
        
        Returns:
            Calibrated confidence (0.0 - 1.0)
        """
        # Base: similarity score
        confidence = similarity_score
        
        # Factor 1: Sample count (more samples = more confidence)
        # log1p(sample_count) / log1p(threshold)
        # Examples:
        # - 1 sample: log1p(1)/log1p(30) = 0.693/3.434 = 0.20
        # - 10 samples: log1p(10)/log1p(30) = 2.398/3.434 = 0.70
        # - 30 samples: log1p(30)/log1p(30) = 1.00
        sample_factor = math.log1p(sample_count) / math.log1p(self.sample_threshold)
        confidence *= sample_factor
        
        # Factor 2: Cross-signal agreement
        if self.enable_agreement and agreement:
            agreement_factor = agreement.agreement_score()
            confidence *= agreement_factor
        
        # Factor 3: Consistency over time
        confidence *= consistency_score
        
        # Clamp to [0, 1]
        confidence = min(1.0, max(0.0, confidence))
        
        return confidence
    
    def calibrate_result(
        self,
        entity_id: str,
        similarity_score: float,
        sample_count: int = 1,
        agreement: Optional[SignalAgreement] = None,
        consistency_score: float = 1.0,
        metadata: Optional[Dict] = None
    ) -> CalibratedResult:
        """
        Calibrate a single similarity result.
        
        Args:
            entity_id: Entity identifier
            similarity_score: Raw similarity score
            sample_count: Historical sample count
            agreement: Cross-signal agreement
            consistency_score: Score consistency
            metadata: Additional metadata
        
        Returns:
            Calibrated result with confidence
        """
        # Calculate confidence
        confidence = self.calculate_confidence(
            similarity_score,
            sample_count,
            agreement,
            consistency_score
        )
        
        # Determine confidence level
        if confidence >= 0.8:
            level = ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW
        
        # Build confidence factors
        agreement_score = agreement.agreement_score() if agreement else 0.4
        factors = ConfidenceFactors(
            similarity_score=similarity_score,
            sample_count=sample_count,
            agreement_score=agreement_score,
            consistency_score=consistency_score
        )
        
        # Generate reasons
        reasons = self._generate_reasons(
            similarity_score,
            confidence,
            sample_count,
            agreement,
            level
        )
        
        return CalibratedResult(
            entity_id=entity_id,
            similarity_score=similarity_score,
            confidence_score=confidence,
            confidence_level=level,
            factors=factors,
            reasons=reasons,
            metadata=metadata
        )
    
    def calibrate_batch(
        self,
        results: List[Tuple[str, float, Optional[Dict]]],
        sample_counts: Optional[Dict[str, int]] = None,
        agreements: Optional[Dict[str, SignalAgreement]] = None
    ) -> List[CalibratedResult]:
        """
        Calibrate a batch of results.
        
        Args:
            results: List of (entity_id, similarity_score, metadata)
            sample_counts: Map of entity_id -> sample count
            agreements: Map of entity_id -> signal agreement
        
        Returns:
            List of calibrated results
        """
        calibrated = []
        
        for entity_id, similarity_score, metadata in results:
            sample_count = sample_counts.get(entity_id, 1) if sample_counts else 1
            agreement = agreements.get(entity_id) if agreements else None
            
            result = self.calibrate_result(
                entity_id,
                similarity_score,
                sample_count,
                agreement,
                metadata=metadata
            )
            
            # Filter by minimum confidence
            if result.confidence_score >= self.min_confidence:
                calibrated.append(result)
        
        # Sort by confidence (then similarity)
        calibrated.sort(
            key=lambda r: (r.confidence_score, r.similarity_score),
            reverse=True
        )
        
        return calibrated
    
    def _generate_reasons(
        self,
        similarity_score: float,
        confidence_score: float,
        sample_count: int,
        agreement: Optional[SignalAgreement],
        level: ConfidenceLevel
    ) -> List[str]:
        """Generate human-readable confidence reasons"""
        reasons = []
        
        # Similarity
        if similarity_score >= 0.9:
            reasons.append("Very high semantic similarity")
        elif similarity_score >= 0.7:
            reasons.append("High semantic similarity")
        elif similarity_score >= 0.5:
            reasons.append("Moderate semantic similarity")
        else:
            reasons.append("Low semantic similarity")
        
        # Sample count
        if sample_count >= 30:
            reasons.append("Strong historical evidence (30+ samples)")
        elif sample_count >= 10:
            reasons.append("Good historical evidence (10+ samples)")
        elif sample_count >= 5:
            reasons.append("Limited historical evidence (5+ samples)")
        else:
            reasons.append("Minimal historical evidence (< 5 samples)")
        
        # Agreement
        if agreement:
            agreement_score = agreement.agreement_score()
            if agreement_score >= 0.9:
                reasons.append("Strong agreement across all signals")
            elif agreement_score >= 0.7:
                reasons.append("Good agreement across signals")
            elif agreement_score >= 0.5:
                reasons.append("Moderate agreement across signals")
            else:
                reasons.append("Low agreement across signals")
        
        # Overall confidence
        if level == ConfidenceLevel.HIGH:
            reasons.append("✅ High confidence result")
        elif level == ConfidenceLevel.MEDIUM:
            reasons.append("⚠️ Medium confidence result")
        else:
            reasons.append("⚠️ Low confidence - verify manually")
        
        return reasons


def create_calibrator(
    sample_threshold: int = 30,
    min_confidence: float = 0.1
) -> ConfidenceCalibrator:
    """Factory function to create confidence calibrator"""
    return ConfidenceCalibrator(
        sample_threshold=sample_threshold,
        min_confidence=min_confidence
    )


def calibrate_with_multi_signal(
    entity_id: str,
    text_score: float,
    ast_score: Optional[float] = None,
    graph_score: Optional[float] = None,
    sample_count: int = 1,
    calibrator: Optional[ConfidenceCalibrator] = None
) -> CalibratedResult:
    """
    Convenience function for multi-signal calibration.
    
    Args:
        entity_id: Entity identifier
        text_score: Semantic similarity score
        ast_score: AST similarity score (optional)
        graph_score: Graph similarity score (optional)
        sample_count: Historical sample count
        calibrator: Calibrator instance (creates default if None)
    
    Returns:
        Calibrated result
    """
    if calibrator is None:
        calibrator = create_calibrator()
    
    # Create signal agreement
    agreement = SignalAgreement(
        text_score=text_score,
        ast_score=ast_score,
        graph_score=graph_score
    )
    
    return calibrator.calibrate_result(
        entity_id=entity_id,
        similarity_score=text_score,  # Use text score as primary
        sample_count=sample_count,
        agreement=agreement
    )
