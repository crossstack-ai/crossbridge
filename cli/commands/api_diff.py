"""
API Diff CLI Commands

Commands for API Change Intelligence
"""

import click
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@click.group(name="api-diff")
def api_diff():
    """API Change Intelligence commands"""
    pass


@api_diff.command()
@click.option("--config", default="crossbridge.yml", help="Config file path", type=click.Path(exists=True))
@click.option("--ai/--no-ai", default=None, help="Enable/disable AI enhancement")
@click.option("--output-dir", help="Output directory for documentation")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(config, ai, output_dir, verbose):
    """Run API diff analysis"""
    
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    try:
        from core.config import load_config
        from core.intelligence.api_change import APIChangeOrchestrator
        
        # Load config
        click.echo(f"Loading configuration from: {config}")
        cfg = load_config(config)
        
        if "api_change" not in cfg:
            click.echo("❌ api_change configuration not found in config file", err=True)
            click.echo("Please add api_change section to your crossbridge.yml", err=True)
            return 1
        
        api_change_config = cfg["api_change"]
        
        # Check if enabled
        if not api_change_config.get("enabled", False):
            click.echo("⚠️  API Change Intelligence is disabled in config")
            click.echo("Set api_change.enabled: true to enable it")
            return 0
        
        # Override with CLI flags
        if ai is not None:
            if "intelligence" not in api_change_config:
                api_change_config["intelligence"] = {}
            if "ai" not in api_change_config["intelligence"]:
                api_change_config["intelligence"]["ai"] = {}
            api_change_config["intelligence"]["ai"]["enabled"] = ai
        
        if output_dir:
            if "documentation" not in api_change_config:
                api_change_config["documentation"] = {}
            api_change_config["documentation"]["output_dir"] = output_dir
        
        # Run analysis
        click.echo("\n" + "=" * 60)
        click.echo("CrossBridge AI - API Change Intelligence")
        click.echo("=" * 60 + "\n")
        
        orchestrator = APIChangeOrchestrator(api_change_config)
        result = orchestrator.run()
        
        if result.status == "completed":
            # Print summary
            click.echo("\n✅ Analysis Complete!\n")
            click.echo(f"📊 Summary:")
            click.echo(f"  • Total Changes: {result.total_changes}")
            click.echo(f"  • Breaking Changes: {result.breaking_changes}")
            click.echo(f"  • High Risk: {result.high_risk_changes}")
            click.echo(f"  • Added Endpoints: {result.added_endpoints}")
            click.echo(f"  • Modified Endpoints: {result.modified_endpoints}")
            click.echo(f"  • Removed Endpoints: {result.removed_endpoints}")
            if result.ai_tokens_used > 0:
                click.echo(f"  • AI Tokens Used: {result.ai_tokens_used}")
            click.echo(f"  • Duration: {result.duration_ms}ms")
            
            # Show documentation location
            doc_dir = output_dir or api_change_config.get("documentation", {}).get("output_dir", "docs/api-changes")
            click.echo(f"\n📝 Documentation: {doc_dir}/api-changes.md")
            
            # Show test recommendations if available
            if result.test_recommendations:
                must_run = result.test_recommendations.get('must_run', [])
                should_run = result.test_recommendations.get('should_run', [])
                if must_run:
                    click.echo(f"\n🧪 Test Recommendations:")
                    click.echo(f"  • Must run: {len(must_run)} tests")
                    click.echo(f"  • Should run: {len(should_run)} tests")
                    click.echo(f"\nRun: crossbridge api-diff export-tests tests.txt --format pytest")
            
            return 0
        elif result.status == "disabled":
            click.echo("⚠️  API Change Intelligence is disabled")
            return 0
        else:
            click.echo(f"\n❌ Analysis failed: {result.error_message}", err=True)
            return 1
            
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


@api_diff.command()
@click.argument("output", type=click.Path())
@click.option("--config", default="crossbridge.yml", help="Config file path")
@click.option("--format", type=click.Choice(["pytest", "robot", "json", "text"]), default="text", help="Output format")
@click.option("--min-confidence", default=0.5, type=float, help="Minimum confidence threshold")
def export_tests(output, config, format, min_confidence):
    """Export selected test list for CI"""
    
    try:
        from core.config import load_config
        from core.intelligence.api_change import APIChangeOrchestrator
        from core.intelligence.api_change.ci_integration import CIIntegration, OutputFormat
        
        click.echo(f"Loading configuration from: {config}")
        cfg = load_config(config)
        
        if "api_change" not in cfg:
            click.echo("❌ api_change configuration not found", err=True)
            return 1
        
        api_change_config = cfg["api_change"]
        
        # Run analysis
        click.echo("Running API change analysis...")
        orchestrator = APIChangeOrchestrator(api_change_config)
        result = orchestrator.run()
        
        if result.status != "completed":
            click.echo(f"❌ Analysis failed: {result.error_message}", err=True)
            return 1
        
        if not result.test_impacts:
            click.echo("⚠️  No test impacts found")
            return 0
        
        # Initialize CI integration
        ci_config = api_change_config.get("ci_integration", {})
        ci_config["min_confidence"] = min_confidence
        ci_integration = CIIntegration(ci_config)
        
        # Select and generate tests
        selected_impacts = ci_integration.select_tests(result.test_impacts, result.changes)
        
        # Map format
        format_map = {
            "pytest": OutputFormat.PYTEST,
            "robot": OutputFormat.ROBOT,
            "json": OutputFormat.JSON,
            "text": OutputFormat.TEXT
        }
        
        output_content = ci_integration.generate_test_command(
            selected_impacts,
            format_map[format]
        )
        
        # Write to file
        with open(output, 'w') as f:
            f.write(output_content)
        
        click.echo(f"✅ Exported {len(selected_impacts)} tests to {output}")
        click.echo(f"   Format: {format}")
        click.echo(f"   Min confidence: {min_confidence}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        return 1


@api_diff.command()
@click.option("--config", default="crossbridge.yml", help="Config file path")
@click.option("--days", default=30, help="Number of days to show")
def stats(config, days):
    """Show API change statistics (placeholder)"""
    click.echo("⚠️  Statistics not yet implemented")
    click.echo("This will show API change statistics from database")
    return 1


@api_diff.command()
def check_deps():
    """Check if oasdiff is installed"""
    import subprocess
    
    click.echo("Checking dependencies...\n")
    
    # Check oasdiff
    try:
        result = subprocess.run(
            ["oasdiff", "--version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.decode().strip()
            click.echo(f"✅ oasdiff: {version}")
        else:
            click.echo("❌ oasdiff: not working properly")
            return 1
    except FileNotFoundError:
        click.echo("❌ oasdiff: not installed")
        click.echo("\nInstall oasdiff:")
        click.echo("  go install github.com/tufin/oasdiff@latest")
        click.echo("Or download from: https://github.com/tufin/oasdiff/releases")
        return 1
    except subprocess.TimeoutExpired:
        click.echo("❌ oasdiff: command timed out")
        return 1
    
    click.echo("\n✅ All dependencies installed")
    return 0


def register_commands(cli_group):
    """Register API diff commands with main CLI"""
    cli_group.add_command(api_diff)
