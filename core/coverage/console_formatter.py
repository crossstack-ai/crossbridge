"""
Console output formatting for Functional Coverage & Impact Analysis.

Provides user-friendly console output using tabulate.
"""

from typing import List
from tabulate import tabulate
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from core.logging import get_logger, LogCategory
from .functional_models import (
    FunctionalCoverageMapReport,
    TestToFeatureCoverageReport,
    ChangeImpactSurfaceReport,
    FunctionalCoverageMapEntry,
    TestToFeatureCoverageEntry,
    ChangeImpactSurfaceEntry
)

logger = get_logger(__name__, category=LogCategory.TESTING)
console = Console()


def print_functional_coverage_map(
    report: FunctionalCoverageMapReport
) -> None:
    """
    Print Functional Coverage Map to console.
    
    Shows: Code Unit → Tests Covering → TestRail TCs
    
    Args:
        report: FunctionalCoverageMapReport
    """
    console.print("\n[bold cyan]Functional Coverage Map[/bold cyan]\n")
    
    if not report.entries:
        console.print("[yellow]No coverage data found.[/yellow]")
        return
    
    # Prepare table data
    headers = ["Code Unit", "Tests", "TestRail TCs"]
    rows = [entry.to_row() for entry in report.entries]
    
    # Print using tabulate
    table_str = tabulate(
        rows,
        headers=headers,
        tablefmt="github"
    )
    
    print(table_str)
    
    # Print summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Total Code Units: {report.total_code_units}")
    console.print(f"  Total Tests: {report.total_tests}")
    console.print(f"  Total TestRail TCs: {report.total_external_tcs}")
    console.print(f"  Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")


def print_test_to_feature_coverage(
    report: TestToFeatureCoverageReport
) -> None:
    """
    Print Test-to-Feature Coverage to console.
    
    Shows: Feature → Test → TestRail TC
    
    Args:
        report: TestToFeatureCoverageReport
    """
    console.print("\n[bold cyan]Test-to-Feature Coverage[/bold cyan]\n")
    
    if not report.entries:
        console.print("[yellow]No feature mappings found.[/yellow]")
        return
    
    # Prepare table data
    headers = ["Feature", "Test Case", "TestRail TC"]
    rows = [entry.to_row() for entry in report.entries]
    
    # Print using tabulate with fancy_grid
    table_str = tabulate(
        rows,
        headers=headers,
        tablefmt="fancy_grid"
    )
    
    print(table_str)
    
    # Print summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Total Features: {report.total_features}")
    console.print(f"  Total Tests: {report.total_tests}")
    console.print(f"  Features Without Tests: {report.features_without_tests}")
    
    if report.features_without_tests > 0:
        console.print(
            f"  [yellow]⚠ {report.features_without_tests} features have no test coverage[/yellow]"
        )
    
    console.print(f"  Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")


def print_change_impact_surface(
    report: ChangeImpactSurfaceReport
) -> None:
    """
    Print Change Impact Surface to console.
    
    Shows: Impacted Test → Feature → TestRail TC
    
    Args:
        report: ChangeImpactSurfaceReport
    """
    console.print(f"\n[bold cyan]Change Impact Surface[/bold cyan]\n")
    console.print(f"[bold]Changed File:[/bold] {report.changed_file}\n")
    
    if not report.entries:
        console.print("[green]✓ No tests impacted by this change.[/green]")
        return
    
    # Prepare table data
    headers = ["Impacted Test", "Feature", "TestRail TC"]
    rows = [entry.to_row() for entry in report.entries]
    
    # Print using tabulate with grid
    table_str = tabulate(
        rows,
        headers=headers,
        tablefmt="grid"
    )
    
    print(table_str)
    
    # Print summary
    console.print(f"\n[bold]Impact Summary:[/bold]")
    console.print(f"  Impacted Tests: {report.total_impacted_tests}")
    console.print(f"  Impacted Features: {report.total_impacted_features}")
    
    if report.total_impacted_tests > 0:
        console.print(
            f"  [yellow]⚠ {report.total_impacted_tests} tests should be run[/yellow]"
        )
    
    console.print(f"  Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")


def print_functional_coverage_map_rich(
    report: FunctionalCoverageMapReport
) -> None:
    """
    Print Functional Coverage Map using Rich (alternative).
    
    Args:
        report: FunctionalCoverageMapReport
    """
    table = Table(
        title="Functional Coverage Map",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Code Unit", style="white")
    table.add_column("Tests", justify="right", style="green")
    table.add_column("TestRail TCs", style="yellow")
    
    for entry in report.entries:
        tc_str = ", ".join(entry.testrail_tcs[:5])
        if len(entry.testrail_tcs) > 5:
            tc_str += f" (+{len(entry.testrail_tcs) - 5} more)"
        
        table.add_row(
            entry.code_unit,
            str(entry.test_count),
            tc_str if tc_str else "-"
        )
    
    console.print(table)
    
    # Print summary panel
    summary = f"""
[bold]Summary:[/bold]
  Total Code Units: {report.total_code_units}
  Total Tests: {report.total_tests}
  Total TestRail TCs: {report.total_external_tcs}
  Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    console.print(Panel(summary, border_style="cyan"))


def print_test_to_feature_coverage_rich(
    report: TestToFeatureCoverageReport
) -> None:
    """
    Print Test-to-Feature Coverage using Rich (alternative).
    
    Args:
        report: TestToFeatureCoverageReport
    """
    table = Table(
        title="Test-to-Feature Coverage",
        box=box.DOUBLE,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Feature", style="cyan")
    table.add_column("Test Case", style="white")
    table.add_column("TestRail TC", style="yellow")
    
    for entry in report.entries:
        table.add_row(
            entry.feature,
            entry.test_name,
            entry.testrail_tc if entry.testrail_tc else "-"
        )
    
    console.print(table)
    
    # Print summary panel
    summary = f"""
[bold]Summary:[/bold]
  Total Features: {report.total_features}
  Total Tests: {report.total_tests}
  Features Without Tests: {report.features_without_tests}
  Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    if report.features_without_tests > 0:
        summary += f"\n[yellow]⚠ {report.features_without_tests} features have no test coverage[/yellow]"
    
    console.print(Panel(summary, border_style="cyan"))


def print_change_impact_surface_rich(
    report: ChangeImpactSurfaceReport
) -> None:
    """
    Print Change Impact Surface using Rich (alternative).
    
    Args:
        report: ChangeImpactSurfaceReport
    """
    table = Table(
        title=f"Change Impact Surface: {report.changed_file}",
        box=box.HEAVY,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Impacted Test", style="white")
    table.add_column("Feature", style="cyan")
    table.add_column("TestRail TC", style="yellow")
    
    if not report.entries:
        console.print("[green]✓ No tests impacted by this change.[/green]")
        return
    
    for entry in report.entries:
        table.add_row(
            entry.impacted_test,
            entry.feature if entry.feature else "-",
            entry.testrail_tc if entry.testrail_tc else "-"
        )
    
    console.print(table)
    
    # Print summary panel
    summary = f"""
[bold]Impact Summary:[/bold]
  Impacted Tests: {report.total_impacted_tests}
  Impacted Features: {report.total_impacted_features}
  Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    if report.total_impacted_tests > 0:
        summary += f"\n[yellow]⚠ {report.total_impacted_tests} tests should be run[/yellow]"
    
    console.print(Panel(summary, border_style="cyan"))


def print_coverage_gaps(features: List) -> None:
    """
    Print features without test coverage.
    
    Args:
        features: List of features without coverage
    """
    console.print("\n[bold red]Coverage Gaps[/bold red]\n")
    console.print("[yellow]Features with no test coverage:[/yellow]\n")
    
    if not features:
        console.print("[green]✓ All features have test coverage![/green]\n")
        return
    
    # Group by type
    by_type = {}
    for feature in features:
        if feature.type not in by_type:
            by_type[feature.type] = []
        by_type[feature.type].append(feature)
    
    # Print by type
    for feature_type, type_features in by_type.items():
        console.print(f"[bold]{feature_type.upper()}:[/bold]")
        for feature in type_features:
            console.print(f"  • {feature.name} (source: {feature.source})")
        console.print()
    
    console.print(f"[bold]Total gaps:[/bold] {len(features)}\n")


def export_to_csv(
    report,
    output_file: str
) -> None:
    """
    Export report to CSV file.
    
    Args:
        report: Any report object
        output_file: Output CSV file path
    """
    import csv
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if isinstance(report, FunctionalCoverageMapReport):
            writer = csv.writer(f)
            writer.writerow(["Code Unit", "Tests", "TestRail TCs"])
            for entry in report.entries:
                tc_str = ", ".join(entry.testrail_tcs)
                writer.writerow([
                    entry.code_unit,
                    entry.test_count,
                    tc_str
                ])
        
        elif isinstance(report, TestToFeatureCoverageReport):
            writer = csv.writer(f)
            writer.writerow(["Feature", "Test Case", "TestRail TC"])
            for entry in report.entries:
                writer.writerow([
                    entry.feature,
                    entry.test_name,
                    entry.testrail_tc if entry.testrail_tc else ""
                ])
        
        elif isinstance(report, ChangeImpactSurfaceReport):
            writer = csv.writer(f)
            writer.writerow([
                "Impacted Test",
                "Feature",
                "TestRail TC",
                "Coverage %"
            ])
            for entry in report.entries:
                writer.writerow([
                    entry.impacted_test,
                    entry.feature if entry.feature else "",
                    entry.testrail_tc if entry.testrail_tc else "",
                    entry.coverage_percentage if entry.coverage_percentage else ""
                ])
    
    console.print(f"[green]✓ Exported to {output_file}[/green]")


def export_to_json(
    report,
    output_file: str
) -> None:
    """
    Export report to JSON file.
    
    Args:
        report: Any report object
        output_file: Output JSON file path
    """
    import json
    from dataclasses import asdict
    
    # Convert report to dict
    report_dict = asdict(report)
    
    # Convert datetime to string
    if 'generated_at' in report_dict:
        report_dict['generated_at'] = report_dict['generated_at'].isoformat()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, indent=2)
    
    console.print(f"[green]✓ Exported to {output_file}[/green]")
