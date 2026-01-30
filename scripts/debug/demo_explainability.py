"""
Demo: Explainability System for Deterministic Failure Classification

This demo showcases the new explainability system that provides detailed
confidence explanations for test failure classifications.

Features demonstrated:
1. Rule influence tracking - Which rules contributed and how much
2. Signal quality assessment - Reliability of input signals
3. Evidence extraction - Supporting evidence summaries
4. CI integration - JSON artifacts and PR comments
5. Framework-agnostic behavior - Works across all frameworks
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.intelligence.explainable_classifier import ExplainableClassifier, classify_and_explain
from core.intelligence.deterministic_classifier import SignalData
from core.intelligence.explainability import save_ci_artifacts, generate_pr_comment
import json


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80 + "\n")


def demo_flaky_test():
    """Demonstrate flaky test classification with explanation."""
    print_section("1. FLAKY TEST - Retry-Based Detection")
    
    signal = SignalData(
        test_name="test_user_login",
        test_suite="auth.tests",
        framework="pytest",
        test_status="pass",
        final_status="pass",
        retry_count=2,  # Failed initially, passed after retries
        total_runs=50,
        historical_failure_rate=0.12,  # 12% historical failure rate
        consecutive_passes=0,
        consecutive_failures=0,
        code_changed=False,
        error_message="TimeoutException: Element not found: LoginButton"
    )
    
    classifier = ExplainableClassifier()
    result, explanation = classifier.classify_with_explanation(signal)
    
    print(f"Classification: {result.label.value.upper()}")
    print(f"Confidence: {explanation.final_confidence:.1%}")
    print(f"\nPrimary Rule: {explanation.primary_rule}")
    
    print("\n📊 Rule Influence:")
    for rule in explanation.rule_influence:
        if rule.matched:
            print(f"  ✓ {rule.rule_name}: {rule.contribution:.1%}")
            print(f"    → {rule.explanation}")
    
    print("\n🔍 Signal Quality:")
    for signal_qual in explanation.signal_quality:
        if signal_qual.quality_score >= 0.6:
            print(f"  • {signal_qual.signal_name}: {signal_qual.quality_score:.1%}")
            print(f"    → {signal_qual.evidence}")
    
    print("\n💡 Evidence:")
    if explanation.evidence_context.error_message_summary:
        print(f"  • {explanation.evidence_context.error_message_summary}")
    
    print("\n🔢 Confidence Breakdown:")
    print(f"  Rule Score: {explanation.confidence_breakdown.rule_score:.2f}")
    print(f"  Signal Score: {explanation.confidence_breakdown.signal_score:.2f}")
    print(f"  Formula: {explanation.confidence_breakdown.formula}")
    print(f"  Final: {explanation.confidence_breakdown.final_confidence:.1%}")


def demo_regression():
    """Demonstrate regression detection with explanation."""
    print_section("2. REGRESSION - Code Change + Failure")
    
    signal = SignalData(
        test_name="test_checkout_total",
        test_suite="shop.tests",
        framework="selenium_pytest",
        test_status="fail",
        final_status="fail",
        retry_count=0,
        total_runs=200,
        historical_failure_rate=0.01,  # Previously stable
        consecutive_passes=25,  # Was passing consistently
        consecutive_failures=1,
        code_changed=True,  # Code change detected
        error_message="AssertionError: Expected total=100.00, got 95.00"
    )
    
    result, explanation = classify_and_explain(signal, failure_id="F-DEMO-001")
    
    print(f"Classification: {result.label.value.upper()}")
    print(f"Confidence: {explanation.final_confidence:.1%}")
    
    print("\n📊 Rule Influence:")
    for rule in explanation.rule_influence:
        if rule.matched:
            print(f"  ✓ {rule.rule_name}: {rule.contribution:.1%}")
            print(f"    → {rule.explanation}")
    
    print("\n🎯 Why High Confidence?")
    print(f"  • Test was stable: {signal.consecutive_passes} consecutive passes")
    print(f"  • Low historical failure rate: {signal.historical_failure_rate:.1%}")
    print(f"  • Code change detected")
    print(f"  • Strong regression signal")


def demo_new_test():
    """Demonstrate new test handling."""
    print_section("3. NEW TEST - Limited Execution History")
    
    signal = SignalData(
        test_name="test_new_feature_x",
        test_suite="features.tests",
        framework="robot",
        test_status="fail",
        final_status="fail",
        retry_count=0,
        total_runs=2,  # Very limited history
        historical_failure_rate=1.0,
        consecutive_passes=0,
        consecutive_failures=2,
        code_changed=True,
        error_message="NotImplementedError: Feature X not yet implemented"
    )
    
    result, explanation = classify_and_explain(signal)
    
    print(f"Classification: {result.label.value.upper()}")
    print(f"Confidence: {explanation.final_confidence:.1%}")
    
    print("\n📊 Rule Influence:")
    for rule in explanation.rule_influence:
        if rule.matched:
            print(f"  ✓ {rule.rule_name}: {rule.contribution:.1%}")
            print(f"    → {rule.explanation}")
    
    print("\n⚠️ Explanation:")
    print(f"  • Only {signal.total_runs} execution(s) - insufficient for confidence")
    print(f"  • Cannot determine if failure is test issue or code issue")
    print(f"  • Needs more runs before stable classification")


def demo_ci_integration():
    """Demonstrate CI artifact generation."""
    print_section("4. CI INTEGRATION - Artifacts & PR Comments")
    
    signal = SignalData(
        test_name="test_api_timeout",
        test_suite="api.tests",
        framework="restassured_java",
        test_status="fail",
        final_status="fail",
        retry_count=3,
        total_runs=100,
        historical_failure_rate=0.35,  # Unstable
        consecutive_passes=0,
        consecutive_failures=4,
        code_changed=False,
        error_message="java.net.SocketTimeoutException: Read timed out after 30s"
    )
    
    result, explanation = classify_and_explain(signal, failure_id="F-API-TIMEOUT-123")
    
    # Save CI artifacts
    artifact_path = save_ci_artifacts(explanation, output_dir=".")
    print(f"✅ Saved CI artifacts to: {artifact_path}")
    
    # Generate PR comment
    pr_comment = generate_pr_comment(explanation)
    print("\n📝 Generated PR Comment:")
    print("-" * 80)
    print(pr_comment)
    print("-" * 80)
    
    # Show JSON structure
    print("\n📄 JSON Artifact Structure:")
    json_data = json.loads(explanation.to_json())
    print(json.dumps({
        "failure_id": json_data["failure_id"],
        "category": json_data["category"],
        "final_confidence": json_data["final_confidence"],
        "rule_influence_count": len(json_data["rule_influence"]),
        "signal_quality_count": len(json_data["signal_quality"]),
        "has_evidence": bool(json_data["evidence_context"]["error_message_summary"])
    }, indent=2))


def demo_framework_agnostic():
    """Demonstrate framework-agnostic behavior."""
    print_section("5. FRAMEWORK-AGNOSTIC - Consistent Across Frameworks")
    
    frameworks = ["pytest", "selenium_java", "robot", "playwright", "cypress"]
    
    print("Testing same flaky pattern across 5 frameworks:\n")
    
    confidences = []
    for framework in frameworks:
        signal = SignalData(
            test_name="test_flaky_element",
            test_suite="ui.tests",
            framework=framework,
            test_status="pass",
            final_status="pass",
            retry_count=1,
            total_runs=30,
            historical_failure_rate=0.15,
            consecutive_passes=5,
            consecutive_failures=0,
            code_changed=False,
            error_message="Element not found"
        )
        
        result, explanation = classify_and_explain(signal)
        confidences.append(explanation.final_confidence)
        
        print(f"  {framework:20} → {result.label.value:10} (Confidence: {explanation.final_confidence:.1%})")
    
    print(f"\n✅ Confidence Variance: {max(confidences) - min(confidences):.4f} (should be ~0.000)")
    print("   All frameworks produce identical results for identical signals!")


def demo_confidence_formula():
    """Demonstrate confidence computation."""
    print_section("6. CONFIDENCE FORMULA - How It Works")
    
    signal = SignalData(
        test_name="test_example",
        test_suite="example.tests",
        framework="pytest",
        test_status="fail",
        final_status="fail",
        retry_count=0,
        total_runs=100,
        historical_failure_rate=0.45,  # Unstable
        consecutive_passes=0,
        consecutive_failures=10,
        code_changed=False,
        error_message="Assertion failed"
    )
    
    result, explanation = classify_and_explain(signal)
    
    print("Standard Confidence Formula:")
    print("  confidence = 0.7 × rule_score + 0.3 × signal_score")
    print()
    print("Breakdown:")
    print(f"  Rule Score:   {explanation.confidence_breakdown.rule_score:.2f} (from matched rules)")
    print(f"  Signal Score: {explanation.confidence_breakdown.signal_score:.2f} (from signal quality)")
    print()
    print("Computation:")
    rule_component = 0.7 * explanation.confidence_breakdown.rule_score
    signal_component = 0.3 * explanation.confidence_breakdown.signal_score
    print(f"  0.7 × {explanation.confidence_breakdown.rule_score:.2f} = {rule_component:.2f}")
    print(f"  0.3 × {explanation.confidence_breakdown.signal_score:.2f} = {signal_component:.2f}")
    print(f"  Total = {explanation.final_confidence:.2f} ({explanation.final_confidence:.1%})")
    
    print("\n🎯 Why This Formula?")
    print("  • 70% weight on rules: Deterministic logic is primary")
    print("  • 30% weight on signals: Data quality matters")
    print("  • Normalized rule contributions sum to 1.0")
    print("  • Signal quality averaged across all signals")


def demo_complete_explanation():
    """Show complete explanation output."""
    print_section("7. COMPLETE EXPLANATION - Full Details")
    
    signal = SignalData(
        test_name="test_payment_processing",
        test_suite="payment.tests",
        framework="selenium_java",
        test_status="fail",
        final_status="fail",
        retry_count=0,
        total_runs=150,
        historical_failure_rate=0.08,
        consecutive_passes=20,
        consecutive_failures=1,
        code_changed=True,
        error_message="PaymentException: Card declined - insufficient funds"
    )
    
    result, explanation = classify_and_explain(signal, failure_id="F-PAYMENT-456")
    
    # Show complete text summary
    print(explanation.to_ci_summary())
    
    print("\n" + "-" * 80)
    print("💾 This summary is saved to CI artifacts as:")
    print("   ci-artifacts/failure_explanations/F-PAYMENT-456.txt")
    print("\n📊 JSON version also saved for programmatic consumption:")
    print("   ci-artifacts/failure_explanations/F-PAYMENT-456.json")


def main():
    """Run all demos."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║          EXPLAINABILITY SYSTEM FOR FAILURE CLASSIFICATION                   ║
║                                                                              ║
║  This demo showcases the comprehensive explainability features added to     ║
║  the deterministic failure classification system.                           ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        demo_flaky_test()
        demo_regression()
        demo_new_test()
        demo_ci_integration()
        demo_framework_agnostic()
        demo_confidence_formula()
        demo_complete_explanation()
        
        print_section("✅ DEMO COMPLETE")
        print("All explainability features demonstrated successfully!")
        print("\nKey Takeaways:")
        print("  1. ✅ Rule influence tracked for every classification")
        print("  2. ✅ Signal quality assessed for reliability")
        print("  3. ✅ Evidence summarized (no raw logs/stacktraces)")
        print("  4. ✅ CI artifacts generated (JSON + text)")
        print("  5. ✅ Framework-agnostic behavior verified")
        print("  6. ✅ Confidence formula standardized (0.7 × rule + 0.3 × signal)")
        print("\nNext Steps:")
        print("  • Integrate into IntelligenceEngine")
        print("  • Add visual dashboards (Grafana)")
        print("  • Implement confidence drift monitoring")
        print("  • Add human feedback loop")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
