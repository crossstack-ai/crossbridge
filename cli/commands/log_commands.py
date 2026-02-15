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
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from core.logging import get_logger, configure_logging, LogCategory
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
logger = get_logger(__name__, category=LogCategory.TESTING)


def log_command(
    log_files: List[Path] = typer.Argument(..., help="Path(s) to log file(s) to parse (supports multiple files)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save merged results to file (JSON format). Per-file results are always saved."),
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
    
    Multi-File Analysis:
    - Analyze multiple log files in one command
    - Per-file console output with clear file headers
    - Per-file JSON output (auto-named with source file)
    - Merged JSON combining all results
    - Unified clustering across all files
    
    Examples:
        # Single file analysis
        crossbridge log output.xml
        
        # Multi-file analysis
        crossbridge log testng-vm1.xml testng-vm2.xml testng-vm3.xml --enable-ai
        
        # Multi-file with custom merged output
        crossbridge log output1.xml output2.xml --output merged-results.json
        
        # Compare with previous run
        crossbridge log output.xml --compare-with previous.json
        
        # Triage mode for CI/CD dashboards
        crossbridge log output.xml --triage
        
        # AI-enhanced analysis
        crossbridge log output.xml --enable-ai --max-ai-clusters 3
        
        # Filter failed tests only
        crossbridge log output.xml --status FAIL
    """
    try:
        # Handle single file (backward compatibility) or multiple files
        if len(log_files) == 1:
            # Single file - use existing logic
            parse_log_file(
                log_file=log_files[0],
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
        else:
            # Multiple files - use new multi-file logic
            parse_multiple_log_files(
                log_files=log_files,
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
    
    def validate_log_file(self, log_file: Path, framework: str = None) -> Tuple[bool, str]:
        """
        Validate log file for format, schema correctness and other checks.
        
        Args:
            log_file: Path to the log file
            framework: Expected framework (if known), None for auto-detect
            
        Returns:
            Tuple of (is_valid, error_message)
            If valid: (True, "")
            If invalid: (False, "error description")
        """
        logger.info(f"Starting validation for file: {log_file.name}")
        
        # Check 1: File exists
        if not log_file.exists():
            logger.error(f"Validation failed - file does not exist: {log_file}")
            return False, f"File does not exist: {log_file}"
        logger.debug(f"✓ File exists: {log_file}")
        
        # Check 2: Is a file (not directory)
        if not log_file.is_file():
            logger.error(f"Validation failed - path is not a file: {log_file}")
            return False, f"Path is not a file: {log_file}"
        logger.debug(f"✓ Path is a file (not directory)")
        
        # Check 3: File is readable
        if not os.access(log_file, os.R_OK):
            logger.error(f"Validation failed - file not readable: {log_file}")
            return False, f"File is not readable (permission denied): {log_file}"
        logger.debug(f"✓ File is readable (permissions OK)")
        
        # Check 4: File size (not empty, not too large)
        file_size = log_file.stat().st_size
        if file_size == 0:
            logger.error(f"Validation failed - file is empty: {log_file}")
            return False, f"File is empty (0 bytes): {log_file}"
        
        file_size_mb = file_size / (1024 * 1024)
        logger.info(f"File size: {file_size_mb:.2f} MB ({file_size:,} bytes)")
        
        # Warn if file is very large (>100MB) but don't fail
        if file_size > 100 * 1024 * 1024:
            logger.warning(f"Large file detected ({file_size_mb:.1f} MB): {log_file}")
            console.print(f"[yellow]⚠️  Large file detected ({file_size_mb:.1f} MB), parsing may be slow[/yellow]")
        
        # Detect framework if not provided
        if framework is None:
            logger.debug(f"Framework not specified, running auto-detection")
            framework = self.detect_framework(log_file)
            if framework == "unknown":
                logger.error(f"Framework detection failed for: {log_file}")
                return False, f"Could not detect framework from filename or content: {log_file}"
            logger.info(f"Auto-detected framework: {framework}")
        else:
            logger.info(f"Using specified framework: {framework}")
        
        # Framework-specific validation
        try:
            if framework in ["robot", "testng"]:
                # XML file validation
                logger.debug(f"Running XML validation for {framework}")
                is_valid, error = self._validate_xml_file(log_file, framework)
                if not is_valid:
                    logger.error(f"XML validation failed for {log_file.name}: {error}")
                    return False, error
                logger.info(f"✓ XML structure validation passed for {framework}")
                    
            elif framework in ["cypress", "playwright", "behave"]:
                # JSON file validation
                logger.debug(f"Running JSON validation for {framework}")
                is_valid, error = self._validate_json_file(log_file, framework)
                if not is_valid:
                    logger.error(f"JSON validation failed for {log_file.name}: {error}")
                    return False, error
                logger.info(f"✓ JSON structure validation passed for {framework}")
                    
            elif framework == "java":
                # Java file validation
                logger.debug(f"Running Java source file validation")
                is_valid, error = self._validate_java_file(log_file)
                if not is_valid:
                    logger.error(f"Java validation failed for {log_file.name}: {error}")
                    return False, error
                logger.info(f"✓ Java source file validation passed")
                    
            else:
                # Unknown framework - basic check passed
                logger.warning(f"No specific validation for framework: {framework}")
                
        except Exception as e:
            logger.error(f"Validation exception for {log_file.name}: {str(e)}", exc_info=True)
            return False, f"Validation error: {str(e)}"
        
        logger.info(f"✓ All validation checks passed for {log_file.name} (framework: {framework}, size: {file_size_mb:.2f} MB)")
        return True, ""
    
    def _validate_xml_file(self, log_file: Path, framework: str) -> Tuple[bool, str]:
        """Validate XML file structure and framework-specific schema."""
        try:
            # Parse XML
            logger.debug(f"Parsing XML file: {log_file.name}")
            tree = ET.parse(log_file)
            root = tree.getroot()
            logger.debug(f"XML parsed successfully, root element: <{root.tag}>")
            
            # Framework-specific validation
            if framework == "robot":
                # Robot Framework: must have <robot> root element
                if root.tag != "robot":
                    logger.error(f"Invalid Robot XML root: expected <robot>, found <{root.tag}>")
                    return False, f"Invalid Robot Framework XML: expected <robot> root, found <{root.tag}>"
                
                # Check for required child elements
                suites = root.findall(".//suite")
                if not suites:
                    logger.error(f"No <suite> elements found in Robot XML")
                    return False, "Invalid Robot Framework XML: no <suite> elements found"
                logger.debug(f"Found {len(suites)} suite(s) in Robot XML")
                
            elif framework == "testng":
                # TestNG: must have <testng-results> root element
                if root.tag != "testng-results":
                    logger.error(f"Invalid TestNG XML root: expected <testng-results>, found <{root.tag}>")
                    return False, f"Invalid TestNG XML: expected <testng-results> root, found <{root.tag}>"
                
                # Check for required child elements
                suites = root.findall(".//suite")
                if not suites:
                    logger.error(f"No <suite> elements found in TestNG XML")
                    return False, "Invalid TestNG XML: no <suite> elements found"
                logger.debug(f"Found {len(suites)} suite(s) in TestNG XML")
            
            return True, ""
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error in {log_file.name}: {str(e)}")
            return False, f"XML parsing error: {str(e)}"
        except Exception as e:
            logger.error(f"XML validation error in {log_file.name}: {str(e)}")
            return False, f"XML validation error: {str(e)}"
    
    def _validate_json_file(self, log_file: Path, framework: str) -> Tuple[bool, str]:
        """Validate JSON file structure and framework-specific schema."""
        try:
            # Parse JSON
            logger.debug(f"Parsing JSON file: {log_file.name}")
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data_type = "object" if isinstance(data, dict) else "array" if isinstance(data, list) else type(data).__name__
            logger.debug(f"JSON parsed successfully, root type: {data_type}")
            
            # Must be dict or list
            if not isinstance(data, (dict, list)):
                logger.error(f"Invalid JSON type: expected object or array, got {type(data).__name__}")
                return False, f"Invalid JSON: expected object or array, got {type(data).__name__}"
            
            # Framework-specific validation
            if framework == "cypress":
                # Cypress: must have stats or results
                if isinstance(data, dict):
                    keys = list(data.keys())
                    logger.debug(f"Cypress JSON keys: {keys[:10]}...")  # Log first 10 keys
                    if "stats" not in data and "results" not in data and "runs" not in data:
                        logger.error(f"Invalid Cypress JSON: missing required fields (has: {keys[:5]})")
                        return False, "Invalid Cypress JSON: missing 'stats', 'results', or 'runs' fields"
                    logger.debug(f"✓ Cypress JSON has required fields")
                        
            elif framework == "playwright":
                # Playwright: must have entries or suites
                if isinstance(data, dict):
                    keys = list(data.keys())
                    logger.debug(f"Playwright JSON keys: {keys[:10]}...")  # Log first 10 keys
                    if "entries" not in data and "suites" not in data:
                        logger.error(f"Invalid Playwright JSON: missing required fields (has: {keys[:5]})")
                        return False, "Invalid Playwright JSON: missing 'entries' or 'suites' fields"
                    logger.debug(f"✓ Playwright JSON has required fields")
                        
            elif framework == "behave":
                # Behave: must be list of features or dict with features
                if isinstance(data, list):
                    # List of features
                    logger.debug(f"Behave JSON is array with {len(data)} items")
                    if data and not all(isinstance(item, dict) and "name" in item for item in data[:3]):
                        logger.error(f"Invalid Behave JSON: list items not feature objects")
                        return False, "Invalid Behave JSON: list items must be feature objects with 'name' field"
                    logger.debug(f"✓ Behave JSON array items have required structure")
                elif isinstance(data, dict):
                    # Dict with features key
                    keys = list(data.keys())
                    logger.debug(f"Behave JSON keys: {keys}")
                    if "features" not in data and "elements" not in data:
                        logger.error(f"Invalid Behave JSON: missing required fields (has: {keys})")
                        return False, "Invalid Behave JSON: missing 'features' or 'elements' fields"
                    logger.debug(f"✓ Behave JSON has required fields")
            
            return True, ""
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in {log_file.name}: line {e.lineno}, col {e.colno} - {e.msg}")
            return False, f"JSON parsing error at line {e.lineno}, column {e.colno}: {e.msg}"
        except UnicodeDecodeError as e:
            logger.error(f"File encoding error in {log_file.name}: {str(e)}")
            return False, f"File encoding error: {str(e)}"
        except Exception as e:
            logger.error(f"JSON validation error in {log_file.name}: {str(e)}")
            return False, f"JSON validation error: {str(e)}"
    
    def _validate_java_file(self, log_file: Path) -> Tuple[bool, str]:
        """Validate Java source file."""
        try:
            # Read file and check for Java syntax
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic Java file checks
            if not content.strip():
                return False, "Java file is empty"
            
            # Check for typical Java keywords
            if "class " not in content and "interface " not in content:
                return False, "Java file does not contain class or interface definition"
            
            # Check for BDD annotations
            has_annotations = any(ann in content for ann in ["@Given", "@When", "@Then", "@And", "@But"])
            if not has_annotations:
                return False, "Java file does not contain BDD step annotations (@Given, @When, @Then)"
            
            return True, ""
            
        except UnicodeDecodeError as e:
            return False, f"File encoding error: {str(e)}"
        except Exception as e:
            return False, f"Java file validation error: {str(e)}"
        
        return False
    
    def detect_framework(self, log_file: Path) -> str:
        """Auto-detect framework based on filename and content."""
        logger.debug(f"Starting framework detection for: {log_file.name}")
        filename = log_file.name.lower()
        
        # Check for Robot Framework HTML files (not parseable)
        if filename in ("log.html", "report.html") or (filename.endswith(".html") and "robot" in filename):
            logger.info(f"Detected unsupported Robot HTML file: {filename}")
            return "robot-html-unsupported"
        
        # Check by filename patterns
        if "output.xml" in filename or filename.startswith("robot"):
            logger.info(f"Framework detected by filename pattern: robot (filename: {filename})")
            return "robot"
        elif "testng" in filename:
            # TestNG files: must be XML, not HTML
            if filename.endswith(".html") or filename.endswith(".htm"):
                logger.info(f"Detected unsupported TestNG HTML file: {filename}")
                return "testng-html-unsupported"
            # TestNG XML files: testng-results.xml, TestNG-Report.xml, etc.
            logger.info(f"Framework detected by filename pattern: testng (filename: {filename})")
            return "testng"
        elif "cypress" in filename:
            logger.info(f"Framework detected by filename pattern: cypress (filename: {filename})")
            return "cypress"
        elif "playwright" in filename or "trace" in filename:
            logger.info(f"Framework detected by filename pattern: playwright (filename: {filename})")
            return "playwright"
        elif "behave" in filename or "cucumber" in filename:
            # Read content to distinguish
            logger.debug(f"Filename contains 'behave' or 'cucumber', checking content to confirm")
            try:
                with open(log_file) as f:
                    content = f.read(1000)
                    if '"feature"' in content:
                        logger.info(f"Framework detected by content inspection: behave (has 'feature' field)")
                        return "behave"
            except Exception as e:
                logger.debug(f"Content inspection failed: {e}")
                pass
            logger.info(f"Defaulting to cypress for behave/cucumber filename pattern")
            return "cypress"
        elif filename.endswith("steps.java") or "stepdefinitions" in filename:
            logger.info(f"Framework detected by filename pattern: java (filename: {filename})")
            return "java"
        
        # Check by content
        logger.debug(f"Filename pattern didn't match, inspecting file content")
        try:
            with open(log_file) as f:
                lines = [f.readline() for _ in range(5)]
                content = "".join(lines)
                
                if "<robot" in content:
                    logger.info(f"Framework detected by content inspection: robot (found '<robot' tag)")
                    return "robot"
                elif "<testng-results" in content:
                    logger.info(f"Framework detected by content inspection: testng (found '<testng-results' tag)")
                    return "testng"
                elif '"suites"' in content:
                    logger.info(f"Framework detected by content inspection: cypress (found 'suites' field)")
                    return "cypress"
                elif '"entries"' in content:
                    logger.info(f"Framework detected by content inspection: playwright (found 'entries' field)")
                    return "playwright"
                elif '"feature"' in content:
                    logger.info(f"Framework detected by content inspection: behave (found 'feature' field)")
                    return "behave"
            
            # Check for Java annotations
            logger.debug(f"Checking for Java BDD annotations in full file content")
            with open(log_file) as f:
                full_content = f.read()
                if "@Given" in full_content or "@When" in full_content or "@Then" in full_content:
                    logger.info(f"Framework detected by content inspection: java (found BDD annotations)")
                    return "java"
        except Exception as e:
            logger.warning(f"Content inspection failed for {log_file.name}: {e}")
            pass
        
        logger.warning(f"Framework detection failed for {log_file.name} - no matching patterns found")
        return "unknown"
    
    def parse_log(self, log_file: Path, framework: str) -> dict:
        """Parse log file via sidecar API."""
        console.print(f"[blue]Parsing log file: {log_file}[/blue]")
        
        file_size = log_file.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        endpoint = f"{self.sidecar_url}/parse/{framework}"
        
        logger.info(f"Sending parse request to sidecar: {endpoint}")
        logger.info(f"File: {log_file.name}, Size: {file_size_mb:.2f} MB, Framework: {framework}")
        
        try:
            parse_start = time.time()
            with open(log_file, "rb") as f:
                logger.debug(f"Uploading file to sidecar endpoint...")
                response = requests.post(
                    endpoint,
                    data=f,
                    headers={"Content-Type": "application/octet-stream"},
                    timeout=60
                )
            
            parse_duration = int(time.time() - parse_start)
            logger.info(f"Sidecar response received: HTTP {response.status_code} (took {parse_duration}s)")
            
            if response.status_code == 200:
                result = response.json()
                total_tests = result.get('total_tests', 0)
                passed_tests = result.get('passed_tests', 0)
                failed_tests = result.get('failed_tests', 0)
                logger.info(f"Parsing successful - Total: {total_tests}, Passed: {passed_tests}, Failed: {failed_tests}")
                return result
            else:
                error_detail = response.json().get("detail", "Unknown error")
                logger.error(f"Sidecar parsing failed: HTTP {response.status_code} - {error_detail}")
                console.print(f"[red]Error: {error_detail}[/red]")
                return {}
        except requests.exceptions.Timeout as e:
            logger.error(f"Sidecar request timeout after 60s for {log_file.name}: {e}")
            console.print(f"[red]Error parsing log: Request timeout (file too large or sidecar not responding)[/red]")
            return {}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Sidecar connection error for {log_file.name}: {e}")
            console.print(f"[red]Error parsing log: Cannot connect to sidecar service[/red]")
            return {}
        except Exception as e:
            logger.error(f"Parsing exception for {log_file.name}: {e}", exc_info=True)
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
            
            analysis_duration = int(time.time() - time.time())
            logger.info(f"Intelligence analysis request completed: HTTP {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                # Log analysis results
                if result.get("failure_clusters"):
                    num_clusters = len(result["failure_clusters"])
                    total_failures = result.get("data", {}).get("failed_tests", 0)
                    logger.info(f"Clustering analysis complete: {num_clusters} unique issue(s) identified from {total_failures} failure(s)")
                    
                    # Log cluster details
                    for idx, cluster in enumerate(result["failure_clusters"][:5], 1):  # Log first 5
                        severity = cluster.get("severity", "unknown")
                        domain = cluster.get("domain", "unknown")
                        count = cluster.get("failure_count", 0)
                        root_cause = cluster.get("root_cause", "Unknown")
                        logger.debug(f"  Cluster {idx}: [{severity}/{domain}] {root_cause} (count: {count})")
                
                if result.get("ai_analysis") and enable_ai:
                    ai_insights = len(result["ai_analysis"].get("insights", []))
                    logger.info(f"AI analysis complete: {ai_insights} insights generated")
                    
                if result.get("intelligence_summary"):
                    summary = result["intelligence_summary"]
                    logger.info(f"Intelligence summary: {summary}")
                
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
            logger.debug("No filters specified, returning unfiltered data")
            return data
        
        active_filters = {k: v for k, v in filters.items() if v is not None}
        if active_filters:
            logger.info(f"Applying filters: {list(active_filters.keys())}")
            logger.debug(f"Filter values: {active_filters}")
        
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
        elif framework == "testng":
            self._display_testng_results(display_data)
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
    
    def _display_testng_results(self, data: dict):
        """Display TestNG results with detailed analysis."""
        console.print("=" * 41, style="green")
        console.print("           TestNG Test Results", style="green bold")
        console.print("=" * 41, style="green")
        console.print()
        
        summary = data.get("summary", {})
        total = summary.get("total_tests", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        pass_rate = summary.get("pass_rate", 0.0)
        
        # Overall status
        status = "PASS" if failed == 0 else "FAIL"
        status_style = "green" if status == "PASS" else "red"
        console.print(f"[blue]Status:[/blue] [{status_style}]{status}[/{status_style}]")
        console.print()
        
        # Test Statistics
        console.print("[blue]Test Statistics:[/blue]")
        console.print(f"  Total:    {total}")
        console.print(f"  Passed:   [green]{passed}[/green]")
        console.print(f"  Failed:   [red]{failed}[/red]")
        if skipped > 0:
            console.print(f"  Skipped:  [yellow]{skipped}[/yellow]")
        console.print(f"  Pass Rate: {pass_rate:.1f}%")
        console.print()
        
        # Failed tests - apply clustering for deduplication
        failed_tests = data.get("failed_tests", [])
        if failed_tests:
            # Import clustering module
            from core.log_analysis.clustering import cluster_failures, get_cluster_summary
            
            # Convert failed tests to clustering format
            failures_for_clustering = []
            for test in failed_tests:
                failures_for_clustering.append({
                    "name": test.get("test_name", "Unknown"),
                    "test_name": test.get("test_name"),
                    "class_name": test.get("class_name"),
                    "error": test.get("error_message", ""),
                    "failure_type": test.get("failure_type", ""),
                    "category": test.get("category", "UNKNOWN"),
                })
            
            # Cluster failures
            clusters = cluster_failures(failures_for_clustering, deduplicate=True)
            cluster_summary = get_cluster_summary(clusters)
            
            total_failed = len(failed_tests)
            unique_issues = cluster_summary["unique_issues"]
            
            # Show summary with deduplication stats
            if unique_issues < total_failed:
                console.print(
                    f"[red]Root Cause Analysis: {unique_issues} unique issues "
                    f"(deduplicated from {total_failed} failures)[/red]"
                )
                console.print(f"[dim]Deduplication saved {total_failed - unique_issues} duplicate entries "
                             f"({int((1 - unique_issues/total_failed) * 100)}% reduction)[/dim]")
            else:
                console.print(f"[red]Failed Tests ({total_failed} unique failures):[/red]")
            
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
            
            # Domain display mapping
            domain_display = {
                "infrastructure": ("magenta", "🔧 INFRA"),
                "environment": ("cyan", "⚙️  ENV"),
                "test_automation": ("blue", "🤖 TEST"),
                "product": ("red", "🐛 PROD"),
                "unknown": ("dim", "❓ UNK")
            }
            
            # Severity display
            severity_display = {
                "critical": ("red bold", "🔴 CRITICAL"),
                "high": ("red", "⚠️  HIGH"),
                "medium": ("yellow", "⚡ MEDIUM"),
                "low": ("dim yellow", "ℹ️  LOW")
            }
            
            # Create table for clustered failures
            from rich.table import Table
            from rich import box
            
            table = Table(
                show_header=True,
                header_style="bold cyan",
                box=box.ROUNDED,
                padding=(0, 1),
                show_lines=True
            )
            table.add_column("Severity", style="white", width=14)
            table.add_column("Domain", style="white", width=10)
            table.add_column("Root Cause", style="white", no_wrap=False, max_width=60)
            table.add_column("Count", justify="right", style="cyan bold", width=7)
            table.add_column("Affected Tests", style="dim", no_wrap=False, max_width=35)
            
            # Sort clusters by severity and count
            sorted_clusters = sorted(
                clusters.values(),
                key=lambda c: (
                    {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(c.severity.value, 4),
                    -c.failure_count
                )
            )
            
            # Display top clusters
            for cluster in sorted_clusters[:10]:
                severity = cluster.severity.value
                domain = cluster.domain.value
                root_cause = cluster.root_cause
                count = cluster.failure_count
                
                # Get severity and domain display
                sev_style, sev_label = severity_display.get(severity, ("dim", "❓ UNKNOWN"))
                dom_style, dom_label = domain_display.get(domain, ("dim", "❓ UNK"))
                
                # Truncate root cause if too long
                if len(root_cause) > 60:
                    root_cause = root_cause[:57] + "..."
                
                # Get affected test names
                failures = cluster.failures
                if failures:
                    first_test = failures[0].test_name
                    # Shorten test names
                    if len(first_test) > 30:
                        first_test = first_test[:27] + "..."
                    
                    if len(failures) > 1:
                        affected = f"{first_test}, +{len(failures)-1} more"
                    else:
                        affected = first_test
                else:
                    affected = "Unknown"
                
                table.add_row(
                    f"[{sev_style}]{sev_label}[/{sev_style}]",
                    f"[{dom_style}]{dom_label}[/{dom_style}]",
                    root_cause,
                    str(count),
                    affected
                )
            
            console.print(table)
            console.print()
            
            # Detailed failure analysis for top 3 issues
            console.print("[cyan bold]━━━ Detailed Failure Analysis ━━━[/cyan bold]")
            console.print()
            
            for idx, cluster in enumerate(sorted_clusters[:3], 1):
                severity = cluster.severity.value
                sev_style, sev_label = severity_display.get(severity, ("dim", "❓ UNKNOWN"))
                root_cause = cluster.root_cause
                count = cluster.failure_count
                
                console.print(f"[bold]{idx}. [{sev_style}]{sev_label}[/{sev_style}] - {root_cause}[/bold]")
                console.print(f"   Occurrences: {count}")
                
                # Show affected tests
                failures = cluster.failures
                if failures:
                    console.print(f"   [dim]Affected Tests:[/dim]")
                    for failure in failures[:5]:
                        test_name = failure.test_name
                        console.print(f"      • {test_name}")
                    if len(failures) > 5:
                        console.print(f"      [dim]... and {len(failures)-5} more[/dim]")
                
                # Show patterns if available
                patterns = cluster.error_patterns
                if patterns:
                    console.print(f"   [yellow]Patterns:[/yellow] {', '.join(patterns)}")
                
                # Show suggested fix if available
                if cluster.suggested_fix:
                    console.print(f"   [cyan]💡 Suggested Fix:[/cyan]")
                    console.print(f"      {cluster.suggested_fix}")
                elif "assertion" in root_cause.lower() or "expected" in root_cause.lower():
                    console.print(f"   [cyan]💡 Suggested Fix:[/cyan]")
                    console.print(f"      Review test expectations and actual application behavior")
                
                console.print()
            
            # Show summary for remaining clusters
            if len(sorted_clusters) > 3:
                console.print(f"[dim]... and {len(sorted_clusters) - 3} additional unique issues[/dim]")
                console.print()
        
        # Slowest tests if available
        all_tests = data.get("all_tests", [])
        if all_tests:
            # Sort by duration
            tests_with_duration = [t for t in all_tests if t.get("duration_ms", 0) > 0]
            sorted_tests = sorted(tests_with_duration, key=lambda t: t.get("duration_ms", 0), reverse=True)
            
            if sorted_tests:
                display_count = min(len(sorted_tests), 5)
                console.print(f"[yellow]⏱️  Slowest Tests (Top {display_count}):[/yellow]")
                
                # Create table for slowest tests
                from rich.table import Table
                from rich import box
                
                table = Table(
                    show_header=True,
                    header_style="bold yellow",
                    box=box.ROUNDED,
                    padding=(0, 1),
                    show_lines=False
                )
                table.add_column("Test Case", style="white", no_wrap=False, max_width=80)
                table.add_column("Duration", style="yellow bold", justify="right", width=12)
                
                for test in sorted_tests[:5]:
                    test_name = test.get("test_name", test.get("name", "Unknown"))
                    duration_ms = test.get("duration_ms", 0)
                    test_duration = self.format_duration(duration_ms // 1000)
                    
                    table.add_row(test_name, test_duration)
                
                console.print(table)
                console.print()
    
    def _display_cypress_results(self, data: dict):
        """Display Cypress results with detailed analysis."""
        console.print("=" * 41, style="green")
        console.print("          Cypress Test Results", style="green bold")
        console.print("=" * 41, style="green")
        console.print()
        
        total = data.get("total_tests", 0)
        passed = data.get("passed", 0)
        failed = data.get("failed", 0)
        skipped = data.get("skipped", 0)
        pass_rate = data.get("pass_rate", 0.0)
        
        # Overall status
        status = "PASS" if failed == 0 else "FAIL"
        status_style = "green" if status == "PASS" else "red"
        console.print(f"[blue]Status:[/blue] [{status_style}]{status}[/{status_style}]")
        console.print()
        
        # Test Statistics
        console.print("[blue]Test Statistics:[/blue]")
        console.print(f"  Total:    {total}")
        console.print(f"  Passed:   [green]{passed}[/green]")
        console.print(f"  Failed:   [red]{failed}[/red]")
        if skipped > 0:
            console.print(f"  Skipped:  [yellow]{skipped}[/yellow]")
        console.print(f"  Pass Rate: {pass_rate:.1f}%")
        console.print()
        
        # Failed tests - apply clustering for deduplication
        failed_tests = data.get("failed_tests", [])
        if failed_tests:
            # Import clustering module
            from core.log_analysis.clustering import cluster_failures, get_cluster_summary
            
            # Convert failed tests to clustering format
            failures_for_clustering = []
            for test in failed_tests:
                failures_for_clustering.append({
                    "name": test.get("test_name", "Unknown"),
                    "test_name": test.get("test_name"),
                    "error": test.get("error_message", ""),
                    "stack_trace": test.get("stack_trace"),
                })
            
            # Cluster failures
            clusters = cluster_failures(failures_for_clustering, deduplicate=True)
            cluster_summary = get_cluster_summary(clusters)
            
            total_failed = len(failed_tests)
            unique_issues = cluster_summary["unique_issues"]
            
            # Show summary with deduplication stats
            if unique_issues < total_failed:
                console.print(
                    f"[red]Root Cause Analysis: {unique_issues} unique issues "
                    f"(deduplicated from {total_failed} failures)[/red]"
                )
                console.print(f"[dim]Deduplication saved {total_failed - unique_issues} duplicate entries "
                             f"({int((1 - unique_issues/total_failed) * 100)}% reduction)[/dim]")
            else:
                console.print(f"[red]Failed Tests ({total_failed} unique failures):[/red]")
            
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
            
            # Display clustered failures
            self._display_clustered_failures(clusters, "Cypress")
            console.print()
        
        # Slowest tests
        all_tests = data.get("all_tests", [])
        if all_tests:
            tests_with_duration = [t for t in all_tests if t.get("duration_ms", 0) > 0]
            sorted_tests = sorted(tests_with_duration, key=lambda t: t.get("duration_ms", 0), reverse=True)
            
            if sorted_tests:
                display_count = min(len(sorted_tests), 5)
                console.print(f"[yellow]⏱️  Slowest Tests (Top {display_count}):[/yellow]")
                
                from rich.table import Table
                from rich import box
                
                table = Table(
                    show_header=True,
                    header_style="bold yellow",
                    box=box.ROUNDED,
                    padding=(0, 1),
                    show_lines=False
                )
                table.add_column("Test Case", style="white", no_wrap=False, max_width=80)
                table.add_column("Duration", style="yellow bold", justify="right", width=12)
                
                for test in sorted_tests[:5]:
                    test_name = test.get("test_name", test.get("title", "Unknown"))
                    duration_ms = test.get("duration_ms", 0)
                    test_duration = self.format_duration(duration_ms // 1000)
                    
                    table.add_row(test_name, test_duration)
                
                console.print(table)
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
        """Display Behave BDD results with detailed analysis."""
        console.print("=" * 41, style="green")
        console.print("           Behave BDD Results", style="green bold")
        console.print("=" * 41, style="green")
        console.print()
        
        total_scenarios = data.get("total_scenarios", 0)
        passed_scenarios = data.get("passed_scenarios", 0)
        failed_scenarios_count = data.get("failed_scenarios", 0)
        skipped = data.get("skipped_scenarios", 0)
        pass_rate = data.get("pass_rate", 0.0)
        
        # Overall status
        status = "PASS" if failed_scenarios_count == 0 else "FAIL"
        status_style = "green" if status == "PASS" else "red"
        console.print(f"[blue]Status:[/blue] [{status_style}]{status}[/{status_style}]")
        console.print()
        
        # BDD Statistics
        console.print("[blue]BDD Statistics:[/blue]")
        console.print(f"  Features:  {data.get('total_features', 0)}")
        console.print(f"  Scenarios: {total_scenarios}")
        console.print(f"  Passed:    [green]{passed_scenarios}[/green]")
        console.print(f"  Failed:    [red]{failed_scenarios_count}[/red]")
        if skipped > 0:
            console.print(f"  Skipped:   [yellow]{skipped}[/yellow]")
        console.print(f"  Pass Rate: {pass_rate:.1f}%")
        console.print()
        
        # Failed scenarios - apply clustering for deduplication
        failed_scenarios = data.get("failed_scenarios_list", [])
        if failed_scenarios:
            # Import clustering module
            from core.log_analysis.clustering import cluster_failures, get_cluster_summary
            
            # Convert failed scenarios to clustering format
            failures_for_clustering = []
            for scenario in failed_scenarios:
                failures_for_clustering.append({
                    "name": scenario.get("test_name", "Unknown"),
                    "test_name": scenario.get("test_name"),
                    "error": scenario.get("error_message", ""),
                })
            
            # Cluster failures
            clusters = cluster_failures(failures_for_clustering, deduplicate=True)
            cluster_summary = get_cluster_summary(clusters)
            
            total_failed = len(failed_scenarios)
            unique_issues = cluster_summary["unique_issues"]
            
            # Show summary with deduplication stats
            if unique_issues < total_failed:
                console.print(
                    f"[red]Root Cause Analysis: {unique_issues} unique issues "
                    f"(deduplicated from {total_failed} failures)[/red]"
                )
                console.print(f"[dim]Deduplication saved {total_failed - unique_issues} duplicate entries "
                             f"({int((1 - unique_issues/total_failed) * 100)}% reduction)[/dim]")
            else:
                console.print(f"[red]Failed Scenarios ({total_failed} unique failures):[/red]")
            
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
            
            # Display clustered failures
            self._display_clustered_failures(clusters, "Behave")
            console.print()
        
        # Slowest scenarios
        all_scenarios = data.get("all_scenarios", [])
        if all_scenarios:
            scenarios_with_duration = [s for s in all_scenarios if s.get("duration_ms", 0) > 0]
            sorted_scenarios = sorted(scenarios_with_duration, key=lambda s: s.get("duration_ms", 0), reverse=True)
            
            if sorted_scenarios:
                display_count = min(len(sorted_scenarios), 5)
                console.print(f"[yellow]⏱️  Slowest Scenarios (Top {display_count}):[/yellow]")
                
                from rich.table import Table
                from rich import box
                
                table = Table(
                    show_header=True,
                    header_style="bold yellow",
                    box=box.ROUNDED,
                    padding=(0, 1),
                    show_lines=False
                )
                table.add_column("Scenario", style="white", no_wrap=False, max_width=80)
                table.add_column("Duration", style="yellow bold", justify="right", width=12)
                
                for scenario in sorted_scenarios[:5]:
                    scenario_name = scenario.get("test_name", scenario.get("scenario_name", "Unknown"))
                    duration_ms = scenario.get("duration_ms", 0)
                    scenario_duration = self.format_duration(duration_ms // 1000)
                    
                    table.add_row(scenario_name, scenario_duration)
                
                console.print(table)
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
    
    def _display_clustered_failures(self, clusters, framework_name: str = "Test"):
        """
        Display clustered failures in a table format (reusable across frameworks).
        
        Args:
            clusters: Dict of FailureCluster objects from cluster_failures()
            framework_name: Name of the framework for display
        """
        from rich.table import Table
        from rich import box
        
        # Domain display mapping
        domain_display = {
            "infrastructure": ("magenta", "🔧 INFRA"),
            "environment": ("cyan", "⚙️  ENV"),
            "test_automation": ("blue", "🤖 TEST"),
            "product": ("red", "🐛 PROD"),
            "unknown": ("dim", "❓ UNK")
        }
        
        # Severity display
        severity_display = {
            "critical": ("red bold", "🔴 CRITICAL"),
            "high": ("red", "⚠️  HIGH"),
            "medium": ("yellow", "⚡ MEDIUM"),
            "low": ("dim yellow", "ℹ️  LOW")
        }
        
        # Create table for clustered failures
        table = Table(
            show_header=True,
            header_style="bold cyan",
            box=box.ROUNDED,
            padding=(0, 1),
            show_lines=True
        )
        table.add_column("Severity", style="white", width=14)
        table.add_column("Domain", style="white", width=10)
        table.add_column("Root Cause", style="white", no_wrap=False, max_width=60)
        table.add_column("Count", justify="right", style="cyan bold", width=7)
        table.add_column(f"Affected {framework_name}s", style="dim", no_wrap=False, max_width=35)
        
        # Sort clusters by severity and count
        sorted_clusters = sorted(
            clusters.values(),
            key=lambda c: (
                {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(c.severity.value, 4),
                -c.failure_count
            )
        )
        
        # Display top clusters
        for cluster in sorted_clusters[:10]:
            severity = cluster.severity.value
            domain = cluster.domain.value
            root_cause = cluster.root_cause
            count = cluster.failure_count
            
            # Get severity and domain display
            sev_style, sev_label = severity_display.get(severity, ("dim", "❓ UNKNOWN"))
            dom_style, dom_label = domain_display.get(domain, ("dim", "❓ UNK"))
            
            # Truncate root cause if too long
            if len(root_cause) > 60:
                root_cause = root_cause[:57] + "..."
            
            # Get affected test names
            failures = cluster.failures
            if failures:
                first_test = failures[0].test_name
                # Shorten test names
                if len(first_test) > 30:
                    first_test = first_test[:27] + "..."
                
                if len(failures) > 1:
                    affected = f"{first_test}, +{len(failures)-1} more"
                else:
                    affected = first_test
            else:
                affected = "Unknown"
            
            table.add_row(
                f"[{sev_style}]{sev_label}[/{sev_style}]",
                f"[{dom_style}]{dom_label}[/{dom_style}]",
                root_cause,
                str(count),
                affected
            )
        
        console.print(table)
        console.print()
        
        # Detailed failure analysis for top 3 issues
        console.print("[cyan bold]━━━ Detailed Failure Analysis ━━━[/cyan bold]")
        console.print()
        
        for idx, cluster in enumerate(sorted_clusters[:3], 1):
            severity = cluster.severity.value
            sev_style, sev_label = severity_display.get(severity, ("dim", "❓ UNKNOWN"))
            root_cause = cluster.root_cause
            count = cluster.failure_count
            
            console.print(f"[bold]{idx}. [{sev_style}]{sev_label}[/{sev_style}] - {root_cause}[/bold]")
            console.print(f"   Occurrences: {count}")
            
            # Show affected tests
            failures = cluster.failures
            if failures:
                console.print(f"   [dim]Affected {framework_name}s:[/dim]")
                for failure in failures[:5]:
                    test_name = failure.test_name
                    console.print(f"      • {test_name}")
                if len(failures) > 5:
                    console.print(f"      [dim]... and {len(failures)-5} more[/dim]")
            
            # Show patterns if available
            patterns = cluster.error_patterns
            if patterns:
                console.print(f"   [yellow]Patterns:[/yellow] {', '.join(patterns)}")
            
            # Show suggested fix if available
            if cluster.suggested_fix:
                console.print(f"   [cyan]💡 Suggested Fix:[/cyan]")
                console.print(f"      {cluster.suggested_fix}")
            elif "timeout" in root_cause.lower():
                console.print(f"   [cyan]💡 Suggested Fix:[/cyan]")
                console.print(f"      Increase timeout values or investigate slow operations")
            elif "element" in root_cause.lower() or "selector" in root_cause.lower():
                console.print(f"   [cyan]💡 Suggested Fix:[/cyan]")
                console.print(f"      Update selectors or add waits for element visibility")
            elif "assertion" in root_cause.lower() or "expected" in root_cause.lower():
                console.print(f"   [cyan]💡 Suggested Fix:[/cyan]")
                console.print(f"      Review test expectations and actual application behavior")
            
            console.print()
        
        # Show summary for remaining clusters
        if len(sorted_clusters) > 3:
            console.print(f"[dim]... and {len(sorted_clusters) - 3} additional unique issues[/dim]")
    
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


def parse_multiple_log_files(
    log_files: List[Path],
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
    """Core multi-file log parsing logic with unified clustering and analysis."""
    # Configure CrossBridge loggers once
    configure_logging(
        enable_console=False,
        enable_file=False
    )
    
    # Initialize root logger with timestamped file
    setup_logging()
    
    logger.info(f"Starting multi-file log parsing for {len(log_files)} files")
    
    # Initialize parser once
    parser = LogParser()
    
    # Check sidecar once (shared across all files)
    if not parser.check_sidecar():
        raise typer.Exit(1)
    
    # Display multi-file analysis header
    console.print()
    console.print("=" * 60, style="cyan bold")
    console.print(f"  📊 Multi-File Log Analysis ({len(log_files)} files)", style="cyan bold")
    console.print("=" * 60, style="cyan bold")
    console.print()
    
    # Collect results from all files
    all_results = []
    all_file_info = []
    failed_files = []
    
    for idx, log_file in enumerate(log_files, 1):
        console.print()
        console.print("┏" + "━" * 58 + "┓", style="blue")
        console.print(f"┃  File {idx}/{len(log_files)}: {log_file.name:<47}┃", style="blue bold")
        console.print("┗" + "━" * 58 + "┛", style="blue")
        console.print()
        
        try:
            # Step 1: Validate file before processing
            console.print(f"[blue][1/4][/blue] Validating file format and schema...")
            is_valid, validation_error = parser.validate_log_file(log_file)
            
            if not is_valid:
                console.print(f"[red]✗ Validation failed:[/red] {validation_error}")
                console.print(f"[yellow]⚠️  Skipping {log_file.name} due to validation failure[/yellow]")
                logger.warning(f"Validation failed for {log_file.name}: {validation_error}")
                failed_files.append({
                    "file": log_file.name, 
                    "reason": f"Validation failed: {validation_error}",
                    "stage": "validation"
                })
                console.print()
                console.print("[dim]" + "─" * 60 + "[/dim]")
                continue
            
            console.print(f"[green]✓ Validation passed[/green]")
            
            # Step 2: Detect framework for this file
            console.print(f"[blue][2/4][/blue] Detecting test framework...")
            framework = parser.detect_framework(log_file)
            
            # Handle unsupported formats
            if framework in ["robot-html-unsupported", "testng-html-unsupported"]:
                console.print(f"[red]✗ Framework detection failed[/red]")
                console.print(f"[yellow]⚠️  Skipping {log_file.name}: HTML files are not supported[/yellow]")
                console.print(f"[dim]   Please use XML output files instead (output.xml or testng-results.xml)[/dim]")
                logger.warning(f"HTML format not supported for {log_file.name}")
                failed_files.append({
                    "file": log_file.name, 
                    "reason": "HTML format not supported",
                    "stage": "framework_detection"
                })
                console.print()
                console.print("[dim]" + "─" * 60 + "[/dim]")
                continue
            
            if framework == "unknown":
                console.print(f"[red]✗ Framework detection failed[/red]")
                console.print(f"[yellow]⚠️  Skipping {log_file.name}: Unknown log format[/yellow]")
                logger.warning(f"Unknown format for {log_file.name}")
                failed_files.append({
                    "file": log_file.name, 
                    "reason": "Unknown format",
                    "stage": "framework_detection"
                })
                console.print()
                console.print("[dim]" + "─" * 60 + "[/dim]")
                continue
            
            console.print(f"[green]✓ Detected framework:[/green] [blue]{framework}[/blue]")
            logger.info(f"Processing file {idx}/{len(log_files)}: {log_file} (framework: {framework})")
            
            # Step 3: Parse log
            console.print(f"[blue][3/4][/blue] Parsing test results...")
            parsed_data = parser.parse_log(log_file, framework)
            
            if not parsed_data:
                console.print(f"[red]✗ Parsing failed[/red]")
                console.print(f"[yellow]⚠️  Skipping {log_file.name}: Parsing returned empty result[/yellow]")
                logger.error(f"Parsing failed for: {log_file}")
                failed_files.append({
                    "file": log_file.name, 
                    "reason": "Parsing failed - empty result",
                    "stage": "parsing"
                })
                console.print()
                console.print("[dim]" + "─" * 60 + "[/dim]")
                continue
            
            console.print(f"[green]✓ Parsing successful[/green]")
            logger.info(f"Parsing successful for: {log_file}")
            
            # Step 4: Intelligence analysis
            console.print(f"[blue][4/4][/blue] Performing intelligence analysis...")
            
            # Enrich with intelligence if not disabled
            if not no_analyze:
                logger.info(f"Starting intelligence analysis for {log_file.name} (AI: {enable_ai})")
                start_time = time.time()
                enriched_data = parser.enrich_with_intelligence(
                    parsed_data,
                    framework,
                    enable_ai=enable_ai,
                    app_logs=app_logs
                )
                analysis_duration = int(time.time() - start_time)
                console.print(f"[green]✓ Analysis complete[/green]")
            else:
                enriched_data = parsed_data
                analysis_duration = 0
                console.print(f"[dim]Skipped (--no-analyze flag)[/dim]")
            
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
            
            # Compute confidence scores if analysis was performed
            if not no_analyze and "failure_clusters" in enriched_data:
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
                    except Exception as e:
                        logger.warning(f"Failed to compute confidence for cluster in {log_file.name}: {e}")
                        cluster["confidence_score"] = None
            
            # Apply AI sanitization if enabled
            if enable_ai and not no_analyze:
                clusters = enriched_data.get("failure_clusters", [])
                for cluster in clusters:
                    if "ai_analysis" in cluster and cluster.get("ai_analysis"):
                        try:
                            sanitized = sanitize_ai_output(cluster["ai_analysis"])
                            cluster["ai_analysis"] = sanitized
                        except Exception as e:
                            logger.warning(f"Failed to sanitize AI output in {log_file.name}: {e}")
            
            # Generate structured output
            output_data = filtered_data
            if not no_analyze:
                try:
                    output_data = create_structured_output(
                        enriched_data,
                        regression_analysis=None  # Multi-file doesn't support regression yet
                    )
                except Exception as e:
                    logger.warning(f"Structured output generation failed for {log_file.name}: {e}")
                    output_data = filtered_data
            
            # Display results for this file
            console.print(f"\n[bold cyan]{'=' * 80}[/bold cyan]")
            console.print(f"[bold cyan]=== {log_file.name} log analysis ===[/bold cyan]")
            console.print(f"[bold cyan]{'=' * 80}[/bold cyan]\n")
            logger.info(f"Displaying results for {log_file.name}")
            parser.display_results(filtered_data, framework)
            
            # Save per-file JSON with log filename in output name
            per_file_output = _generate_per_file_output_path(log_file)
            logger.debug(f"Writing per-file results to: {per_file_output}")
            json_content = json.dumps(output_data, indent=2, default=str)
            per_file_output.write_text(json_content)
            output_size = len(json_content) / 1024  # KB
            console.print(f"\n[blue]Results saved to: {per_file_output.name}[/blue]")
            logger.info(f"Per-file results saved to: {per_file_output} ({output_size:.1f} KB)")
            
            # Collect for merged output
            all_results.append({
                "source_file": str(log_file),
                "framework": framework,
                "data": output_data,
                "output_file": str(per_file_output)
            })
            
            all_file_info.append({
                "file": log_file.name,
                "framework": framework,
                "status": "success",
                "total_tests": filtered_data.get("total_tests", 0),
                "passed_tests": filtered_data.get("passed_tests", 0),
                "failed_tests": filtered_data.get("failed_tests", 0),
            })
            
            console.print()
            console.print("[dim]" + "─" * 60 + "[/dim]")
            
        except Exception as e:
            console.print(f"\n[red]✗ Unexpected error:[/red] {str(e)}")
            logger.error(f"Error processing {log_file}: {e}", exc_info=True)
            failed_files.append({
                "file": log_file.name, 
                "reason": f"Unexpected error: {str(e)}",
                "stage": "processing"
            })
            console.print()
            console.print("[dim]" + "─" * 60 + "[/dim]")
            continue
    
    # Generate merged results
    if all_results:
        logger.info(f"Merging results from {len(all_results)} successfully processed file(s)")
        merged_data = _merge_results(all_results, log_files)
        
        # Save merged JSON
        if output:
            merged_output = output
            logger.info(f"Using specified output path: {merged_output}")
        else:
            # Generate filename based on framework(s)
            frameworks = list(set(result["framework"] for result in all_results))
            frameworks.sort()  # Consistent ordering
            
            if len(frameworks) == 1:
                # Single framework: TestNG_Full_Log_Analyze.20260214_233841.json
                framework_name = frameworks[0].title()
                filename = f"{framework_name}_Full_Log_Analyze.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            else:
                # Multiple frameworks: TestNG_Cypress_Full_Log_Analyze.20260214_233841.json
                framework_names = "_".join(f.title() for f in frameworks)
                filename = f"{framework_names}_Full_Log_Analyze.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            merged_output = Path(filename)
            logger.info(f"Using auto-generated output path: {merged_output}")
        
        logger.debug(f"Writing merged results to: {merged_output}")
        json_content = json.dumps(merged_data, indent=2, default=str)
        merged_output.write_text(json_content)
        merged_size = len(json_content) / 1024  # KB
        logger.info(f"Merged results saved to: {merged_output} ({merged_size:.1f} KB)")
        
        # Display overall summary
        console.print()
        console.print("=" * 60, style="green bold")
        console.print("  📊 Multi-File Analysis Summary", style="green bold")
        console.print("=" * 60, style="green bold")
        console.print()
        
        console.print(f"[green]✅ Successfully processed:[/green] {len(all_results)} file(s)")
        if failed_files:
            console.print(f"[yellow]⚠️  Failed/Skipped:[/yellow] {len(failed_files)} file(s)")
        
        console.print()
        console.print("[blue]📁 Output Files:[/blue]")
        console.print(f"   Merged results: [cyan]{merged_output}[/cyan]")
        console.print(f"   Per-file results: {len(all_results)} individual files")
        
        # Display aggregate statistics
        total_tests = sum(r["data"].get("total_tests", 0) for r in all_results)
        total_passed = sum(r["data"].get("passed_tests", 0) for r in all_results)
        total_failed = sum(r["data"].get("failed_tests", 0) for r in all_results)
        
        console.print()
        console.print("[blue]📈 Aggregate Statistics:[/blue]")
        console.print(f"   Total tests:  {total_tests}")
        console.print(f"   Passed:       {total_passed} ({(total_passed/total_tests*100) if total_tests > 0 else 0:.1f}%)")
        console.print(f"   Failed:       {total_failed} ({(total_failed/total_tests*100) if total_tests > 0 else 0:.1f}%)")
        
        # Show failed files if any
        if failed_files:
            console.print()
            console.print("[yellow]⚠️  Skipped Files:[/yellow]")
            
            # Group by stage for better visibility
            validation_failures = [f for f in failed_files if f.get("stage") == "validation"]
            framework_failures = [f for f in failed_files if f.get("stage") == "framework_detection"]
            parsing_failures = [f for f in failed_files if f.get("stage") == "parsing"]
            other_failures = [f for f in failed_files if "stage" not in f]
            
            if validation_failures:
                console.print()
                console.print("   [red]Validation Failures:[/red]")
                for failed in validation_failures:
                    console.print(f"      • {failed['file']}: {failed['reason']}")
            
            if framework_failures:
                console.print()
                console.print("   [yellow]Framework Detection Failures:[/yellow]")
                for failed in framework_failures:
                    console.print(f"      • {failed['file']}: {failed['reason']}")
            
            if parsing_failures:
                console.print()
                console.print("   [orange]Parsing Failures:[/orange]")
                for failed in parsing_failures:
                    console.print(f"      • {failed['file']}: {failed['reason']}")
            
            if other_failures:
                console.print()
                console.print("   [red]Other Failures:[/red]")
                for failed in other_failures:
                    console.print(f"      • {failed['file']}: {failed['reason']}")
        
        console.print()
        console.print("=" * 60, style="green")
        console.print("[green][OK] Multi-file parsing complete![/green]")
        logger.info(f"Multi-file parsing completed: {len(all_results)} successful, {len(failed_files)} failed")
        
    else:
        console.print()
        console.print("[red]❌ No files were successfully processed[/red]")
        if failed_files:
            console.print()
            console.print("[yellow]Failed files breakdown:[/yellow]")
            
            # Group by stage
            validation_failures = [f for f in failed_files if f.get("stage") == "validation"]
            framework_failures = [f for f in failed_files if f.get("stage") == "framework_detection"]
            parsing_failures = [f for f in failed_files if f.get("stage") == "parsing"]
            other_failures = [f for f in failed_files if "stage" not in f or f.get("stage") == "processing"]
            
            if validation_failures:
                console.print()
                console.print("   [red]Validation Failures ({count}):[/red]".format(count=len(validation_failures)))
                for failed in validation_failures:
                    console.print(f"      • {failed['file']}")
                    console.print(f"        [dim]{failed['reason']}[/dim]")
            
            if framework_failures:
                console.print()
                console.print("   [yellow]Framework Detection Failures ({count}):[/yellow]".format(count=len(framework_failures)))
                for failed in framework_failures:
                    console.print(f"      • {failed['file']}")
                    console.print(f"        [dim]{failed['reason']}[/dim]")
            
            if parsing_failures:
                console.print()
                console.print("   [orange]Parsing Failures ({count}):[/orange]".format(count=len(parsing_failures)))
                for failed in parsing_failures:
                    console.print(f"      • {failed['file']}")
                    console.print(f"        [dim]{failed['reason']}[/dim]")
            
            if other_failures:
                console.print()
                console.print("   [red]Processing Failures ({count}):[/red]".format(count=len(other_failures)))
                for failed in other_failures:
                    console.print(f"      • {failed['file']}")
                    console.print(f"        [dim]{failed['reason']}[/dim]")
        
        logger.error("Multi-file parsing failed: no files processed successfully")
        raise typer.Exit(1)


def _generate_per_file_output_path(log_file: Path) -> Path:
    """Generate output path for individual file using log filename."""
    # Extract base name without extension
    base_name = log_file.stem
    
    # Add timestamp and parsed suffix
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_name = f"{base_name}.parsed.{timestamp}.json"
    
    # Use same directory as input file
    return log_file.parent / output_name


def _merge_results(all_results: List[dict], log_files: List[Path]) -> dict:
    """Merge results from multiple files with unified clustering."""
    logger.info(f"Merging results from {len(all_results)} files")
    
    # Collect all failures across files for unified clustering
    all_failures = []
    
    for result in all_results:
        data = result["data"]
        source_file = result["source_file"]
        
        # Extract failures from this file
        if "failure_clusters" in data:
            for cluster in data.get("failure_clusters", []):
                for failure in cluster.get("failures", []):
                    failure["source_file"] = source_file
                    all_failures.append(failure)
        elif "failed_tests" in data and isinstance(data.get("tests", []), list):
            # If no clustering yet, extract from tests
            for test in data.get("tests", []):
                if test.get("status") in ["FAIL", "failed", "FAILED"]:
                    failure = {
                        "test_name": test.get("name", test.get("test_name", "Unknown")),
                        "error_message": test.get("error_message", test.get("message", "")),
                        "test_file": test.get("test_file", ""),
                        "source_file": source_file,
                    }
                    all_failures.append(failure)
    
    # Perform unified clustering across all failures
    from core.log_analysis.clustering import cluster_failures, get_cluster_summary
    
    unified_clusters = []
    if all_failures:
        logger.info(f"Performing unified clustering on {len(all_failures)} failures")
        try:
            unified_clusters = cluster_failures(all_failures)
            logger.info(f"Created {len(unified_clusters)} unified clusters")
        except Exception as e:
            logger.warning(f"Unified clustering failed: {e}")
    
    # Build merged output
    merged_data = {
        "analysis_type": "multi-file",
        "timestamp": datetime.now().isoformat(),
        "total_files": len(all_results),
        "files": [
            {
                "path": result["source_file"],
                "framework": result["framework"],
                "output_file": result["output_file"],
                "statistics": {
                    "total_tests": result["data"].get("total_tests", 0),
                    "passed_tests": result["data"].get("passed_tests", 0),
                    "failed_tests": result["data"].get("failed_tests", 0),
                    "skipped_tests": result["data"].get("skipped_tests", 0),
                }
            }
            for result in all_results
        ],
        "aggregate_statistics": {
            "total_tests": sum(r["data"].get("total_tests", 0) for r in all_results),
            "passed_tests": sum(r["data"].get("passed_tests", 0) for r in all_results),
            "failed_tests": sum(r["data"].get("failed_tests", 0) for r in all_results),
            "skipped_tests": sum(r["data"].get("skipped_tests", 0) for r in all_results),
        },
        "unified_failure_clusters": unified_clusters,
        "unified_cluster_summary": get_cluster_summary(unified_clusters) if unified_clusters else None,
        "per_file_results": [result["data"] for result in all_results]
    }
    
    logger.info("Results merged successfully")
    return merged_data


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
    
    # Log the parsing request details
    logger.info(f"Starting log parsing for: {log_file.name} (framework: auto-detect)")
    logger.info(f"Options: AI={enable_ai}, no_analyze={no_analyze}, triage={triage}")
    if app_logs:
        logger.info(f"Application logs provided: {app_logs}")
    if compare_with:
        logger.info(f"Regression comparison: {compare_with}")
    
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
    
    if framework == "testng-html-unsupported":
        console.print(f"[red]Error: TestNG HTML files cannot be parsed[/red]")
        console.print("")
        console.print(f"[yellow]You provided:[/yellow] {log_file.name}")
        console.print("")
        console.print("[yellow]HTML files (TestNG-Report.html, index.html) are for viewing results in a browser.[/yellow]")
        console.print("[yellow]To parse and analyze test results, please use the XML output file instead:[/yellow]")
        console.print("")
        console.print("  [green]✓[/green] Use: [cyan]testng-results.xml[/cyan] (typically in test-output directory)")
        console.print("")
        console.print("Example:")
        if log_file.parent:
            testng_xml_path = log_file.parent / "testng-results.xml"
            console.print(f"  $ crossbridge log [cyan]{testng_xml_path}[/cyan] --enable-ai")
        else:
            console.print("  $ crossbridge log [cyan]testng-results.xml[/cyan] --enable-ai")
        console.print("")
        console.print("[dim]Note: TestNG XML output is usually in the test-output/ directory[/dim]")
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
        logger.debug(f"Writing results to: {output}")
        json_content = json.dumps(output_data, indent=2, default=str)
        output.write_text(json_content)
        output_size = len(json_content) / 1024  # KB
        console.print(f"\n[blue]Results saved to: {output}[/blue]")
        logger.info(f"Results saved to: {output} ({output_size:.1f} KB)")
    else:
        # Save to default file
        default_output = log_file.with_suffix(f".parsed.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        logger.debug(f"Writing results to auto-generated path: {default_output}")
        json_content = json.dumps(output_data, indent=2, default=str)
        default_output.write_text(json_content)
        output_size = len(json_content) / 1024  # KB
        console.print(f"\n[blue]Full results saved to: {default_output}[/blue]")
        logger.info(f"Results saved to: {default_output} ({output_size:.1f} KB)")
    
    console.print()
    console.print("=" * 41, style="green")
    console.print("[green][OK] Parsing complete![/green]")
    logger.info("Log parsing completed successfully")


if __name__ == "__main__":
    typer.run(log_command)
