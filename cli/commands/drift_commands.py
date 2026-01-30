"""CLI commands for confidence drift monitoring."""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from tabulate import tabulate
from typing import Optional

from core.intelligence.confidence_drift import (
    DriftDetector,
    DriftAlertManager,
    DriftSeverity,
    DriftThresholds
)
from core.intelligence.drift_persistence import DriftPersistenceManager


def cmd_drift_status(args):
    """Show current drift status across all tests."""
    manager = DriftPersistenceManager(args.db_path)
    detector = DriftDetector()
    
    # Get drift statistics
    since = datetime.utcnow() - timedelta(days=args.window)
    stats = manager.get_drift_statistics(category=args.category, since=since)
    
    print("\n" + "="*60)
    print(f"  CONFIDENCE DRIFT STATUS")
    print("="*60 + "\n")
    
    if args.category:
        print(f"Category: {args.category}")
    print(f"Time Window: Last {args.window} days")
    print(f"Database: {args.db_path}\n")
    
    print(f"Total Tests: {stats['total_tests']}")
    print(f"Total Measurements: {stats['total_measurements']}")
    if stats['avg_confidence']:
        print(f"Average Confidence: {stats['avg_confidence']:.2%}")
        print(f"Confidence Range: {stats['min_confidence']:.2%} - {stats['max_confidence']:.2%}")
    else:
        print("No measurements found in time window")
    
    # Get tests with measurements
    if args.category:
        test_names = manager.get_category_tests(args.category)
    else:
        # Get all unique test names
        all_measurements = manager.get_measurements(since=since, limit=1000)
        test_names = list(set(m.test_name for m in all_measurements))
    
    if not test_names:
        print("\nNo tests found.")
        return 0
    
    # Analyze drift for each test
    print(f"\nAnalyzing {len(test_names)} test(s)...")
    
    drifting_tests = []
    for test_name in test_names:
        measurements = manager.get_test_history(test_name, window=timedelta(days=args.window))
        
        # Load into detector
        for m in measurements:
            detector.record_confidence(
                m.test_name,
                m.confidence,
                m.category,
                m.timestamp
            )
        
        # Analyze drift
        analysis = detector.detect_drift(test_name)
        if analysis and analysis.is_drifting:
            drifting_tests.append((
                test_name,
                analysis.severity.value,
                analysis.drift_percentage,
                analysis.direction.value
            ))
    
    if drifting_tests:
        print(f"\n⚠️  Found {len(drifting_tests)} test(s) with drift:\n")
        
        headers = ["Test Name", "Severity", "Drift %", "Direction"]
        table = []
        for test, severity, drift, direction in sorted(drifting_tests, key=lambda x: abs(x[2]), reverse=True):
            emoji = {"low": "⚠️", "moderate": "🔶", "high": "🔥", "critical": "🚨"}
            severity_display = f"{emoji.get(severity, '?')} {severity.upper()}"
            table.append([test, severity_display, f"{drift:+.1%}", direction])
        
        print(tabulate(table, headers=headers, tablefmt="simple"))
    else:
        print("\n✓ No significant drift detected")
    
    return 0


def cmd_drift_analyze(args):
    """Analyze drift for a specific test."""
    manager = DriftPersistenceManager(args.db_path)
    detector = DriftDetector()
    
    # Load test history
    measurements = manager.get_test_history(args.test_name, window=timedelta(days=args.window))
    
    if not measurements:
        print(f"❌ No measurements found for test: {args.test_name}")
        return 1
    
    # Load into detector
    for m in measurements:
        detector.record_confidence(m.test_name, m.confidence, m.category, m.timestamp)
    
    # Analyze drift
    analysis = detector.detect_drift(args.test_name)
    
    if not analysis:
        print(f"❌ Insufficient data to analyze drift for: {args.test_name}")
        print(f"   (Need at least 3 measurements, found {len(measurements)})")
        return 1
    
    # Display results
    print("\n" + "="*60)
    print(f"  DRIFT ANALYSIS: {args.test_name}")
    print("="*60 + "\n")
    
    severity_emoji = {
        "none": "✓",
        "low": "⚠️",
        "moderate": "🔶",
        "high": "🔥",
        "critical": "🚨"
    }
    
    direction_emoji = {
        "stable": "→",
        "increasing": "↑",
        "decreasing": "↓",
        "volatile": "⚡"
    }
    
    emoji = severity_emoji.get(analysis.severity.value, "?")
    dir_emoji = direction_emoji.get(analysis.direction.value, "?")
    
    print(f"Status: {emoji} {analysis.severity.value.upper()} drift")
    print(f"Direction: {dir_emoji} {analysis.direction.value}")
    print(f"Trend: {analysis.trend}")
    print(f"\nBaseline: {analysis.baseline_confidence:.2%}")
    print(f"Current: {analysis.current_confidence:.2%}")
    print(f"Drift: {analysis.drift_percentage:+.1%} ({analysis.drift_absolute:+.2f})")
    print(f"\nMeasurements: {analysis.measurements_count} over {analysis.time_span}")
    
    if analysis.recommendations:
        print(f"\n📋 Recommendations:")
        for rec in analysis.recommendations:
            print(f"  • {rec}")
    
    # Show recent measurements
    print(f"\n📊 Recent Measurements (last 10):")
    recent = measurements[:10]
    
    table = []
    for m in recent:
        table.append([
            m.timestamp.strftime("%Y-%m-%d %H:%M"),
            f"{m.confidence:.2%}",
            m.category
        ])
    
    print(tabulate(table, headers=["Timestamp", "Confidence", "Category"], tablefmt="simple"))
    
    return 0


def cmd_drift_alerts(args):
    """Show drift alerts."""
    manager = DriftPersistenceManager(args.db_path)
    
    min_severity = DriftSeverity(args.severity) if args.severity else None
    acknowledged = False if args.unacknowledged else None
    since = datetime.utcnow() - timedelta(hours=args.hours)
    
    alerts = manager.get_alerts(
        min_severity=min_severity,
        acknowledged=acknowledged,
        since=since
    )
    
    if not alerts:
        print("✓ No alerts found")
        return 0
    
    print(f"\n🚨 Found {len(alerts)} alert(s):\n")
    
    for i, alert in enumerate(alerts, 1):
        severity_emoji = {"low": "⚠️", "moderate": "🔶", "high": "🔥", "critical": "🚨"}
        emoji = severity_emoji.get(alert['severity'].value, "?")
        
        status = "✓ Acknowledged" if alert['acknowledged'] else "❌ Unacknowledged"
        
        print(f"[{i}] {emoji} {alert['test_name']}")
        print(f"    Severity: {alert['severity'].value.upper()}")
        print(f"    Message: {alert['message']}")
        print(f"    Status: {status}")
        print(f"    Created: {alert['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        if alert['recommendations']:
            print(f"    Top Recommendations:")
            for rec in alert['recommendations'][:3]:
                print(f"      • {rec}")
        
        print()
    
    return 0


def cmd_drift_stats(args):
    """Show drift statistics and trends."""
    manager = DriftPersistenceManager(args.db_path)
    
    since = datetime.utcnow() - timedelta(days=args.days)
    
    print("\n" + "="*60)
    print(f"  DRIFT STATISTICS (Last {args.days} days)")
    print("="*60 + "\n")
    
    # Overall statistics
    stats = manager.get_drift_statistics(category=args.category, since=since)
    
    print(f"Tests Tracked: {stats['total_tests']}")
    print(f"Total Measurements: {stats['total_measurements']}")
    
    if stats['avg_confidence']:
        print(f"Average Confidence: {stats['avg_confidence']:.2%}")
        print(f"Range: {stats['min_confidence']:.2%} - {stats['max_confidence']:.2%}")
    
    # Alert summary
    alert_summary = manager.get_alert_summary(since=since)
    
    if alert_summary:
        print(f"\n📊 Alerts by Severity:")
        
        severity_order = ["critical", "high", "moderate", "low"]
        for sev in severity_order:
            count = alert_summary.get(sev, 0)
            if count > 0:
                emoji = {"low": "⚠️", "moderate": "🔶", "high": "🔥", "critical": "🚨"}
                print(f"  {emoji.get(sev, '?')} {sev.upper()}: {count}")
    
    # Database size
    size = manager.get_database_size()
    print(f"\nDatabase Size: {size / 1024:.1f} KB")
    
    return 0


def add_drift_commands(subparsers):
    """Add drift monitoring commands to CLI."""
    drift_parser = subparsers.add_parser(
        'drift',
        help='Monitor and analyze confidence drift over time'
    )
    drift_subparsers = drift_parser.add_subparsers(dest='drift_command')
    
    # drift status
    status_parser = drift_subparsers.add_parser(
        'status',
        help='Show current drift status across all tests'
    )
    status_parser.add_argument('--category', help='Filter by category')
    status_parser.add_argument('--window', type=int, default=30, help='Time window in days (default: 30)')
    status_parser.add_argument('--db-path', default='data/drift_tracking.db', help='Database path')
    status_parser.set_defaults(func=cmd_drift_status)
    
    # drift analyze
    analyze_parser = drift_subparsers.add_parser(
        'analyze',
        help='Analyze drift for a specific test'
    )
    analyze_parser.add_argument('test_name', help='Test name to analyze')
    analyze_parser.add_argument('--window', type=int, default=30, help='Time window in days')
    analyze_parser.add_argument('--db-path', default='data/drift_tracking.db', help='Database path')
    analyze_parser.set_defaults(func=cmd_drift_analyze)
    
    # drift alerts
    alerts_parser = drift_subparsers.add_parser(
        'alerts',
        help='Show drift alerts'
    )
    alerts_parser.add_argument('--severity', choices=['low', 'moderate', 'high', 'critical'], 
                              help='Minimum severity level')
    alerts_parser.add_argument('--unacknowledged', action='store_true', 
                              help='Show only unacknowledged alerts')
    alerts_parser.add_argument('--hours', type=int, default=24, help='Time window in hours')
    alerts_parser.add_argument('--db-path', default='data/drift_tracking.db', help='Database path')
    alerts_parser.set_defaults(func=cmd_drift_alerts)
    
    # drift stats
    stats_parser = drift_subparsers.add_parser(
        'stats',
        help='Show drift statistics and trends'
    )
    stats_parser.add_argument('--category', help='Filter by category')
    stats_parser.add_argument('--days', type=int, default=7, help='Time window in days')
    stats_parser.add_argument('--db-path', default='data/drift_tracking.db', help='Database path')
    stats_parser.set_defaults(func=cmd_drift_stats)
    
    drift_parser.set_defaults(func=lambda args: drift_parser.print_help())


def execute_drift_command(args):
    """Execute drift command."""
    if not hasattr(args, 'drift_command') or args.drift_command is None:
        print("Error: No drift subcommand specified")
        return 1
    
    return args.func(args)
