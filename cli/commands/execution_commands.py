"""
Execution Commands

CLI commands for test execution orchestration.

Commands:
- crossbridge run: Execute tests with strategy
- crossbridge plan: Show execution plan (dry-run)
"""

import typer
from pathlib import Path
from typing import Optional
import json
import sys

from core.execution.orchestration import (
    ExecutionRequest,
    StrategyType,
    create_orchestrator,
)
from cli.branding import show_info, show_error, show_step
from cli.errors import handle_cli_error

# Simple console output helpers
def console_print(msg):
    """Print message to console"""
    print(msg)

def format_info(msg):
    """Format info message"""
    return f"ℹ️  {msg}"

def format_success(msg):
    """Format success message"""
    return f"✅ {msg}"

def format_error(msg):
    """Format error message"""
    return f"❌ {msg}"


execution_commands = typer.Typer(
    name="exec",
    help="Test execution orchestration commands"
)


@execution_commands.command(name="run")
def run_command(
    framework: str = typer.Option(
        ...,
        help="Test framework to use",
    ),
    strategy: str = typer.Option(
        "impacted",
        help="Test selection strategy (smoke/impacted/risk/full)",
    ),
    env: str = typer.Option(
        "dev",
        "--env",
        help="Target environment (dev, qa, staging, prod)",
    ),
    ci: bool = typer.Option(
        False,
        "--ci",
        help="Enable CI mode (affects logging and retries)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show execution plan without running tests",
    ),
    max_tests: Optional[int] = typer.Option(
        None,
        "--max-tests",
        help="Maximum number of tests to run (budget limit)",
    ),
    max_duration: Optional[int] = typer.Option(
        None,
        "--max-duration",
        help="Maximum execution duration in minutes",
    ),
    tags: Optional[str] = typer.Option(
        None,
        "--tags",
        help="Comma-separated tags to include",
    ),
    exclude_tags: Optional[str] = typer.Option(
        None,
        "--exclude-tags",
        help="Comma-separated tags to exclude",
    ),
    include_flaky: bool = typer.Option(
        False,
        "--include-flaky",
        help="Include known flaky tests",
    ),
    no_parallel: bool = typer.Option(
        False,
        "--no-parallel",
        help="Disable parallel execution",
    ),
    base_branch: Optional[str] = typer.Option(
        None,
        "--base-branch",
        help="Base branch for impact analysis (e.g., main, develop)",
    ),
    branch: Optional[str] = typer.Option(
        None,
        "--branch",
        help="Current branch name",
    ),
    commit: Optional[str] = typer.Option(
        None,
        "--commit",
        help="Commit SHA",
    ),
    build_id: Optional[str] = typer.Option(
        None,
        "--build-id",
        help="CI build ID",
    ),
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        help="Path to workspace (defaults to current directory)",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Output result as JSON",
    ),
):
    """
    Execute tests with intelligent orchestration.
    
    Examples:
    
        # Run impacted tests (default)
        crossbridge exec run --framework pytest
        
        # Run smoke tests
        crossbridge exec run --framework testng --strategy smoke
        
        # Run risk-based tests with budget
        crossbridge exec run --framework robot --strategy risk --max-tests 50
        
        # CI mode with full logging
        crossbridge exec run --framework pytest --strategy impacted --ci
        
        # Dry run to see plan
        crossbridge exec run --framework testng --strategy risk --dry-run
    """
    try:
        # Build request
        request = ExecutionRequest(
            framework=framework,
            strategy=StrategyType(strategy),
            environment=env,
            ci_mode=ci,
            dry_run=dry_run,
            max_tests=max_tests,
            max_duration_minutes=max_duration,
            tags=tags.split(",") if tags else None,
            exclude_tags=exclude_tags.split(",") if exclude_tags else None,
            include_flaky=include_flaky,
            parallel=not no_parallel,
            base_branch=base_branch,
            metadata={
                "branch": branch or "",
                "commit": commit or "",
                "build_id": build_id or "",
            },
        )
        
        # Create orchestrator
        workspace_path = Path(workspace) if workspace else Path.cwd()
        orchestrator = create_orchestrator(workspace_path)
        
        # Execute
        if not output_json:
            console_print(format_info(
                f"\n🚀 Starting {strategy} execution for {framework} ({env})\n"
            ))
        
        result = orchestrator.execute(request)
        
        # Output result
        if output_json:
            # JSON output for CI/CD consumption
            output = {
                "status": result.status.value,
                "executed": len(result.executed_tests),
                "passed": len(result.passed_tests),
                "failed": len(result.failed_tests),
                "skipped": len(result.skipped_tests),
                "errors": len(result.error_tests),
                "pass_rate": result.pass_rate(),
                "execution_time_seconds": result.execution_time_seconds,
                "report_paths": result.report_paths,
                "has_failures": result.has_failures(),
            }
            print(json.dumps(output, indent=2))
        else:
            # Human-readable output
            _print_result(result, dry_run)
        
        # Exit code
        if result.has_failures():
            sys.exit(1)
        else:
            sys.exit(0)
            
    except ValueError as e:
        # Configuration error (exit code 3)
        handle_cli_error(e, "Configuration error")
        sys.exit(3)
    except RuntimeError as e:
        # Execution error (exit code 2)
        handle_cli_error(e, "Execution error")
        sys.exit(2)
    except Exception as e:
        # General error (exit code 2)
        handle_cli_error(e, "Execution failed")
        sys.exit(2)




@execution_commands.command(name="plan")
def plan_command(
    framework: str = typer.Option(
        ...,
        help="Test framework",
    ),
    strategy: str = typer.Option(
        "impacted",
        help="Test selection strategy (smoke/impacted/risk/full)",
    ),
    env: str = typer.Option(
        "dev",
        "--env",
        help="Target environment",
    ),
    base_branch: Optional[str] = typer.Option(
        None,
        "--base-branch",
        help="Base branch for impact analysis",
    ),
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        help="Path to workspace",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        help="Output plan as JSON",
    ),
):
    """
    Show execution plan without running tests.
    
    Examples:
    
        # See what impacted strategy would select
        crossbridge exec plan --framework pytest --strategy impacted
        
        # See risk-based selection
        crossbridge exec plan --framework testng --strategy risk
        
        # JSON output for scripts
        crossbridge exec plan --framework robot --strategy smoke --json
    """
    try:
        # Build request (dry-run enabled)
        request = ExecutionRequest(
            framework=framework,
            strategy=StrategyType(strategy),
            environment=env,
            ci_mode=False,
            dry_run=True,
            base_branch=base_branch,
        )
        
        # Create orchestrator
        workspace_path = Path(workspace) if workspace else Path.cwd()
        orchestrator = create_orchestrator(workspace_path)
        
        # Generate plan
        plan = orchestrator.plan(request)
        
        # Output plan
        if output_json:
            output = {
                "strategy": plan.strategy.value,
                "framework": plan.framework,
                "environment": plan.environment,
                "selected_tests": plan.selected_tests,
                "skipped_tests": plan.skipped_tests,
                "total_selected": plan.total_tests(),
                "estimated_duration_minutes": plan.estimated_duration_minutes,
                "confidence_score": plan.confidence_score,
                "grouping": plan.grouping,
                "priority": plan.priority,
            }
            print(json.dumps(output, indent=2))
        else:
            _print_plan(plan)
        
    except Exception as e:
        handle_cli_error(e, "Planning failed")
        sys.exit(1)


def _print_plan(plan):
    """Print execution plan in human-readable format"""
    console_print(format_info(f"\n📋 Execution Plan\n"))
    console_print(f"Strategy: {plan.strategy.value}")
    console_print(f"Framework: {plan.framework}")
    console_print(f"Environment: {plan.environment}")
    console_print(f"\nSelected Tests: {plan.total_tests()}")
    console_print(f"Estimated Duration: {plan.estimated_duration_minutes} minutes")
    console_print(f"Confidence Score: {plan.confidence_score:.2f}")
    
    # Show sample of selected tests
    console_print("\n📝 Sample Tests (first 10):")
    for test in plan.selected_tests[:10]:
        reason = plan.reasons.get(test, "No reason")
        priority = plan.priority.get(test, 3)
        console_print(f"  • {test}")
        console_print(f"    Priority: {priority}/5 | {reason}")
    
    if len(plan.selected_tests) > 10:
        console_print(f"\n  ... and {len(plan.selected_tests) - 10} more tests")


def _print_result(result, dry_run: bool):
    """Print execution result in human-readable format"""
    if dry_run:
        console_print(format_success("\n✅ Dry run complete - no tests executed\n"))
        return
    
    console_print("\n" + "="*60)
    console_print(format_info("  Execution Results"))
    console_print("="*60 + "\n")
    
    # Summary
    total = len(result.executed_tests)
    passed = len(result.passed_tests)
    failed = len(result.failed_tests)
    errors = len(result.error_tests)
    skipped = len(result.skipped_tests)
    
    console_print(f"Total Executed: {total}")
    console_print(format_success(f"✅ Passed: {passed}"))
    
    if failed > 0:
        console_print(format_error(f"❌ Failed: {failed}"))
    
    if errors > 0:
        console_print(format_error(f"⚠️  Errors: {errors}"))
    
    if skipped > 0:
        console_print(f"⏭️  Skipped: {skipped}")
    
    console_print(f"\nPass Rate: {result.pass_rate():.1f}%")
    console_print(f"Execution Time: {result.execution_time_seconds:.1f}s")
    
    # Failed tests detail
    if result.has_failures():
        console_print(format_error("\n❌ Failed Tests:"))
        for test in result.failed_tests[:10]:
            console_print(f"  • {test}")
        if len(result.failed_tests) > 10:
            console_print(f"  ... and {len(result.failed_tests) - 10} more failures")
        
        for test in result.error_tests[:5]:
            console_print(f"  • {test} (ERROR)")
    
    # Reports
    if result.report_paths:
        console_print(f"\n📊 Reports:")
        for path in result.report_paths[:3]:
            console_print(f"  • {path}")
    
    console_print("\n" + "="*60 + "\n")
    
    if result.has_failures():
        console_print(format_error("❌ Execution completed with failures"))
    else:
        console_print(format_success("✅ All tests passed!"))
