"""
AI Transformation Validation

Ensures AI-generated/modified outputs are:
- Auditable
- Reviewable by humans
- Reversible
- Confidence-scored

Never auto-merge AI output silently.
"""

import difflib
import hashlib
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from core.logging import get_logger, LogCategory
from cli.errors import CrossBridgeError

logger = get_logger(__name__, category=LogCategory.AI)


class TransformationStatus(Enum):
    """Status of an AI transformation"""
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"
    APPLIED = "applied"


class ConfidenceLevel(Enum):
    """Confidence level classification"""
    HIGH = "high"        # 0.8 - 1.0
    MEDIUM = "medium"    # 0.5 - 0.79
    LOW = "low"          # < 0.5


@dataclass
class ConfidenceSignals:
    """Input signals for confidence computation"""
    model_confidence: float = 1.0
    similarity_to_existing: float = 1.0
    rule_violations: int = 0
    historical_acceptance_rate: float = 1.0
    diff_size: int = 0
    syntax_valid: bool = True
    test_coverage_maintained: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'model_confidence': self.model_confidence,
            'similarity_to_existing': self.similarity_to_existing,
            'rule_violations': self.rule_violations,
            'historical_acceptance_rate': self.historical_acceptance_rate,
            'diff_size': self.diff_size,
            'syntax_valid': self.syntax_valid,
            'test_coverage_maintained': self.test_coverage_maintained
        }


@dataclass
class AITransformationReview:
    """Human review of AI transformation"""
    transformation_id: str
    reviewer: str
    decision: str  # approved | rejected
    comments: str = ""
    reviewed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'transformation_id': self.transformation_id,
            'reviewer': self.reviewer,
            'decision': self.decision,
            'comments': self.comments,
            'reviewed_at': self.reviewed_at.isoformat()
        }


@dataclass
class AITransformation:
    """
    AI-generated transformation with full audit trail
    
    Stores before/after snapshots, confidence scores,
    review status, and rollback capability.
    """
    id: str = field(default_factory=lambda: f"ai-{uuid.uuid4().hex[:12]}")
    
    # Transformation metadata
    operation: str = ""  # generate, modify, refactor, etc.
    artifact_type: str = ""  # test, code, config, mapping
    artifact_path: str = ""
    
    # Before/after snapshots
    before_snapshot: str = ""
    after_snapshot: str = ""
    diff: str = ""
    
    # Confidence and scoring
    confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    confidence_signals: Optional[ConfidenceSignals] = None
    
    # Review and approval
    status: TransformationStatus = TransformationStatus.PENDING_REVIEW
    requires_review: bool = True
    review: Optional[AITransformationReview] = None
    
    # Audit trail
    model_used: str = ""
    prompt_hash: str = ""
    actor: str = "crossbridge-ai"
    created_at: datetime = field(default_factory=datetime.utcnow)
    applied_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence"""
        return {
            'id': self.id,
            'operation': self.operation,
            'artifact_type': self.artifact_type,
            'artifact_path': self.artifact_path,
            'before_snapshot': self.before_snapshot,
            'after_snapshot': self.after_snapshot,
            'diff': self.diff,
            'confidence': self.confidence,
            'confidence_level': self.confidence_level.value,
            'confidence_signals': self.confidence_signals.to_dict() if self.confidence_signals else {},
            'status': self.status.value,
            'requires_review': self.requires_review,
            'review': self.review.to_dict() if self.review else None,
            'model_used': self.model_used,
            'prompt_hash': self.prompt_hash,
            'actor': self.actor,
            'created_at': self.created_at.isoformat(),
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'rolled_back_at': self.rolled_back_at.isoformat() if self.rolled_back_at else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AITransformation':
        """Create from dictionary"""
        transformation = cls(
            id=data.get('id', f"ai-{uuid.uuid4().hex[:12]}"),
            operation=data.get('operation', ''),
            artifact_type=data.get('artifact_type', ''),
            artifact_path=data.get('artifact_path', ''),
            before_snapshot=data.get('before_snapshot', ''),
            after_snapshot=data.get('after_snapshot', ''),
            diff=data.get('diff', ''),
            confidence=data.get('confidence', 0.0),
            confidence_level=ConfidenceLevel(data.get('confidence_level', 'low')),
            status=TransformationStatus(data.get('status', 'pending_review')),
            requires_review=data.get('requires_review', True),
            model_used=data.get('model_used', ''),
            prompt_hash=data.get('prompt_hash', ''),
            actor=data.get('actor', 'crossbridge-ai'),
            metadata=data.get('metadata', {})
        )
        
        # Parse timestamps
        if data.get('created_at'):
            transformation.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('applied_at'):
            transformation.applied_at = datetime.fromisoformat(data['applied_at'])
        if data.get('rolled_back_at'):
            transformation.rolled_back_at = datetime.fromisoformat(data['rolled_back_at'])
        
        # Parse confidence signals
        if data.get('confidence_signals'):
            transformation.confidence_signals = ConfidenceSignals(**data['confidence_signals'])
        
        # Parse review
        if data.get('review'):
            review_data = data['review']
            transformation.review = AITransformationReview(
                transformation_id=review_data['transformation_id'],
                reviewer=review_data['reviewer'],
                decision=review_data['decision'],
                comments=review_data.get('comments', ''),
                reviewed_at=datetime.fromisoformat(review_data['reviewed_at'])
            )
        
        return transformation


class AITransformationError(CrossBridgeError):
    """Error in AI transformation validation"""
    
    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CS-AI-TRANSFORM-001",
            suggestion=suggestion or "Check transformation status and review requirements"
        )


def compute_prompt_hash(prompt: str) -> str:
    """Compute hash of AI prompt for audit trail"""
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


def generate_diff(before: str, after: str, filename: str = "artifact") -> str:
    """
    Generate unified diff between before and after states
    
    Args:
        before: Before content
        after: After content
        filename: Artifact filename for diff header
        
    Returns:
        Unified diff string
    """
    diff_lines = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    
    return "".join(diff_lines)


def classify_confidence(score: float) -> ConfidenceLevel:
    """
    Classify numeric confidence into level
    
    Args:
        score: Confidence score (0.0 - 1.0)
        
    Returns:
        ConfidenceLevel
    """
    if score >= 0.8:
        return ConfidenceLevel.HIGH
    elif score >= 0.5:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW


def compute_confidence(signals: ConfidenceSignals) -> float:
    """
    Compute confidence score from multiple signals
    
    Confidence ≠ correctness
    Confidence = likelihood output is usable without edits
    
    Args:
        signals: Input signals for confidence computation
        
    Returns:
        Confidence score (0.0 - 1.0)
    """
    score = 1.0
    
    # Base model confidence
    score *= signals.model_confidence
    
    # Penalize large diffs (higher risk)
    if signals.diff_size > 100:
        score -= 0.3
    elif signals.diff_size > 50:
        score -= 0.2
    elif signals.diff_size > 20:
        score -= 0.1
    
    # Penalize rule violations
    if signals.rule_violations > 0:
        score -= min(0.3, signals.rule_violations * 0.1)
    
    # Penalize low similarity to existing code
    if signals.similarity_to_existing < 0.6:
        score -= 0.2
    elif signals.similarity_to_existing < 0.8:
        score -= 0.1
    
    # Consider historical acceptance
    if signals.historical_acceptance_rate < 0.5:
        score -= 0.2
    elif signals.historical_acceptance_rate < 0.7:
        score -= 0.1
    
    # Penalize invalid syntax
    if not signals.syntax_valid:
        score -= 0.4
    
    # Penalize coverage loss
    if not signals.test_coverage_maintained:
        score -= 0.2
    
    # Clamp to [0.0, 1.0]
    return max(0.0, min(score, 1.0))


def requires_human_review(confidence: float, threshold: float = 0.8) -> bool:
    """
    Determine if transformation requires human review
    
    Args:
        confidence: Confidence score
        threshold: Minimum confidence for auto-apply (default: 0.8)
        
    Returns:
        True if review required
    """
    return confidence < threshold
