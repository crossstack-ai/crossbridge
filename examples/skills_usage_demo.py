"""
CrossBridge AI Skills Usage Examples

Demonstrates how to use all 5 AI skills:
1. FlakyAnalyzer - Detect flaky tests
2. TestGenerator - Generate test cases from source code
3. TestMigrator - Migrate tests between frameworks
4. CoverageReasoner - Analyze test coverage gaps
5. RootCauseAnalyzer - Debug test failures

All examples use the AIOrchestrator for execution with governance.
"""

import os
from pathlib import Path
from typing import List, Dict, Any

from core.ai.models import (
    AIExecutionContext,
    TaskType,
)
from core.ai.orchestrator import AIOrchestrator, ExecutionPolicy
from core.ai.skills import (
    FlakyAnalyzer,
    TestGenerator,
    TestMigrator,
    CoverageReasoner,
    RootCauseAnalyzer,
)


def setup_orchestrator() -> AIOrchestrator:
    """
    Setup AI orchestrator with OpenAI configuration.
    
    For self-hosted, change:
        provider_type="vllm"
        api_base="http://localhost:8000"
    """
    config = {
        "providers": {
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", "sk-test-key"),
            },
            "anthropic": {
                "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
            },
        },
        "audit_log_path": "logs/ai_audit.jsonl",
        "cost_tracker_path": "logs/cost_tracking.json",
        "credit_manager_path": "logs/credits.json",
    }
    
    orchestrator = AIOrchestrator(config)
    
    # Add credits for testing ($10 = 10000 credits)
    orchestrator.credit_manager.add_credits(
        user_id="demo_user",
        amount=10.0,
        project_id="demo_project"
    )
    
    return orchestrator


def demo_flaky_analyzer():
    """
    Demo 1: Detect flaky tests
    
    Analyzes test execution history to identify flakiness patterns.
    """
    print("\n" + "="*60)
    print("DEMO 1: Flaky Test Analysis")
    print("="*60)
    
    orchestrator = setup_orchestrator()
    
    # Create execution context
    context = AIExecutionContext(
        user="demo_user",
        project_id="demo_project",
        task_type=TaskType.FLAKY_ANALYSIS,
        allow_external_ai=True,
        allow_self_hosted=False,
        max_cost=1.0,
    )
    
    # Prepare test execution history
    execution_history = [
        {"run_id": 1, "status": "passed", "duration_ms": 120},
        {"run_id": 2, "status": "failed", "duration_ms": 125, "error": "AssertionError"},
        {"run_id": 3, "status": "passed", "duration_ms": 118},
        {"run_id": 4, "status": "passed", "duration_ms": 122},
        {"run_id": 5, "status": "failed", "duration_ms": 130, "error": "AssertionError"},
        {"run_id": 6, "status": "passed", "duration_ms": 121},
    ]
    
    # Execute FlakyAnalyzer skill
    skill = FlakyAnalyzer()
    result = orchestrator.execute_skill(
        skill=skill,
        inputs={
            "test_name": "test_user_authentication",
            "test_file": "tests/test_auth.py",
            "execution_history": execution_history,
            "code_context": "async def test_user_authentication():\n    user = await create_user()\n    assert user.is_authenticated",
        },
        context=context,
    )
    
    # Display results
    print(f"\nTest: test_user_authentication")
    print(f"Is Flaky: {result.get('is_flaky')}")
    print(f"Confidence: {result.get('confidence'):.2f}")
    print(f"Root Causes: {', '.join(result.get('root_causes', []))}")
    print(f"Recommendations: {', '.join(result.get('recommendations', []))}")


def demo_test_generator():
    """
    Demo 2: Generate test cases from source code
    
    Analyzes source code and generates comprehensive test suite.
    """
    print("\n" + "="*60)
    print("DEMO 2: Test Case Generation")
    print("="*60)
    
    orchestrator = setup_orchestrator()
    
    context = AIExecutionContext(
        user="demo_user",
        project_id="demo_project",
        task_type=TaskType.TEST_GENERATION,
        allow_external_ai=True,
        max_cost=2.0,
    )
    
    # Source code to generate tests for
    source_code = '''
class Calculator:
    """Simple calculator with basic operations."""
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    
    def power(self, base: float, exponent: int) -> float:
        """Raise base to exponent."""
        return base ** exponent
'''
    
    # Execute TestGenerator skill
    skill = TestGenerator()
    result = orchestrator.execute_skill(
        skill=skill,
        inputs={
            "source_file": "calculator.py",
            "source_code": source_code,
            "language": "python",
            "test_framework": "pytest",
            "coverage_gaps": "Need edge cases for divide() and power()",
        },
        context=context,
    )
    
    # Display results
    print(f"\nSource File: calculator.py")
    print(f"Generated {result.get('test_count', 0)} test cases")
    print(f"\nGenerated Test Code (first 500 chars):")
    print("─" * 60)
    test_code = result.get('test_code', '')
    print(test_code[:500] + "..." if len(test_code) > 500 else test_code)
    print("─" * 60)


def demo_test_migrator():
    """
    Demo 3: Migrate tests between frameworks
    
    Converts JUnit tests to pytest while preserving logic.
    """
    print("\n" + "="*60)
    print("DEMO 3: Test Framework Migration (JUnit → pytest)")
    print("="*60)
    
    orchestrator = setup_orchestrator()
    
    context = AIExecutionContext(
        user="demo_user",
        project_id="demo_project",
        task_type=TaskType.TEST_MIGRATION,
        allow_external_ai=True,
        max_cost=2.0,
    )
    
    # Original JUnit test
    junit_test = '''
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import static org.junit.jupiter.api.Assertions.*;

public class UserServiceTest {
    private UserService userService;
    
    @BeforeEach
    public void setUp() {
        userService = new UserService();
    }
    
    @Test
    public void testCreateUser() {
        User user = userService.createUser("alice", "alice@example.com");
        assertNotNull(user);
        assertEquals("alice", user.getUsername());
        assertEquals("alice@example.com", user.getEmail());
    }
    
    @Test
    public void testCreateUserWithInvalidEmail() {
        assertThrows(IllegalArgumentException.class, () -> {
            userService.createUser("bob", "invalid-email");
        });
    }
}
'''
    
    # Execute TestMigrator skill
    skill = TestMigrator()
    result = orchestrator.execute_skill(
        skill=skill,
        inputs={
            "source_framework": "junit5",
            "target_framework": "pytest",
            "language": "java_to_python",
            "source_test_code": junit_test,
            "migration_notes": "Convert to pytest with fixtures",
        },
        context=context,
    )
    
    # Display results
    print(f"\nMigration: JUnit 5 → pytest")
    print(f"Confidence: {result.get('confidence', 0):.2f}")
    print(f"Changes: {len(result.get('changes', []))} transformations")
    print(f"\nMigrated Code (first 500 chars):")
    print("─" * 60)
    migrated = result.get('migrated_code', '')
    print(migrated[:500] + "..." if len(migrated) > 500 else migrated)
    print("─" * 60)
    
    warnings = result.get('warnings', [])
    if warnings:
        print(f"\nWarnings:")
        for w in warnings:
            print(f"  • {w}")


def demo_coverage_reasoner():
    """
    Demo 4: Analyze test coverage gaps
    
    Identifies untested code paths and suggests tests.
    """
    print("\n" + "="*60)
    print("DEMO 4: Coverage Gap Analysis")
    print("="*60)
    
    orchestrator = setup_orchestrator()
    
    context = AIExecutionContext(
        user="demo_user",
        project_id="demo_project",
        task_type=TaskType.COVERAGE_INFERENCE,
        allow_external_ai=True,
        max_cost=1.5,
    )
    
    # Source code with coverage gaps
    source_code = '''
class PaymentProcessor:
    def process_payment(self, amount: float, method: str) -> dict:
        """Process payment with multiple methods."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if method == "credit_card":
            return self._process_credit_card(amount)
        elif method == "paypal":
            return self._process_paypal(amount)
        elif method == "crypto":
            return self._process_crypto(amount)
        else:
            raise ValueError(f"Unknown payment method: {method}")
    
    def _process_credit_card(self, amount: float) -> dict:
        # Complex credit card logic
        return {"status": "success", "transaction_id": "cc_123"}
    
    def _process_paypal(self, amount: float) -> dict:
        # PayPal integration
        return {"status": "success", "transaction_id": "pp_456"}
    
    def _process_crypto(self, amount: float) -> dict:
        # Cryptocurrency processing
        return {"status": "success", "transaction_id": "crypto_789"}
'''
    
    existing_tests = '''
def test_process_payment_credit_card():
    processor = PaymentProcessor()
    result = processor.process_payment(100.0, "credit_card")
    assert result["status"] == "success"
'''
    
    # Execute CoverageReasoner skill
    skill = CoverageReasoner()
    result = orchestrator.execute_skill(
        skill=skill,
        inputs={
            "source_code": source_code,
            "existing_tests": existing_tests,
            "language": "python",
        },
        context=context,
    )
    
    # Display results
    print(f"\nCoverage Analysis for PaymentProcessor")
    print(f"Current Coverage: {result.get('current_coverage', 0):.1f}%")
    
    gaps = result.get('coverage_gaps', [])
    print(f"\nCoverage Gaps ({len(gaps)}):")
    for gap in gaps[:5]:  # Show first 5
        print(f"  • {gap}")
    
    suggestions = result.get('test_suggestions', [])
    print(f"\nTest Suggestions ({len(suggestions)}):")
    for sug in suggestions[:3]:  # Show first 3
        print(f"  • {sug}")


def demo_root_cause_analyzer():
    """
    Demo 5: Debug test failures
    
    Analyzes failure details to identify root cause.
    """
    print("\n" + "="*60)
    print("DEMO 5: Root Cause Analysis")
    print("="*60)
    
    orchestrator = setup_orchestrator()
    
    context = AIExecutionContext(
        user="demo_user",
        project_id="demo_project",
        task_type=TaskType.ROOT_CAUSE_ANALYSIS,
        allow_external_ai=True,
        max_cost=1.5,
    )
    
    # Failure information
    failure_message = "AssertionError: Expected 200, got 404"
    stack_trace = '''
Traceback (most recent call last):
  File "tests/test_api.py", line 45, in test_get_user_profile
    assert response.status_code == 200
AssertionError: Expected 200, got 404

During handling of the above exception, another exception occurred:
  File "app/api/users.py", line 123, in get_user
    user = database.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
'''
    
    test_code = '''
def test_get_user_profile():
    """Test retrieving user profile."""
    client = TestClient(app)
    
    # Create test user
    user = create_test_user(username="testuser")
    
    # Get user profile
    response = client.get(f"/api/users/{user.id}")
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"
'''
    
    # Execute RootCauseAnalyzer skill
    skill = RootCauseAnalyzer()
    result = orchestrator.execute_skill(
        skill=skill,
        inputs={
            "test_name": "test_get_user_profile",
            "failure_message": failure_message,
            "stack_trace": stack_trace,
            "test_code": test_code,
        },
        context=context,
    )
    
    # Display results
    print(f"\nFailed Test: test_get_user_profile")
    print(f"Root Cause: {result.get('root_cause', 'Unknown')}")
    print(f"Confidence: {result.get('confidence', 0):.2f}")
    
    print(f"\nAnalysis:")
    print(result.get('explanation', 'No explanation available'))
    
    fixes = result.get('suggested_fixes', [])
    print(f"\nSuggested Fixes ({len(fixes)}):")
    for fix in fixes:
        print(f"  • {fix}")


def demo_complete_workflow():
    """
    Demo 6: Complete workflow using multiple skills
    
    Demonstrates chaining skills for end-to-end test improvement.
    """
    print("\n" + "="*60)
    print("DEMO 6: Complete Workflow (Multi-Skill)")
    print("="*60)
    
    orchestrator = setup_orchestrator()
    
    context = AIExecutionContext(
        user="demo_user",
        project_id="demo_project",
        task_type=TaskType.TEST_GENERATION,
        allow_external_ai=True,
        max_cost=5.0,
    )
    
    print("\n1. Analyzing flaky tests...")
    flaky_skill = FlakyAnalyzer()
    flaky_result = orchestrator.execute_skill(
        skill=flaky_skill,
        inputs={
            "test_name": "test_database_connection",
            "test_file": "tests/test_db.py",
            "execution_history": [
                {"run_id": i, "status": "passed" if i % 2 == 0 else "failed", "duration_ms": 100 + i}
                for i in range(10)
            ],
        },
        context=context,
    )
    print(f"   ✓ Found {1 if flaky_result.get('is_flaky') else 0} flaky tests")
    
    print("\n2. Analyzing coverage gaps...")
    coverage_skill = CoverageReasoner()
    coverage_result = orchestrator.execute_skill(
        skill=coverage_skill,
        inputs={
            "source_code": "class DatabaseManager:\n    def connect(self): pass\n    def disconnect(self): pass",
            "existing_tests": "def test_connect(): pass",
            "language": "python",
        },
        context=context,
    )
    print(f"   ✓ Found {len(coverage_result.get('coverage_gaps', []))} coverage gaps")
    
    print("\n3. Generating new tests...")
    generator_skill = TestGenerator()
    generator_result = orchestrator.execute_skill(
        skill=generator_skill,
        inputs={
            "source_file": "db_manager.py",
            "source_code": "class DatabaseManager:\n    def connect(self): pass\n    def disconnect(self): pass",
            "language": "python",
            "test_framework": "pytest",
        },
        context=context,
    )
    print(f"   ✓ Generated {generator_result.get('test_count', 0)} new tests")
    
    # Summary
    balance = orchestrator.credit_manager.get_balance('demo_user', 'demo_project')
    
    print(f"\n{'─'*60}")
    print(f"Workflow Complete!")
    print(f"Credit Balance: ${balance:.2f}")
    print(f"{'─'*60}")


def main():
    """
    Run all skill demos.
    
    NOTE: These demos require valid API keys:
        export OPENAI_API_KEY=sk-...
    
    For self-hosted/vLLM:
        - No API key needed
        - Change provider_type to "vllm" in setup_orchestrator()
        - Ensure vLLM server running at http://localhost:8000
    """
    print("\n" + "╔" + "═"*58 + "╗")
    print("║" + " "*10 + "CrossBridge AI Skills - Usage Examples" + " "*10 + "║")
    print("╚" + "═"*58 + "╝")
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY not set!")
        print("   These demos will fail without a valid API key.")
        print("   Set it with: export OPENAI_API_KEY=sk-...")
        print("\n   Proceeding with demo (will use placeholder)...")
    
    try:
        # Run individual demos
        demo_flaky_analyzer()
        demo_test_generator()
        demo_test_migrator()
        demo_coverage_reasoner()
        demo_root_cause_analyzer()
        
        # Run complete workflow
        demo_complete_workflow()
        
        print("\n" + "="*60)
        print("✅ All demos completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("   Make sure you have a valid OpenAI API key set.")
        raise


if __name__ == "__main__":
    main()
