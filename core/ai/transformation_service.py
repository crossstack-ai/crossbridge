"""
AI Transformation Service

Manages the complete lifecycle of AI transformations:
- Generation and confidence scoring
- Review and approval workflow
- Rollback and diff management
- Audit trail persistence
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from core.logging import get_logger, LogCategory
from core.ai.transformation_validation import (
    AITransformation,
    AITransformationReview,
    AITransformationError,
    ConfidenceSignals,
    TransformationStatus,
    ConfidenceLevel,
    compute_confidence,
    compute_prompt_hash,
    generate_diff,
    classify_confidence,
    requires_human_review
)

logger = get_logger(__name__, category=LogCategory.AI)


class AITransformationService:
    """
    Service for managing AI transformations
    
    Provides:
    - Transformation generation and validation
    - Confidence scoring
    - Human review integration
    - Rollback capabilities
    - Audit trail persistence
    """
    
    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        confidence_threshold: float = 0.8
    ):
        """
        Initialize transformation service
        
        Args:
            storage_dir: Directory for storing transformation records
            confidence_threshold: Minimum confidence for auto-apply
        """
        self.storage_dir = storage_dir or Path(".crossbridge/transformations")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.confidence_threshold = confidence_threshold
        self._transformations: Dict[str, AITransformation] = {}
        self._load_transformations()
        
        logger.info(f"AITransformationService initialized", 
                   storage_dir=str(self.storage_dir),
                   confidence_threshold=confidence_threshold)
    
    def _load_transformations(self) -> None:
        """Load existing transformations from storage"""
        try:
            for file in self.storage_dir.glob("*.json"):
                with open(file, 'r') as f:
                    data = json.load(f)
                    transformation = AITransformation.from_dict(data)
                    self._transformations[transformation.id] = transformation
            
            logger.debug(f"Loaded {len(self._transformations)} transformations")
        except Exception as e:
            logger.error(f"Failed to load transformations: {e}", exc_info=True)
    
    def _save_transformation(self, transformation: AITransformation) -> None:
        """Save transformation to storage"""
        try:
            file_path = self.storage_dir / f"{transformation.id}.json"
            with open(file_path, 'w') as f:
                json.dump(transformation.to_dict(), f, indent=2)
            
            logger.debug(f"Saved transformation {transformation.id}")
        except Exception as e:
            logger.error(f"Failed to save transformation: {e}", exc_info=True)
            raise AITransformationError(
                f"Failed to persist transformation: {e}",
                suggestion="Check file permissions and disk space"
            )
    
    def generate(
        self,
        operation: str,
        artifact_type: str,
        artifact_path: str,
        before_content: str,
        after_content: str,
        model: str,
        prompt: str,
        signals: Optional[ConfidenceSignals] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AITransformation:
        """
        Generate a new AI transformation
        
        Args:
            operation: Type of operation (generate, modify, refactor, etc.)
            artifact_type: Type of artifact (test, code, config, etc.)
            artifact_path: Path to artifact
            before_content: Original content (empty for new artifacts)
            after_content: AI-generated content
            model: AI model used
            prompt: Prompt used to generate output
            signals: Confidence signals (auto-computed if not provided)
            metadata: Additional metadata
            
        Returns:
            AITransformation instance
        """
        logger.info(f"Generating AI transformation", 
                   operation=operation,
                   artifact_type=artifact_type,
                   artifact_path=artifact_path)
        
        # Create transformation
        transformation = AITransformation(
            operation=operation,
            artifact_type=artifact_type,
            artifact_path=artifact_path,
            before_snapshot=before_content,
            after_snapshot=after_content,
            model_used=model,
            prompt_hash=compute_prompt_hash(prompt),
            metadata=metadata or {}
        )
        
        # Generate diff
        transformation.diff = generate_diff(
            before_content,
            after_content,
            artifact_path
        )
        
        # Compute confidence if not provided
        if signals is None:
            signals = ConfidenceSignals(
                diff_size=len(transformation.diff.splitlines()),
                model_confidence=0.85  # Default for production models
            )
        
        transformation.confidence_signals = signals
        transformation.confidence = compute_confidence(signals)
        transformation.confidence_level = classify_confidence(transformation.confidence)
        
        # Determine if review required
        transformation.requires_review = requires_human_review(
            transformation.confidence,
            self.confidence_threshold
        )
        
        # Store transformation
        self._transformations[transformation.id] = transformation
        self._save_transformation(transformation)
        
        logger.success(
            f"Generated transformation {transformation.id}",
            confidence=transformation.confidence,
            confidence_level=transformation.confidence_level.value,
            requires_review=transformation.requires_review
        )
        
        return transformation
    
    def get_transformation(self, transformation_id: str) -> Optional[AITransformation]:
        """Get transformation by ID"""
        return self._transformations.get(transformation_id)
    
    def list_transformations(
        self,
        status: Optional[TransformationStatus] = None,
        requires_review: Optional[bool] = None
    ) -> List[AITransformation]:
        """
        List transformations with optional filters
        
        Args:
            status: Filter by status
            requires_review: Filter by review requirement
            
        Returns:
            List of transformations
        """
        results = list(self._transformations.values())
        
        if status:
            results = [t for t in results if t.status == status]
        
        if requires_review is not None:
            results = [t for t in results if t.requires_review == requires_review]
        
        return results
    
    def approve(
        self,
        transformation_id: str,
        reviewer: str,
        comments: str = ""
    ) -> AITransformation:
        """
        Approve a transformation
        
        Args:
            transformation_id: Transformation ID
            reviewer: Reviewer name/email
            comments: Optional review comments
            
        Returns:
            Updated transformation
            
        Raises:
            AITransformationError: If transformation not found or invalid state
        """
        transformation = self.get_transformation(transformation_id)
        if not transformation:
            raise AITransformationError(
                f"Transformation {transformation_id} not found",
                suggestion="Check transformation ID"
            )
        
        if transformation.status != TransformationStatus.PENDING_REVIEW:
            raise AITransformationError(
                f"Cannot approve transformation in {transformation.status.value} state",
                suggestion="Only pending transformations can be approved"
            )
        
        # Create review record
        transformation.review = AITransformationReview(
            transformation_id=transformation_id,
            reviewer=reviewer,
            decision="approved",
            comments=comments
        )
        
        transformation.status = TransformationStatus.APPROVED
        self._save_transformation(transformation)
        
        logger.success(
            f"Transformation {transformation_id} approved",
            reviewer=reviewer,
            confidence=transformation.confidence
        )
        
        return transformation
    
    def reject(
        self,
        transformation_id: str,
        reviewer: str,
        comments: str = ""
    ) -> AITransformation:
        """
        Reject a transformation
        
        Args:
            transformation_id: Transformation ID
            reviewer: Reviewer name/email
            comments: Rejection reason (required)
            
        Returns:
            Updated transformation
            
        Raises:
            AITransformationError: If transformation not found or invalid state
        """
        transformation = self.get_transformation(transformation_id)
        if not transformation:
            raise AITransformationError(
                f"Transformation {transformation_id} not found"
            )
        
        if not comments:
            raise AITransformationError(
                "Rejection reason required",
                suggestion="Provide comments explaining why transformation was rejected"
            )
        
        # Create review record
        transformation.review = AITransformationReview(
            transformation_id=transformation_id,
            reviewer=reviewer,
            decision="rejected",
            comments=comments
        )
        
        transformation.status = TransformationStatus.REJECTED
        self._save_transformation(transformation)
        
        logger.warning(
            f"Transformation {transformation_id} rejected",
            reviewer=reviewer,
            reason=comments
        )
        
        return transformation
    
    def apply(
        self,
        transformation_id: str,
        apply_fn: Optional[Callable[[str], None]] = None
    ) -> AITransformation:
        """
        Apply an approved transformation
        
        Args:
            transformation_id: Transformation ID
            apply_fn: Optional function to apply changes (default: write to file)
            
        Returns:
            Updated transformation
            
        Raises:
            AITransformationError: If transformation not approved
        """
        transformation = self.get_transformation(transformation_id)
        if not transformation:
            raise AITransformationError(f"Transformation {transformation_id} not found")
        
        if transformation.status != TransformationStatus.APPROVED:
            raise AITransformationError(
                f"Cannot apply transformation in {transformation.status.value} state",
                suggestion="Only approved transformations can be applied"
            )
        
        # Apply transformation
        try:
            if apply_fn:
                apply_fn(transformation.after_snapshot)
            else:
                # Default: write to file
                Path(transformation.artifact_path).write_text(transformation.after_snapshot)
            
            transformation.status = TransformationStatus.APPLIED
            transformation.applied_at = datetime.utcnow()
            self._save_transformation(transformation)
            
            logger.success(
                f"Applied transformation {transformation_id}",
                artifact_path=transformation.artifact_path
            )
            
            return transformation
            
        except Exception as e:
            logger.error(f"Failed to apply transformation: {e}", exc_info=True)
            raise AITransformationError(
                f"Failed to apply transformation: {e}",
                suggestion="Check file permissions and path validity"
            )
    
    def rollback(
        self,
        transformation_id: str,
        rollback_fn: Optional[Callable[[str], None]] = None
    ) -> AITransformation:
        """
        Rollback an applied transformation
        
        Args:
            transformation_id: Transformation ID
            rollback_fn: Optional function to rollback changes
            
        Returns:
            Updated transformation
            
        Raises:
            AITransformationError: If transformation not applied
        """
        transformation = self.get_transformation(transformation_id)
        if not transformation:
            raise AITransformationError(f"Transformation {transformation_id} not found")
        
        if transformation.status != TransformationStatus.APPLIED:
            raise AITransformationError(
                f"Cannot rollback transformation in {transformation.status.value} state",
                suggestion="Only applied transformations can be rolled back"
            )
        
        # Rollback transformation
        try:
            if rollback_fn:
                rollback_fn(transformation.before_snapshot)
            else:
                # Default: restore file
                Path(transformation.artifact_path).write_text(transformation.before_snapshot)
            
            transformation.status = TransformationStatus.ROLLED_BACK
            transformation.rolled_back_at = datetime.utcnow()
            self._save_transformation(transformation)
            
            logger.warning(
                f"Rolled back transformation {transformation_id}",
                artifact_path=transformation.artifact_path
            )
            
            return transformation
            
        except Exception as e:
            logger.error(f"Failed to rollback transformation: {e}", exc_info=True)
            raise AITransformationError(
                f"Failed to rollback transformation: {e}",
                suggestion="Manual intervention may be required"
            )
    
    def get_audit_trail(self, transformation_id: str) -> Dict[str, Any]:
        """
        Get complete audit trail for transformation
        
        Args:
            transformation_id: Transformation ID
            
        Returns:
            Audit trail dictionary
        """
        transformation = self.get_transformation(transformation_id)
        if not transformation:
            raise AITransformationError(f"Transformation {transformation_id} not found")
        
        return {
            'transformation_id': transformation.id,
            'operation': transformation.operation,
            'artifact_type': transformation.artifact_type,
            'artifact_path': transformation.artifact_path,
            'actor': transformation.actor,
            'model': transformation.model_used,
            'prompt_hash': transformation.prompt_hash,
            'confidence': transformation.confidence,
            'confidence_level': transformation.confidence_level.value,
            'status': transformation.status.value,
            'requires_review': transformation.requires_review,
            'review': transformation.review.to_dict() if transformation.review else None,
            'created_at': transformation.created_at.isoformat(),
            'applied_at': transformation.applied_at.isoformat() if transformation.applied_at else None,
            'rolled_back_at': transformation.rolled_back_at.isoformat() if transformation.rolled_back_at else None,
            'metadata': transformation.metadata
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get transformation statistics"""
        transformations = list(self._transformations.values())
        
        total = len(transformations)
        pending = sum(1 for t in transformations if t.status == TransformationStatus.PENDING_REVIEW)
        approved = sum(1 for t in transformations if t.status == TransformationStatus.APPROVED)
        rejected = sum(1 for t in transformations if t.status == TransformationStatus.REJECTED)
        applied = sum(1 for t in transformations if t.status == TransformationStatus.APPLIED)
        rolled_back = sum(1 for t in transformations if t.status == TransformationStatus.ROLLED_BACK)
        
        high_conf = sum(1 for t in transformations if t.confidence_level == ConfidenceLevel.HIGH)
        medium_conf = sum(1 for t in transformations if t.confidence_level == ConfidenceLevel.MEDIUM)
        low_conf = sum(1 for t in transformations if t.confidence_level == ConfidenceLevel.LOW)
        
        avg_confidence = sum(t.confidence for t in transformations) / total if total > 0 else 0.0
        
        return {
            'total_transformations': total,
            'by_status': {
                'pending': pending,
                'approved': approved,
                'rejected': rejected,
                'applied': applied,
                'rolled_back': rolled_back
            },
            'by_confidence': {
                'high': high_conf,
                'medium': medium_conf,
                'low': low_conf
            },
            'average_confidence': round(avg_confidence, 3),
            'approval_rate': round(approved / total, 3) if total > 0 else 0.0,
            'rejection_rate': round(rejected / total, 3) if total > 0 else 0.0
        }
