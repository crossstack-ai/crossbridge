"""
Example: Flaky Test Detection Demo

Demonstrates the complete flaky test detection workflow using
synthetic data.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.flaky_detection import (
    TestExecutionRecord,
    TestFramework,
    TestStatus,
    FeatureEngineer,
    FlakyDetector,
    FlakyDetectionConfig
)


def generate_stable_test_history(test_id: str, num_executions: int = 30):
    """Generate execution history for a stable test."""
    executions = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(num_executions):
        # Stable test: always passes with consistent duration
        record = TestExecutionRecord(
            test_id=test_id,
            framework=TestFramework.JUNIT,
            status=TestStatus.PASSED,
            duration_ms=100 + random.uniform(-5, 5),  # Small variance
            executed_at=base_time + timedelta(hours=i*24/num_executions),
            git_commit=f"commit_{i//5}",  # Same commit for groups of 5
            environment="ci"
        )
        executions.append(record)
    
    return executions


def generate_flaky_test_history(test_id: str, num_executions: int = 30):
    """Generate execution history for a flaky test."""
    executions = []
    base_time = datetime.now() - timedelta(days=30)
    
    error_types = [
        "AssertionError: Element not found",
        "TimeoutException: Timed out waiting for element",
        "StaleElementReferenceException: Element is stale"
    ]
    
    for i in range(num_executions):
        # Flaky test: intermittent failures with varying errors
        is_failed = random.random() < 0.4  # 40% failure rate
        
        if is_failed:
            status = TestStatus.FAILED
            error = random.choice(error_types)
        else:
            status = TestStatus.PASSED
            error = None
        
        # More duration variance in flaky tests
        duration = 150 + random.uniform(-50, 50)
        
        record = TestExecutionRecord(
            test_id=test_id,
            framework=TestFramework.JUNIT,
            status=status,
            duration_ms=duration,
            executed_at=base_time + timedelta(hours=i*24/num_executions),
            error_signature=error,
            git_commit=f"commit_{i//5}",
            environment="ci",
            retry_count=1 if is_failed and random.random() < 0.5 else 0
        )
        executions.append(record)
    
    return executions


def generate_broken_test_history(test_id: str, num_executions: int = 30):
    """Generate execution history for a consistently broken test."""
    executions = []
    base_time = datetime.now() - timedelta(days=30)
    
    for i in range(num_executions):
        # Broken test: always fails with same error
        record = TestExecutionRecord(
            test_id=test_id,
            framework=TestFramework.JUNIT,
            status=TestStatus.FAILED,
            duration_ms=80 + random.uniform(-5, 5),
            executed_at=base_time + timedelta(hours=i*24/num_executions),
            error_signature="NullPointerException: Object is null",
            git_commit=f"commit_{i//5}",
            environment="ci"
        )
        executions.append(record)
    
    return executions


def main():
    """Run the flaky detection demo."""
    print("=" * 70)
    print("Flaky Test Detection Demo")
    print("=" * 70)
    print()
    
    # Generate synthetic test data
    print("📊 Generating synthetic test execution data...")
    
    test_data = {}
    
    # Create 15 stable tests
    for i in range(15):
        test_id = f"com.example.StableTest.test{i}"
        test_data[test_id] = generate_stable_test_history(test_id)
    
    # Create 3 flaky tests
    for i in range(3):
        test_id = f"com.example.FlakyTest.test{i}"
        test_data[test_id] = generate_flaky_test_history(test_id)
    
    # Create 2 broken tests (consistently failing)
    for i in range(2):
        test_id = f"com.example.BrokenTest.test{i}"
        test_data[test_id] = generate_broken_test_history(test_id)
    
    print(f"   Generated {len(test_data)} tests:")
    print(f"     - 15 stable tests")
    print(f"     - 3 flaky tests")
    print(f"     - 2 broken tests")
    print()
    
    # Extract features
    print("🔧 Extracting features from execution history...")
    engineer = FeatureEngineer()
    feature_vectors = engineer.extract_batch_features(test_data)
    
    print(f"   Extracted features for {len(feature_vectors)} tests")
    print()
    
    # Show example features
    print("Example Feature Values:")
    print("-" * 70)
    
    # Show one stable test
    stable_example = next(k for k in feature_vectors.keys() if "Stable" in k)
    stable_features = feature_vectors[stable_example]
    print(f"Stable Test: {stable_example}")
    print(f"  Failure rate:     {stable_features.failure_rate:.2%}")
    print(f"  Switch rate:      {stable_features.pass_fail_switch_rate:.2%}")
    print(f"  Duration CV:      {stable_features.duration_cv:.2f}")
    print(f"  Unique errors:    {stable_features.unique_error_count}")
    print(f"  Confidence:       {stable_features.confidence:.2f}")
    print()
    
    # Show one flaky test
    flaky_example = next(k for k in feature_vectors.keys() if "Flaky" in k)
    flaky_features = feature_vectors[flaky_example]
    print(f"Flaky Test: {flaky_example}")
    print(f"  Failure rate:     {flaky_features.failure_rate:.2%}")
    print(f"  Switch rate:      {flaky_features.pass_fail_switch_rate:.2%}")
    print(f"  Duration CV:      {flaky_features.duration_cv:.2f}")
    print(f"  Unique errors:    {flaky_features.unique_error_count}")
    print(f"  Confidence:       {flaky_features.confidence:.2f}")
    print()
    
    # Show one broken test
    broken_example = next(k for k in feature_vectors.keys() if "Broken" in k)
    broken_features = feature_vectors[broken_example]
    print(f"Broken Test: {broken_example}")
    print(f"  Failure rate:     {broken_features.failure_rate:.2%}")
    print(f"  Switch rate:      {broken_features.pass_fail_switch_rate:.2%}")
    print(f"  Duration CV:      {broken_features.duration_cv:.2f}")
    print(f"  Unique errors:    {broken_features.unique_error_count}")
    print(f"  Confidence:       {broken_features.confidence:.2f}")
    print()
    
    # Train detector
    print("🤖 Training Isolation Forest model...")
    config = FlakyDetectionConfig(contamination=0.2)  # Expect 20% flaky
    detector = FlakyDetector(config)
    detector.train(list(feature_vectors.values()))
    
    print(f"   Model trained on {detector.training_sample_count} tests")
    print()
    
    # Detect flaky tests
    print("🎯 Detecting flaky tests...")
    framework_map = {test_id: TestFramework.JUNIT for test_id in feature_vectors.keys()}
    name_map = {test_id: test_id.split('.')[-1] for test_id in feature_vectors.keys()}
    
    results = detector.detect_batch(feature_vectors, framework_map, name_map)
    
    # Analyze results
    flaky_results = [r for r in results.values() if r.is_flaky]
    stable_results = [r for r in results.values() if not r.is_flaky]
    
    print(f"   Detected {len(flaky_results)} flaky tests")
    print(f"   Classified {len(stable_results)} as stable")
    print()
    
    # Show detection results
    print("=" * 70)
    print("Detection Results")
    print("=" * 70)
    print()
    
    print("Flaky Tests Detected:")
    print("-" * 70)
    for result in sorted(flaky_results, key=lambda r: r.features.failure_rate, reverse=True):
        test_type = "FLAKY" if "Flaky" in result.test_id else ("BROKEN" if "Broken" in result.test_id else "STABLE")
        correct = "✅" if test_type == "FLAKY" or test_type == "BROKEN" else "❌"
        
        print(f"{correct} {result.test_id}")
        print(f"   Classification: {result.classification}")
        print(f"   Severity:       {result.severity}")
        print(f"   Confidence:     {result.confidence:.2f}")
        print(f"   Failure rate:   {result.features.failure_rate:.1%}")
        print(f"   Indicators:")
        for indicator in result.primary_indicators[:3]:
            print(f"     - {indicator}")
        print()
    
    if not flaky_results:
        print("   None detected")
        print()
    
    # Calculate accuracy
    print("=" * 70)
    print("Accuracy Analysis")
    print("=" * 70)
    print()
    
    true_flaky = [r for r in results.values() if "Flaky" in r.test_id]
    detected_flaky = flaky_results
    
    # True positives: Correctly identified flaky tests
    true_positives = sum(1 for r in detected_flaky if "Flaky" in r.test_id)
    
    # False positives: Stable tests marked as flaky
    false_positives = sum(1 for r in detected_flaky if "Stable" in r.test_id)
    
    # False negatives: Flaky tests marked as stable
    false_negatives = sum(1 for r in stable_results if "Flaky" in r.test_id)
    
    # Note: Broken tests (100% failure) should NOT be flagged as flaky
    broken_correctly_identified = sum(1 for r in detected_flaky if "Broken" in r.test_id)
    
    print(f"True Positives (Flaky detected as flaky):     {true_positives}")
    print(f"False Positives (Stable detected as flaky):   {false_positives}")
    print(f"False Negatives (Flaky detected as stable):   {false_negatives}")
    print(f"Broken tests flagged as flaky:                {broken_correctly_identified}")
    print()
    
    if len(true_flaky) > 0:
        recall = true_positives / len(true_flaky)
        print(f"Recall (Detection rate): {recall:.1%}")
    
    if len(detected_flaky) > 0:
        precision = true_positives / len(detected_flaky)
        print(f"Precision:               {precision:.1%}")
    
    print()
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print()
    print("Key Takeaways:")
    print("  • Flaky tests show intermittent failures (30-50% failure rate)")
    print("  • Stable tests have 0% failure rate and low variance")
    print("  • Broken tests have 100% failure rate (not flaky)")
    print("  • ML model detects flaky patterns automatically")
    print("  • Confidence increases with more execution data")
    print()


if __name__ == "__main__":
    main()
