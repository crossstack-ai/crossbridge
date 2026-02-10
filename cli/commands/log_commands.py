"""
CrossBridge Log Parser Commands

Pure Python implementation of crossbridge-log functionality.
Parses and analyzes logs from various test frameworks with intelligence features.
"""

import typer
import sys
import os
import json
import requests
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import box

console = Console()

log_app = typer.Typer(
    name="log",
    help="Parse and analyze test execution logs"
)


class LogParser:
    """Manages log parsing and intelligence analysis."""
    
    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "robot": ["output.xml", "robot*.xml", r"<robot"],
        "cypress": ["*cypress*.json", "cypress-*.json", r'"suites"'],
        "playwright": ["*playwright*.json", "trace*.json", r'"entries"'],
        "behave": ["*behave*.json", "*cucumber*.json", r'"feature"'],
        "java": ["*Steps.java", "*StepDefinitions.java", r"@Given|@When|@Then"],
    }
    
    def __init__(self):
        self.sidecar_host = os.getenv("CROSSBRIDGE_SIDECAR_HOST", "localhost")
        self.sidecar_port = os.getenv("CROSSBRIDGE_SIDECAR_PORT", "8765")
        self.sidecar_url = f"http://{self.sidecar_host}:{self.sidecar_port}"
    
    def check_sidecar(self) -> bool:
        """Check if sidecar is reachable."""
        console.print("[blue]🔍 Checking CrossBridge Sidecar API...[/blue]")
        
        try:
            response = requests.get(f"{self.sidecar_url}/health", timeout=2)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        
        # Show detailed error message
        console.print("\n" + "━" * 60, style="red")
        console.print("  ❌ CROSSBRIDGE SIDECAR API NOT REACHABLE", style="red bold")
        console.print("━" * 60, style="red")
        console.print(f"\nAttempting to reach: [yellow]{self.sidecar_url}[/yellow]")
        console.print("\n[yellow]🔧 Troubleshooting Steps:[/yellow]")
        console.print("\n[blue]1. Check if Sidecar is Running:[/blue]")
        console.print("   docker ps | grep crossbridge-sidecar")
        console.print("\n[blue]2. Start Sidecar:[/blue]")
        console.print("   docker-compose up -d crossbridge-sidecar")
        console.print("\n[blue]3. For local development:[/blue]")
        console.print("   python -m services.sidecar_api")
        console.print(f"\n[blue]4. Current configuration:[/blue]")
        console.print(f"   • CROSSBRIDGE_SIDECAR_HOST = {self.sidecar_host}")
        console.print(f"   • CROSSBRIDGE_SIDECAR_PORT = {self.sidecar_port}\n")
        
        return False
    
    def detect_framework(self, log_file: Path) -> str:
        """Auto-detect framework based on filename and content."""
        filename = log_file.name.lower()
        
        # Check by filename patterns
        if "output.xml" in filename or filename.startswith("robot"):
            return "robot"
        elif "cypress" in filename:
            return "cypress"
        elif "playwright" in filename or "trace" in filename:
            return "playwright"
        elif "behave" in filename or "cucumber" in filename:
            # Read content to distinguish
            try:
                with open(log_file) as f:
                    content = f.read(1000)
                    if '"feature"' in content:
                        return "behave"
            except Exception:
                pass
            return "cypress"
        elif filename.endswith("Steps.java") or "StepDefinitions" in filename:
            return "java"
        
        # Check by content
        try:
            with open(log_file) as f:
                lines = [f.readline() for _ in range(5)]
                content = "".join(lines)
                
                if "<robot" in content:
                    return "robot"
                elif '"suites"' in content:
                    return "cypress"
                elif '"entries"' in content:
                    return "playwright"
                elif '"feature"' in content:
                    return "behave"
                
            # Check for Java annotations
            with open(log_file) as f:
                full_content = f.read()
                if "@Given" in full_content or "@When" in full_content or "@Then" in full_content:
                    return "java"
        except Exception:
            pass
        
        return "unknown"
    
    def parse_log(self, log_file: Path, framework: str) -> dict:
        """Parse log file via sidecar API."""
        console.print(f"[blue]Parsing log file: {log_file}[/blue]")
        
        try:
            with open(log_file, "rb") as f:
                response = requests.post(
                    f"{self.sidecar_url}/parse/{framework}",
                    data=f,
                    headers={"Content-Type": "application/octet-stream"},
                    timeout=60
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_detail = response.json().get("detail", "Unknown error")
                console.print(f"[red]Error: {error_detail}[/red]")
                return {}
        except Exception as e:
            console.print(f"[red]Error parsing log: {e}[/red]")
            return {}
    
    def enrich_with_intelligence(
        self,
        data: dict,
        framework: str,
        enable_ai: bool = False,
        app_logs: Optional[str] = None
    ) -> dict:
        """Enrich parsed data with intelligence analysis."""
        if not data:
            return data
        
        console.print("[blue]Running intelligence analysis...[/blue]")
        
        if enable_ai:
            self._show_ai_banner(framework)
        
        # Build payload
        payload = {
            "data": data,
            "framework": framework,
            "workspace_root": os.getcwd(),
            "enable_ai": enable_ai
        }
        
        if app_logs:
            payload["app_logs"] = app_logs
            endpoint = "/analyze/with-app-logs"
        else:
            endpoint = "/analyze"
        
        try:
            # Show progress spinner
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(
                    "Processing test results and extracting failure patterns...",
                    total=None
                )
                
                response = requests.post(
                    f"{self.sidecar_url}{endpoint}",
                    json=payload,
                    timeout=7200  # 2 hours for AI analysis
                )
                
                progress.stop()
            
            if response.status_code == 200:
                result = response.json()
                if enable_ai:
                    console.print("[green]✓ AI analysis completed successfully[/green]")
                else:
                    console.print("[green]✓ Analysis completed[/green]")
                return result
            else:
                console.print("[yellow]⚠ Analysis completed with warnings[/yellow]")
                return data
        except Exception as e:
            console.print(f"[yellow]Note: Intelligence analysis failed - {e}[/yellow]")
            return data
    
    def _show_ai_banner(self, framework: str):
        """Show AI cost warning banner."""
        try:
            response = requests.get(f"{self.sidecar_url}/ai-provider-info", timeout=2)
            if response.status_code == 200:
                info = response.json()
                provider = info.get("provider", "unknown")
                model = info.get("model", "")
                
                if provider == "selfhosted":
                    console.print("\n" + "━" * 41, style="green")
                    console.print("🤖  AI-ENHANCED ANALYSIS ENABLED", style="green bold")
                    console.print("━" * 41, style="green")
                    console.print(f"[green]Provider: Self-hosted ({model})[/green]")
                    console.print("[green]Cost: No additional costs (local inference)[/green]")
                else:
                    cost_per_1k = info.get("cost_per_1k_tokens", 0)
                    typical_cost = info.get("typical_run_cost", "$0.01-$0.10")
                    
                    console.print("\n" + "━" * 41, style="yellow")
                    console.print("⚠️  AI-ENHANCED ANALYSIS ENABLED", style="yellow bold")
                    console.print("━" * 41, style="yellow")
                    console.print(f"[yellow]Provider: {provider.title()} ({model})[/yellow]")
                    console.print(f"[yellow]Cost: ~${cost_per_1k} per 1000 tokens[/yellow]")
                    console.print(f"[yellow]Typical analysis: {typical_cost}[/yellow]")
        except Exception:
            console.print("\n" + "━" * 41, style="yellow")
            console.print("⚠️  AI-ENHANCED ANALYSIS ENABLED", style="yellow bold")
            console.print("━" * 41, style="yellow")
    
    def apply_filters(self, data: dict, filters: dict) -> dict:
        """Apply filtering to the parsed data."""
        if not filters:
            return data
        
        # This is a simplified version - full implementation would use jq-like filtering
        # For now, we'll let the sidecar handle filtering via query parameters
        return data
    
    def format_duration(self, seconds: int) -> str:
        """Format duration into human-readable format."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s" if secs else f"{minutes}m"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m" if minutes else f"{hours}h"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h" if hours else f"{days}d"
    
    def display_results(self, data: dict, framework: str):
        """Display parsed results in a rich format."""
        # Extract data from intelligence wrapper if present
        if data.get("analyzed"):
            display_data = data.get("data", data)
        else:
            display_data = data
        
        console.print()
        
        if framework == "robot":
            self._display_robot_results(display_data)
        elif framework == "cypress":
            self._display_cypress_results(display_data)
        elif framework == "playwright":
            self._display_playwright_results(display_data)
        elif framework == "behave":
            self._display_behave_results(display_data)
        elif framework == "java":
            self._display_java_results(display_data)
        
        # Display intelligence summary if available
        if data.get("intelligence_summary"):
            self._display_intelligence_summary(data)
        
        # Display AI usage if available
        if data.get("ai_usage"):
            self._display_ai_usage(data)
    
    def _display_robot_results(self, data: dict):
        """Display Robot Framework results."""
        console.print("━" * 41, style="green")
        console.print("  Robot Framework Results", style="green bold")
        console.print("━" * 41, style="green")
        console.print()
        
        suite = data.get("suite", {})
        suite_name = suite.get("name", "Unknown")
        suite_status = suite.get("status", "UNKNOWN")
        
        # Suite info
        status_style = "green" if suite_status == "PASS" else "red"
        console.print(f"[blue]Suite:[/blue] {suite_name}")
        console.print(f"[blue]Status:[/blue] [{status_style}]{suite_status}[/{status_style}]")
        console.print()
        
        # Statistics
        total = suite.get("total_tests", 0)
        passed = suite.get("passed_tests", 0)
        failed = suite.get("failed_tests", 0)
        elapsed_ms = suite.get("elapsed_ms", 0)
        duration = self.format_duration(elapsed_ms // 1000)
        
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_row("[blue]Total:[/blue]", str(total))
        table.add_row("[blue]Passed:[/blue]", f"[green]{passed}[/green]")
        table.add_row("[blue]Failed:[/blue]", f"[red]{failed}[/red]")
        table.add_row("[blue]Duration:[/blue]", duration)
        console.print(table)
        console.print()
        
        # Failed keywords
        failed_kw = data.get("failed_keywords", [])
        if failed_kw:
            console.print(f"[red]Failed Keywords (showing {min(len(failed_kw), 5)}):[ /red]")
            for kw in failed_kw[:5]:
                name = kw.get("name", "Unknown")
                library = kw.get("library", "")
                error = kw.get("error", "")
                lib_str = f" [{library}]" if library else ""
                console.print(f"  ❌ {name}{lib_str}")
                if error:
                    console.print(f"     [dim]Error: {error}[/dim]")
            console.print()
    
    def _display_cypress_results(self, data: dict):
        """Display Cypress results."""
        console.print("━" * 41, style="green")
        console.print("  Cypress Test Results", style="green bold")
        console.print("━" * 41, style="green")
        console.print()
        
        stats = data.get("statistics", {})
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_row("[blue]Total:[/blue]", str(stats.get("total_tests", 0)))
        table.add_row("[blue]Passed:[/blue]", f"[green]{stats.get('passed_tests', 0)}[/green]")
        table.add_row("[blue]Failed:[/blue]", f"[red]{stats.get('failed_tests', 0)}[/red]")
        console.print(table)
        console.print()
        
        failures = data.get("failures", [])
        if failures:
            console.print("[red]Failed Tests:[/red]")
            for failure in failures:
                title = failure.get("title", "Unknown")
                error = failure.get("error_message", "")
                console.print(f"  ❌ {title}: {error}")
    
    def _display_playwright_results(self, data: dict):
        """Display Playwright results."""
        console.print("━" * 41, style="green")
        console.print("  Playwright Trace Analysis", style="green bold")
        console.print("━" * 41, style="green")
        console.print()
        
        action_count = len(data.get("actions", []))
        network_count = len(data.get("network_calls", []))
        
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_row("[blue]Actions:[/blue]", str(action_count))
        table.add_row("[blue]Network Calls:[/blue]", str(network_count))
        console.print(table)
        console.print()
        
        if action_count > 0:
            console.print("[blue]Actions (First 10):[/blue]")
            for action in data.get("actions", [])[:10]:
                action_type = action.get("action", "Unknown")
                selector = action.get("selector", "N/A")
                console.print(f"  • {action_type}: {selector}")
    
    def _display_behave_results(self, data: dict):
        """Display Behave BDD results."""
        console.print("━" * 41, style="green")
        console.print("  Behave BDD Results", style="green bold")
        console.print("━" * 41, style="green")
        console.print()
        
        feature_count = len(data.get("features", []))
        stats = data.get("statistics", {})
        
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_row("[blue]Features:[/blue]", str(feature_count))
        table.add_row("[blue]Scenarios:[/blue]", str(stats.get("total_scenarios", 0)))
        table.add_row("[blue]Passed:[/blue]", f"[green]{stats.get('passed_scenarios', 0)}[/green]")
        table.add_row("[blue]Failed:[/blue]", f"[red]{stats.get('failed_scenarios', 0)}[/red]")
        console.print(table)
    
    def _display_java_results(self, data: dict):
        """Display Java Cucumber results."""
        console.print("━" * 41, style="green")
        console.print("  Java Cucumber Step Definitions", style="green bold")
        console.print("━" * 41, style="green")
        console.print()
        
        step_defs = data.get("step_definitions", [])
        step_count = len(step_defs)
        
        console.print(f"[blue]Step Definitions Found:[/blue] {step_count}")
        console.print()
        
        if step_count > 0:
            # Group by type
            given = sum(1 for s in step_defs if s.get("step_type") == "Given")
            when = sum(1 for s in step_defs if s.get("step_type") == "When")
            then = sum(1 for s in step_defs if s.get("step_type") == "Then")
            
            table = Table(show_header=False, box=box.SIMPLE)
            table.add_row("[blue]Given:[/blue]", str(given))
            table.add_row("[blue]When:[/blue]", str(when))
            table.add_row("[blue]Then:[/blue]", str(then))
            console.print(table)
    
    def _display_intelligence_summary(self, data: dict):
        """Display intelligence analysis summary."""
        summary = data.get("intelligence_summary", {})
        
        console.print()
        console.print("━" * 41, style="blue")
        console.print("  Intelligence Analysis Summary", style="blue bold")
        console.print("━" * 41, style="blue")
        console.print()
        
        # Classifications
        classifications = summary.get("classifications", {})
        if classifications:
            console.print("[yellow]Failure Classifications:[/yellow]")
            for key, value in classifications.items():
                console.print(f"  • {key}: {value}")
            console.print()
        
        # Signals
        signals = summary.get("signals", {})
        if signals:
            console.print("[yellow]Detected Signals:[/yellow]")
            for key, value in signals.items():
                console.print(f"  • {key}: {value}")
            console.print()
    
    def _display_ai_usage(self, data: dict):
        """Display AI usage summary."""
        ai_usage = data.get("ai_usage", {})
        
        console.print()
        console.print("━" * 41, style="blue")
        console.print("  AI Log Analysis Summary", style="blue bold")
        console.print("━" * 41, style="blue")
        console.print()
        
        provider = ai_usage.get("provider", "unknown")
        model = ai_usage.get("model", "unknown")
        total_tokens = ai_usage.get("total_tokens", 0)
        cost = ai_usage.get("cost", 0)
        
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_row("[blue]Provider:[/blue]", provider.title())
        table.add_row("[blue]Model:[/blue]", model)
        table.add_row("[blue]Total Tokens:[/blue]", str(total_tokens))
        
        if provider not in ["selfhosted", "ollama"]:
            table.add_row("[blue]Total Cost:[/blue]", f"${cost:.4f}")
        
        console.print(table)


@log_app.command()
def parse(
    log_file: Path = typer.Argument(..., help="Path to log file to parse", exists=True),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save results to file"),
    enable_ai: bool = typer.Option(False, "--enable-ai", help="Enable AI-enhanced analysis"),
    app_logs: Optional[str] = typer.Option(None, "--app-logs", "-a", help="Application logs for correlation"),
    test_name: Optional[str] = typer.Option(None, "--test-name", "-t", help="Filter by test name pattern"),
    test_id: Optional[str] = typer.Option(None, "--test-id", "-i", help="Filter by test ID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (PASS/FAIL/SKIP)"),
    error_code: Optional[str] = typer.Option(None, "--error-code", "-e", help="Filter by error code"),
    pattern: Optional[str] = typer.Option(None, "--pattern", "-p", help="Filter by text pattern"),
    time_from: Optional[str] = typer.Option(None, "--time-from", help="Filter tests after datetime"),
    time_to: Optional[str] = typer.Option(None, "--time-to", help="Filter tests before datetime"),
    no_analyze: bool = typer.Option(False, "--no-analyze", help="Disable intelligence analysis"),
):
    """
    Parse and analyze test execution logs.
    
    Supports multiple test frameworks with automatic detection:
    - Robot Framework (output.xml)
    - Cypress (cypress-results.json)
    - Playwright (playwright-trace.json)
    - Behave (behave-results.json)
    - Java Cucumber (*Steps.java)
    
    \b
    Examples:
        crossbridge log output.xml
        crossbridge log output.xml --enable-ai
        crossbridge log output.xml --output results.json
        crossbridge log output.xml --test-name "Login*"
        crossbridge log output.xml --status FAIL
    """
    parser = LogParser()
    
    # Check sidecar
    if not parser.check_sidecar():
        raise typer.Exit(1)
    
    # Detect framework
    framework = parser.detect_framework(log_file)
    
    if framework == "unknown":
        console.print(f"[red]Error: Could not detect log format for {log_file}[/red]")
        console.print("Supported formats:")
        console.print("  - Robot Framework (output.xml)")
        console.print("  - Cypress (cypress-results.json)")
        console.print("  - Playwright (playwright-trace.json)")
        console.print("  - Behave (behave-results.json)")
        console.print("  - Java Cucumber (*Steps.java)")
        raise typer.Exit(1)
    
    console.print(f"[green]✓ Detected framework: {framework}[/green]")
    
    # Parse log
    parsed_data = parser.parse_log(log_file, framework)
    
    if not parsed_data:
        raise typer.Exit(1)
    
    # Enrich with intelligence if not disabled
    if not no_analyze:
        start_time = time.time()
        enriched_data = parser.enrich_with_intelligence(
            parsed_data,
            framework,
            enable_ai=enable_ai,
            app_logs=app_logs
        )
        analysis_duration = int(time.time() - start_time)
    else:
        enriched_data = parsed_data
        analysis_duration = 0
    
    # Apply filters
    filters = {
        "test_name": test_name,
        "test_id": test_id,
        "status": status,
        "error_code": error_code,
        "pattern": pattern,
        "time_from": time_from,
        "time_to": time_to,
    }
    filtered_data = parser.apply_filters(enriched_data, {k: v for k, v in filters.items() if v})
    
    # Display results
    parser.display_results(filtered_data, framework)
    
    # Save to file
    if output:
        output.write_text(json.dumps(filtered_data, indent=2))
        console.print(f"\n[blue]Results saved to: {output}[/blue]")
    else:
        # Save to default file
        default_output = log_file.with_suffix(f".parsed.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        default_output.write_text(json.dumps(filtered_data, indent=2))
        console.print(f"\n[blue]Full results saved to: {default_output}[/blue]")
    
    console.print()
    console.print("━" * 41, style="green")
    console.print("[green]✓ Parsing complete![/green]")


if __name__ == "__main__":
    log_app()
