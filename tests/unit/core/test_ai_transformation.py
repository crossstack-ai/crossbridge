"""
Unit Tests for AI Transformation Validation

Tests all components of the AI transformation validation system.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from core.ai.transformation_validation import (
    AITransformation,
    AITransformationReview,
    ConfidenceSignals,
    TransformationStatus,
    ConfidenceLevel,
    AITransformationError,
    compute_confidence,
    compute_prompt_hash,
    generate_diff,
    classify_confidence,
    requires_human_review
)
from core.ai.transformation_service import AITransformationService


class TestConfidenceScoring:
    """Test confidence scoring system"""
    
    def test_perfect_confidence(self):
        """Test perfect confidence score"""
        signals = ConfidenceSignals(
            model_confidence=1.0,
            similarity_to_existing=1.0,
            rule_violations=0,
            historical_acceptance_rate=1.0,
            diff_size=10,
            syntax_valid=True,
            test_coverage_maintained=True
        )
        
        score = compute_confidence(signals)
        assert score >= 0.8  # Should be high confidence
    
    def test_low_confidence_large_diff(self):
        """Test low confidence due to large diff"""
        signals = ConfidenceSignals(
            model_confidence=0.9,
            diff_size=200  # Very large diff
        )
        
        score = compute_confidence(signals)
        assert score < 0.8  # Should be penalized
    
    def test_low_confidence_rule_violations(self):
        """Test low confidence due to rule violations"""
        signals = ConfidenceSignals(
            model_confidence=1.0,
            rule_violations=5
        )
        
        score = compute_confidence(signals)
        assert score < 0.8  # Should be penalized
    
    def test_low_confidence_invalid_syntax(self):
        """Test low confidence due to invalid syntax"""
        signals = ConfidenceSignals(
            model_confidence=1.0,
            syntax_valid=False
        )
        
        score = compute_confidence(signals)
        assert score < 0.8  # Should be heavily penalized
    
    def test_confidence_classification(self):
        """Test confidence level classification"""
        assert classify_confidence(0.9) == ConfidenceLevel.HIGH
        assert classify_confidence(0.8) == ConfidenceLevel.HIGH
        assert classify_confidence(0.7) == ConfidenceLevel.MEDIUM
        assert classify_confidence(0.5) == ConfidenceLevel.MEDIUM
        assert classify_confidence(0.4) == ConfidenceLevel.LOW


class TestDiffGeneration:
    """Test diff generation"""
    
    def test_generate_diff(self):
        """Test unified diff generation"""
        before = "line1\nline2\nline3\n"
        after = "line1\nmodified\nline3\n"
        
        diff = generate_diff(before, after, "test.py")
        
        assert "---" in diff
        assert "+++" in diff
        assert "-line2" in diff
        assert "+modified" in diff
    
    def test_empty_diff(self):
        """Test diff with no changes"""
        content = "line1\nline2\n"
        diff = generate_diff(content, content, "test.py")
        
        assert diff == ""  # No changes


class TestTransformationModel:
    """Test AI transformation data model"""
    
    def test_transformation_creation(self):
        """Test creating transformation"""
        transformation = AITransformation(
            operation="generate",
            artifact_type="test",
            artifact_path="test_login.py",
            before_snapshot="",
            after_snapshot="def test_login(): pass",
            model_used="gpt-4",
            prompt_hash="abc123"
        )
        
        assert transformation.id.startswith("ai-")
        assert transformation.status == TransformationStatus.PENDING_REVIEW
        assert transformation.requires_review is True
    
    def test_transformation_to_dict(self):
        """Test transformation serialization"""
        transformation = AITransformation(
            operation="modify",
            artifact_type="code",
            confidence=0.85
        )
        
        data = transformation.to_dict()
        
        assert data['operation'] == "modify"
        assert data['artifact_type'] == "code"
        assert data['confidence'] == 0.85
        assert 'id' in data
        assert 'created_at' in data
    
    def test_transformation_from_dict(self):
        """Test transformation deserialization"""
        data = {
            'id': 'ai-test123',
            'operation': 'refactor',
            'artifact_type': 'test',
            'confidence': 0.92,
            'status': 'approved',
            'created_at': '2026-01-29T10:00:00'
        }
        
        transformation = AITransformation.from_dict(data)
        
        assert transformation.id == 'ai-test123'
        assert transformation.operation == 'refactor'
        assert transformation.confidence == 0.92
        assert transformation.status == TransformationStatus.APPROVED


class TestReviewModel:
    """Test review data model"""
    
    def test_review_creation(self):
        """Test creating review"""
        review = AITransformationReview(
            transformation_id="ai-123",
            reviewer="user@example.com",
            decision="approved",
            comments="Looks good"
        )
        
        assert review.transformation_id == "ai-123"
        assert review.reviewer == "user@example.com"
        assert review.decision == "approved"
        assert isinstance(review.reviewed_at, datetime)
    
    def test_review_to_dict(self):
        """Test review serialization"""
        review = AITransformationReview(
            transformation_id="ai-456",
            reviewer="reviewer@test.com",
            decision="rejected",
            comments="Needs work"
        )
        
        data = review.to_dict()
        
        assert data['transformation_id'] == "ai-456"
        assert data['decision'] == "rejected"
        assert 'reviewed_at' in data


class TestTransformationService:
    """Test AI Transformation Service"""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def service(self, temp_storage):
        """Create service instance"""
        return AITransformationService(storage_dir=temp_storage)
    
    def test_service_initialization(self, service):
        """Test service initializes correctly"""
        assert service.storage_dir.exists()
        assert service.confidence_threshold == 0.8
    
    def test_generate_transformation(self, service):
        """Test generating transformation"""
        transformation = service.generate(
            operation="generate",
            artifact_type="test",
            artifact_path="test_new.py",
            before_content="",
            after_content="def test_new(): pass",
            model="gpt-4",
            prompt="Generate a test"
        )
        
        assert transformation.id.startswith("ai-")
        assert transformation.operation == "generate"
        assert transformation.confidence > 0.0
        assert transformation.diff != ""
        assert transformation.status == TransformationStatus.PENDING_REVIEW
    
    def test_approve_transformation(self, service):
        """Test approving transformation"""
        transformation = service.generate(
            operation="modify",
            artifact_type="code",
            artifact_path="app.py",
            before_content="old code",
            after_content="new code",
            model="gpt-4",
            prompt="Improve code"
        )
        
        approved = service.approve(
            transformation.id,
            reviewer="test@example.com",
            comments="LGTM"
        )
        
        assert approved.status == TransformationStatus.APPROVED
        assert approved.review is not None
        assert approved.review.reviewer == "test@example.com"
    
    def test_reject_transformation(self, service):
        """Test rejecting transformation"""
        transformation = service.generate(
            operation="generate",
            artifact_type="test",
            artifact_path="bad_test.py",
            before_content="",
            after_content="bad code",
            model="gpt-4",
            prompt="Generate test"
        )
        
        rejected = service.reject(
            transformation.id,
            reviewer="reviewer@test.com",
            comments="Syntax errors found"
        )
        
        assert rejected.status == TransformationStatus.REJECTED
        assert rejected.review.decision == "rejected"
    
    def test_reject_requires_comments(self, service):
        """Test rejection requires comments"""
        transformation = service.generate(
            operation="generate",
            artifact_type="test",
            artifact_path="test.py",
            before_content="",
            after_content="code",
            model="gpt-4",
            prompt="test"
        )
        
        with pytest.raises(AITransformationError, match="Rejection reason required"):
            service.reject(transformation.id, "reviewer@test.com", comments="")
    
    def test_list_transformations(self, service):
        """Test listing transformations"""
        # Generate some transformations
        service.generate("generate", "test", "t1.py", "", "code1", "gpt-4", "p1")
        service.generate("modify", "code", "t2.py", "old", "new", "gpt-4", "p2")
        
        all_trans = service.list_transformations()
        assert len(all_trans) == 2
        
        pending = service.list_transformations(status=TransformationStatus.PENDING_REVIEW)
        assert len(pending) == 2
    
    def test_get_audit_trail(self, service):
        """Test getting audit trail"""
        transformation = service.generate(
            operation="refactor",
            artifact_type="code",
            artifact_path="main.py",
            before_content="old",
            after_content="new",
            model="gpt-4",
            prompt="refactor code"
        )
        
        audit = service.get_audit_trail(transformation.id)
        
        assert audit['transformation_id'] == transformation.id
        assert audit['operation'] == "refactor"
        assert audit['model'] == "gpt-4"
        assert 'prompt_hash' in audit
        assert 'confidence' in audit
    
    def test_get_statistics(self, service):
        """Test getting statistics"""
        # Generate various transformations
        t1 = service.generate("generate", "test", "t1.py", "", "code", "gpt-4", "p")
        service.approve(t1.id, "reviewer", "ok")
        
        t2 = service.generate("modify", "code", "t2.py", "old", "new", "gpt-4", "p")
        service.reject(t2.id, "reviewer", "bad")
        
        stats = service.get_statistics()
        
        assert stats['total_transformations'] == 2
        assert stats['by_status']['approved'] == 1
        assert stats['by_status']['rejected'] == 1
        assert 'average_confidence' in stats
        assert 'approval_rate' in stats


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_compute_prompt_hash(self):
        """Test prompt hash computation"""
        prompt = "Generate a test for login functionality"
        hash1 = compute_prompt_hash(prompt)
        hash2 = compute_prompt_hash(prompt)
        
        assert hash1 == hash2  # Same input = same hash
        assert len(hash1) == 16  # Truncated to 16 chars
    
    def test_requires_human_review(self):
        """Test review requirement check"""
        assert requires_human_review(0.7, threshold=0.8) is True
        assert requires_human_review(0.85, threshold=0.8) is False
        assert requires_human_review(0.8, threshold=0.8) is False  # Equal to threshold


class TestWorkflow:
    """Test end-to-end workflows"""
    
    @pytest.fixture
    def service(self):
        """Create service with temp storage"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield AITransformationService(storage_dir=Path(tmpdir))
    
    def test_full_approval_workflow(self, service):
        """Test complete approval workflow"""
        # 1. Generate transformation
        transformation = service.generate(
            operation="generate",
            artifact_type="test",
            artifact_path="test_feature.py",
            before_content="",
            after_content="def test_feature(): assert True",
            model="gpt-4",
            prompt="Create feature test"
        )
        
        assert transformation.status == TransformationStatus.PENDING_REVIEW
        
        # 2. Approve
        approved = service.approve(transformation.id, "senior_dev@test.com", "Approved")
        assert approved.status == TransformationStatus.APPROVED
        
        # 3. Check audit trail
        audit = service.get_audit_trail(transformation.id)
        assert audit['status'] == 'approved'
        assert audit['review']['reviewer'] == "senior_dev@test.com"
    
    def test_rejection_workflow(self, service):
        """Test rejection workflow"""
        # 1. Generate with low confidence
        signals = ConfidenceSignals(
            model_confidence=0.5,
            syntax_valid=False,
            rule_violations=3
        )
        
        transformation = service.generate(
            operation="modify",
            artifact_type="code",
            artifact_path="broken.py",
            before_content="good code",
            after_content="bad code",
            model="gpt-3.5",
            prompt="modify",
            signals=signals
        )
        
        assert transformation.confidence < 0.5
        assert transformation.requires_review is True
        
        # 2. Reject
        rejected = service.reject(
            transformation.id,
            "tech_lead@test.com",
            "Syntax errors and rule violations"
        )
        
        assert rejected.status == TransformationStatus.REJECTED
        assert rejected.review.comments == "Syntax errors and rule violations"
