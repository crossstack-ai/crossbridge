"""
CLI commands for extended framework adapters.

Provides commands to interact with the 12 framework adapters:
- List supported frameworks
- Discover tests in a project
- Analyze tests from specific frameworks
- Generate reports on framework usage
"""

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from core.logging import get_logger, LogCategory
from core.intelligence.adapters import AdapterFactory
from core.intelligence.models import UnifiedTestMemory

logger = get_logger(__name__, category=LogCategory.CLI)
console = Console()

app = typer.Typer(
    name="framework",
    help="Multi-framework adapter commands",
    no_args_is_help=True
)


@app.command("list")
def list_frameworks():
    """List all supported testing frameworks."""
    frameworks = AdapterFactory.list_supported_frameworks()
    
    console.print("\n[bold cyan]Supported Testing Frameworks[/bold cyan]\n")
    
    table = Table(title="CrossBridge Framework Support (12 Frameworks)")
    table.add_column("#", style="dim", width=3)
    table.add_column("Framework", style="cyan")
    table.add_column("Language", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Status", style="magenta")
    
    framework_info = [
        ("pytest", "Python", "Unit/Integration", "✅ Full"),
        ("junit", "Java", "Unit", "⚠️  Partial"),
        ("testng", "Java", "Enterprise", "⚠️  Partial"),
        ("nunit", "C#", "Unit", "⚠️  Partial"),
        ("specflow", "C#", "BDD", "⚠️  Partial"),
        ("robot", "Robot", "Keyword-Driven", "⚠️  Basic"),
        ("restassured", "Java", "REST API", "⚠️  Partial"),
        ("playwright", "JavaScript/TS", "E2E", "⚠️  Partial"),
        ("selenium_python", "Python", "UI", "✅ Full"),
        ("selenium_java", "Java", "UI", "⚠️  Partial"),
        ("cucumber", "Gherkin", "BDD", "⚠️  Partial"),
        ("behave", "Python", "BDD", "⚠️  Partial"),
    ]
    
    for i, (name, lang, type_, status) in enumerate(framework_info, 1):
        table.add_row(str(i), name, lang, type_, status)
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(frameworks)} frameworks[/dim]\n")


@app.command("discover")
def discover_tests(
    framework: str = typer.Argument(..., help="Framework name (e.g., pytest, cucumber)"),
    project_root: Path = typer.Argument(..., help="Project root directory", exists=True, file_okay=False),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output")
):
    """Discover all tests in a project for a specific framework."""
    try:
        adapter = AdapterFactory.get_adapter(framework)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("\n[yellow]Use 'crossbridge framework list' to see supported frameworks[/yellow]")
        raise typer.Exit(1)
    
    console.print(f"\n[cyan]Discovering {framework} tests in:[/cyan] {project_root}\n")
    
    try:
        test_files = adapter.discover_tests(str(project_root))
        
        if not test_files:
            console.print(f"[yellow]No {framework} tests found[/yellow]")
            return
        
        console.print(f"[green]Found {len(test_files)} test file(s)[/green]\n")
        
        if verbose:
            for i, test_file in enumerate(test_files, 1):
                console.print(f"  {i}. {test_file}")
        else:
            # Show first 10
            for i, test_file in enumerate(test_files[:10], 1):
                console.print(f"  {i}. {test_file}")
            if len(test_files) > 10:
                console.print(f"  ... and {len(test_files) - 10} more")
        
        console.print()
        
    except Exception as e:
        console.print(f"[red]Error discovering tests:[/red] {e}")
        raise typer.Exit(1)


@app.command("analyze")
def analyze_test(
    framework: str = typer.Argument(..., help="Framework name"),
    test_file: Path = typer.Argument(..., help="Test file path", exists=True),
    test_name: str = typer.Argument(..., help="Test name/method"),
    show_signals: bool = typer.Option(True, "--signals/--no-signals", help="Show extracted signals"),
    show_code: bool = typer.Option(False, "--code", help="Show test source code")
):
    """Analyze a specific test and show extracted intelligence."""
    try:
        adapter = AdapterFactory.get_adapter(framework)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    
    console.print(f"\n[cyan]Analyzing test:[/cyan] {test_name}")
    console.print(f"[dim]Framework: {framework}[/dim]")
    console.print(f"[dim]File: {test_file}[/dim]\n")
    
    try:
        # Normalize to unified format
        unified = adapter.normalize_to_core_model(
            test_file=str(test_file),
            test_name=test_name
        )
        
        # Display test information
        info_panel = Panel(
            f"[bold]Test ID:[/bold] {unified.test_id}\n"
            f"[bold]Framework:[/bold] {unified.framework}\n"
            f"[bold]Language:[/bold] {unified.language}\n"
            f"[bold]Priority:[/bold] {unified.metadata.priority}\n"
            f"[bold]Tags:[/bold] {', '.join(unified.metadata.tags) if unified.metadata.tags else 'None'}",
            title="Test Information",
            border_style="cyan"
        )
        console.print(info_panel)
        
        # Display structural signals
        if show_signals and unified.structural:
            signals_text = []
            
            if unified.structural.api_calls:
                signals_text.append(f"[bold]API Calls:[/bold] {len(unified.structural.api_calls)}")
                for call in unified.structural.api_calls[:5]:
                    signals_text.append(f"  • {call.method} {call.endpoint or '(endpoint not extracted)'}")
            
            if unified.structural.assertions:
                signals_text.append(f"\n[bold]Assertions:[/bold] {len(unified.structural.assertions)}")
                for assertion in unified.structural.assertions[:5]:
                    signals_text.append(f"  • {assertion.type}: {assertion.target}")
            
            if unified.structural.ui_interactions:
                signals_text.append(f"\n[bold]UI Interactions:[/bold] {len(unified.structural.ui_interactions)}")
                for interaction in unified.structural.ui_interactions[:5]:
                    signals_text.append(f"  • {interaction}")
            
            if unified.structural.imports:
                signals_text.append(f"\n[bold]Imports:[/bold] {len(unified.structural.imports)}")
                for imp in unified.structural.imports[:5]:
                    signals_text.append(f"  • {imp}")
            
            if unified.structural.functions:
                signals_text.append(f"\n[bold]Functions:[/bold] {len(unified.structural.functions)}")
            
            if unified.structural.classes:
                signals_text.append(f"\n[bold]Classes:[/bold] {len(unified.structural.classes)}")
            
            if signals_text:
                signals_panel = Panel(
                    "\n".join(signals_text),
                    title="Extracted Signals",
                    border_style="green"
                )
                console.print(signals_panel)
        
        # Show source code if requested
        if show_code:
            try:
                code = test_file.read_text()
                # Find the test method (simplified)
                if test_name in code:
                    syntax = Syntax(code, adapter.get_language(), theme="monokai", line_numbers=True)
                    console.print("\n")
                    console.print(syntax)
            except Exception as e:
                console.print(f"[yellow]Could not read source code:[/yellow] {e}")
        
        console.print()
        
    except Exception as e:
        console.print(f"[red]Error analyzing test:[/red] {e}")
        logger.exception("Test analysis failed")
        raise typer.Exit(1)


@app.command("stats")
def framework_stats(
    project_root: Path = typer.Argument(..., help="Project root directory", exists=True, file_okay=False),
):
    """Show statistics on framework usage in a project."""
    console.print(f"\n[cyan]Analyzing project:[/cyan] {project_root}\n")
    
    frameworks = AdapterFactory.list_supported_frameworks()
    
    table = Table(title="Framework Usage Statistics")
    table.add_column("Framework", style="cyan")
    table.add_column("Test Files", justify="right", style="green")
    table.add_column("Status", style="yellow")
    
    total_files = 0
    
    for framework in frameworks:
        try:
            adapter = AdapterFactory.get_adapter(framework)
            test_files = adapter.discover_tests(str(project_root))
            count = len(test_files)
            total_files += count
            
            if count > 0:
                status = "✓ Active"
            else:
                status = "− Not found"
            
            table.add_row(framework, str(count), status)
            
        except Exception as e:
            table.add_row(framework, "?", f"⚠️ Error")
    
    console.print(table)
    console.print(f"\n[bold]Total test files:[/bold] {total_files}\n")


@app.command("info")
def framework_info(
    framework: str = typer.Argument(..., help="Framework name")
):
    """Show detailed information about a specific framework."""
    try:
        adapter = AdapterFactory.get_adapter(framework)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    
    console.print(f"\n[bold cyan]{framework.upper()} Framework Information[/bold cyan]\n")
    
    info_lines = [
        f"[bold]Framework:[/bold] {adapter.get_framework_name()}",
        f"[bold]Language:[/bold] {adapter.get_language()}",
        f"[bold]Feature:[/bold] {getattr(adapter, '_feature', 'general')}",
    ]
    
    # Add framework-specific information
    if hasattr(adapter, 'file_patterns'):
        patterns = getattr(adapter, 'file_patterns', [])
        if patterns:
            info_lines.append(f"[bold]File Patterns:[/bold] {', '.join(patterns)}")
    
    info_panel = Panel(
        "\n".join(info_lines),
        border_style="cyan"
    )
    console.print(info_panel)
    
    # Show capabilities
    capabilities = []
    if hasattr(adapter, '_extract_priority'):
        capabilities.append("✓ Priority extraction")
    if hasattr(adapter, '_extract_tags') or hasattr(adapter, '_extract_pytest_marks'):
        capabilities.append("✓ Tag extraction")
    if hasattr(adapter, 'extract_ast_signals'):
        capabilities.append("✓ AST extraction")
    if hasattr(adapter, '_parse_gherkin_steps'):
        capabilities.append("✓ Gherkin parsing")
    
    if capabilities:
        console.print("\n[bold]Capabilities:[/bold]")
        for cap in capabilities:
            console.print(f"  {cap}")
    
    console.print()
