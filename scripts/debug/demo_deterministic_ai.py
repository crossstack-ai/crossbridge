"""
Demo: Deterministic + AI Behavior System

This script demonstrates the new intelligence system that provides:
- Guaranteed deterministic classification
- Optional AI enrichment
- Graceful AI failure handling
"""

from core.intelligence.intelligence_engine import (
    IntelligenceEngine,
    SignalData,
    classify_test
)
from core.intelligence.intelligence_config import IntelligenceConfig


def demo_basic_classification():
    """Demo: Basic test classification."""
    print("\n" + "=" * 70)
    print("DEMO 1: Basic Classification")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "New Test",
            "signal": SignalData(
                test_name="test_new_feature",
                test_status="pass",
                total_runs=0
            )
        },
        {
            "name": "Flaky Test (Retry)",
            "signal": SignalData(
                test_name="test_search_api",
                test_status="pass",
                retry_count=2,
                final_status="pass",
                total_runs=10
            )
        },
        {
            "name": "Stable Test",
            "signal": SignalData(
                test_name="test_homepage",
                test_status="pass",
                historical_failure_rate=0.01,
                total_runs=100
            )
        },
        {
            "name": "Unstable Test",
            "signal": SignalData(
                test_name="test_flaky_component",
                test_status="fail",
                historical_failure_rate=0.65,
                total_runs=50
            )
        },
        {
            "name": "Regression",
            "signal": SignalData(
                test_name="test_checkout",
                test_status="fail",
                code_changed=True,
                consecutive_passes=20,
                total_runs=25
            )
        }
    ]
    
    engine = IntelligenceEngine()
    
    for case in test_cases:
        result = engine.classify(case["signal"])
        
        print(f"\n{case['name']}:")
        print(f"  Classification: {result.label}")
        print(f"  Confidence: {result.deterministic_confidence:.0%}")
        print(f"  Reasons:")
        for reason in result.deterministic_reasons:
            print(f"    - {reason}")


def demo_convenience_function():
    """Demo: Convenience function for quick classification."""
    print("\n" + "=" * 70)
    print("DEMO 2: Convenience Function")
    print("=" * 70)
    
    result = classify_test(
        test_name="test_login",
        test_status="pass",
        retry_count=1,
        final_status="pass",
        historical_failure_rate=0.12,
        total_runs=25
    )
    
    print(f"\nTest: {result.test_name}")
    print(f"Classification: {result.label}")
    print(f"Confidence: {result.deterministic_confidence:.0%}")
    print(f"AI Enrichment: {'Yes' if result.ai_enrichment else 'No'}")


def demo_batch_classification():
    """Demo: Batch classification of multiple tests."""
    print("\n" + "=" * 70)
    print("DEMO 3: Batch Classification")
    print("=" * 70)
    
    signals = [
        SignalData(test_name="test_1", test_status="pass", total_runs=0),
        SignalData(test_name="test_2", test_status="pass", retry_count=1, final_status="pass", total_runs=5),
        SignalData(test_name="test_3", test_status="pass", historical_failure_rate=0.0, total_runs=50),
        SignalData(test_name="test_4", test_status="fail", historical_failure_rate=0.5, total_runs=20),
    ]
    
    engine = IntelligenceEngine()
    results = engine.batch_classify(signals)
    
    print(f"\nClassified {len(results)} tests:")
    for result in results:
        print(f"  {result.test_name}: {result.label} ({result.deterministic_confidence:.0%})")


def demo_custom_configuration():
    """Demo: Custom configuration."""
    print("\n" + "=" * 70)
    print("DEMO 4: Custom Configuration")
    print("=" * 70)
    
    # Create custom config
    config = IntelligenceConfig()
    config.deterministic.flaky_threshold = 0.15  # 15% instead of 10%
    config.ai.enabled = False  # Disable AI
    
    engine = IntelligenceEngine(config=config)
    
    # Test that would be "stable" with default threshold (10%)
    # but "flaky" with custom threshold (15%)
    signal = SignalData(
        test_name="test_borderline",
        test_status="pass",
        historical_failure_rate=0.12,  # 12% failure rate
        total_runs=50
    )
    
    result = engine.classify(signal)
    
    print(f"\nWith custom threshold (15%):")
    print(f"  Test: {signal.test_name}")
    print(f"  Failure Rate: {signal.historical_failure_rate:.0%}")
    print(f"  Classification: {result.label}")
    print(f"  Note: Would be 'stable' with default threshold (10%)")


def demo_health_monitoring():
    """Demo: Health monitoring and metrics."""
    print("\n" + "=" * 70)
    print("DEMO 5: Health Monitoring")
    print("=" * 70)
    
    engine = IntelligenceEngine()
    
    # Run some classifications
    for i in range(5):
        signal = SignalData(
            test_name=f"test_{i}",
            test_status="pass",
            total_runs=10 + i,
            historical_failure_rate=0.0
        )
        engine.classify(signal)
    
    # Get health status
    health = engine.get_health()
    
    print("\nSystem Health:")
    print(f"  Status: {health['status']}")
    print(f"\nDeterministic Classifier:")
    print(f"  Status: {health['deterministic']['status']}")
    print(f"  Total Classifications: {health['deterministic']['total_classifications']}")
    print(f"\nAI Enrichment:")
    print(f"  Status: {health['ai_enrichment']['status']}")
    print(f"  Enabled: {health['ai_enrichment']['enabled']}")
    print(f"  Success Rate: {health['ai_enrichment']['success_rate_pct']}%")


def demo_metrics():
    """Demo: Detailed metrics."""
    print("\n" + "=" * 70)
    print("DEMO 6: Detailed Metrics")
    print("=" * 70)
    
    engine = IntelligenceEngine()
    
    # Classify various test types
    test_types = [
        ("flaky", 3),
        ("stable", 5),
        ("unstable", 2),
    ]
    
    for label_type, count in test_types:
        for i in range(count):
            if label_type == "flaky":
                signal = SignalData(
                    test_name=f"test_{label_type}_{i}",
                    test_status="pass",
                    retry_count=1,
                    final_status="pass",
                    total_runs=10
                )
            elif label_type == "stable":
                signal = SignalData(
                    test_name=f"test_{label_type}_{i}",
                    test_status="pass",
                    historical_failure_rate=0.0,
                    total_runs=50
                )
            else:  # unstable
                signal = SignalData(
                    test_name=f"test_{label_type}_{i}",
                    test_status="fail",
                    historical_failure_rate=0.6,
                    total_runs=20
                )
            
            engine.classify(signal)
    
    # Get metrics
    metrics = engine.get_metrics()
    
    print("\nMetrics Summary:")
    print(f"  Total Classifications: {metrics['total_classifications']}")
    print(f"\nAI Enrichment:")
    print(f"  Attempted: {metrics['ai_enrichment']['attempted']}")
    print(f"  Success: {metrics['ai_enrichment']['success']}")
    print(f"  Failed: {metrics['ai_enrichment']['failed']}")
    print(f"  Success Rate: {metrics['ai_enrichment']['success_rate_pct']}%")
    print(f"\nLatency (ms):")
    print(f"  Deterministic P95: {metrics['latency']['deterministic_p95_ms']}")
    print(f"  AI P95: {metrics['latency']['ai_p95_ms']}")
    print(f"  Total P95: {metrics['latency']['final_p95_ms']}")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("CROSSBRIDGE: Deterministic + AI Behavior System Demo")
    print("=" * 70)
    
    demo_basic_classification()
    demo_convenience_function()
    demo_batch_classification()
    demo_custom_configuration()
    demo_health_monitoring()
    demo_metrics()
    
    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  ✓ Deterministic classification always works")
    print("  ✓ AI enrichment is optional and can fail safely")
    print("  ✓ Configuration is flexible and environment-aware")
    print("  ✓ Comprehensive metrics for monitoring")
    print("  ✓ Health checks for system status")
    print("\nFor more information, see:")
    print("  - docs/intelligence/DETERMINISTIC_AI_BEHAVIOR.md")
    print("  - intelligence_config.yaml.example")
    print()


if __name__ == "__main__":
    main()
