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
from rich.table import Table
from rich import box

from core.logging import get_logger

console = Console()
logger = get_logger(__name__)


def log_command(
    log_file: Path = typer.Argument(..., help="Path to log file to parse"),
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
    
    Examples:
        crossbridge log output.xml
        crossbridge log output.xml --enable-ai
        crossbridge log output.xml --output results.json
        crossbridge log output.xml --test-name "Login*"
        crossbridge log output.xml --status FAIL
    """
    parse_log_file(
        log_file=log_file,
        output=output,
        enable_ai=enable_ai,
        app_logs=app_logs,
        test_name=test_name,
        test_id=test_id,
        status=status,
        error_code=error_code,
        pattern=pattern,
        time_from=time_from,
        time_to=time_to,
        no_analyze=no_analyze,
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
        
        if enable_ai:
            self._show_ai_banner(framework)
        else:
            console.print("[blue]Running intelligence analysis...[/blue]")
        
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
            # Manual spinner implementation for better Windows/Git Bash compatibility
            import threading
            import time
            import sys
            
            response_holder = [None]
            error_holder = [None]
            stop_spinner = [False]
            
            def make_request():
                try:
                    response_holder[0] = requests.post(
                        f"{self.sidecar_url}{endpoint}",
                        json=payload,
                        timeout=7200  # 2 hours for AI analysis
                    )
                except Exception as e:
                    error_holder[0] = e
                finally:
                    stop_spinner[0] = True
            
            def animate_spinner():
                """Manual spinner animation that works in all terminals."""
                spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
                idx = 0
                message = "Processing test results and extracting failure patterns..."
                
                while not stop_spinner[0]:
                    # Use \r to return to start of line and overwrite
                    sys.stdout.write(f"\r{spinner_chars[idx]} {message}")
                    sys.stdout.flush()
                    idx = (idx + 1) % len(spinner_chars)
                    time.sleep(0.1)
                
                # Clear the spinner line when done
                sys.stdout.write("\r" + " " * (len(message) + 3) + "\r")
                sys.stdout.flush()
            
            # Start both threads
            request_thread = threading.Thread(target=make_request, daemon=True)
            spinner_thread = threading.Thread(target=animate_spinner, daemon=True)
            
            request_thread.start()
            spinner_thread.start()
            
            # Wait for request to complete
            request_thread.join()
            
            # Stop spinner and wait for it to finish
            stop_spinner[0] = True
            spinner_thread.join(timeout=1)
            
            # Check for errors
            if error_holder[0]:
                raise error_holder[0]
            
            response = response_holder[0]
            
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
                    console.print()
                    console.print("━" * 41, style="green")
                    console.print("🤖  AI-ENHANCED ANALYSIS ENABLED", style="green bold")
                    console.print("━" * 41, style="green")
                    console.print(f"[green]Provider: Self-hosted ({model})[/green]")
                    console.print("[green]Cost: No additional costs (local inference)[/green]")
                    console.print()
                else:
                    cost_per_1k = info.get("cost_per_1k_tokens", 0)
                    typical_cost = info.get("typical_run_cost", "$0.01-$0.10")
                    
                    console.print()
                    console.print("━" * 41, style="yellow")
                    console.print("⚠️  AI-ENHANCED ANALYSIS ENABLED", style="yellow bold")
                    console.print("━" * 41, style="yellow")
                    console.print(f"[yellow]Provider: {provider.title()} ({model})[/yellow]")
                    console.print(f"[yellow]Cost: ~${cost_per_1k} per 1000 tokens[/yellow]")
                    console.print(f"[yellow]Typical analysis: {typical_cost}[/yellow]")
                    console.print()
        except Exception:
            console.print()
            console.print("━" * 41, style="yellow")
            console.print("⚠️  AI-ENHANCED ANALYSIS ENABLED", style="yellow bold")
            console.print("━" * 41, style="yellow")
            console.print()
    
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
        
        # Display detailed AI failure analysis if available
        if data.get("ai_analysis"):
            self._display_ai_failure_analysis(data)
        
        # Display AI usage if available
        if data.get("ai_usage"):
            self._display_ai_usage(data)
    
    def _display_robot_results(self, data: dict):
        """Display Robot Framework results."""
        console.print("━" * 41, style="green")
        console.print("           Robot Framework Results", style="green bold")
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
        
        console.print("[blue]Test Statistics:[/blue]")
        console.print(f"  Total:    {total}")
        console.print(f"  Passed:   [green]{passed}[/green]")
        console.print(f"  Failed:   [red]{failed}[/red]")
        console.print(f"  Duration: {duration}")
        console.print()
        
        # Failed keywords - show top 5 with count
        failed_kw = data.get("failed_keywords", [])
        if failed_kw:
            total_failed = len(failed_kw)
            display_count = min(total_failed, 5)
            console.print(f"[red]Top Failed Keywords (showing {display_count} of {total_failed}):[/red]")
            for kw in failed_kw[:5]:
                name = kw.get("name", "Unknown")
                library = kw.get("library", "")
                error = kw.get("error", "")
                lib_str = f" [{library}]" if library else ""
                console.print(f"  ❌ {name}{lib_str}")
                if error:
                    console.print(f"     [dim]Error: {error}[/dim]")
            console.print()
        
        # Slowest tests
        slowest_tests = data.get("slowest_tests", [])
        if slowest_tests:
            display_count = min(len(slowest_tests), 5)
            console.print(f"[yellow]Slowest Tests (Top {display_count}):[/yellow]")
            for test in slowest_tests[:5]:
                test_name = test.get("name", "Unknown")
                elapsed = test.get("elapsed_ms", 0)
                test_duration = self.format_duration(elapsed // 1000)
                
                # Truncate long test names
                if len(test_name) > 80:
                    test_name = test_name[:77] + "..."
                
                # Right-align duration
                console.print(f"  {test_name:<85} {test_duration:>10}")
            console.print()
    
    def _display_cypress_results(self, data: dict):
        """Display Cypress results."""
        console.print("━" * 41, style="green")
        console.print("           Cypress Test Results", style="green bold")
        console.print("━" * 41, style="green")
        console.print()
        
        stats = data.get("statistics", {})
        console.print("[blue]Test Statistics:[/blue]")
        console.print(f"  Total:  {stats.get('total_tests', 0)}")
        console.print(f"  Passed: [green]{stats.get('passed_tests', 0)}[/green]")
        console.print(f"  Failed: [red]{stats.get('failed_tests', 0)}[/red]")
        console.print()
        
        failures = data.get("failures", [])
        if failures:
            console.print("[red]Failed Tests:[/red]")
            for failure in failures:
                title = failure.get("title", "Unknown")
                error = failure.get("error_message", "")
                console.print(f"  ❌ {title}: {error}")
            console.print()
    
    def _display_playwright_results(self, data: dict):
        """Display Playwright results."""
        console.print("━" * 41, style="green")
        console.print("          Playwright Trace Analysis", style="green bold")
        console.print("━" * 41, style="green")
        console.print()
        
        action_count = len(data.get("actions", []))
        network_count = len(data.get("network_calls", []))
        
        console.print("[blue]Trace Summary:[/blue]")
        console.print(f"  Actions:       {action_count}")
        console.print(f"  Network Calls: {network_count}")
        console.print()
        
        if action_count > 0:
            console.print("[blue]Actions (First 10):[/blue]")
            for action in data.get("actions", [])[:10]:
                action_type = action.get("action", "Unknown")
                selector = action.get("selector", "N/A")
                console.print(f"  • {action_type}: {selector}")
            console.print()
    
    def _display_behave_results(self, data: dict):
        """Display Behave BDD results."""
        console.print("━" * 41, style="green")
        console.print("            Behave BDD Results", style="green bold")
        console.print("━" * 41, style="green")
        console.print()
        
        feature_count = len(data.get("features", []))
        stats = data.get("statistics", {})
        
        console.print("[blue]BDD Statistics:[/blue]")
        console.print(f"  Features:  {feature_count}")
        console.print(f"  Scenarios: {stats.get('total_scenarios', 0)}")
        console.print(f"  Passed:    [green]{stats.get('passed_scenarios', 0)}[/green]")
        console.print(f"  Failed:    [red]{stats.get('failed_scenarios', 0)}[/red]")
        console.print()
    
    def _display_java_results(self, data: dict):
        """Display Java Cucumber results."""
        console.print("━" * 41, style="green")
        console.print("       Java Cucumber Step Definitions", style="green bold")
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
            
            console.print("[blue]By Type:[/blue]")
            console.print(f"  Given: {given}")
            console.print(f"  When:  {when}")
            console.print(f"  Then:  {then}")
            console.print()
    
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
    
    def _display_ai_failure_analysis(self, data: dict):
        """Display detailed AI failure analysis."""
        ai_analysis = data.get("ai_analysis", {})
        
        if not ai_analysis:
            return
        
        console.print()
        console.print("━" * 41, style="cyan")
        console.print("  🤖 AI Failure Analysis", style="cyan bold")
        console.print("━" * 41, style="cyan")
        console.print()
        
        # Get failure analyses
        failure_analyses = ai_analysis.get("failure_analyses", [])
        
        if not failure_analyses:
            console.print("[dim]No AI failure analyses available[/dim]")
            return
        
        for idx, analysis in enumerate(failure_analyses, 1):
            # Test/Failure identification
            test_name = analysis.get("test_name", "Unknown Test")
            failure_id = analysis.get("failure_id", "N/A")
            
            console.print(f"[yellow]Failure #{idx}:[/yellow] {test_name}")
            if failure_id != "N/A":
                console.print(f"[dim]ID: {failure_id}[/dim]")
            console.print()
            
            # Category and confidence
            category = analysis.get("category", "unknown")
            confidence = analysis.get("final_confidence", 0.0)
            primary_rule = analysis.get("primary_rule", "")
            
            category_color = {
                "flaky": "yellow",
                "product_defect": "red",
                "automation_defect": "magenta",
                "environment_issue": "blue",
                "test_data_issue": "cyan"
            }.get(category.lower(), "white")
            
            console.print(f"  [blue]Classification:[/blue] [{category_color}]{category.upper()}[/{category_color}]")
            console.print(f"  [blue]Confidence:[/blue] {confidence:.1%}")
            if primary_rule:
                console.print(f"  [blue]Primary Rule:[/blue] {primary_rule}")
            console.print()
            
            # Root cause / AI explanation
            explanation = analysis.get("ai_explanation", analysis.get("explanation", ""))
            if explanation:
                console.print(f"  [green]Root Cause Analysis:[/green]")
                # Wrap long explanations
                for line in explanation.split('\n'):
                    if line.strip():
                        console.print(f"    {line.strip()}")
                console.print()
            
            # Code references
            code_refs = analysis.get("code_references", [])
            if code_refs:
                console.print(f"  [green]Code References:[/green]")
                for ref in code_refs[:3]:  # Show top 3
                    file_path = ref.get("file", "")
                    line_num = ref.get("line", "")
                    context = ref.get("context", "")
                    if file_path:
                        console.print(f"    📄 {file_path}:{line_num}")
                        if context:
                            console.print(f"       [dim]{context}[/dim]")
                console.print()
            
            # Evidence context
            evidence = analysis.get("evidence_context", {})
            if evidence:
                error_summary = evidence.get("error_message_summary", "")
                stacktrace = evidence.get("stacktrace_summary", "")
                
                if error_summary and error_summary != stacktrace:
                    console.print(f"  [blue]Error:[/blue] {error_summary}")
                if stacktrace:
                    console.print(f"  [blue]Stack Trace:[/blue] {stacktrace}")
                
                if error_summary or stacktrace:
                    console.print()
            
            # Rule influences (show top contributing rules)
            rule_influence = analysis.get("rule_influence", [])
            if rule_influence:
                # Filter to matched rules or top contributors
                top_rules = [r for r in rule_influence if r.get("matched", False) or r.get("contribution", 0) > 0][:3]
                if top_rules:
                    console.print(f"  [dim]Key Decision Factors:[/dim]")
                    for rule in top_rules:
                        rule_name = rule.get("rule_name", "")
                        rule_explanation = rule.get("explanation", "")
                        matched = "✓" if rule.get("matched", False) else "○"
                        console.print(f"    {matched} {rule_name}: {rule_explanation}")
                    console.print()
            
            # Separator between failures
            if idx < len(failure_analyses):
                console.print("[dim]" + "─" * 41 + "[/dim]")
                console.print()
    
    def _display_ai_usage(self, data: dict):
        """Display AI usage summary."""
        ai_usage = data.get("ai_usage", {})
        
        console.print()
        console.print("━" * 41, style="blue")
        console.print("      AI Log Analysis Summary", style="blue bold")
        console.print("━" * 41, style="blue")
        console.print()
        
        provider = ai_usage.get("provider", "unknown")
        model = ai_usage.get("model", "unknown")
        total_tokens = ai_usage.get("total_tokens", 0)
        cost = ai_usage.get("cost", 0)
        
        console.print(f"  [blue]Provider:[/blue]       {provider.title()}")
        console.print(f"  [blue]Model:[/blue]          {model}")
        console.print(f"  [blue]Total Tokens:[/blue]   {total_tokens}")
        
        if provider not in ["selfhosted", "ollama"]:
            console.print(f"  [blue]Total Cost:[/blue]     ${cost:.4f}")
        
        console.print(table)


def parse_log_file(
    log_file: Path,
    output: Optional[Path] = None,
    enable_ai: bool = False,
    app_logs: Optional[str] = None,
    test_name: Optional[str] = None,
    test_id: Optional[str] = None,
    status: Optional[str] = None,
    error_code: Optional[str] = None,
    pattern: Optional[str] = None,
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    no_analyze: bool = False,
):
    """Core log parsing logic."""
    logger.info(f"Starting log parsing for: {log_file}")
    parser = LogParser()
    
    # Check sidecar
    if not parser.check_sidecar():
        logger.error("Sidecar check failed")
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
        logger.error(f"Unknown log format: {log_file}")
        raise typer.Exit(1)
    
    console.print(f"[green]✓[/green] Detected framework: [blue]{framework}[/blue]")
    logger.info(f"Detected framework: {framework}")
    
    # Parse log
    parsed_data = parser.parse_log(log_file, framework)
    
    if not parsed_data:
        logger.error("Log parsing failed - empty result")
        raise typer.Exit(1)
    
    logger.info("Log parsing successful")
    
    # Enrich with intelligence if not disabled
    if not no_analyze:
        logger.info(f"Starting intelligence analysis (AI enabled: {enable_ai})")
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
        logger.info(f"Results saved to: {output}")
    else:
        # Save to default file
        default_output = log_file.with_suffix(f".parsed.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        default_output.write_text(json.dumps(filtered_data, indent=2))
        console.print(f"\n[blue]Full results saved to: {default_output}[/blue]")
        logger.info(f"Results saved to: {default_output}")
    
    console.print()
    console.print("━" * 41, style="green")
    console.print("[green]✓ Parsing complete![/green]")
    logger.info("Log parsing completed successfully")


if __name__ == "__main__":
    typer.run(log_command)
