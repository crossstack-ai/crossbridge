"""
Analyze Logs Command

CLI command for analyzing execution logs with Execution Intelligence Engine.

Supports:
- Mandatory automation logs (test framework logs)
- Optional application logs (product/service logs)
- Configuration via YAML or CLI arguments
- Multiple output formats (text, JSON, markdown)

Usage:
    crossbridge analyze-logs --framework selenium --logs-automation target/surefire-reports
    crossbridge analyze-logs --config crossbridge.yaml
    crossbridge analyze-logs --framework pytest --logs-automation junit.xml --logs-application app/logs/service.log
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional, List

from core.logging import get_logger, LogCategory
from core.execution.intelligence.config_loader import load_config_or_default, create_default_config
from core.execution.intelligence.log_source_builder import build_log_sources
from core.execution.intelligence.log_router import route_log_collection
from core.execution.intelligence.analyzer import ExecutionIntelligenceAnalyzer
from cli.branding import print_header
from cli.errors import CrossbridgeError

logger = get_logger(__name__, category=LogCategory.CLI)


@click.command(name='analyze-logs')
@click.option(
    '--framework',
    type=str,
    help='Test framework name (selenium, pytest, robot, etc.)',
)
@click.option(
    '--logs-automation',
    type=str,
    multiple=True,
    help='Automation log paths (test framework logs) - can be specified multiple times',
)
@click.option(
    '--logs-application',
    type=str,
    multiple=True,
    help='Application log paths (product/service logs) - OPTIONAL - can be specified multiple times',
)
@click.option(
    '--config',
    type=click.Path(exists=True),
    default='crossbridge.yml',
    help='Path to configuration file (default: crossbridge.yml)',
)
@click.option(
    '--format',
    type=click.Choice(['text', 'json', 'markdown'], case_sensitive=False),
    default='text',
    help='Output format',
)
@click.option(
    '--enable-ai/--no-ai',
    default=False,
    help='Enable AI enhancement for analysis (requires AI configuration)',
)
@click.option(
    '--output',
    type=click.Path(),
    help='Output file path (default: print to stdout)',
)
@click.option(
    '--fail-on',
    type=click.Choice(['product', 'automation', 'environment', 'config', 'all', 'none'], case_sensitive=False),
    default='all',
    help='CI decision: exit with code 1 for specific failure types',
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Enable verbose logging',
)
def analyze_logs_command(
    framework: Optional[str],
    logs_automation: tuple,
    logs_application: tuple,
    config: str,
    format: str,
    enable_ai: bool,
    output: Optional[str],
    fail_on: str,
    verbose: bool
):
    """
    Analyze execution logs with Execution Intelligence Engine.
    
    This command analyzes test execution logs to classify failures and provide
    actionable insights. It supports both automation logs (mandatory) and
    application logs (optional for enrichment).
    
    Examples:
    
        # Analyze with explicit paths
        crossbridge analyze-logs --framework selenium --logs-automation target/surefire-reports
        
        # Analyze with configuration file
        crossbridge analyze-logs --config crossbridge.yml
        
        # Analyze with both automation and application logs
        crossbridge analyze-logs --framework pytest \\
            --logs-automation junit.xml \\
            --logs-application app/logs/service.log
        
        # Output as JSON for CI/CD integration
        crossbridge analyze-logs --framework selenium \\
            --logs-automation target/surefire-reports \\
            --format json --output analysis.json
    """
    # Setup logging
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    try:
        # Print header
        print_header("Execution Intelligence - Log Analysis")
        
        # Load configuration (if exists)
        exec_config = None
        if Path(config).exists():
            click.echo(f"📄 Loading configuration from: {config}")
            exec_config = load_config_or_default(config)
            if exec_config:
                click.echo(f"✓ Configuration loaded: framework={exec_config.framework}")
        
        # Priority resolution for framework
        resolved_framework = framework or (exec_config.framework if exec_config else None)
        
        if not resolved_framework:
            raise CrossbridgeError(
                "Framework not specified. Provide --framework or set it in crossbridge.yaml"
            )
        
        # Convert tuples to lists
        automation_paths = list(logs_automation) if logs_automation else None
        application_paths = list(logs_application) if logs_application else None
        
        # Build log source collection
        click.echo(f"\n🔍 Framework: {resolved_framework}")
        click.echo(f"📊 Building log sources...")
        
        log_collection = build_log_sources(
            framework=resolved_framework,
            automation_log_paths=automation_paths,
            application_log_paths=application_paths,
            config=exec_config
        )
        
        # Validate collection
        is_valid, error_msg = log_collection.validate()
        if not is_valid:
            raise CrossbridgeError(error_msg)
        
        # Display log sources
        click.echo(f"\n📝 Automation logs: {len(log_collection.automation_logs)}")
        for source in log_collection.automation_logs:
            exists_marker = "✓" if source.exists() else "✗"
            click.echo(f"  {exists_marker} {source.path}")
        
        if log_collection.has_application_logs():
            click.echo(f"\n📝 Application logs: {len(log_collection.application_logs)} (OPTIONAL)")
            for source in log_collection.application_logs:
                exists_marker = "✓" if source.exists() else "✗"
                click.echo(f"  {exists_marker} {source.path}")
        else:
            click.echo(f"\n⚠️  No application logs provided (optional - system will work without them)")
        
        # Parse logs
        click.echo(f"\n⚙️  Parsing logs...")
        events = route_log_collection(log_collection)
        click.echo(f"✓ Parsed {len(events)} events")
        
        # Count event sources
        automation_events = [e for e in events if e.log_source_type.value == 'automation']
        application_events = [e for e in events if e.log_source_type.value == 'application']
        
        click.echo(f"  - Automation events: {len(automation_events)}")
        click.echo(f"  - Application events: {len(application_events)}")
        
        # Create analyzer
        click.echo(f"\n🧠 Initializing analyzer (AI: {'enabled' if enable_ai else 'disabled'})...")
        analyzer = ExecutionIntelligenceAnalyzer(
            enable_ai=enable_ai,
            has_application_logs=log_collection.has_application_logs()
        )
        
        # Analyze failures
        click.echo(f"\n🔬 Analyzing failures...")
        
        # Group events by test
        test_logs = _group_events_by_test(events)
        
        if not test_logs:
            click.echo("✓ No test failures detected!")
            return
        
        click.echo(f"Found {len(test_logs)} test failures")
        
        # Analyze each test
        results = []
        for test_name, test_events in test_logs.items():
            # Combine event messages for analysis
            log_content = '\n'.join([e.message for e in test_events])
            result = analyzer.analyze_single_test(test_name, log_content)
            results.append(result)
        
        # Generate summary
        summary = analyzer.generate_summary(results)
        
        # Output results
        _output_results(results, summary, format, output, log_collection.has_application_logs())
        
        # CI decision
        exit_code = _determine_exit_code(results, fail_on)
        
        if exit_code != 0:
            click.echo(f"\n❌ Exiting with code {exit_code} based on --fail-on={fail_on}")
        
        sys.exit(exit_code)
        
    except CrossbridgeError as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _group_events_by_test(events: List) -> dict:
    """Group events by test name"""
    test_logs = {}
    
    for event in events:
        test_name = event.test_name or "unknown_test"
        
        if test_name not in test_logs:
            test_logs[test_name] = []
        
        test_logs[test_name].append(event)
    
    return test_logs


def _output_results(results: List, summary: dict, format: str, output_path: Optional[str], has_app_logs: bool):
    """Output analysis results"""
    if format == 'json':
        output_data = {
            'summary': summary,
            'failures': [r.to_dict() for r in results],
            'has_application_logs': has_app_logs
        }
        output_text = json.dumps(output_data, indent=2)
    
    elif format == 'markdown':
        output_text = _format_markdown(results, summary, has_app_logs)
    
    else:  # text
        output_text = _format_text(results, summary, has_app_logs)
    
    # Write to file or stdout
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_text)
        click.echo(f"\n✓ Results written to: {output_path}")
    else:
        click.echo("\n" + output_text)


def _format_text(results: List, summary: dict, has_app_logs: bool) -> str:
    """Format results as text"""
    lines = []
    lines.append("=" * 80)
    lines.append("EXECUTION INTELLIGENCE ANALYSIS")
    lines.append("=" * 80)
    
    # Summary
    lines.append(f"\nTotal Tests Analyzed: {summary['total_tests']}")
    lines.append(f"Application Logs: {'Yes' if has_app_logs else 'No (analysis based on automation logs only)'}")
    lines.append("\nFailure Distribution:")
    for failure_type, count in summary['by_type'].items():
        pct = summary['by_type_percentage'][failure_type]
        lines.append(f"  - {failure_type}: {count} ({pct:.1f}%)")
    
    lines.append(f"\nAverage Confidence: {summary['average_confidence']:.2f}")
    
    # Individual failures
    lines.append("\n" + "=" * 80)
    lines.append("FAILURE DETAILS")
    lines.append("=" * 80)
    
    for result in results:
        lines.append(f"\nTest: {result.test_name}")
        lines.append(f"Type: {result.failure_type.value}")
        lines.append(f"Confidence: {result.confidence:.2f}")
        
        if result.signals:
            lines.append(f"Signals: {', '.join([s.signal_type.value for s in result.signals])}")
        
        if result.code_references:
            lines.append(f"Code: {result.code_references[0]}")
        
        if result.reasoning:
            lines.append(f"Reasoning: {result.reasoning}")
    
    return '\n'.join(lines)


def _format_markdown(results: List, summary: dict, has_app_logs: bool) -> str:
    """Format results as markdown"""
    lines = []
    lines.append("# Execution Intelligence Analysis\n")
    
    # Summary
    lines.append("## Summary\n")
    lines.append(f"- **Total Tests Analyzed**: {summary['total_tests']}")
    lines.append(f"- **Application Logs**: {'✅ Yes (enriched analysis)' if has_app_logs else '⚠️ No (automation logs only)'}")
    lines.append(f"- **Average Confidence**: {summary['average_confidence']:.2f}\n")
    
    lines.append("### Failure Distribution\n")
    lines.append("| Failure Type | Count | Percentage |")
    lines.append("|-------------|-------|------------|")
    for failure_type, count in summary['by_type'].items():
        pct = summary['by_type_percentage'][failure_type]
        lines.append(f"| {failure_type} | {count} | {pct:.1f}% |")
    
    # Individual failures
    lines.append("\n## Failure Details\n")
    
    for i, result in enumerate(results, 1):
        lines.append(f"### {i}. {result.test_name}\n")
        lines.append(f"- **Type**: `{result.failure_type.value}`")
        lines.append(f"- **Confidence**: {result.confidence:.2f}")
        
        if result.signals:
            signals = ', '.join([f"`{s.signal_type.value}`" for s in result.signals])
            lines.append(f"- **Signals**: {signals}")
        
        if result.code_references:
            lines.append(f"- **Code**: `{result.code_references[0]}`")
        
        if result.reasoning:
            lines.append(f"- **Reasoning**: {result.reasoning}")
        
        lines.append("")
    
    return '\n'.join(lines)


def _determine_exit_code(results: List, fail_on: str) -> int:
    """Determine exit code based on failure types"""
    if fail_on == 'none':
        return 0
    
    failure_types = [r.failure_type.value for r in results]
    
    if fail_on == 'all':
        return 1 if results else 0
    
    elif fail_on == 'product':
        return 1 if 'PRODUCT_DEFECT' in failure_types else 0
    
    elif fail_on == 'automation':
        return 1 if 'AUTOMATION_DEFECT' in failure_types else 0
    
    elif fail_on == 'environment':
        return 1 if 'ENVIRONMENT_ISSUE' in failure_types else 0
    
    elif fail_on == 'config':
        return 1 if 'CONFIGURATION_ISSUE' in failure_types else 0
    
    return 0
