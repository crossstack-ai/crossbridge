"""
CLI commands for Flaky Test Detection.

Commands:
- flaky detect: Detect flaky tests from execution history
- flaky list: List detected flaky tests
- flaky report: Generate detailed flaky test report
- flaky export: Export flaky test data
"""

import typer
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.flaky_detection import (
    FlakyDetector,
    FlakyDetectionConfig,
    FeatureEngineer,
    TestFramework,
    TestStatus
)
from core.flaky_detection.models import TestExecutionRecord
from core.flaky_detection.persistence import FlakyDetectionRepository
from core.flaky_detection.detector import create_flaky_report
from persistence.db import create_session, DatabaseConfig


console = Console()
flaky_group = typer.Typer(
    help="Flaky Test Detection and Analysis"
)


def get_framework_enum(framework_str: str) -> TestFramework:
    """Convert framework string to enum."""
    framework_map = {
        'pytest': TestFramework.PYTEST,
        'junit': TestFramework.JUNIT,
        'testng': TestFramework.TESTNG,
        'cucumber': TestFramework.CUCUMBER,
        'robot': TestFramework.ROBOT_FRAMEWORK
    }
    return framework_map.get(framework_str.lower(), TestFramework.PYTEST)


@flaky_group.command(name="detect")
def detect_command(
    days: int = typer.Option(30, "--days", help="Analyze test executions from last N days"),
    framework: Optional[str] = typer.Option(None, "--framework", help="Filter by framework (pytest, junit, etc.)"),
    min_executions: int = typer.Option(10, "--min-executions", help="Minimum executions required for analysis"),
    confidence_threshold: float = typer.Option(0.7, "--confidence", help="Minimum confidence threshold (0.0-1.0)"),
    output: Optional[Path] = typer.Option(None, "--output", help="Export results to JSON file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed analysis"),
):
    """
    Detect flaky tests from execution history.
    
    Analyzes test execution patterns using Isolation Forest ML algorithm
    to identify flaky tests based on:
    - Failure rate patterns
    - Pass/fail alternation
    - Execution time variance
    - Retry patterns
    - Error diversity
    
    Examples:
        crossbridge flaky detect
        crossbridge flaky detect --days 60 --framework pytest
        crossbridge flaky detect --output flaky_report.json --verbose
    """
    console.print(Panel.fit(
        "🔬 [bold cyan]Flaky Test Detection[/bold cyan]",
        subtitle=f"Analyzing last {days} days"
    ))
    console.print()
    
    # Check database configuration
    if not DatabaseConfig.get_db_url():
        console.print("[red]❌ Database not configured![/red]")
        console.print("Set CROSSBRIDGE_DB_URL environment variable:")
        console.print("  export CROSSBRIDGE_DB_URL='postgresql://user:pass@localhost:5432/crossbridge'")
        raise typer.Exit(1)
    
    # Get database session
    session = create_session()
    repo = FlakyDetectionRepository(session)
    
    try:
        # Load test execution records
        console.print("📊 Loading test execution history...")
        since_date = datetime.now() - timedelta(days=days)
        
        framework_filter = get_framework_enum(framework) if framework else None
        executions = repo.get_test_executions(
            since=since_date,
            framework=framework_filter
        )
        
        if not executions:
            console.print(f"[yellow]⚠️  No test executions found in the last {days} days[/yellow]")
            raise typer.Exit(0)
        
        console.print(f"   Found {len(executions)} test executions")
        console.print()
        
        # Group executions by test_id
        from collections import defaultdict
        test_executions = defaultdict(list)
        for exec_record in executions:
            test_executions[exec_record.test_id].append(exec_record)
        
        # Filter tests with sufficient execution history
        qualified_tests = {
            test_id: execs for test_id, execs in test_executions.items()
            if len(execs) >= min_executions
        }
        
        console.print(f"🔍 Analyzing {len(qualified_tests)} tests with ≥{min_executions} executions...")
        console.print()
        
        if len(qualified_tests) < 10:
            console.print("[yellow]⚠️  Insufficient tests for training (need at least 10)[/yellow]")
            console.print(f"   Found: {len(qualified_tests)} tests")
            console.print(f"   Try reducing --min-executions or --days parameters")
            raise typer.Exit(0)
        
        # Extract features
        console.print("🔧 Extracting features from execution history...")
        feature_engineer = FeatureEngineer()
        features = {}
        framework_map = {}
        name_map = {}
        external_id_map = {}
        external_system_map = {}
        
        for test_id, execs in qualified_tests.items():
            fv = feature_engineer.extract_features(execs)
            if fv:
                features[test_id] = fv
                framework_map[test_id] = execs[0].framework
                name_map[test_id] = execs[0].test_name or test_id
                
                # Collect external test IDs
                ext_ids = set()
                ext_systems = set()
                for exec_rec in execs:
                    if exec_rec.external_test_id:
                        ext_ids.add(exec_rec.external_test_id)
                        ext_systems.add(exec_rec.external_system)
                
                if ext_ids:
                    external_id_map[test_id] = list(ext_ids)
                    external_system_map[test_id] = list(ext_systems)
        
        console.print(f"   Extracted features for {len(features)} tests")
        console.print()
        
        # Train detector
        console.print("🤖 Training Isolation Forest model...")
        config = FlakyDetectionConfig(
            min_confidence_threshold=confidence_threshold
        )
        detector = FlakyDetector(config)
        detector.train(list(features.values()))
        
        console.print(f"   Model trained with {config.n_estimators} trees")
        console.print(f"   Contamination rate: {config.contamination}")
        console.print()
        
        # Detect flaky tests
        console.print("🎯 Running flaky detection...")
        results = detector.detect_batch(
            features,
            framework_map,
            name_map,
            external_id_map,
            external_system_map
        )
        
        # Store results in database
        console.print("💾 Storing results in database...")
        for test_id, result in results.items():
            repo.save_flaky_result(result)
        
        session.commit()
        console.print()
        
        # Generate report
        report = create_flaky_report(results, include_stable=verbose)
        
        # Display results
        _display_detection_results(report, verbose)
        
        # Export if requested
        if output:
            import json
            output.write_text(json.dumps(report, indent=2))
            console.print(f"\n✅ Results exported to: {output}")
        
        session.close()
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        session.rollback()
        session.close()
        raise typer.Exit(1)


@flaky_group.command(name="list")
def list_command(
    severity: Optional[str] = typer.Option(None, "--severity", help="Filter by severity: critical, high, medium, low"),
    framework: Optional[str] = typer.Option(None, "--framework", help="Filter by framework"),
    limit: int = typer.Option(50, "--limit", help="Maximum results to display"),
    include_stable: bool = typer.Option(False, "--include-stable", help="Include stable tests"),
):
    """
    List detected flaky tests from database.
    
    Shows previously detected flaky tests with their severity,
    confidence scores, and key indicators.
    
    Examples:
        crossbridge flaky list
        crossbridge flaky list --severity critical
        crossbridge flaky list --framework pytest --limit 20
    """
    console.print(Panel.fit("📋 [bold cyan]Flaky Tests[/bold cyan]"))
    console.print()
    
    # Check database
    if not DatabaseConfig.get_db_url():
        console.print("[red]❌ Database not configured![/red]")
        raise typer.Exit(1)
    
    session = create_session()
    repo = FlakyDetectionRepository(session)
    
    try:
        # Query flaky tests
        framework_filter = get_framework_enum(framework) if framework else None
        
        results = repo.get_flaky_tests(
            framework=framework_filter,
            severity=severity,
            limit=limit,
            include_stable=include_stable
        )
        
        if not results:
            console.print("[yellow]No flaky tests found[/yellow]")
            raise typer.Exit(0)
        
        # Display table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Status", width=8)
        table.add_column("Test Name", width=35)
        table.add_column("Framework", width=12)
        table.add_column("Severity", width=10)
        table.add_column("Score", width=8)
        table.add_column("Confidence", width=10)
        table.add_column("External ID", width=15)
        
        for result in results:
            status = "🔴 FLAKY" if result.is_flaky else "✅ STABLE"
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(result.severity, "⚪")
            
            external_ids = ", ".join(
                f"{sys}:{id}" for sys, id in zip(result.external_systems, result.external_test_ids)
            ) if result.external_test_ids else "-"
            
            table.add_row(
                status,
                result.test_name or result.test_id,
                result.framework.value,
                f"{severity_emoji} {result.severity.upper()}",
                f"{result.flaky_score:.3f}",
                f"{result.confidence:.0%}",
                external_ids
            )
        
        console.print(table)
        console.print(f"\nTotal: {len(results)} tests")
        
        session.close()
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        session.close()
        raise typer.Exit(1)


@flaky_group.command(name="report")
def report_command(
    test_id: str = typer.Argument(..., help="Test ID to generate report for"),
    verbose: bool = typer.Option(True, "--verbose", "-v", help="Show detailed information"),
):
    """
    Generate detailed report for a specific flaky test.
    
    Shows comprehensive information including:
    - Classification and severity
    - Confidence score
    - All extracted features
    - Flakiness indicators
    - Historical trends
    
    Example:
        crossbridge flaky report test_login
    """
    console.print(Panel.fit(f"📊 [bold cyan]Flaky Test Report[/bold cyan]: {test_id}"))
    console.print()
    
    # Check database
    if not DatabaseConfig.get_db_url():
        console.print("[red]❌ Database not configured![/red]")
        raise typer.Exit(1)
    
    session = create_session()
    repo = FlakyDetectionRepository(session)
    
    try:
        # Get test result
        result = repo.get_flaky_test_by_id(test_id)
        
        if not result:
            console.print(f"[red]Test not found: {test_id}[/red]")
            raise typer.Exit(1)
        
        # Display detailed information
        _display_detailed_report(result, verbose)
        
        session.close()
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        session.close()
        raise typer.Exit(1)


@flaky_group.command(name="export")
def export_command(
    output: Path = typer.Argument(..., help="Output file path (CSV or JSON)"),
    format: str = typer.Option("json", "--format", help="Export format: json or csv"),
    days: int = typer.Option(30, "--days", help="Export results from last N days"),
):
    """
    Export flaky test detection results.
    
    Exports results to JSON or CSV format for integration with
    external tools or reporting systems.
    
    Examples:
        crossbridge flaky export flaky_tests.json
        crossbridge flaky export report.csv --format csv --days 60
    """
    console.print(f"📤 Exporting flaky test data to {output}...")
    
    # Check database
    if not DatabaseConfig.get_db_url():
        console.print("[red]❌ Database not configured![/red]")
        raise typer.Exit(1)
    
    session = create_session()
    repo = FlakyDetectionRepository(session)
    
    try:
        since_date = datetime.now() - timedelta(days=days)
        results = repo.get_flaky_tests(since=since_date, limit=10000)
        
        if not results:
            console.print("[yellow]No results to export[/yellow]")
            raise typer.Exit(0)
        
        # Export based on format
        if format.lower() == 'json':
            import json
            data = [result.to_dict() for result in results]
            output.write_text(json.dumps(data, indent=2, default=str))
        elif format.lower() == 'csv':
            import csv
            with output.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'test_id', 'test_name', 'framework', 'is_flaky',
                    'severity', 'flaky_score', 'confidence', 'detected_at',
                    'external_test_ids', 'external_systems'
                ])
                writer.writeheader()
                for result in results:
                    writer.writerow({
                        'test_id': result.test_id,
                        'test_name': result.test_name,
                        'framework': result.framework.value,
                        'is_flaky': result.is_flaky,
                        'severity': result.severity,
                        'flaky_score': result.flaky_score,
                        'confidence': result.confidence,
                        'detected_at': result.detected_at,
                        'external_test_ids': ','.join(result.external_test_ids),
                        'external_systems': ','.join(result.external_systems)
                    })
        
        console.print(f"✅ Exported {len(results)} results to {output}")
        session.close()
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        session.close()
        raise typer.Exit(1)


def _display_detection_results(report: dict, verbose: bool = False):
    """Display detection results in console."""
    
    # Summary
    console.print("=" * 80)
    console.print("[bold cyan]📋 DETECTION RESULTS[/bold cyan]")
    console.print("=" * 80)
    console.print()
    
    summary = report['summary']
    console.print(f"Total tests:      {summary['total_tests']}")
    console.print(f"Flaky detected:   {summary['flaky_tests']} ({summary['flaky_percentage']:.1f}%)")
    console.print(f"Stable tests:     {summary['stable_tests']} ({summary['stable_percentage']:.1f}%)")
    console.print()
    
    if summary.get('by_severity'):
        console.print("By Severity:")
        for severity, count in summary['by_severity'].items():
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            console.print(f"   {emoji.get(severity, '⚪')} {severity.upper():8} {count} test(s)")
    console.print()
    
    # Flaky tests table
    if report.get('flaky_tests'):
        table = Table(show_header=True, header_style="bold red")
        table.add_column("Test Name", width=30)
        table.add_column("Severity", width=10)
        table.add_column("Score", width=8)
        table.add_column("Confidence", width=10)
        table.add_column("Failure %", width=10)
        table.add_column("External ID", width=15)
        
        for test in report['flaky_tests']:
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(test['severity'], "⚪")
            
            external_refs = ", ".join(test.get('external_refs', [])) if test.get('external_refs') else "-"
            
            table.add_row(
                test['test_name'] or test['test_id'],
                f"{severity_emoji} {test['severity'].upper()}",
                f"{test['flaky_score']:.3f}",
                f"{test['confidence']:.0%}",
                f"{test['features']['failure_rate']:.1%}",
                external_refs
            )
        
        console.print(table)
    
    console.print()


def _display_detailed_report(result, verbose: bool = True):
    """Display detailed report for a single test."""
    
    status_emoji = "🔴" if result.is_flaky else "✅"
    console.print(f"{status_emoji} [bold]{result.test_name or result.test_id}[/bold]")
    console.print()
    
    # Basic info
    console.print(f"Classification:  {result.classification.upper()}")
    console.print(f"Framework:       {result.framework.value}")
    console.print(f"Flaky Score:     {result.flaky_score:.3f}")
    console.print(f"Confidence:      {result.confidence:.0%}")
    
    if result.external_test_ids:
        external_refs = [f"{sys}:{id}" for sys, id in zip(result.external_systems, result.external_test_ids)]
        console.print(f"External IDs:    {', '.join(external_refs)}")
    
    if result.is_flaky:
        console.print(f"Severity:        {result.severity.upper()}")
    
    console.print(f"Detected:        {result.detected_at}")
    console.print()
    
    # Features
    if verbose and result.features:
        console.print("[bold]Features:[/bold]")
        f = result.features
        console.print(f"  Failure Rate:        {f.failure_rate:.1%}")
        console.print(f"  Switch Rate:         {f.pass_fail_switch_rate:.1%}")
        console.print(f"  Duration CV:         {f.duration_cv:.3f}")
        console.print(f"  Duration Variance:   {f.duration_variance:.1f}")
        console.print(f"  Retry Success Rate:  {f.retry_success_rate:.1%}")
        console.print(f"  Avg Retry Count:     {f.avg_retry_count:.2f}")
        console.print(f"  Unique Errors:       {f.unique_error_count}")
        console.print(f"  Error Diversity:     {f.error_diversity_ratio:.2f}")
        console.print(f"  Execution Count:     {f.execution_count}")
        console.print()
    
    # Indicators
    if result.primary_indicators:
        console.print("[bold]Flakiness Indicators:[/bold]")
        for indicator in result.primary_indicators:
            console.print(f"  • {indicator}")
        console.print()


if __name__ == "__main__":
    flaky_group()
