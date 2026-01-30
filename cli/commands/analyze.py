"""
CLI Commands for Execution Intelligence

Provides command-line interface for analyzing test execution logs.
"""

import typer
import json
import sys
from pathlib import Path
from typing import Optional
from enum import Enum

from core.execution.intelligence.analyzer import ExecutionAnalyzer
from core.execution.intelligence.models import FailureType
from core.logging import get_logger

logger = get_logger(__name__)


class Framework(str, Enum):
    """Supported frameworks"""
    selenium = "selenium"
    pytest = "pytest"
    robot = "robot"
    playwright = "playwright"
    generic = "generic"


class OutputFormat(str, Enum):
    """Output formats"""
    json = "json"
    text = "text"
    summary = "summary"


class FailOn(str, Enum):
    """Fail-on options"""
    product = "product"
    automation = "automation"
    all = "all"
    none = "none"


analyze_group = typer.Typer(
    name="analyze",
    help="Analyze test execution logs and classify failures"
)


@analyze_group.command(name="logs")
def analyze_logs_command(
    log_file: Path = typer.Option(
        ...,
        "--log-file",
        exists=True,
        help="Path to test log file"
    ),
    test_name: str = typer.Option(
        ...,
        "--test-name",
        help="Name of the test"
    ),
    framework: Framework = typer.Option(
        Framework.generic,
        "--framework",
        help="Test framework"
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        exists=True,
        help="Workspace root directory"
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.text,
        "--format",
        help="Output format"
    ),
    enable_ai: bool = typer.Option(
        False,
        "--enable-ai",
        help="Enable AI enhancement (requires AI provider configuration)"
    ),
    fail_on: FailOn = typer.Option(
        FailOn.none,
        "--fail-on",
        help="Exit with error code if failure type matches"
    )
):
    """
    Analyze a single test execution log file.
    
    Example:
        crossbridge analyze logs --log-file test_output.log --test-name test_login --framework pytest
    """
    # Read log file
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            raw_log = f.read()
    except Exception as e:
        typer.echo(f"Error reading log file: {e}", err=True)
        raise typer.Exit(1)
    
    # Initialize analyzer
    analyzer = ExecutionAnalyzer(
        workspace_root=str(workspace),
        enable_ai=enable_ai
    )
    
    # Analyze
    typer.echo(f"Analyzing {test_name}...")
    result = analyzer.analyze(
        raw_log=raw_log,
        test_name=test_name,
        framework=framework.value
    )
    
    # Output result
    if output_format == OutputFormat.json:
        typer.echo(json.dumps(result.to_dict(), indent=2))
    elif output_format == OutputFormat.summary:
        _print_summary(result)
    else:  # text
        _print_text(result)
    
    # Determine exit code
    exit_code = _get_exit_code(result, fail_on.value)
    raise typer.Exit(exit_code)


@analyze_group.command(name="directory")
def analyze_directory_command(
    log_dir: Path = typer.Option(
        ...,
        "--log-dir",
        exists=True,
        help="Directory containing test logs"
    ),
    pattern: str = typer.Option(
        "*.log",
        "--pattern",
        help="File pattern to match (e.g., *.log, test_*.txt)"
    ),
    framework: Framework = typer.Option(
        Framework.generic,
        "--framework",
        help="Test framework"
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        exists=True,
        help="Workspace root directory"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        help="Output file (JSON format)"
    ),
    fail_on: FailOn = typer.Option(
        FailOn.none,
        "--fail-on",
        help="Exit with error code if any failure type matches"
    )
):
    """
    Analyze all test logs in a directory.
    
    Example:
        crossbridge analyze directory --log-dir ./test-output --pattern "*.log"
    """
    # Find log files
    log_files = list(log_dir.glob(pattern))
    
    if not log_files:
        typer.echo(f"No log files found matching pattern: {pattern}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"Found {len(log_files)} log files")
    
    # Initialize analyzer
    analyzer = ExecutionAnalyzer(workspace_root=str(workspace))
    
    # Analyze each log
    test_logs = []
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                raw_log = f.read()
            
            test_logs.append({
                'raw_log': raw_log,
                'test_name': log_file.stem,
                'framework': framework.value,
                'test_file': str(log_file)
            })
        except Exception as e:
            typer.echo(f"Error reading {log_file}: {e}", err=True)
    
    # Batch analyze
    typer.echo(f"Analyzing {len(test_logs)} tests...")
    results = analyzer.analyze_batch(test_logs)
    
    # Get summary
    summary = analyzer.get_summary(results)
    
    # Print summary
    typer.echo("\n" + "=" * 60)
    typer.echo("ANALYSIS SUMMARY")
    typer.echo("=" * 60)
    typer.echo(f"Total Tests: {summary['total_tests']}")
    typer.echo(f"Product Defects: {summary['product_defects']} ({summary['by_type_percentage']['PRODUCT_DEFECT']:.1f}%)")
    typer.echo(f"Automation Defects: {summary['automation_defects']} ({summary['by_type_percentage']['AUTOMATION_DEFECT']:.1f}%)")
    typer.echo(f"Environment Issues: {summary['environment_issues']} ({summary['by_type_percentage']['ENVIRONMENT_ISSUE']:.1f}%)")
    typer.echo(f"Configuration Issues: {summary['configuration_issues']} ({summary['by_type_percentage']['CONFIGURATION_ISSUE']:.1f}%)")
    typer.echo(f"Unknown: {summary['unknown']} ({summary['by_type_percentage']['UNKNOWN']:.1f}%)")
    typer.echo(f"Average Confidence: {summary['average_confidence']:.2f}")
    
    # Save to file if requested
    if output:
        output_data = {
            'summary': summary,
            'results': [r.to_dict() for r in results]
        }
        with open(output, 'w') as f:
            json.dump(output_data, f, indent=2)
        typer.echo(f"\nDetailed results saved to: {output}")
    
    # Determine exit code
    fail_types = _parse_fail_on(fail_on.value)
    should_fail = analyzer.should_fail_ci(results, fail_types)
    raise typer.Exit(1 if should_fail else 0)


def _print_text(result):
    """Print result in human-readable text format"""
    click.echo("\n" + "=" * 60)
    typer.echo("\n" + "=" * 60)
    typer.echo(f"TEST: {result.test_name}")
    typer.echo("=" * 60)
    
    if result.classification:
        cls = result.classification
        typer.echo(f"Failure Type: {cls.failure_type.value}")
        typer.echo(f"Confidence: {cls.confidence:.2f}")
        typer.echo(f"Reason: {cls.reason}")
        
        if cls.evidence:
            typer.echo("\nEvidence:")
            for i, evidence in enumerate(cls.evidence[:3], 1):
                typer.echo(f"  {i}. {evidence[:100]}...")
        
        if cls.code_reference:
            ref = cls.code_reference
            typer.echo(f"\nCode Reference:")
            typer.echo(f"  File: {ref.file}")
            typer.echo(f"  Line: {ref.line}")
            if ref.function:
                typer.echo(f"  Function: {ref.function}")
            typer.echo(f"\nCode Snippet:")
            typer.echo(ref.snippet)
        
        if cls.ai_enhanced and cls.ai_reasoning:
            typer.echo(f"\nAI Insights:")
            typer.echo(f"  {cls.ai_reasoning[:200]}...")
    
    else:
        typer.echo("Unable to classify failure")
    
    typer.echo("\n" + "=" * 60)


def _print_summary(result):
    """Print minimal summary"""
    if result.classification:
        typer.echo(
            f"{result.test_name}: {result.classification.failure_type.value} "
            f"(confidence: {result.classification.confidence:.2f})"
        )
    else:
        typer

def _parse_fail_on(fail_on: str) -> list:
    """Parse fail-on option into FailureType list"""
    if fail_on == 'product':
        return [FailureType.PRODUCT_DEFECT]
    elif fail_on == 'automation':
        return [FailureType.AUTOMATION_DEFECT]
    elif fail_on == 'all':
        return [
            FailureType.PRODUCT_DEFECT,
            FailureType.AUTOMATION_DEFECT,
            FailureType.ENVIRONMENT_ISSUE,
            FailureType.CONFIGURATION_ISSUE,
        ]
    else:  # none
        return []


def _get_exit_code(result, fail_on: str) -> int:
    """Get exit code based on result and fail-on option"""
    fail_types = _parse_fail_on(fail_on)
    
    if result.should_fail_ci(fail_types):
        return 1
    
    return 0
