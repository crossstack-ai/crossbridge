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
import threading
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from core.logging import get_logger, configure_logging
from services.logging_service import setup_logging
from core.log_analysis.regression import (
    compare_with_previous,
    compute_confidence_score,
    sanitize_ai_output,
)
from core.log_analysis.structured_output import (
    create_structured_output,
    create_triage_output,
)

console = Console()
logger = get_logger(__name__)


def log_command(
    log_file: Path = typer.Argument(..., help="Path to log file to parse"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save results to file (JSON format)"),
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
    compare_with: Optional[Path] = typer.Option(None, "--compare-with", help="Compare with previous run JSON for regression detection"),
    triage: bool = typer.Option(False, "--triage", help="Triage mode: show only top issues for CI dashboards"),
    max_ai_clusters: int = typer.Option(5, "--max-ai-clusters", help="Maximum clusters to analyze with AI (default: 5)"),
    ai_summary_only: bool = typer.Option(False, "--ai-summary-only", help="AI mode: generate summary only, skip per-cluster analysis"),
):
    """
    Parse and analyze test execution logs with advanced failure analysis.
    
    Supports multiple test frameworks with automatic detection:
    - Robot Framework (output.xml)
    - TestNG (testng-results.xml)
    - Cypress (cypress-results.json)
    - Playwright (playwright-trace.json)
    - Behave (behave-results.json)
    - Java Cucumber (*Steps.java)
    
    Intelligence Features:
    - Automatic failure clustering and deduplication
    - Severity-based prioritization (Critical/High/Medium/Low)
    - Domain classification (Infra/Env/Test/Product)
    - Regression detection (compare with previous runs)
    - Confidence scoring for root cause identification
    - AI-enhanced analysis with smart recommendations
    
    Examples:
        # Basic parsing with clustering
        crossbridge log output.xml
        
        # Compare with previous run
        crossbridge log output.xml --compare-with previous.json
        
        # Triage mode for CI/CD dashboards
        crossbridge log output.xml --triage
        
        # AI-enhanced analysis
        crossbridge log output.xml --enable-ai --max-ai-clusters 3
        
        # Export structured JSON
        crossbridge log output.xml --output results.json
        
        # Filter failed tests only
        crossbridge log output.xml --status FAIL
    """
    try:
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
            compare_with=compare_with,
            triage=triage,
            max_ai_clusters=max_ai_clusters,
            ai_summary_only=ai_summary_only,
        )
    except typer.Exit:
        # Re-raise exit without logging - this is an intentional exit with user-friendly message already shown
        raise
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        logger.error(f"Command failed: {e}", exc_info=True)
        raise typer.Exit(1)


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
        console.print("[blue][i] Checking CrossBridge Sidecar API...[/blue]")
        
        try:
            response = requests.get(f"{self.sidecar_url}/health", timeout=2)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        
        # Show detailed error message
        console.print("\n" + "=" * 60, style="red")
        console.print("  [X] CROSSBRIDGE SIDECAR API NOT REACHABLE", style="red bold")
        console.print("=" * 60, style="red")
        console.print(f"\nAttempting to reach: [yellow]{self.sidecar_url}[/yellow]")
        console.print("\n[yellow][*] Troubleshooting Steps:[/yellow]")
        console.print("\n[blue]1. Check if Sidecar is Running:[/blue]")
        console.print("   docker ps | grep crossbridge-sidecar")
        console.print("\n[blue]2. Start Sidecar:[/blue]")
        console.print("   docker-compose up -d crossbridge-sidecar")
        console.print("\n[blue]3. For local development:[/blue]")
        console.print("   python -m services.sidecar_api")
        console.print(f"\n[blue]4. Current configuration:[/blue]")
        console.print(f"   - CROSSBRIDGE_SIDECAR_HOST = {self.sidecar_host}")
        console.print(f"   - CROSSBRIDGE_SIDECAR_PORT = {self.sidecar_port}\n")
        
        return False
    
    def detect_framework(self, log_file: Path) -> str:
        """Auto-detect framework based on filename and content."""
        filename = log_file.name.lower()
        
        # Check for Robot Framework HTML files (not parseable)
        if filename in ("log.html", "report.html") or (filename.endswith(".html") and "robot" in filename):
            return "robot-html-unsupported"
        
        # Check by filename patterns
        if "output.xml" in filename or filename.startswith("robot"):
            return "robot"
        elif "testng" in filename:
            # TestNG files: testng-results.xml, TestNG-Report.xml, etc.
            return "testng"
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
                elif "<testng-results" in content:
                    return "testng"
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
            console.print("[blue][AI] Running AI-enhanced analysis... (this may take 30-120 minutes for large logs)[/blue]")
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
            # Simple approach: use print() with flush for spinner
            response_holder = [None]
            error_holder = [None]
            
            def make_request():
                try:
                    response_holder[0] = requests.post(
                        f"{self.sidecar_url}{endpoint}",
                        json=payload,
                        timeout=7200  # 2 hours for AI analysis
                    )
                except Exception as e:
                    error_holder[0] = e
            
            # Spinner frames
            spin_chars = ['|', '/', '-', '\\']
            message = "Processing test results and extracting failure patterns..."
            
            # Start request thread
            request_thread = threading.Thread(target=make_request, daemon=True)
            request_thread.start()
            
            # Use ASCII spinner chars that work in all terminals (Git Bash compatible)
            spin_chars = ['|', '/', '-', '\\']  # Classic ASCII spinner
            spin_index = 0
            
            # Keep spinning until we have a response or error
            while response_holder[0] is None and error_holder[0] is None:
                # Show message with current spinner char, use \r to overwrite
                sys.stderr.write(f"\r  {message} {spin_chars[spin_index]}")
                sys.stderr.flush()
                spin_index = (spin_index + 1) % len(spin_chars)
                time.sleep(0.15)
            
            # Clear the spinner line and move to next line
            sys.stderr.write("\r" + " " * (len(message) + 10) + "\r")
            sys.stderr.flush()
            
            # Wait for thread to fully finish
            request_thread.join(timeout=1)
            
            # Check for errors
            if error_holder[0]:
                raise error_holder[0]
            
            response = response_holder[0]
            
            if response.status_code == 200:
                result = response.json()
                if enable_ai:
                    console.print("[green][OK] AI analysis completed successfully[/green]")
                else:
                    console.print("[green][OK] Analysis completed[/green]")
                console.print()  # Blank line after completion
                return result
            else:
                console.print("[yellow][!] Analysis completed with warnings[/yellow]")
                console.print()  # Blank line after completion
                return data
        except Exception as e:
            console.print(f"[yellow]Note: Intelligence analysis failed - {e}[/yellow]")
            console.print()  # Blank line after error
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
                    console.print("=" * 41, style="green")
                    console.print("[AI]  AI-ENHANCED ANALYSIS ENABLED", style="green bold")
                    console.print("=" * 41, style="green")
                    console.print(f"[green]Provider: Self-hosted ({model})[/green]")
                    console.print("[green]Cost: No additional costs (local inference)[/green]")
                    console.print()
                else:
                    cost_per_1k = info.get("cost_per_1k_tokens", 0)
                    typical_cost = info.get("typical_run_cost", "$0.01-$0.10")
                    
                    console.print()
                    console.print("=" * 41, style="yellow")
                    console.print("[!]  AI-ENHANCED ANALYSIS ENABLED", style="yellow bold")
                    console.print("=" * 41, style="yellow")
                    console.print(f"[yellow]Provider: {provider.title()} ({model})[/yellow]")
                    console.print(f"[yellow]Cost: ~${cost_per_1k} per 1000 tokens[/yellow]")
                    console.print(f"[yellow]Typical analysis: {typical_cost}[/yellow]")
                    console.print()
        except Exception:
            console.print()
            console.print("=" * 41, style="yellow")
            console.print("[!]  AI-ENHANCED ANALYSIS ENABLED", style="yellow bold")
            console.print("=" * 41, style="yellow")
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
        console.print("=" * 41, style="green")
        console.print("           Robot Framework Results", style="green bold")
        console.print("=" * 41, style="green")
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
        
        # Failed keywords - apply clustering for deduplication
        failed_kw = data.get("failed_keywords", [])
        if failed_kw:
            # Import clustering module
            from core.log_analysis.clustering import cluster_failures, get_cluster_summary
            
            # Convert failed keywords to clustering format
            failures_for_clustering = []
            for kw in failed_kw:
                failures_for_clustering.append({
                    "name": kw.get("name", "Unknown"),
                    "keyword_name": kw.get("name"),
                    "error": kw.get("error", ""),
                    "library": kw.get("library", ""),
                })
            
            # Cluster failures
            clusters = cluster_failures(failures_for_clustering, deduplicate=True)
            cluster_summary = get_cluster_summary(clusters)
            
            total_failed = len(failed_kw)
            unique_issues = cluster_summary["unique_issues"]
            dedup_ratio = cluster_summary["deduplication_ratio"]
            
            # Show summary with deduplication stats
            if unique_issues < total_failed:
                console.print(
                    f"[red]Root Cause Analysis: {unique_issues} unique issues "
                    f"(deduplicated from {total_failed} failures)[/red]"
                )
                console.print(f"[dim]Deduplication saved {total_failed - unique_issues} duplicate entries "
                             f"({int((1 - unique_issues/total_failed) * 100)}% reduction)[/dim]")
            else:
                console.print(f"[red]Failed Keywords ({total_failed} unique failures):[/red]")
            
            # Show domain distribution
            domain_stats = cluster_summary.get("by_domain", {})
            if any(domain_stats.values()):
                domain_parts = []
                if domain_stats.get("product", 0) > 0:
                    domain_parts.append(f"[red]{domain_stats['product']} Product[/red]")
                if domain_stats.get("infrastructure", 0) > 0:
                    domain_parts.append(f"[magenta]{domain_stats['infrastructure']} Infra[/magenta]")
                if domain_stats.get("environment", 0) > 0:
                    domain_parts.append(f"[cyan]{domain_stats['environment']} Env[/cyan]")
                if domain_stats.get("test_automation", 0) > 0:
                    domain_parts.append(f"[blue]{domain_stats['test_automation']} Test[/blue]")
                if domain_stats.get("unknown", 0) > 0:
                    domain_parts.append(f"[dim]{domain_stats['unknown']} Unknown[/dim]")
                
                if domain_parts:
                    console.print(f"[dim]Domain breakdown: {', '.join(domain_parts)}[/dim]")
            
            # Display systemic patterns if detected
            systemic_patterns = cluster_summary.get("systemic_patterns", [])
            if systemic_patterns:
                console.print()
                console.print("[yellow bold]⚠️  Systemic Patterns Detected:[/yellow bold]")
                for pattern in systemic_patterns:
                    console.print(f"   {pattern}")
            
            console.print()
            
            # Display clustered failures by severity
            severity_display = {
                "critical": ("red bold", "🔴 CRITICAL"),
                "high": ("red", "⚠️  HIGH"),
                "medium": ("yellow", "⚡ MEDIUM"),
                "low": ("dim yellow", "ℹ️  LOW")
            }
            
            # Domain display mapping for failure classification
            domain_display = {
                "infrastructure": ("magenta", "🔧 INFRA"),
                "environment": ("cyan", "⚙️  ENV"),
                "test_automation": ("blue", "🤖 TEST"),
                "product": ("red", "🐛 PROD"),
                "unknown": ("dim white", "❓ UNK")
            }
            
            # Create table for clustered failures
            table = Table(
                show_header=True, 
                header_style="bold cyan", 
                box=box.ROUNDED,
                padding=(0, 1),
                show_lines=False
            )
            table.add_column("Severity", style="white", width=14, no_wrap=True)
            table.add_column("Domain", style="white", width=10, no_wrap=True)
            table.add_column("Root Cause", style="white", no_wrap=False, max_width=60)
            table.add_column("Count", style="cyan bold", justify="right", width=7)
            table.add_column("Affected Tests/Keywords", style="dim white", no_wrap=False, max_width=35)
            
            rows_added = 0
            max_rows = 10
            
            # Sort clusters by severity and count
            sorted_clusters = sorted(
                clusters.values(),
                key=lambda c: (
                    {"critical": 0, "high": 1, "medium": 2, "low": 3}[c.severity.value],
                    -c.failure_count
                )
            )
            
            for cluster in sorted_clusters[:max_rows]:
                severity_style, severity_label = severity_display.get(
                    cluster.severity.value,
                    ("red", "⚠️  HIGH")
                )
                
                domain_style, domain_label = domain_display.get(
                    cluster.domain.value,
                    ("dim white", "❓ UNK")
                )
                
                # Truncate root cause if too long (adjusted for domain column)
                root_cause = cluster.root_cause
                if len(root_cause) > 60:
                    root_cause = root_cause[:57] + "..."
                
                # Show affected tests/keywords (more descriptive)
                affected_items = list(cluster.keywords) if cluster.keywords else list(cluster.tests)
                if len(affected_items) > 3:
                    # Show first item and count
                    affected = f"{affected_items[0]}, +{len(affected_items)-1} more"
                elif len(affected_items) > 1:
                    # Show first 2 items
                    affected = f"{affected_items[0]}, {affected_items[1]}"
                    if len(affected_items) > 2:
                        affected += f", +{len(affected_items)-2} more"
                elif affected_items:
                    affected = affected_items[0]
                else:
                    affected = "Multiple tests"
                
                # Don't truncate affected column - let it wrap naturally
                
                table.add_row(
                    f"[{severity_style}]{severity_label}[/{severity_style}]",
                    f"[{domain_style}]{domain_label}[/{domain_style}]",
                    root_cause,
                    str(cluster.failure_count),
                    affected
                )
                rows_added += 1
            
            console.print(table)
            
            # Show detailed breakdown of top clusters
            console.print()
            console.print("[cyan bold]━━━ Detailed Failure Analysis ━━━[/cyan bold]")
            console.print()
            
            for idx, cluster in enumerate(sorted_clusters[:3], 1):  # Show top 3 in detail
                severity_style, severity_label = severity_display.get(
                    cluster.severity.value,
                    ("red", "⚠️  HIGH")
                )
                
                console.print(f"[{severity_style} bold]{idx}. {severity_label}[/] - {cluster.root_cause}")
                console.print(f"   [dim]Occurrences:[/dim] {cluster.failure_count}")
                
                # Show all affected tests/keywords
                if cluster.keywords:
                    console.print(f"   [dim]Affected Keywords:[/dim]")
                    for kw in sorted(cluster.keywords)[:10]:  # Limit to 10
                        console.print(f"      • {kw}")
                    if len(cluster.keywords) > 10:
                        console.print(f"      [dim]... and {len(cluster.keywords) - 10} more[/dim]")
                
                if cluster.tests:
                    console.print(f"   [dim]Affected Tests:[/dim]")
                    for test in sorted(cluster.tests)[:10]:  # Limit to 10
                        console.print(f"      • {test}")
                    if len(cluster.tests) > 10:
                        console.print(f"      [dim]... and {len(cluster.tests) - 10} more[/dim]")
                
                # Show error patterns
                if cluster.error_patterns:
                    console.print(f"   [dim]Patterns:[/dim] {', '.join(cluster.error_patterns)}")
                
                # Show fix suggestion
                if cluster.suggested_fix:
                    console.print(f"   [cyan]💡 Suggested Fix:[/cyan]")
                    console.print(f"      [dim]{cluster.suggested_fix}[/dim]")
                
                console.print()  # Blank line between clusters
            
            # Show summary for remaining clusters if any
            if len(sorted_clusters) > 3:
                console.print(f"[dim]... and {len(sorted_clusters) - 3} additional unique issues[/dim]")
                console.print()
        
        # Slowest tests
        slowest_tests = data.get("slowest_tests", [])
        if slowest_tests:
            display_count = min(len(slowest_tests), 5)
            console.print(f"[yellow]⏱️  Slowest Tests (Top {display_count}):[/yellow]")
            
            # Create table for slowest tests
            table = Table(
                show_header=True, 
                header_style="bold yellow", 
                box=box.ROUNDED, 
                padding=(0, 1),
                show_lines=False
            )
            table.add_column("Test Case", style="white", no_wrap=False, max_width=80)
            table.add_column("Duration", style="yellow bold", justify="right", width=12)
            
            for test in slowest_tests[:5]:
                test_name = test.get("name", "Unknown")
                elapsed = test.get("elapsed_ms", 0)
                test_duration = self.format_duration(elapsed // 1000)
                
                table.add_row(test_name, test_duration)
            
            console.print(table)
            console.print()
    
    def _display_cypress_results(self, data: dict):
        """Display Cypress results."""
        console.print("=" * 41, style="green")
        console.print("           Cypress Test Results", style="green bold")
        console.print("=" * 41, style="green")
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
                console.print(f"  [X] {title}: {error}")
            console.print()
    
    def _display_playwright_results(self, data: dict):
        """Display Playwright results."""
        console.print("=" * 41, style="green")
        console.print("          Playwright Trace Analysis", style="green bold")
        console.print("=" * 41, style="green")
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
                console.print(f"  - {action_type}: {selector}")
            console.print()
    
    def _display_behave_results(self, data: dict):
        """Display Behave BDD results."""
        console.print("=" * 41, style="green")
        console.print("            Behave BDD Results", style="green bold")
        console.print("=" * 41, style="green")
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
        console.print("=" * 41, style="green")
        console.print("       Java Cucumber Step Definitions", style="green bold")
        console.print("=" * 41, style="green")
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
        console.print("=" * 41, style="blue")
        console.print("  Intelligence Analysis Summary", style="blue bold")
        console.print("=" * 41, style="blue")
        console.print()
        
        # Classifications
        classifications = summary.get("classifications", {})
        if classifications:
            console.print("[yellow]Failure Classifications:[/yellow]")
            for key, value in classifications.items():
                console.print(f"  - {key}: {value}")
            console.print()
        
        # Signals
        signals = summary.get("signals", {})
        if signals:
            console.print("[yellow]Detected Signals:[/yellow]")
            for key, value in signals.items():
                console.print(f"  - {key}: {value}")
            console.print()
    
    def _display_ai_failure_analysis(self, data: dict):
        """Display detailed AI failure analysis."""
        ai_analysis = data.get("ai_analysis", {})
        
        if not ai_analysis:
            return
        
        console.print()
        console.print("=" * 41, style="cyan")
        console.print("  [AI] AI Failure Analysis", style="cyan bold")
        console.print("=" * 41, style="cyan")
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
                        console.print(f"    [>] {file_path}:{line_num}")
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
                        matched = "[OK]" if rule.get("matched", False) else "[ ]" 
                        console.print(f"    {matched} {rule_name}: {rule_explanation}")
                    console.print()
            
            # Separator between failures
            if idx < len(failure_analyses):
                console.print("[dim]" + "-" * 41 + "[/dim]")
                console.print()
    
    def _display_ai_usage(self, data: dict):
        """Display AI usage summary."""
        ai_usage = data.get("ai_usage", {})
        
        console.print()
        console.print("=" * 41, style="blue")
        console.print("      AI Log Analysis Summary", style="blue bold")
        console.print("=" * 41, style="blue")
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
        
        console.print()


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
    compare_with: Optional[Path] = None,
    triage: bool = False,
    max_ai_clusters: int = 5,
    ai_summary_only: bool = False,
):
    """Core log parsing logic."""
    # Configure CrossBridge loggers to use propagation only (no custom handlers)
    # This ensures all logs go to the root logger's handlers (file + console)
    configure_logging(
        enable_console=False,  # Disable custom console handlers (use root logger's)
        enable_file=False      # Disable file handlers (use root logger's)
    )
    
    # Initialize root logger with timestamped file
    setup_logging()
    
    parser = LogParser()
    
    # Check sidecar
    if not parser.check_sidecar():
        raise typer.Exit(1)
    
    # Detect framework
    framework = parser.detect_framework(log_file)
    
    if framework == "robot-html-unsupported":
        console.print(f"[red]Error: Robot Framework HTML files cannot be parsed[/red]")
        console.print("")
        console.print(f"[yellow]You provided:[/yellow] {log_file.name}")
        console.print("")
        console.print("[yellow]HTML files (log.html, report.html) are for viewing results in a browser.[/yellow]")
        console.print("[yellow]To parse and analyze test results, please use the XML output file instead:[/yellow]")
        console.print("")
        console.print("  [green]✓[/green] Use: [cyan]output.xml[/cyan] (typically in the same directory)")
        console.print("")
        console.print("Example:")
        if log_file.parent:
            output_xml_path = log_file.parent / "output.xml"
            console.print(f"  $ crossbridge log [cyan]{output_xml_path}[/cyan] --enable-ai")
        else:
            console.print("  $ crossbridge log [cyan]output.xml[/cyan] --enable-ai")
        raise typer.Exit(1)
    
    if framework == "unknown":
        console.print(f"[red]Error: Could not detect log format for {log_file}[/red]")
        console.print("")
        console.print("Supported formats:")
        console.print("  - Robot Framework (output.xml)")
        console.print("  - TestNG (testng-results.xml)")
        console.print("  - Cypress (cypress-results.json)")
        console.print("  - Playwright (playwright-trace.json)")
        console.print("  - Behave (behave-results.json)")
        console.print("  - Java Cucumber (*Steps.java)")
        raise typer.Exit(1)
    
    console.print(f"[green][OK][/green] Detected framework: [blue]{framework}[/blue]")
    logger.info(f"Starting log parsing for: {log_file} (framework: {framework})")
    
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
    
    # Perform regression analysis if requested
    regression_analysis = None
    if compare_with and not no_analyze:
        console.print("[blue]🔄 Performing regression analysis...[/blue]")
        logger.info(f"Comparing with previous run: {compare_with}")
        try:
            regression_analysis = compare_with_previous(
                enriched_data,
                compare_with,
                similarity_threshold=0.85
            )
            if regression_analysis:
                console.print(f"[green]✅ Regression analysis complete:[/green]")
                console.print(f"   New failures: [red]{len(regression_analysis.new_failures)}[/red]")
                console.print(f"   Recurring: [yellow]{len(regression_analysis.recurring_failures)}[/yellow]")
                console.print(f"   Resolved: [green]{len(regression_analysis.resolved_failures)}[/green]")
                logger.info(f"Regression analysis: {len(regression_analysis.new_failures)} new, "
                          f"{len(regression_analysis.recurring_failures)} recurring, "
                          f"{len(regression_analysis.resolved_failures)} resolved")
        except Exception as e:
            console.print(f"[yellow]⚠️  Regression analysis failed: {e}[/yellow]")
            logger.warning(f"Regression analysis failed: {e}")
    
    # Compute confidence scores for clusters if analysis was performed
    if not no_analyze and "failure_clusters" in enriched_data:
        console.print("[blue]📊 Computing confidence scores...[/blue]")
        clusters = enriched_data.get("failure_clusters", [])
        for cluster in clusters:
            try:
                confidence = compute_confidence_score(cluster, enriched_data)
                cluster["confidence_score"] = {
                    "overall": confidence.overall_score,
                    "cluster_signal": confidence.cluster_signal,
                    "domain_signal": confidence.domain_signal,
                    "pattern_signal": confidence.pattern_signal,
                    "ai_signal": confidence.ai_signal,
                    "components": confidence.components
                }
                logger.debug(f"Confidence score for {cluster.get('root_cause', 'unknown')}: {confidence.overall_score:.2f}")
            except Exception as e:
                logger.warning(f"Failed to compute confidence for cluster: {e}")
                cluster["confidence_score"] = None
    
    # Apply AI sanitization if AI was enabled
    if enable_ai and not no_analyze:
        console.print("[blue]🧹 Sanitizing AI output...[/blue]")
        clusters = enriched_data.get("failure_clusters", [])
        for cluster in clusters:
            if "ai_analysis" in cluster and cluster.get("ai_analysis"):
                try:
                    sanitized = sanitize_ai_output(cluster["ai_analysis"])
                    cluster["ai_analysis"] = sanitized
                    logger.debug(f"Sanitized AI output for cluster: {cluster.get('root_cause', 'unknown')}")
                except Exception as e:
                    logger.warning(f"Failed to sanitize AI output: {e}")
    
    # Generate structured output if triage mode is enabled
    output_data = filtered_data
    if triage and not no_analyze:
        console.print(f"[blue]📋 Generating triage output (top {max_ai_clusters} critical issues)...[/blue]")
        try:
            output_data = create_triage_output(
                enriched_data,
                max_clusters=max_ai_clusters,
                regression_analysis=regression_analysis
            )
            logger.info(f"Generated triage output with {len(output_data.get('critical_issues', []))} issues")
        except Exception as e:
            console.print(f"[yellow]⚠️  Triage output generation failed: {e}[/yellow]")
            logger.warning(f"Triage output failed: {e}")
            output_data = filtered_data
    elif output and not no_analyze:
        # Generate full structured output if saving to file (not in triage mode)
        console.print("[blue]📦 Generating structured output...[/blue]")
        try:
            output_data = create_structured_output(
                enriched_data,
                regression_analysis=regression_analysis
            )
            logger.info("Generated structured output")
        except Exception as e:
            console.print(f"[yellow]⚠️  Structured output generation failed: {e}[/yellow]")
            logger.warning(f"Structured output failed: {e}")
            output_data = filtered_data
    
    # Display results (use filtered_data for console display, not structured output)
    parser.display_results(filtered_data, framework)
    
    # Save to file (use structured output if generated)
    if output:
        output.write_text(json.dumps(output_data, indent=2, default=str))
        console.print(f"\n[blue]Results saved to: {output}[/blue]")
        logger.info(f"Results saved to: {output}")
    else:
        # Save to default file
        default_output = log_file.with_suffix(f".parsed.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        default_output.write_text(json.dumps(output_data, indent=2, default=str))
        console.print(f"\n[blue]Full results saved to: {default_output}[/blue]")
        logger.info(f"Results saved to: {default_output}")
    
    console.print()
    console.print("=" * 41, style="green")
    console.print("[green][OK] Parsing complete![/green]")
    logger.info("Log parsing completed successfully")


if __name__ == "__main__":
    typer.run(log_command)
