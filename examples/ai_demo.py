"""
CrossBridge AI Module - Demonstration Examples.

This script demonstrates all major capabilities of the AI module:
1. Provider abstraction and selection
2. Flaky test analysis
3. Test generation
4. Test migration
5. Coverage inference
6. Root cause analysis
7. Cost tracking and governance
"""

import time
from pathlib import Path

# Import AI components
from core.ai import (
    AIExecutionContext,
    CoverageReasoner,
    FlakyAnalyzer,
    ProviderType,
    RootCauseAnalyzer,
    SafetyLevel,
    TaskType,
    TestGenerator,
    TestMigrator,
    get_orchestrator,
)


def demo_flaky_analysis():
    """Demonstrate flaky test analysis."""
    print("\n" + "="*80)
    print("DEMO 1: Flaky Test Analysis")
    print("="*80 + "\n")
    
    # Create orchestrator
    orchestrator = get_orchestrator(
        config={
            "policy": {
                "allow_external_ai": False,  # Use self-hosted only
                "allow_self_hosted": True,
                "safety_level": "moderate",
            }
        }
    )
    
    # Create skill
    analyzer = FlakyAnalyzer()
    
    # Prepare test execution history
    execution_history = [
        {"status": "passed", "duration": 0.5, "error": ""},
        {"status": "failed", "duration": 0.6, "error": "Timeout after 5s"},
        {"status": "passed", "duration": 0.4, "error": ""},
        {"status": "failed", "duration": 0.7, "error": "Timeout after 5s"},
        {"status": "passed", "duration": 0.5, "error": ""},
    ]
    
    # Create execution context
    context = AIExecutionContext(
        task_type=TaskType.FLAKY_ANALYSIS,
        user="demo_user",
        project_id="crossbridge",
        allow_self_hosted=True,
        max_cost=0.10,
    )
    
    print("Analyzing test: test_user_login")
    print(f"Execution history: {len(execution_history)} runs")
    print(f"Pass/Fail: 3 passed, 2 failed\n")
    
    try:
        # Execute analysis
        result = orchestrator.execute_skill(
            skill=analyzer,
            inputs={
                "test_name": "test_user_login",
                "test_file": "tests/test_auth.py",
                "execution_history": execution_history,
                "environment_info": "Python 3.11, Ubuntu 22.04",
            },
            context=context,
        )
        
        # Print results
        print("Analysis Results:")
        print(f"  Is Flaky: {result['is_flaky']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Flaky Score: {result['flaky_score']:.2f}")
        print(f"  Explanation: {result['explanation']}")
        
        if result.get('root_causes'):
            print(f"  Root Causes:")
            for cause in result['root_causes']:
                print(f"    - {cause}")
        
        if result.get('recommendations'):
            print(f"  Recommendations:")
            for rec in result['recommendations']:
                print(f"    - {rec}")
        
        print("\n✅ Flaky analysis completed successfully!")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")


def demo_test_generation():
    """Demonstrate test generation."""
    print("\n" + "="*80)
    print("DEMO 2: Test Generation")
    print("="*80 + "\n")
    
    orchestrator = get_orchestrator()
    generator = TestGenerator()
    
    # Sample source code
    source_code = """
def calculate_discount(price, discount_percent, is_member=False):
    '''Calculate final price after discount.'''
    if price < 0:
        raise ValueError("Price cannot be negative")
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")
    
    discount = price * (discount_percent / 100)
    if is_member:
        discount *= 1.1  # 10% extra discount for members
    
    return price - discount
"""
    
    context = AIExecutionContext(
        task_type=TaskType.TEST_GENERATION,
        user="demo_user",
        max_cost=0.20,
    )
    
    print("Generating tests for: calculate_discount()")
    print(f"Language: Python")
    print(f"Framework: pytest\n")
    
    try:
        result = orchestrator.execute_skill(
            skill=generator,
            inputs={
                "source_file": "utils/pricing.py",
                "source_code": source_code,
                "language": "python",
                "test_framework": "pytest",
            },
            context=context,
        )
        
        print("Generated Tests:")
        print("-" * 80)
        print(result['test_code'])
        print("-" * 80)
        print(f"\nGenerated {result.get('test_count', 0)} test cases")
        print("\n✅ Test generation completed successfully!")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")


def demo_test_migration():
    """Demonstrate test migration."""
    print("\n" + "="*80)
    print("DEMO 3: Test Migration")
    print("="*80 + "\n")
    
    orchestrator = get_orchestrator()
    migrator = TestMigrator()
    
    # Sample Selenium test
    selenium_test = """
from selenium import webdriver
from selenium.webdriver.common.by import By

class TestLogin:
    def setup_method(self):
        self.driver = webdriver.Chrome()
        self.driver.get("https://example.com/login")
    
    def test_successful_login(self):
        self.driver.find_element(By.ID, "username").send_keys("testuser")
        self.driver.find_element(By.ID, "password").send_keys("password123")
        self.driver.find_element(By.ID, "login-button").click()
        
        assert "Dashboard" in self.driver.title
    
    def teardown_method(self):
        self.driver.quit()
"""
    
    context = AIExecutionContext(
        task_type=TaskType.TEST_MIGRATION,
        user="demo_user",
        max_cost=0.25,
    )
    
    print("Migrating test from Selenium to Playwright")
    print(f"Source: Selenium WebDriver")
    print(f"Target: Playwright Python\n")
    
    try:
        result = orchestrator.execute_skill(
            skill=migrator,
            inputs={
                "source_framework": "Selenium",
                "target_framework": "Playwright",
                "language": "python",
                "source_test_code": selenium_test,
            },
            context=context,
        )
        
        print("Migrated Code:")
        print("-" * 80)
        print(result['migrated_code'])
        print("-" * 80)
        
        if result.get('changes'):
            print(f"\nKey Changes:")
            for change in result['changes']:
                print(f"  - {change}")
        
        if result.get('warnings'):
            print(f"\nWarnings:")
            for warning in result['warnings']:
                print(f"  - {warning}")
        
        print(f"\nConfidence: {result.get('confidence', 0):.2f}")
        print("\n✅ Test migration completed successfully!")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")


def demo_coverage_inference():
    """Demonstrate coverage inference."""
    print("\n" + "="*80)
    print("DEMO 4: Coverage Inference")
    print("="*80 + "\n")
    
    orchestrator = get_orchestrator()
    reasoner = CoverageReasoner()
    
    source_code = """
class PaymentProcessor:
    def process_payment(self, amount, payment_method, customer_id):
        '''Process a payment transaction.'''
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if payment_method not in ["credit_card", "debit_card", "paypal"]:
            raise ValueError("Invalid payment method")
        
        # Check customer credit
        if not self._check_customer_credit(customer_id):
            return {"status": "declined", "reason": "Insufficient credit"}
        
        # Process based on method
        if payment_method == "credit_card":
            result = self._process_credit_card(amount, customer_id)
        elif payment_method == "debit_card":
            result = self._process_debit_card(amount, customer_id)
        else:
            result = self._process_paypal(amount, customer_id)
        
        # Log transaction
        self._log_transaction(customer_id, amount, result)
        
        return result
"""
    
    context = AIExecutionContext(
        task_type=TaskType.COVERAGE_INFERENCE,
        user="demo_user",
        max_cost=0.15,
    )
    
    print("Analyzing coverage needs for: PaymentProcessor.process_payment()")
    print(f"Language: Python\n")
    
    try:
        result = orchestrator.execute_skill(
            skill=reasoner,
            inputs={
                "source_file": "payments/processor.py",
                "source_code": source_code,
                "language": "python",
            },
            context=context,
        )
        
        print("Coverage Analysis:")
        print(f"  Complexity Score: {result['complexity_score']}/10")
        
        if result.get('critical_paths'):
            print(f"  Critical Paths:")
            for path in result['critical_paths']:
                print(f"    - {path}")
        
        if result.get('edge_cases'):
            print(f"  Edge Cases:")
            for case in result['edge_cases']:
                print(f"    - {case}")
        
        if result.get('test_scenarios'):
            print(f"  Recommended Test Scenarios:")
            for scenario in result['test_scenarios'][:3]:  # Show first 3
                print(f"    - [{scenario.get('priority', 'N/A')}] {scenario.get('scenario', '')}")
        
        print(f"\nRecommendation: {result['coverage_recommendation']}")
        print("\n✅ Coverage inference completed successfully!")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")


def demo_governance():
    """Demonstrate governance features."""
    print("\n" + "="*80)
    print("DEMO 5: Governance & Cost Tracking")
    print("="*80 + "\n")
    
    orchestrator = get_orchestrator()
    
    # Get cost summary
    cost_summary = orchestrator.get_cost_summary()
    print("Cost Summary:")
    print(f"  Total Cost: ${cost_summary['total']:.4f}")
    print(f"  Today: ${cost_summary['today']:.4f}")
    print(f"  This Month: ${cost_summary['this_month']:.4f}")
    
    # Get usage stats
    usage_stats = orchestrator.get_usage_stats()
    print(f"\nUsage Statistics:")
    print(f"  Total Operations: {usage_stats['total_operations']}")
    print(f"  Total Tokens: {usage_stats['total_tokens']}")
    print(f"  Average Latency: {usage_stats['average_latency']:.2f}s")
    
    if usage_stats.get('by_task_type'):
        print(f"\n  By Task Type:")
        for task_type, stats in usage_stats['by_task_type'].items():
            print(f"    {task_type}: {stats['count']} ops, ${stats['cost']:.4f}")
    
    if usage_stats.get('by_provider'):
        print(f"\n  By Provider:")
        for provider, stats in usage_stats['by_provider'].items():
            print(f"    {provider}: {stats['count']} ops, ${stats['cost']:.4f}")
    
    print("\n✅ Governance tracking active!")


def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("CrossBridge AI Module - Demonstration")
    print("="*80)
    print("\nThis demo showcases the AI module's capabilities.")
    print("Note: Demos will only run if AI providers are available.\n")
    
    # Check available providers
    from core.ai.providers import get_available_providers
    available = get_available_providers()
    
    print(f"Available Providers: {[p.value for p in available]}")
    
    if not available:
        print("\n⚠️  Warning: No AI providers available!")
        print("To run demos, configure at least one provider:")
        print("  - OpenAI: Set OPENAI_API_KEY environment variable")
        print("  - Anthropic: Set ANTHROPIC_API_KEY environment variable")
        print("  - vLLM: Start vLLM server at http://localhost:8000")
        print("  - Ollama: Start Ollama at http://localhost:11434")
        return
    
    # Run demos
    demos = [
        ("Flaky Analysis", demo_flaky_analysis),
        ("Test Generation", demo_test_generation),
        ("Test Migration", demo_test_migration),
        ("Coverage Inference", demo_coverage_inference),
        ("Governance", demo_governance),
    ]
    
    for name, demo_func in demos:
        try:
            demo_func()
            time.sleep(1)  # Brief pause between demos
        except KeyboardInterrupt:
            print("\n\n⚠️  Demo interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Demo '{name}' failed: {e}")
            continue
    
    print("\n" + "="*80)
    print("Demo completed! Check data/ai/ for audit logs and cost tracking.")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
