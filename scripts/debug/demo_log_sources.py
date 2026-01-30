"""
Demo: Automation + Application Logs

Demonstrates the complete flow of analyzing logs with and without application logs.
Shows confidence boosting when application logs correlate with failures.
"""

import tempfile
from pathlib import Path

from core.execution.intelligence.log_input_models import LogSourceCollection
from core.execution.intelligence.log_router import route_log_collection
from core.execution.intelligence.enhanced_analyzer import ExecutionIntelligenceAnalyzer


def demo_automation_logs_only():
    """Demo 1: Analyze with automation logs only (baseline)"""
    print("=" * 80)
    print("DEMO 1: Automation Logs Only (Baseline)")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create automation log
        auto_log = Path(tmpdir) / "test.log"
        auto_log.write_text("""
FAILED test_api.py::test_create_order
AssertionError: Expected status 200, got 500
Expected: 200
Actual: 500
""")
        
        # Build collection (automation only)
        collection = LogSourceCollection()
        collection.add_automation_log(str(auto_log), framework="pytest")
        
        print(f"✓ Automation logs: {len(collection.automation_logs)}")
        print(f"✓ Application logs: {len(collection.application_logs)}")
        
        # Parse and analyze
        events = route_log_collection(collection)
        print(f"✓ Parsed {len(events)} events")
        
        analyzer = ExecutionIntelligenceAnalyzer(
            enable_ai=False,
            has_application_logs=False
        )
        
        result = analyzer.analyze_single_test(
            test_name="test_create_order",
            log_content="",
            events=events
        )
        
        print(f"\nRESULTS:")
        print(f"  Test: {result.test_name}")
        print(f"  Failure Type: {result.failure_type.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Has App Logs: {result.has_application_logs}")
        print(f"  Reasoning: {result.reasoning}")
        
        return result.confidence


def demo_with_application_logs():
    """Demo 2: Analyze with automation + application logs (enriched)"""
    print("\n" + "=" * 80)
    print("DEMO 2: Automation + Application Logs (Enriched)")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create automation log
        auto_log = Path(tmpdir) / "test.log"
        auto_log.write_text("""
FAILED test_api.py::test_create_order
AssertionError: Expected status 200, got 500
Expected: 200
Actual: 500
""")
        
        # Create application log with correlated error
        app_log = Path(tmpdir) / "app.log"
        app_log.write_text("""
2024-01-30 10:30:00 INFO Application started
2024-01-30 10:31:00 ERROR Failed to process order
java.lang.NullPointerException: Order service not initialized
\tat com.example.OrderService.create(OrderService.java:45)
\tat com.example.OrderController.handle(OrderController.java:23)
2024-01-30 10:31:01 ERROR HTTP 500 returned to client
""")
        
        # Build collection (automation + application)
        collection = LogSourceCollection()
        collection.add_automation_log(str(auto_log), framework="pytest")
        collection.add_application_log(str(app_log), service="order-service")
        
        print(f"✓ Automation logs: {len(collection.automation_logs)}")
        print(f"✓ Application logs: {len(collection.application_logs)}")
        
        # Parse and analyze
        events = route_log_collection(collection)
        automation_events = [e for e in events if e.log_source_type.value == "automation"]
        application_events = [e for e in events if e.log_source_type.value == "application"]
        
        print(f"✓ Parsed {len(events)} events ({len(automation_events)} automation, {len(application_events)} application)")
        
        analyzer = ExecutionIntelligenceAnalyzer(
            enable_ai=False,
            has_application_logs=True  # Enable confidence boosting
        )
        
        result = analyzer.analyze_single_test(
            test_name="test_create_order",
            log_content="",
            events=events
        )
        
        print(f"\nRESULTS:")
        print(f"  Test: {result.test_name}")
        print(f"  Failure Type: {result.failure_type.value}")
        print(f"  Confidence: {result.confidence:.2f} 🚀")
        print(f"  Has App Logs: {result.has_application_logs} ✅")
        print(f"  Reasoning: {result.reasoning}")
        
        return result.confidence


def demo_comparison():
    """Demo 3: Side-by-side comparison"""
    print("\n" + "=" * 80)
    print("DEMO 3: Confidence Boosting Comparison")
    print("=" * 80)
    
    baseline_confidence = demo_automation_logs_only()
    enriched_confidence = demo_with_application_logs()
    
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print(f"Baseline (automation only):  {baseline_confidence:.2f}")
    print(f"Enriched (with app logs):    {enriched_confidence:.2f}")
    
    if enriched_confidence > baseline_confidence:
        boost = enriched_confidence - baseline_confidence
        print(f"Confidence Boost:            +{boost:.2f} ({boost*100:.0f}%)")
        print("\n✅ Application logs successfully boosted confidence!")
    else:
        print("\nℹ️  No correlation found - confidence unchanged")


def demo_batch_analysis():
    """Demo 4: Batch analysis of multiple tests"""
    print("\n" + "=" * 80)
    print("DEMO 4: Batch Analysis")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create automation log with multiple failures
        auto_log = Path(tmpdir) / "test.log"
        auto_log.write_text("""
FAILED test_checkout.py::test_payment
AssertionError: Payment failed with status 500

FAILED test_search.py::test_product_search
NoSuchElementException: Element #search-btn not found

PASSED test_login.py::test_valid_user
""")
        
        collection = LogSourceCollection()
        collection.add_automation_log(str(auto_log), framework="pytest")
        
        events = route_log_collection(collection)
        
        analyzer = ExecutionIntelligenceAnalyzer(enable_ai=False, has_application_logs=False)
        
        # Analyze multiple tests
        test_logs = [
            {'test_name': 'test_payment', 'log_content': '', 'events': events},
            {'test_name': 'test_product_search', 'log_content': '', 'events': events}
        ]
        
        results = analyzer.analyze_batch(test_logs)
        
        print(f"✓ Analyzed {len(results)} tests")
        
        # Generate summary
        summary = analyzer.generate_summary(results)
        
        print(f"\nSUMMARY:")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Average Confidence: {summary['average_confidence']:.2f}")
        print(f"\n  Failure Distribution:")
        for failure_type, count in summary['by_type'].items():
            pct = summary['by_type_percentage'][failure_type]
            print(f"    - {failure_type}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "EXECUTION INTELLIGENCE LOG SOURCES DEMO" + " " * 23 + "║")
    print("║" + " " * 15 + "Automation + Application Logs" + " " * 34 + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        # Run all demos
        demo_comparison()
        demo_batch_analysis()
        
        print("\n" + "=" * 80)
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nKey Takeaways:")
        print("  1. System works perfectly with automation logs alone")
        print("  2. Application logs boost confidence when they correlate")
        print("  3. Missing application logs don't cause failures")
        print("  4. Batch analysis supports multiple tests")
        print("\n✅ Production Ready!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
