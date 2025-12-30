"""
CLI commands for flaky test detection.

Provides commands for analyzing test flakiness, listing flaky tests,
and managing flaky test detection.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import json

from core.flaky_detection import (
    FlakyDetector,
    FlakyDetectionConfig,
    FeatureEngineer,
    TestFramework
)
from core.flaky_detection.persistence import FlakyDetectionRepository
from core.flaky_detection.integrations import convert_test_results


def add_flaky_commands(subparsers):
    """Add flaky detection commands to CLI."""
    
    # Main flaky command group
    flaky_parser = subparsers.add_parser(
        'flaky',
        help='Flaky test detection and management'
    )
    
    flaky_subparsers = flaky_parser.add_subparsers(dest='flaky_command')
    
    # analyze command
    analyze_parser = flaky_subparsers.add_parser(
        'analyze',
        help='Analyze tests for flakiness'
    )
    analyze_parser.add_argument(
        '--db-url',
        required=True,
        help='Database connection URL'
    )
    analyze_parser.add_argument(
        '--framework',
        choices=['all', 'junit', 'cucumber', 'pytest', 'robot'],
        default='all',
        help='Framework to analyze (default: all)'
    )
    analyze_parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days of history to analyze (default: 30)'
    )
    analyze_parser.add_argument(
        '--min-executions',
        type=int,
        default=15,
        help='Minimum executions required for analysis (default: 15)'
    )
    analyze_parser.add_argument(
        '--output',
        help='Output JSON report to file'
    )
    analyze_parser.set_defaults(func=cmd_analyze_flakiness)
    
    # list command
    list_parser = flaky_subparsers.add_parser(
        'list',
        help='List detected flaky tests'
    )
    list_parser.add_argument(
        '--db-url',
        required=True,
        help='Database connection URL'
    )
    list_parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.5,
        help='Minimum confidence threshold (default: 0.5)'
    )
    list_parser.add_argument(
        '--severity',
        choices=['critical', 'high', 'medium', 'low'],
        help='Filter by severity'
    )
    list_parser.add_argument(
        '--framework',
        help='Filter by framework'
    )
    list_parser.add_argument(
        '--format',
        choices=['table', 'json', 'csv'],
        default='table',
        help='Output format (default: table)'
    )
    list_parser.set_defaults(func=cmd_list_flaky_tests)
    
    # import command
    import_parser = flaky_subparsers.add_parser(
        'import',
        help='Import test results into database'
    )
    import_parser.add_argument(
        '--db-url',
        required=True,
        help='Database connection URL'
    )
    import_parser.add_argument(
        '--result-file',
        required=True,
        help='Test result file path'
    )
    import_parser.add_argument(
        '--framework',
        required=True,
        choices=['junit', 'cucumber', 'pytest', 'robot'],
        help='Test framework'
    )
    import_parser.add_argument(
        '--git-commit',
        help='Git commit SHA'
    )
    import_parser.add_argument(
        '--environment',
        default='unknown',
        help='Test environment (default: unknown)'
    )
    import_parser.add_argument(
        '--build-id',
        help='CI build identifier'
    )
    import_parser.set_defaults(func=cmd_import_results)
    
    # stats command
    stats_parser = flaky_subparsers.add_parser(
        'stats',
        help='Show flaky test statistics'
    )
    stats_parser.add_argument(
        '--db-url',
        required=True,
        help='Database connection URL'
    )
    stats_parser.set_defaults(func=cmd_show_stats)


def cmd_analyze_flakiness(args):
    """Analyze tests for flakiness."""
    print("🔍 Analyzing tests for flakiness...")
    print(f"   Database: {args.db_url}")
    print(f"   Days of history: {args.days}")
    print(f"   Minimum executions: {args.min_executions}")
    print()
    
    try:
        # Initialize repository
        repo = FlakyDetectionRepository(args.db_url)
        
        # Get execution history
        since = datetime.now() - timedelta(days=args.days)
        
        framework_filter = None
        if args.framework != 'all':
            framework_filter = TestFramework(args.framework)
        
        print("📊 Loading execution history...")
        execution_groups = repo.get_all_test_executions(
            framework=framework_filter,
            since=since
        )
        
        print(f"   Found {len(execution_groups)} unique tests")
        print()
        
        # Extract features
        print("🔧 Extracting features...")
        engineer = FeatureEngineer()
        feature_vectors = engineer.extract_batch_features(execution_groups)
        
        # Filter by minimum executions
        reliable_features = {
            test_id: fv
            for test_id, fv in feature_vectors.items()
            if fv.total_executions >= args.min_executions
        }
        
        print(f"   {len(reliable_features)} tests with sufficient data")
        print()
        
        if len(reliable_features) < 10:
            print("❌ Insufficient data for ML training (need at least 10 tests)")
            print("   Import more test execution history first.")
            return 1
        
        # Train detector
        print("🤖 Training ML model...")
        detector = FlakyDetector()
        detector.train(list(reliable_features.values()))
        print(f"   Model trained on {len(reliable_features)} tests")
        print()
        
        # Detect flaky tests
        print("🎯 Detecting flaky tests...")
        framework_map = {
            test_id: execution_groups[test_id][0].framework
            for test_id in reliable_features.keys()
        }
        name_map = {
            test_id: execution_groups[test_id][0].test_name
            for test_id in reliable_features.keys()
        }
        
        results = detector.detect_batch(
            reliable_features,
            framework_map,
            name_map
        )
        
        # Save results to database
        print("💾 Saving results to database...")
        for result in results.values():
            repo.save_flaky_result(result)
        
        print(f"   Saved {len(results)} results")
        print()
        
        # Generate report
        from core.flaky_detection.detector import create_flaky_report
        report = create_flaky_report(results)
        
        # Display summary
        print("=" * 70)
        print("Flaky Test Detection Summary")
        print("=" * 70)
        print(f"Total tests analyzed: {report['summary']['total_tests']}")
        print(f"Flaky tests found:    {report['summary']['flaky_tests']} "
              f"({report['summary']['flaky_percentage']:.1f}%)")
        print(f"Suspected flaky:      {report['summary']['suspected_flaky']}")
        print(f"Stable tests:         {report['summary']['stable_tests']}")
        print()
        
        print("Severity Breakdown:")
        for severity, count in report['severity_breakdown'].items():
            if count > 0:
                print(f"  {severity.upper():10} {count:3} tests")
        print()
        
        # Show top flaky tests
        if report['flaky_tests']:
            print("Top Flaky Tests:")
            print("-" * 70)
            for test in sorted(
                report['flaky_tests'][:10],
                key=lambda t: t['failure_rate'],
                reverse=True
            ):
                print(f"  {test['test_id']}")
                print(f"    Failure rate: {test['failure_rate']:.1%}")
                print(f"    Confidence:   {test['confidence']:.2f}")
                print(f"    Severity:     {test['severity']}")
                if test['primary_indicators']:
                    print(f"    Indicators:   {test['primary_indicators'][0]}")
                print()
        
        # Save JSON report if requested
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"📄 Full report saved to: {output_path}")
        
        print("=" * 70)
        print("✅ Analysis complete!")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_list_flaky_tests(args):
    """List detected flaky tests."""
    try:
        repo = FlakyDetectionRepository(args.db_url)
        
        framework_filter = TestFramework(args.framework) if args.framework else None
        
        flaky_tests = repo.get_flaky_tests(
            is_flaky=True,
            min_confidence=args.min_confidence,
            framework=framework_filter
        )
        
        # Filter by severity if specified
        if args.severity:
            flaky_tests = [
                t for t in flaky_tests
                if t['severity'] == args.severity
            ]
        
        if args.format == 'json':
            print(json.dumps(flaky_tests, indent=2, default=str))
        elif args.format == 'csv':
            print("test_id,framework,severity,failure_rate,confidence,classification")
            for test in flaky_tests:
                print(f"{test['test_id']},{test['framework']},{test['severity']},"
                      f"{test['failure_rate']:.3f},{test['confidence']:.3f},"
                      f"{test['classification']}")
        else:  # table format
            print()
            print("=" * 100)
            print("Flaky Tests")
            print("=" * 100)
            print(f"Found {len(flaky_tests)} flaky tests")
            print()
            
            if flaky_tests:
                print(f"{'Test ID':<50} {'Severity':<10} {'Failure %':<12} {'Confidence':<12}")
                print("-" * 100)
                
                for test in flaky_tests:
                    test_id_short = test['test_id'][:47] + "..." if len(test['test_id']) > 50 else test['test_id']
                    failure_pct = f"{test['failure_rate']*100:.1f}%"
                    confidence_pct = f"{test['confidence']*100:.0f}%"
                    
                    print(f"{test_id_short:<50} {test['severity']:<10} {failure_pct:<12} {confidence_pct:<12}")
                
                print()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_import_results(args):
    """Import test results into database."""
    print(f"📥 Importing test results...")
    print(f"   File: {args.result_file}")
    print(f"   Framework: {args.framework}")
    print()
    
    try:
        result_file = Path(args.result_file)
        
        if not result_file.exists():
            print(f"❌ Result file not found: {result_file}")
            return 1
        
        # Convert results
        framework = TestFramework(args.framework)
        records = convert_test_results(
            result_file,
            framework,
            git_commit=args.git_commit,
            environment=args.environment,
            build_id=args.build_id
        )
        
        print(f"   Parsed {len(records)} test execution records")
        
        # Save to database
        repo = FlakyDetectionRepository(args.db_url)
        repo.save_executions_batch(records)
        
        print(f"   ✅ Saved to database")
        
        # Show summary
        passed = sum(1 for r in records if r.is_passed)
        failed = sum(1 for r in records if r.is_failed)
        skipped = sum(1 for r in records if r.is_skipped)
        
        print()
        print("   Summary:")
        print(f"     Passed:  {passed}")
        print(f"     Failed:  {failed}")
        print(f"     Skipped: {skipped}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_show_stats(args):
    """Show flaky test statistics."""
    try:
        repo = FlakyDetectionRepository(args.db_url)
        
        flaky_tests = repo.get_flaky_tests(is_flaky=True)
        all_tests = repo.get_flaky_tests()
        
        print()
        print("=" * 70)
        print("Flaky Test Statistics")
        print("=" * 70)
        print()
        
        print(f"Total tests tracked:  {len(all_tests)}")
        print(f"Flaky tests detected: {len(flaky_tests)}")
        
        if all_tests:
            flaky_pct = len(flaky_tests) / len(all_tests) * 100
            print(f"Flaky percentage:     {flaky_pct:.1f}%")
        
        print()
        
        # Breakdown by severity
        severities = {}
        for test in flaky_tests:
            sev = test['severity']
            severities[sev] = severities.get(sev, 0) + 1
        
        if severities:
            print("Severity Breakdown:")
            for sev in ['critical', 'high', 'medium', 'low']:
                count = severities.get(sev, 0)
                if count > 0:
                    print(f"  {sev.capitalize():10} {count:3}")
        
        print()
        
        # Breakdown by framework
        frameworks = {}
        for test in flaky_tests:
            fw = test['framework']
            frameworks[fw] = frameworks.get(fw, 0) + 1
        
        if frameworks:
            print("Framework Breakdown:")
            for fw, count in sorted(frameworks.items(), key=lambda x: x[1], reverse=True):
                print(f"  {fw:15} {count:3}")
        
        print()
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
