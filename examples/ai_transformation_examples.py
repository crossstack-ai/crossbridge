"""
AI Transformation Validation Examples

Comprehensive examples demonstrating AI transformation validation workflows.
"""

from pathlib import Path
from core.ai.transformation_service import AITransformationService
from core.ai.transformation_validation import ConfidenceSignals
import subprocess


def example_1_basic_generation():
    """Example 1: Basic transformation generation"""
    print("\n=== Example 1: Basic Generation ===\n")
    
    service = AITransformationService()
    
    # Generate a simple test transformation
    transformation = service.generate(
        operation="generate",
        artifact_type="test",
        artifact_path="tests/test_example.py",
        before_content="",
        after_content="""
def test_addition():
    '''Test basic addition'''
    assert 1 + 1 == 2

def test_subtraction():
    '''Test basic subtraction'''
    assert 5 - 3 == 2
""",
        model="gpt-4",
        prompt="Generate basic math tests",
        signals=ConfidenceSignals(
            model_confidence=0.95,
            diff_size=8,
            syntax_valid=True,
            rule_violations=0
        )
    )
    
    print(f"Created transformation: {transformation.id}")
    print(f"Confidence: {transformation.confidence:.2f}")
    print(f"Requires review: {transformation.requires_review}")
    print(f"Status: {transformation.status.value}")


def example_2_approval_workflow():
    """Example 2: Complete approval workflow"""
    print("\n=== Example 2: Approval Workflow ===\n")
    
    service = AITransformationService()
    
    # Generate transformation
    transformation = service.generate(
        operation="modify",
        artifact_type="code",
        artifact_path="src/calculator.py",
        before_content="def add(a, b): return a + b",
        after_content="def add(a: int, b: int) -> int:\n    '''Add two integers'''\n    return a + b",
        model="gpt-4",
        prompt="Add type hints and docstring",
        signals=ConfidenceSignals(
            model_confidence=0.88,
            diff_size=3,
            syntax_valid=True
        )
    )
    
    print(f"Generated: {transformation.id}")
    print(f"Confidence: {transformation.confidence:.2f}")
    
    # Approve
    approved = service.approve(
        transformation.id,
        reviewer="senior_dev@example.com",
        comments="Type hints look good"
    )
    
    print(f"Status after approval: {approved.status.value}")
    print(f"Reviewer: {approved.review.reviewer}")
    
    # Note: In production, you would apply to actual file
    print(f"\nTo apply: service.apply('{transformation.id}')")


def example_3_rejection_workflow():
    """Example 3: Rejection workflow"""
    print("\n=== Example 3: Rejection Workflow ===\n")
    
    service = AITransformationService()
    
    # Generate transformation with issues
    transformation = service.generate(
        operation="generate",
        artifact_type="test",
        artifact_path="tests/test_bad.py",
        before_content="",
        after_content="def test_invalid():\n    assert True = False",  # Syntax error
        model="gpt-3.5",
        prompt="Generate test",
        signals=ConfidenceSignals(
            model_confidence=0.6,
            diff_size=2,
            syntax_valid=False,  # Invalid syntax!
            rule_violations=2
        )
    )
    
    print(f"Generated: {transformation.id}")
    print(f"Confidence: {transformation.confidence:.2f} (LOW)")
    print(f"Requires review: {transformation.requires_review}")
    
    # Reject
    rejected = service.reject(
        transformation.id,
        reviewer="tech_lead@example.com",
        comments="Syntax error: cannot assign to comparison"
    )
    
    print(f"Status: {rejected.status.value}")
    print(f"Rejection reason: {rejected.review.comments}")


def example_4_rollback_workflow():
    """Example 4: Rollback workflow"""
    print("\n=== Example 4: Rollback Workflow ===\n")
    
    service = AITransformationService()
    
    # Create temp file for demonstration
    temp_file = Path("temp_test.py")
    temp_file.write_text("# Original content")
    
    try:
        # Generate and apply transformation
        transformation = service.generate(
            operation="modify",
            artifact_type="code",
            artifact_path=str(temp_file),
            before_content="# Original content",
            after_content="# Modified content\ndef test_new():\n    pass",
            model="gpt-4",
            prompt="Add test",
            signals=ConfidenceSignals(model_confidence=0.9)
        )
        
        print(f"Generated: {transformation.id}")
        
        # Approve and apply
        service.approve(transformation.id, "dev@example.com", "ok")
        service.apply(transformation.id)
        
        print(f"Applied - File now contains: {temp_file.read_text()[:50]}...")
        
        # Simulate issue - rollback
        print("\n⚠ Issue detected, rolling back...")
        rolled_back = service.rollback(transformation.id)
        
        print(f"Status: {rolled_back.status.value}")
        print(f"File restored to: {temp_file.read_text()}")
        
    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()


def example_5_audit_trail():
    """Example 5: Audit trail inspection"""
    print("\n=== Example 5: Audit Trail ===\n")
    
    service = AITransformationService()
    
    # Generate transformation
    transformation = service.generate(
        operation="refactor",
        artifact_type="code",
        artifact_path="src/legacy.py",
        before_content="def old_func(): pass",
        after_content="def new_func(): pass",
        model="gpt-4",
        prompt="Refactor function name",
        signals=ConfidenceSignals(model_confidence=0.85)
    )
    
    # Get audit trail
    audit = service.get_audit_trail(transformation.id)
    
    print("Audit Trail:")
    print(f"  ID: {audit['transformation_id']}")
    print(f"  Operation: {audit['operation']}")
    print(f"  Model: {audit['model']}")
    print(f"  Prompt Hash: {audit['prompt_hash']}")
    print(f"  Confidence: {audit['confidence']:.2f}")
    print(f"  Status: {audit['status']}")
    print(f"  Created: {audit['created_at']}")


def example_6_statistics():
    """Example 6: System statistics"""
    print("\n=== Example 6: Statistics ===\n")
    
    service = AITransformationService()
    
    # Generate some transformations
    for i in range(5):
        t = service.generate(
            operation="generate",
            artifact_type="test",
            artifact_path=f"test_{i}.py",
            before_content="",
            after_content=f"def test_{i}(): pass",
            model="gpt-4",
            prompt=f"Generate test {i}",
            signals=ConfidenceSignals(model_confidence=0.7 + i * 0.05)
        )
        
        # Approve some, reject others
        if i % 2 == 0:
            service.approve(t.id, "reviewer@test.com", "ok")
        else:
            service.reject(t.id, "reviewer@test.com", "not ok")
    
    # Get statistics
    stats = service.get_statistics()
    
    print("System Statistics:")
    print(f"  Total Transformations: {stats['total_transformations']}")
    print(f"  Approved: {stats['by_status'].get('approved', 0)}")
    print(f"  Rejected: {stats['by_status'].get('rejected', 0)}")
    print(f"  Approval Rate: {stats['approval_rate']:.1%}")
    print(f"  Average Confidence: {stats['average_confidence']:.2f}")


def example_7_custom_apply_rollback():
    """Example 7: Custom apply/rollback functions"""
    print("\n=== Example 7: Custom Apply/Rollback ===\n")
    
    service = AITransformationService()
    
    # Custom apply function (e.g., git commit)
    def git_apply(transformation):
        """Apply with git commit"""
        print(f"Writing to {transformation.artifact_path}")
        Path(transformation.artifact_path).write_text(transformation.after_snapshot)
        
        print("Git add and commit")
        # In production: subprocess.run(['git', 'add', transformation.artifact_path])
        # In production: subprocess.run(['git', 'commit', '-m', f'AI: {transformation.operation}'])
        
        return True
    
    # Custom rollback function (e.g., git revert)
    def git_rollback(transformation):
        """Rollback with git"""
        print(f"Restoring {transformation.artifact_path}")
        Path(transformation.artifact_path).write_text(transformation.before_snapshot)
        
        print("Git checkout previous version")
        # In production: subprocess.run(['git', 'checkout', 'HEAD~1', '--', transformation.artifact_path])
        
        return True
    
    # Generate transformation
    transformation = service.generate(
        operation="modify",
        artifact_type="code",
        artifact_path="src/example.py",
        before_content="# old",
        after_content="# new",
        model="gpt-4",
        prompt="update comment"
    )
    
    service.approve(transformation.id, "dev@test.com", "ok")
    
    print("Applying with custom function...")
    # service.apply(transformation.id, apply_fn=git_apply)
    
    print("Rolling back with custom function...")
    # service.rollback(transformation.id, rollback_fn=git_rollback)


def example_8_programmatic_integration():
    """Example 8: Integration with existing AI workflow"""
    print("\n=== Example 8: Programmatic Integration ===\n")
    
    def generate_test_with_validation(test_name, ai_prompt):
        """Integrate AI generation with validation"""
        
        # Simulate AI generation
        ai_code = f"""
def test_{test_name}():
    '''Test generated by AI'''
    assert True
"""
        
        # Create transformation
        service = AITransformationService()
        transformation = service.generate(
            operation="generate",
            artifact_type="test",
            artifact_path=f"tests/test_{test_name}.py",
            before_content="",
            after_content=ai_code,
            model="gpt-4",
            prompt=ai_prompt,
            signals=ConfidenceSignals(
                model_confidence=0.9,
                syntax_valid=True,
                diff_size=len(ai_code.split('\n'))
            )
        )
        
        # Handle based on confidence
        if transformation.confidence >= 0.8:
            print(f"✓ High confidence ({transformation.confidence:.2f})")
            print(f"  Auto-applying transformation {transformation.id}")
            service.apply(transformation.id)
            return transformation
        else:
            print(f"⚠ Low confidence ({transformation.confidence:.2f})")
            print(f"  Review required: crossbridge ai-transform show {transformation.id}")
            return transformation
    
    # Use the function
    result = generate_test_with_validation("login", "Generate login test")
    print(f"Result: {result.status.value}")


def main():
    """Run all examples"""
    print("=" * 70)
    print("AI Transformation Validation Examples")
    print("=" * 70)
    
    example_1_basic_generation()
    example_2_approval_workflow()
    example_3_rejection_workflow()
    example_4_rollback_workflow()
    example_5_audit_trail()
    example_6_statistics()
    example_7_custom_apply_rollback()
    example_8_programmatic_integration()
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\nNext steps:")
    print("- Review full documentation: docs/ai/AI_TRANSFORMATION_VALIDATION.md")
    print("- Try CLI commands: crossbridge ai-transform --help")
    print("- Run tests: pytest tests/unit/core/test_ai_transformation.py")


if __name__ == "__main__":
    main()
