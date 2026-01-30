"""
Confidence Models

Data models for confidence scoring breakdown.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ConfidenceComponents:
    """
    Weighted components that make up the final confidence score.
    
    Weights (must sum to 1.0):
    - rule_score: 0.35 (rule match strength)
    - signal_score: 0.25 (signal quality)
    - history_score: 0.20 (historical consistency)
    - log_score: 0.20 (log completeness)
    - ai_score: bonus adjustment (can push to 1.0)
    """
    
    # Component weights
    RULE_WEIGHT: float = 0.35
    SIGNAL_WEIGHT: float = 0.25
    HISTORY_WEIGHT: float = 0.20
    LOG_WEIGHT: float = 0.20
    
    @classmethod
    def validate_weights(cls) -> bool:
        """Validate that base weights sum to 1.0"""
        total = cls.RULE_WEIGHT + cls.SIGNAL_WEIGHT + cls.HISTORY_WEIGHT + cls.LOG_WEIGHT
        return abs(total - 1.0) < 0.001


@dataclass
class ConfidenceBreakdown:
    """
    Detailed breakdown of confidence score calculation.
    
    Each score is 0.0-1.0 representing the component's contribution.
    AI score is a bonus that can push final confidence up but never override base classification.
    """
    
    rule_score: float = 0.0          # Strength of matched rules
    signal_score: float = 0.0        # Quality of extracted signals
    history_score: float = 0.0       # Historical consistency
    log_score: float = 0.0           # Log completeness
    ai_score: float = 0.0            # AI adjustment (optional bonus)
    
    # Metadata for explainability
    rule_matches: int = 0
    has_stacktrace: bool = False
    has_code_reference: bool = False
    historical_occurrences: int = 0
    has_application_logs: bool = False
    
    # Explanation strings
    explanation: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate scores are in valid range"""
        for score_name in ['rule_score', 'signal_score', 'history_score', 'log_score', 'ai_score']:
            score = getattr(self, score_name)
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"{score_name} must be between 0.0 and 1.0, got {score}")
    
    def calculate_base_confidence(self) -> float:
        """
        Calculate base confidence (without AI) using weighted components.
        
        Returns:
            Base confidence score (0.0-1.0)
        """
        base = (
            ConfidenceComponents.RULE_WEIGHT * self.rule_score +
            ConfidenceComponents.SIGNAL_WEIGHT * self.signal_score +
            ConfidenceComponents.HISTORY_WEIGHT * self.history_score +
            ConfidenceComponents.LOG_WEIGHT * self.log_score
        )
        return min(base, 1.0)
    
    def calculate_final_confidence(self) -> float:
        """
        Calculate final confidence including AI adjustment.
        
        AI can boost confidence but never exceed 1.0.
        
        Returns:
            Final confidence score (0.0-1.0)
        """
        base = self.calculate_base_confidence()
        final = base + self.ai_score
        return min(final, 1.0)
    
    def get_explanation(self) -> str:
        """
        Generate human-readable explanation of confidence score.
        
        Returns:
            Multi-line explanation string
        """
        lines = [
            f"Confidence Breakdown (Final: {self.calculate_final_confidence():.2f}):",
            f"  • Rule Match: {self.rule_score:.2f} (weight: {ConfidenceComponents.RULE_WEIGHT})",
            f"  • Signal Quality: {self.signal_score:.2f} (weight: {ConfidenceComponents.SIGNAL_WEIGHT})",
            f"  • History: {self.history_score:.2f} (weight: {ConfidenceComponents.HISTORY_WEIGHT})",
            f"  • Log Completeness: {self.log_score:.2f} (weight: {ConfidenceComponents.LOG_WEIGHT})",
        ]
        
        if self.ai_score > 0:
            lines.append(f"  • AI Adjustment: +{self.ai_score:.2f}")
        
        # Add context
        lines.append("\nDetails:")
        if self.rule_matches > 0:
            lines.append(f"  • {self.rule_matches} rule(s) matched")
        if self.has_stacktrace:
            lines.append("  • Stacktrace available")
        if self.has_code_reference:
            lines.append("  • Code reference resolved")
        if self.historical_occurrences > 0:
            lines.append(f"  • Seen {self.historical_occurrences} time(s) before")
        if self.has_application_logs:
            lines.append("  • Application logs available")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'base_confidence': self.calculate_base_confidence(),
            'final_confidence': self.calculate_final_confidence(),
            'components': {
                'rule_score': self.rule_score,
                'signal_score': self.signal_score,
                'history_score': self.history_score,
                'log_score': self.log_score,
                'ai_score': self.ai_score
            },
            'metadata': {
                'rule_matches': self.rule_matches,
                'has_stacktrace': self.has_stacktrace,
                'has_code_reference': self.has_code_reference,
                'historical_occurrences': self.historical_occurrences,
                'has_application_logs': self.has_application_logs
            },
            'explanation': self.explanation
        }


@dataclass
class ConfidenceThresholds:
    """
    Thresholds for confidence-based decisions.
    
    Used for CI/CD automation and decision-making.
    """
    
    HIGH_CONFIDENCE: float = 0.85    # Very confident classification
    MEDIUM_CONFIDENCE: float = 0.65  # Moderately confident
    LOW_CONFIDENCE: float = 0.40     # Low confidence - needs review
    
    @classmethod
    def get_confidence_level(cls, confidence: float) -> str:
        """
        Get confidence level string.
        
        Args:
            confidence: Confidence score (0.0-1.0)
            
        Returns:
            "HIGH", "MEDIUM", or "LOW"
        """
        if confidence >= cls.HIGH_CONFIDENCE:
            return "HIGH"
        elif confidence >= cls.MEDIUM_CONFIDENCE:
            return "MEDIUM"
        else:
            return "LOW"
    
    @classmethod
    def should_fail_ci(cls, confidence: float, failure_type: str) -> bool:
        """
        Determine if CI should fail based on confidence and failure type.
        
        Args:
            confidence: Confidence score
            failure_type: Type of failure
            
        Returns:
            True if CI should fail
        """
        if failure_type == "PRODUCT_DEFECT" and confidence >= cls.HIGH_CONFIDENCE:
            return True
        return False
    
    @classmethod
    def should_annotate_pr(cls, confidence: float, failure_type: str) -> bool:
        """
        Determine if PR should be annotated.
        
        Args:
            confidence: Confidence score
            failure_type: Type of failure
            
        Returns:
            True if PR should be annotated
        """
        # Annotate if medium+ confidence for automation/product defects
        if failure_type in ["AUTOMATION_DEFECT", "PRODUCT_DEFECT"]:
            return confidence >= cls.MEDIUM_CONFIDENCE
        return False
