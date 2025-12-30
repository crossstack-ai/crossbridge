"""
Phase-2 CLI Commands for Flaky Detection.

New commands:
- crossbridge flaky explain: Detailed explanation of why a test is flaky
- crossbridge flaky steps: Show flaky steps in BDD scenarios
- crossbridge flaky frameworks: Show flaky tests grouped by framework
"""

import sys
import json
from typing import Optional, List
from datetime import datetime, timedelta

from core.flaky_detection.multi_framework_detector import (
    MultiFrameworkFlakyDetector,
    MultiFrameworkDetectorConfig
)
from core.flaky_detection.persistence import FlakyDetectionRepository
from core.flaky_detection.confidence_calibration import create_confidence_explanation
from core.flaky_detection.models import TestFramework


def cmd_explain_flaky(
    db_url: str,
    test_id: str,
    output_format: str = "text",
    verbose: bool = False
):
    """
    Explain why a specific test is flaky.
    
    Usage:
        crossbridge flaky explain --db-url <url> --test-id <id> [--format json] [--verbose]
    
    Args:
        db_url: Database connection URL
        test_id: Test identifier to explain
        output_format: Output format (text/json)
        verbose: Include detailed feature breakdown
    """
    repo = FlakyDetectionRepository(db_url)
    
    # Get test detection result
    flaky_result = repo.get_flaky_test(test_id)
    
    if not flaky_result:
        print(f"Test not found in flaky detection database: {test_id}", file=sys.stderr)
        return 1
    
    # Get execution history
    executions = repo.get_test_executions(test_id, limit=100)
    
    if output_format == "json":
        explanation = _create_json_explanation(flaky_result, executions, verbose)
        print(json.dumps(explanation, indent=2))
    else:
        _print_text_explanation(flaky_result, executions, verbose)
    
    return 0


def cmd_list_flaky_steps(
    db_url: str,
    scenario_id: Optional[str] = None,
    min_confidence: float = 0.5,
    severity: Optional[str] = None,
    top_n: int = 10,
    output_format: str = "table"
):
    """
    List flaky steps in BDD scenarios.
    
    Usage:
        crossbridge flaky steps --db-url <url> [--scenario-id <id>] [--min-confidence 0.7] [--top 10]
    
    Args:
        db_url: Database connection URL
        scenario_id: Optional scenario filter
        min_confidence: Minimum confidence threshold
        severity: Filter by severity (critical/high/medium/low)
        top_n: Number of top flaky steps to show
        output_format: Output format (table/json/csv)
    """
    repo = FlakyDetectionRepository(db_url)
    
    # Get flaky steps
    # Note: This requires implementing step persistence in repository
    # For now, we'll show a placeholder
    
    print("Step-level flaky detection results:\n")
    print("Coming soon: Full step-level persistence and querying")
    print("\nFor now, use 'crossbridge flaky analyze --enable-steps' to detect step flakiness")
    
    return 0


def cmd_list_by_framework(
    db_url: str,
    framework: Optional[str] = None,
    min_confidence: float = 0.5,
    output_format: str = "table"
):
    """
    List flaky tests grouped by framework.
    
    Usage:
        crossbridge flaky frameworks --db-url <url> [--framework selenium-java] [--format table]
    
    Args:
        db_url: Database connection URL
        framework: Optional framework filter
        min_confidence: Minimum confidence threshold
        output_format: Output format (table/json/csv)
    """
    repo = FlakyDetectionRepository(db_url)
    
    # Get all flaky tests
    all_flaky = repo.get_all_flaky_tests()
    
    # Filter by confidence
    flaky_tests = [
        t for t in all_flaky
        if t.confidence >= min_confidence
    ]
    
    # Filter by framework if specified
    if framework:
        try:
            framework_enum = TestFramework(framework)
            flaky_tests = [t for t in flaky_tests if t.framework == framework_enum]
        except ValueError:
            print(f"Unknown framework: {framework}", file=sys.stderr)
            print(f"Valid frameworks: {', '.join(f.value for f in TestFramework)}")
            return 1
    
    # Group by framework
    by_framework = {}
    for test in flaky_tests:
        fw = test.framework.value
        if fw not in by_framework:
            by_framework[fw] = []
        by_framework[fw].append(test)
    
    if output_format == "json":
        _print_json_by_framework(by_framework)
    elif output_format == "csv":
        _print_csv_by_framework(by_framework)
    else:
        _print_table_by_framework(by_framework)
    
    return 0


def cmd_confidence_report(
    db_url: str,
    output_format: str = "text"
):
    """
    Show confidence distribution across all flaky tests.
    
    Usage:
        crossbridge flaky confidence --db-url <url> [--format json]
    
    Args:
        db_url: Database connection URL
        output_format: Output format (text/json)
    """
    repo = FlakyDetectionRepository(db_url)
    all_flaky = repo.get_all_flaky_tests()
    
    if not all_flaky:
        print("No flaky tests found")
        return 0
    
    # Calculate confidence statistics
    confidences = [t.confidence for t in all_flaky]
    
    # Group by confidence bands
    bands = {
        "high (≥0.7)": [t for t in all_flaky if t.confidence >= 0.7],
        "medium (0.5-0.7)": [t for t in all_flaky if 0.5 <= t.confidence < 0.7],
        "low (<0.5)": [t for t in all_flaky if t.confidence < 0.5],
    }
    
    if output_format == "json":
        result = {
            "total_flaky_tests": len(all_flaky),
            "average_confidence": sum(confidences) / len(confidences),
            "distribution": {
                name: {
                    "count": len(tests),
                    "percentage": len(tests) / len(all_flaky) * 100
                }
                for name, tests in bands.items()
            }
        }
        print(json.dumps(result, indent=2))
    else:
        print("Confidence Distribution:\n")
        print(f"Total flaky tests: {len(all_flaky)}")
        print(f"Average confidence: {sum(confidences) / len(confidences):.1%}\n")
        
        for name, tests in bands.items():
            pct = len(tests) / len(all_flaky) * 100
            print(f"  {name:20} {len(tests):4} tests ({pct:5.1f}%)")
    
    return 0


# ============================================================================
# Helper Functions
# ============================================================================

def _create_json_explanation(flaky_result, executions, verbose):
    """Create JSON explanation."""
    explanation = {
        "test_id": flaky_result.test_id,
        "test_name": flaky_result.test_name,
        "framework": flaky_result.framework.value,
        "classification": flaky_result.classification,
        "severity": flaky_result.severity,
        "confidence": round(flaky_result.confidence, 2),
        "flaky_score": round(flaky_result.flaky_score, 3),
        "primary_indicators": flaky_result.primary_indicators,
        "detection": {
            "detected_at": flaky_result.detected_at.isoformat(),
            "model_version": flaky_result.model_version,
        }
    }
    
    if verbose:
        explanation["features"] = {
            "failure_rate": round(flaky_result.features.failure_rate, 2),
            "switch_rate": round(flaky_result.features.pass_fail_switch_rate, 2),
            "duration_cv": round(flaky_result.features.duration_cv, 2),
            "unique_errors": flaky_result.features.unique_error_count,
            "retry_success_rate": round(flaky_result.features.retry_success_rate, 2),
            "total_executions": flaky_result.features.execution_count,
        }
        
        explanation["execution_summary"] = {
            "total": len(executions),
            "passed": sum(1 for e in executions if e.status == "passed"),
            "failed": sum(1 for e in executions if e.status == "failed"),
            "first": executions[-1].execution_time.isoformat() if executions else None,
            "last": executions[0].execution_time.isoformat() if executions else None,
        }
    
    return explanation


def _print_text_explanation(flaky_result, executions, verbose):
    """Print text explanation."""
    print(f"Flaky Test Explanation: {flaky_result.test_id}\n")
    print("=" * 80)
    
    # Basic info
    print(f"\nTest: {flaky_result.test_name or flaky_result.test_id}")
    print(f"Framework: {flaky_result.framework.value}")
    print(f"Classification: {flaky_result.classification.upper()}")
    print(f"Severity: {flaky_result.severity.upper()}")
    print(f"Confidence: {flaky_result.confidence:.1%}")
    
    # Why it's flaky
    print(f"\nWhy this test is flaky:")
    for indicator in flaky_result.primary_indicators:
        print(f"  • {indicator}")
    
    # Key metrics
    print(f"\nKey Metrics:")
    print(f"  Failure rate: {flaky_result.features.failure_rate:.1%}")
    print(f"  Pass/fail switches: {flaky_result.features.pass_fail_switch_rate:.1%}")
    print(f"  Duration variance (CV): {flaky_result.features.duration_cv:.2f}")
    print(f"  Unique error types: {flaky_result.features.unique_error_count}")
    print(f"  Total executions: {flaky_result.features.execution_count}")
    
    if verbose and executions:
        print(f"\nRecent Execution History:")
        passed = sum(1 for e in executions if e.status == "passed")
        failed = sum(1 for e in executions if e.status == "failed")
        print(f"  Passed: {passed}/{len(executions)} ({passed/len(executions):.1%})")
        print(f"  Failed: {failed}/{len(executions)} ({failed/len(executions):.1%})")
        
        if executions:
            time_span = executions[0].execution_time - executions[-1].execution_time
            print(f"  Time span: {time_span.days} days")
        
        # Show last 5 executions
        print(f"\n  Last 5 executions:")
        for i, e in enumerate(executions[:5]):
            status_icon = "✓" if e.status == "passed" else "✗"
            print(f"    {i+1}. {status_icon} {e.status:8} {e.execution_time.strftime('%Y-%m-%d %H:%M')}")
    
    # Recommendations
    print(f"\nRecommendations:")
    if flaky_result.severity in ("critical", "high"):
        print("  ⚠️  HIGH PRIORITY: Fix or quarantine immediately")
        print("  • Review test for timing issues, race conditions, or external dependencies")
        print("  • Add explicit waits or retries as needed")
        print("  • Consider running in isolation to identify root cause")
    elif flaky_result.severity == "medium":
        print("  • Schedule for fixing in upcoming sprint")
        print("  • Monitor for worsening trends")
    else:
        print("  • Continue monitoring")
        print("  • May resolve with more test data")
    
    print("\n" + "=" * 80)


def _print_table_by_framework(by_framework):
    """Print table grouped by framework."""
    print("\nFlaky Tests by Framework:\n")
    
    for framework, tests in sorted(by_framework.items()):
        print(f"\n{framework.upper()}: {len(tests)} flaky tests")
        print("-" * 80)
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
        sorted_tests = sorted(tests, key=lambda t: (
            severity_order.get(t.severity, 4),
            -t.confidence
        ))
        
        for test in sorted_tests[:10]:  # Top 10 per framework
            conf_str = f"{test.confidence:.0%}"
            severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(test.severity, "⚪")
            print(f"  {severity_icon} {test.test_name or test.test_id:60} {test.severity:8} {conf_str:>4}")
        
        if len(tests) > 10:
            print(f"  ... and {len(tests) - 10} more")


def _print_json_by_framework(by_framework):
    """Print JSON grouped by framework."""
    result = {
        framework: [
            {
                "test_id": t.test_id,
                "test_name": t.test_name,
                "severity": t.severity,
                "confidence": round(t.confidence, 2),
                "failure_rate": round(t.features.failure_rate, 2)
            }
            for t in tests
        ]
        for framework, tests in by_framework.items()
    }
    
    print(json.dumps(result, indent=2))


def _print_csv_by_framework(by_framework):
    """Print CSV grouped by framework."""
    print("framework,test_id,test_name,severity,confidence,failure_rate")
    
    for framework, tests in by_framework.items():
        for test in tests:
            print(f"{framework},{test.test_id},{test.test_name or ''},"
                  f"{test.severity},{test.confidence:.2f},"
                  f"{test.features.failure_rate:.2f}")
