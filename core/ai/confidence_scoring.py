"""
AI Transformation Confidence Scoring Module

Provides confidence scoring and quality assessment for AI-generated transformations.
Enables human-in-the-loop feedback and continuous improvement of AI outputs.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from core.logging import get_logger, LogCategory

logger = get_logger(__name__, category=LogCategory.AI)


class TransformationStatus(Enum):
    """Status of an AI transformation."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    IN_PROGRESS = "in_progress"


class ConfidenceLevel(Enum):
    """Confidence level categories."""
    VERY_HIGH = "very_high"  # >= 0.9
    HIGH = "high"  # >= 0.8
    MEDIUM = "medium"  # >= 0.6
    LOW = "low"  # >= 0.4
    VERY_LOW = "very_low"  # < 0.4


@dataclass
class ConfidenceMetrics:
    """
    Detailed confidence metrics for a transformation.
    
    Attributes:
        overall_score: Overall confidence (0.0 to 1.0)
        structural_accuracy: Code structure correctness (0.0 to 1.0)
        semantic_preservation: Intent preservation (0.0 to 1.0)
        idiom_quality: Target framework idiom usage (0.0 to 1.0)
        completeness: Feature completeness (0.0 to 1.0)
        reasoning: AI reasoning explanation
    """
    overall_score: float
    structural_accuracy: float = 0.0
    semantic_preservation: float = 0.0
    idiom_quality: float = 0.0
    completeness: float = 1.0
    reasoning: str = ""
    factors: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level category."""
        if self.overall_score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif self.overall_score >= 0.8:
            return ConfidenceLevel.HIGH
        elif self.overall_score >= 0.6:
            return ConfidenceLevel.MEDIUM
        elif self.overall_score >= 0.4:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    @property
    def requires_review(self) -> bool:
        """Determine if human review is required."""
        return self.overall_score < 0.8 or min(
            self.structural_accuracy,
            self.semantic_preservation,
            self.idiom_quality
        ) < 0.7


@dataclass
class TransformationReview:
    """
    Human review feedback for a transformation.
    
    Attributes:
        transformation_id: UUID of transformation
        feedback_type: accept | reject | modify
        actual_quality: Assessed quality (0.0 to 1.0)
        reviewer_notes: Free-form feedback
        reviewed_by: Reviewer identifier
    """
    transformation_id: uuid.UUID
    feedback_type: str  # accept | reject | modify
    actual_quality: float
    reviewer_notes: str = ""
    reviewed_by: str = "unknown"
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)


class ConfidenceScorer:
    """
    Calculates confidence scores for AI transformations.
    
    Uses multiple factors including:
    - Structural analysis (syntax validity, completeness)
    - Semantic analysis (intent preservation, logic equivalence)
    - Idiom analysis (framework best practices)
    - Historical performance (past accuracy for similar transformations)
    """
    
    def __init__(self):
        self.historical_adjustments: Dict[str, float] = {}
    
    def score_transformation(
        self,
        source_code: str,
        target_code: str,
        source_framework: str,
        target_framework: str,
        ai_raw_confidence: Optional[float] = None,
    ) -> ConfidenceMetrics:
        """
        Calculate comprehensive confidence score for a transformation.
        
        Args:
            source_code: Original source code
            target_code: Generated target code
            source_framework: Source framework name
            target_framework: Target framework name
            ai_raw_confidence: Optional raw confidence from AI model
            
        Returns:
            ConfidenceMetrics with detailed scoring
        """
        logger.info(
            f"Scoring transformation: {source_framework} → {target_framework}",
            extra={"source_lines": len(source_code.split('\n')),
                   "target_lines": len(target_code.split('\n'))}
        )
        
        # Score individual dimensions
        structural = self._score_structural(source_code, target_code)
        semantic = self._score_semantic(source_code, target_code, source_framework, target_framework)
        idiom = self._score_idiom(target_code, target_framework)
        completeness = self._score_completeness(source_code, target_code)
        
        # Calculate overall score (weighted average)
        overall = (
            structural * 0.3 +
            semantic * 0.35 +
            idiom * 0.25 +
            completeness * 0.10
        )
        
        # Apply historical adjustment if available
        framework_pair = f"{source_framework}->{target_framework}"
        if framework_pair in self.historical_adjustments:
            adjustment = self.historical_adjustments[framework_pair]
            overall = overall * adjustment
            logger.debug(f"Applied historical adjustment: {adjustment:.2f}")
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            overall, structural, semantic, idiom, completeness
        )
        
        return ConfidenceMetrics(
            overall_score=overall,
            structural_accuracy=structural,
            semantic_preservation=semantic,
            idiom_quality=idiom,
            completeness=completeness,
            reasoning=reasoning,
            factors={
                "framework_pair": framework_pair,
                "source_length": len(source_code),
                "target_length": len(target_code),
                "ai_raw_confidence": ai_raw_confidence,
            }
        )
    
    def _score_structural(self, source: str, target: str) -> float:
        """Score structural/syntactic correctness."""
        score = 0.5  # Base score
        
        # Check basic syntax validity
        if target and not target.isspace():
            score += 0.2
        
        # Check length reasonableness (target shouldn't be drastically different)
        source_lines = len(source.split('\n'))
        target_lines = len(target.split('\n'))
        if source_lines > 0:
            ratio = target_lines / source_lines
            if 0.5 <= ratio <= 2.0:
                score += 0.2
            elif 0.3 <= ratio <= 3.0:
                score += 0.1
        
        # Check for common structural elements
        if 'def ' in target or 'class ' in target or 'function' in target:
            score += 0.1
        
        return min(1.0, score)
    
    def _score_semantic(
        self,
        source: str,
        target: str,
        source_framework: str,
        target_framework: str
    ) -> float:
        """Score semantic preservation (intent)."""
        score = 0.4  # Base score
        
        # Extract key actions/verbs from both
        source_actions = self._extract_actions(source, source_framework)
        target_actions = self._extract_actions(target, target_framework)
        
        # Check action preservation
        if source_actions and target_actions:
            common = set(source_actions) & set(target_actions)
            if source_actions:
                preservation_ratio = len(common) / len(source_actions)
                score += preservation_ratio * 0.4
        
        # Check for essential keywords
        essential_preserved = 0
        essential_keywords = ['click', 'type', 'wait', 'assert', 'verify', 'get', 'post']
        for keyword in essential_keywords:
            if keyword.lower() in source.lower() and keyword.lower() in target.lower():
                essential_preserved += 1
        
        if essential_preserved > 0:
            score += min(0.2, essential_preserved * 0.05)
        
        return min(1.0, score)
    
    def _score_idiom(self, target: str, target_framework: str) -> float:
        """Score idiomatic usage of target framework."""
        score = 0.5  # Base score
        
        # Framework-specific idiom checks
        framework_patterns = {
            'robot': ['${', '}', 'Should Be Equal', 'Click Element'],
            'playwright': ['page.', 'expect(', '.locator(', 'async '],
            'pytest': ['def test_', 'assert ', 'pytest.', '@pytest.'],
            'selenium': ['driver.', 'find_element', 'WebDriverWait'],
        }
        
        patterns = framework_patterns.get(target_framework.lower(), [])
        matches = sum(1 for pattern in patterns if pattern in target)
        
        if patterns:
            score += min(0.5, (matches / len(patterns)) * 0.5)
        
        return min(1.0, score)
    
    def _score_completeness(self, source: str, target: str) -> float:
        """Score completeness of transformation."""
        score = 0.6  # Base score
        
        # Check if target is not empty
        if target and len(target.strip()) > 20:
            score += 0.2
        
        # Check relative completeness
        source_lines = len([l for l in source.split('\n') if l.strip()])
        target_lines = len([l for l in target.split('\n') if l.strip()])
        
        if source_lines > 0:
            if target_lines >= source_lines * 0.7:
                score += 0.2
        
        return min(1.0, score)
    
    def _extract_actions(self, code: str, framework: str) -> List[str]:
        """Extract action verbs from code."""
        actions = []
        action_keywords = [
            'click', 'type', 'send', 'press', 'wait', 'navigate', 'goto',
            'assert', 'verify', 'check', 'expect', 'should', 'get', 'post',
            'put', 'delete', 'select', 'fill', 'submit'
        ]
        
        code_lower = code.lower()
        for action in action_keywords:
            if action in code_lower:
                actions.append(action)
        
        return actions
    
    def _generate_reasoning(
        self,
        overall: float,
        structural: float,
        semantic: float,
        idiom: float,
        completeness: float
    ) -> str:
        """Generate human-readable reasoning for the score."""
        reasons = []
        
        if overall >= 0.9:
            reasons.append("Excellent transformation quality")
        elif overall >= 0.8:
            reasons.append("High quality transformation")
        elif overall >= 0.6:
            reasons.append("Acceptable transformation with room for improvement")
        else:
            reasons.append("Low confidence - manual review strongly recommended")
        
        # Identify weak areas
        if structural < 0.7:
            reasons.append(f"Structural accuracy needs attention ({structural:.2f})")
        if semantic < 0.7:
            reasons.append(f"Semantic preservation could be improved ({semantic:.2f})")
        if idiom < 0.7:
            reasons.append(f"Framework idioms could be more idiomatic ({idiom:.2f})")
        if completeness < 0.8:
            reasons.append(f"Completeness check flagged ({completeness:.2f})")
        
        return " | ".join(reasons)
    
    def update_from_feedback(self, review: TransformationReview, metrics: ConfidenceMetrics):
        """
        Update historical adjustments based on human feedback.
        
        This enables continuous improvement of confidence scoring.
        """
        framework_pair = metrics.factors.get('framework_pair')
        if not framework_pair:
            return
        
        # Calculate adjustment factor
        predicted = metrics.overall_score
        actual = review.actual_quality
        
        # Simple exponential smoothing
        alpha = 0.1  # Learning rate
        current_adjustment = self.historical_adjustments.get(framework_pair, 1.0)
        
        if predicted > 0:
            new_adjustment = current_adjustment * (1 - alpha) + (actual / predicted) * alpha
            self.historical_adjustments[framework_pair] = new_adjustment
            
            logger.info(
                f"Updated historical adjustment for {framework_pair}: {new_adjustment:.3f}",
                extra={
                    "predicted": predicted,
                    "actual": actual,
                    "feedback_type": review.feedback_type
                }
            )


def evaluate_transformation_quality(
    source_code: str,
    target_code: str,
    source_framework: str,
    target_framework: str,
) -> ConfidenceMetrics:
    """
    Convenience function to evaluate transformation quality.
    
    Args:
        source_code: Original source code
        target_code: Generated target code
        source_framework: Source framework name
        target_framework: Target framework name
        
    Returns:
        ConfidenceMetrics with detailed scoring
        
    Example:
        >>> metrics = evaluate_transformation_quality(
        ...     selenium_code,
        ...     playwright_code,
        ...     "selenium",
        ...     "playwright"
        ... )
        >>> print(f"Confidence: {metrics.overall_score:.2f}")
        >>> print(f"Requires review: {metrics.requires_review}")
    """
    scorer = ConfidenceScorer()
    return scorer.score_transformation(
        source_code=source_code,
        target_code=target_code,
        source_framework=source_framework,
        target_framework=target_framework
    )
