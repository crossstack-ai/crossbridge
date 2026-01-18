"""
CLI commands for Functional Coverage & Impact Analysis.

Commands:
- coverage map: Show Functional Coverage Map
- coverage features: Show Test-to-Feature Coverage
- coverage gaps: Show coverage gaps (features without tests)
- coverage impact --file <path>: Show Change Impact Surface for a file
"""

import typer
from datetime import datetime
from typing import Optional

from core.coverage.functional_repository import FunctionalCoverageRepository
from core.coverage.functional_models import (
    FunctionalCoverageMapReport,
    TestToFeatureCoverageReport,
    ChangeImpactSurfaceReport
)
from core.coverage.console_formatter import (
    print_functional_coverage_map,
    print_test_to_feature_coverage,
    print_change_impact_surface,
    print_coverage_gaps,
    export_to_csv,
    export_to_json
)
from persistence.db import get_session


coverage_group = typer.Typer(
    help="Functional Coverage & Impact Analysis commands"
)


@coverage_group.command(name="map")
def coverage_map_command(
    limit: int = typer.Option(50, "--limit", help="Limit number of results"),
    output: Optional[str] = typer.Option(None, "--output", help="Export to CSV/JSON file"),
    format: str = typer.Option("console", "--format", help="Output format: console, csv, json")
):
    """
    Show Functional Coverage Map.
    
    Displays:
    - Code units (classes, methods)
    - Number of tests covering each unit
    - Associated TestRail TC IDs
    
    Example:
        crossbridge coverage map
        crossbridge coverage map --limit 20
        crossbridge coverage map --output report.csv --format csv
    """
    typer.echo("📊 Generating Functional Coverage Map...\n")
    
    # Get database session
    session = get_session()
    repo = FunctionalCoverageRepository(session)
    
    # Query coverage map
    entries = repo.get_functional_coverage_map(limit=limit)
    
    # Calculate totals
    total_code_units = len(entries)
    total_tests = sum(entry.test_count for entry in entries)
    total_external_tcs = sum(len(entry.testrail_tcs) for entry in entries)
    
    # Create report
    report = FunctionalCoverageMapReport(
        entries=entries,
        total_code_units=total_code_units,
        total_tests=total_tests,
        total_external_tcs=total_external_tcs
    )
    
    # Output based on format
    if format == "console":
        print_functional_coverage_map(report)
    elif format == "csv" and output:
        export_to_csv(report, output)
    elif format == "json" and output:
        export_to_json(report, output)
    else:
        print_functional_coverage_map(report)
        if output:
            if output.endswith('.csv'):
                export_to_csv(report, output)
            elif output.endswith('.json'):
                export_to_json(report, output)


@coverage_group.command(name="features")
def coverage_features_command(
    feature: Optional[str] = typer.Option(None, "--feature", help="Filter by feature name (partial match)"),
    output: Optional[str] = typer.Option(None, "--output", help="Export to CSV/JSON file"),
    format: str = typer.Option("console", "--format", help="Output format: console, csv, json")
):
    """
    Show Test-to-Feature Coverage.
    
    Displays:
    - Features in the system
    - Tests that validate each feature
    - Associated TestRail TC IDs
    
    Example:
        crossbridge coverage features
        crossbridge coverage features --feature login
        crossbridge coverage features --output report.json --format json
    """
    click.echo("🎯 Generating Test-to-Feature Coverage...\n")
    
    # Get database session
    session = get_session()
    repo = FunctionalCoverageRepository(session)
    
    # Query test-to-feature coverage
    entries = repo.get_test_to_feature_coverage(feature_filter=feature)
    
    # Calculate totals
    total_features = len(set(entry.feature for entry in entries))
    total_tests = len(entries)
    
    # Get coverage gaps
    gaps = repo.get_coverage_gaps()
    features_without_tests = len(gaps)
    typer
    # Create report
    report = TestToFeatureCoverageReport(
        entries=entries,
        total_features=total_features,
        total_tests=total_tests,
        features_without_tests=features_without_tests
    )
    
    # Output based on format
    if format == "console":
        print_test_to_feature_coverage(report)
    elif format == "csv" and output:
        export_to_csv(report, output)
    elif format == "json" and output:
        export_to_json(report, output)
    else:
        print_test_to_feature_coverage(report)
        if output:
            if output.endswith('.csv'):
                export_to_csv(report, output)
            elif output.endswith('.json'):
                export_to_json(report, output)


@coverage_group.command(name="gaps")
def coverage_gaps_command(
    type: Optional[str] = typer.Option(None, "--type", help="Filter by feature type: api, service, bdd, module, component")
):
    """
    Show coverage gaps (features without tests).
    
    Identifies features that have no test coverage.
    
    Example:
        crossbridge coverage gaps
        crossbridge coverage gaps --type api
    """
    click.echo("🔍 Identifying Coverage Gaps...\n")
    
    # Get database session
    typeron = get_session()
    repo = FunctionalCoverageRepository(session)
    
    # Query coverage gaps
    gaps = repo.get_coverage_gaps()
    
    # Filter by type if specified
    if type:
        gaps = [gap for gap in gaps if gap.type == type]
    
    # Print gaps
    print_coverage_gaps(gaps)


@coverage_group.command(name="impact")
@click.option(
    "--file",
    required=True,
def impact_command(
    file: str = typer.Option(..., "--file", help="File path to analyze impact for"),
    output: Optional[str] = typer.Option(None, "--output", help="Export to CSV/JSON file"),
    format: str = typer.Option("console", "--format", help="Output format: console, csv, json") Impact Surface for a file.
    
    Displays:
    - Tests impacted by changes to the file
    - Features affected
    - Associated TestRail TC IDs
    
    Example:
        crossbridge coverage impact --file src/LoginService.java
        crossbridge coverage impact --file auth.py --output impact.csv
    """
    click.echo(f"🎯 Analyzing impact for: {file}\n")
    
    # Get database session
    session = get_session()
    repo = FunctionalCoverageRepository(session)
    
    # Query change impact surface
    entries = repo.get_change_impact_surface(file_path=file)
    
    # Calculate totals
    total_impacted_tests = len(entries)
    total_impacted_features = len(
        set(entry.feature for entry in entries if entry.feature)
    )
    
    # Create report
    report = ChangeImpactSurfaceReport(
    typerhanged_file=file,
        entries=entries,
        total_impacted_tests=total_impacted_tests,
        total_impacted_features=total_impacted_features
    )
    
    # Output based on format
    if format == "console":
        print_change_impact_surface(report)
    elif format == "csv" and output:
        export_to_csv(report, output)
    elif format == "json" and output:
        export_to_json(report, output)
    else:
        print_change_impact_surface(report)
        if output:
            if output.endswith('.csv'):
                export_to_csv(report, output)
            elif output.endswith('.json'):
                export_to_json(report, output)


# Optional: Add sync command to sync with external systems
@coverage_group.command(name="sync")
@click.option(
    "--system",
    type=click.Choice(["testrail", "zephyr", "qtest"]),
    required=True,
    help="External test management system"
)
@click.option(
    "--api-key",
    type=str,
    required=True,
    help="API key for the system"
)
@click.option(
    "--url",
    type=str,
    required=True,
    help="API URL for the system"
def sync_command(
    system: str = typer.Option(..., "--system", help="External test management system: testrail, zephyr, qtest"),
    api_key: str = typer.Option(..., "--api-key", help="API key for the system"),
    url: str = typer.Option(..., "--url", help="API URL for the system")

@coverage_group.command(name="summary")
def summary_command():
    """
    Show coverage summary statistics.
    
    Provides high-level overview of:
    - Total code units
    - Total tests
    - Total features
    - Coverage gaps
    - External TC mappings
    """
    click.echo("📈 Coverage Summary\n")
@coverage_group.command(name="summary")
def summary_command():
    """
    Show coverage summary statistics.
    
    Provides high-level overview of:
    - Total code units
    - Total tests
    - Total features
    - Coverage gaps
    - External TC mappings
    """
    typer
    typer_gaps = len(gaps)
    total_external_tcs = sum(len(entry.testrail_tcs) for entry in coverage_map)
    
    # Print summary
    click.echo("=" * 50)
    click.echo(f"Code Units Covered:      {total_code_units}")
    click.echo(f"Total Tests:             {total_tests}")
    click.echo(f"Total Features:          {total_features}")
    click.echo(f"Coverage Gaps:           {total_gaps}")
    click.echo(f"External TC Mappings:    {total_external_tcs}")
    click.echo("=" * 50)
    
    if total_gaps > 0:
        click.echo(f"\n[yellow]⚠ {total_gaps} features have no test coverage[/yellow]")
    else:
        click.echo("\n[green]✓ All features have test coverage![/green]")
    
    click.echo(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
typer.echo("=" * 50)
    typer.echo(f"Code Units Covered:      {total_code_units}")
    typer.echo(f"Total Tests:             {total_tests}")
    typer.echo(f"Total Features:          {total_features}")
    typer.echo(f"Coverage Gaps:           {total_gaps}")
    typer.echo(f"External TC Mappings:    {total_external_tcs}")
    typer.echo("=" * 50)
    
    if total_gaps > 0:
        typer.echo(f"\n[yellow]⚠ {total_gaps} features have no test coverage[/yellow]")
    else:
        typer.echo("\n[green]✓ All features have test coverage![/green]")
    
    typer