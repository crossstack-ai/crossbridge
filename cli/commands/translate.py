"""
Translation CLI command.

Provides command-line interface for framework-to-framework translation.
"""

import sys
from pathlib import Path
from typing import Optional

import click

from core.translation.pipeline import TranslationPipeline, TranslationConfig, TranslationMode, ValidationLevel


@click.command()
@click.option(
    '--source',
    '-s',
    required=True,
    type=click.Choice([
        'selenium-java',
        'selenium-python',
        'restassured',
        'robot',
        'cypress',
        'playwright',
    ], case_sensitive=False),
    help='Source test framework'
)
@click.option(
    '--target',
    '-t',
    required=True,
    type=click.Choice([
        'playwright-python',
        'playwright-typescript',
        'pytest',
        'robot',
        'cypress',
    ], case_sensitive=False),
    help='Target test framework'
)
@click.option(
    '--input',
    '-i',
    'input_path',
    required=True,
    type=click.Path(exists=True),
    help='Input file or directory'
)
@click.option(
    '--output',
    '-o',
    'output_path',
    required=True,
    type=click.Path(),
    help='Output file or directory'
)
@click.option(
    '--mode',
    '-m',
    default='assistive',
    type=click.Choice(['assistive', 'automated', 'batch'], case_sensitive=False),
    help='Translation mode (assistive=review each, automated=auto-apply, batch=bulk)'
)
@click.option(
    '--use-ai/--no-ai',
    default=False,
    help='Use AI refinement for better quality (requires credits)'
)
@click.option(
    '--max-credits',
    type=int,
    default=100,
    help='Maximum AI credits to spend'
)
@click.option(
    '--confidence-threshold',
    type=float,
    default=0.7,
    help='Minimum confidence threshold (0.0-1.0)'
)
@click.option(
    '--validation',
    type=click.Choice(['strict', 'lenient', 'skip'], case_sensitive=False),
    default='strict',
    help='Validation level for generated code'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be translated without writing files'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Verbose output'
)
@click.option(
    '--enable-sidecar/--disable-sidecar',
    default=True,
    help='Enable/disable automatic sidecar observer integration (default: enabled)'
)
@click.option(
    '--sidecar-db-host',
    default='10.55.12.99',
    help='Database host for sidecar observer'
)
@click.option(
    '--sidecar-app-version',
    default='v1.0.0',
    help='Application version for sidecar tracking'
)
def translate(
    source: str,
    target: str,
    input_path: str,
    output_path: str,
    mode: str,
    use_ai: bool,
    max_credits: int,
    confidence_threshold: float,
    validation: str,
    dry_run: bool,
    verbose: bool,
    enable_sidecar: bool,
    sidecar_db_host: str,
    sidecar_app_version: str,
):
    """
    Translate test code between frameworks.
    
    Translates test code from one framework to another using semantic
    understanding via the Neutral Intent Model. NOT a syntax converter!
    
    Examples:
    
        # Translate single file (assistive mode)
        crossbridge translate \\
            --source selenium-java \\
            --target playwright-python \\
            --input tests/LoginTest.java \\
            --output tests/test_login.py
        
        # Translate directory with AI refinement
        crossbridge translate \\
            --source selenium-java \\
            --target playwright-python \\
            --input src/test/java \\
            --output tests/ \\
            --mode automated \\
            --use-ai \\
            --max-credits 500
        
        # Batch translation
        crossbridge translate \\
            --source restassured \\
            --target pytest \\
            --input api-tests/ \\
            --output pytest-tests/ \\
            --mode batch
    
    Supported Translation Paths (Phase 1):
    
        - Selenium Java → Playwright Python
        - Selenium Python → Playwright Python
        - RestAssured → Pytest
        - RestAssured → Robot Framework
        - Robot Framework → Pytest
    
    Translation Modes:
    
        - assistive: Show preview, require confirmation for each file
        - automated: Auto-apply high-confidence translations, prompt for low-confidence
        - batch: Bulk translate all files, save review report
    
    Validation Levels:
    
        - strict: Fail on any syntax errors or missing imports
        - lenient: Warn on issues but still generate code
        - skip: Generate code without validation
    """
    click.echo(f"🔄 CrossBridge Framework Translation")
    click.echo(f"   Source: {source}")
    click.echo(f"   Target: {target}")
    click.echo(f"   Mode: {mode}")
    click.echo()
    
    # Validate translation path
    if not _is_supported_path(source, target):
        click.secho(
            f"❌ Translation path {source} → {target} is not yet supported.",
            fg='red'
        )
        click.echo()
        click.echo("Supported paths in Phase 1:")
        click.echo("  • selenium-java → playwright-python")
        click.echo("  • selenium-python → playwright-python")
        click.echo("  • restassured → pytest")
        click.echo("  • restassured → robot")
        click.echo("  • robot → pytest")
        sys.exit(1)
    
    # Create config
    config = TranslationConfig(
        source_framework=source,
        target_framework=target,
        mode=TranslationMode[mode.upper()],
        use_ai=use_ai,
        max_credits=max_credits,
        confidence_threshold=confidence_threshold,
        validation_level=ValidationLevel[validation.upper()],
    )
    
    # Create pipeline
    pipeline = TranslationPipeline()
    
    # Determine if input is file or directory
    input_path_obj = Path(input_path)
    output_path_obj = Path(output_path)
    
    if input_path_obj.is_file():
        # Single file translation
        _translate_file(
            pipeline=pipeline,
            config=config,
            input_file=input_path_obj,
            output_file=output_path_obj,
            dry_run=dry_run,
            verbose=verbose,
        )
    else:
        # Directory translation
        _translate_directory(
            pipeline=pipeline,
            config=config,
            input_dir=input_path_obj,
            output_dir=output_path_obj,
            dry_run=dry_run,
            verbose=verbose,
        )


def _translate_file(
    pipeline: TranslationPipeline,
    config: TranslationConfig,
    input_file: Path,
    output_file: Path,
    dry_run: bool,
    verbose: bool,
):
    """Translate a single file."""
    click.echo(f"📄 Translating: {input_file.name}")
    
    # Read source code
    source_code = input_file.read_text()
    
    # Translate
    result = pipeline.translate(
        source_code=source_code,
        source_framework=config.source_framework,
        target_framework=config.target_framework,
        source_file=str(input_file),
    )
    
    # Check result
    if not result.success:
        click.secho(f"❌ Translation failed:", fg='red')
        for error in result.errors:
            click.echo(f"   • {error}")
        sys.exit(1)
    
    # Show statistics
    click.echo()
    click.echo(f"   ✅ Success")
    click.echo(f"   📊 Confidence: {result.confidence:.1%}")
    click.echo(f"   📈 Actions: {result.statistics.get('actions', 0)}")
    click.echo(f"   ✓ Assertions: {result.statistics.get('assertions', 0)}")
    
    # Show warnings
    if result.warnings:
        click.echo()
        click.secho(f"   ⚠️  Warnings:", fg='yellow')
        for warning in result.warnings:
            click.echo(f"      • {warning}")
    
    # Show TODOs
    if result.todos:
        click.echo()
        click.secho(f"   📝 TODOs (manual review needed):", fg='cyan')
        for todo in result.todos:
            click.echo(f"      • {todo}")
    
    # Show generated code if verbose or dry-run
    if verbose or dry_run:
        click.echo()
        click.echo("─" * 80)
        click.echo(result.target_code)
        click.echo("─" * 80)
    
    # Write output
    if not dry_run:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(result.target_code)
        click.echo()
        click.echo(f"   💾 Saved to: {output_file}")
    else:
        click.echo()
        click.echo("   🔍 Dry run - no files written")
    
    click.echo()


def _translate_directory(
    pipeline: TranslationPipeline,
    config: TranslationConfig,
    input_dir: Path,
    output_dir: Path,
    dry_run: bool,
    verbose: bool,
):
    """Translate all files in a directory."""
    # Find test files
    extensions = _get_file_extensions(config.source_framework)
    test_files = []
    for ext in extensions:
        test_files.extend(input_dir.rglob(f"*{ext}"))
    
    if not test_files:
        click.secho(f"❌ No test files found in {input_dir}", fg='red')
        sys.exit(1)
    
    click.echo(f"📁 Found {len(test_files)} test file(s)")
    click.echo()
    
    # Translate each file
    results = []
    for test_file in test_files:
        # Determine output path (preserve directory structure)
        relative_path = test_file.relative_to(input_dir)
        output_file = output_dir / _convert_filename(relative_path, config.target_framework)
        
        click.echo(f"📄 {relative_path} → {output_file.name}")
        
        # Read and translate
        source_code = test_file.read_text()
        result = pipeline.translate(
            source_code=source_code,
            source_framework=config.source_framework,
            target_framework=config.target_framework,
            source_file=str(test_file),
        )
        
        results.append({
            'file': relative_path,
            'result': result,
            'output': output_file,
        })
        
        # Show result
        if result.success:
            click.secho(f"   ✅ Confidence: {result.confidence:.1%}", fg='green')
        else:
            click.secho(f"   ❌ Failed: {result.errors[0] if result.errors else 'Unknown error'}", fg='red')
        
        click.echo()
    
    # Summary
    click.echo("=" * 80)
    click.echo(f"📊 Translation Summary")
    click.echo("=" * 80)
    
    successful = sum(1 for r in results if r['result'].success)
    failed = len(results) - successful
    
    click.echo(f"   Total: {len(results)}")
    click.secho(f"   ✅ Successful: {successful}", fg='green')
    if failed > 0:
        click.secho(f"   ❌ Failed: {failed}", fg='red')
    
    # Average confidence
    if successful > 0:
        avg_confidence = sum(
            r['result'].confidence for r in results if r['result'].success
        ) / successful
        click.echo(f"   📈 Average Confidence: {avg_confidence:.1%}")
    
    # Total TODOs
    total_todos = sum(len(r['result'].todos) for r in results)
    if total_todos > 0:
        click.secho(f"   📝 Total TODOs: {total_todos}", fg='cyan')
    
    # Write files
    if not dry_run:
        click.echo()
        click.echo("💾 Writing files...")
        migrated_files = []
        for item in results:
            if item['result'].success:
                item['output'].parent.mkdir(parents=True, exist_ok=True)
                item['output'].write_text(item['result'].target_code)
                migrated_files.append(item['output'])
        click.echo(f"   ✅ Saved to: {output_dir}")
        
        # Auto-integrate sidecar hooks
        if enable_sidecar:
            click.echo()
            click.echo("🔌 Integrating sidecar observer hooks...")
            _integrate_sidecar_hooks(
                target_framework=target,
                output_dir=output_dir,
                migrated_files=migrated_files,
                db_host=sidecar_db_host,
                app_version=sidecar_app_version,
                verbose=verbose
            )
    else:
        click.echo()
        click.echo("🔍 Dry run - no files written")
        click.echo("   (Sidecar hooks would be auto-integrated on actual migration)")
    
    click.echo()


def _is_supported_path(source: str, target: str) -> bool:
    """Check if translation path is supported."""
    supported_paths = [
        ('selenium-java', 'playwright-python'),
        ('selenium-python', 'playwright-python'),
        ('restassured', 'pytest'),
        ('restassured', 'robot'),
        ('robot', 'pytest'),
    ]
    return (source.lower(), target.lower()) in supported_paths


def _get_file_extensions(framework: str) -> list:
    """Get file extensions for framework."""
    extensions = {
        'selenium-java': ['.java'],
        'selenium-python': ['.py'],
        'restassured': ['.java'],
        'robot': ['.robot'],
        'cypress': ['.js', '.ts'],
        'playwright': ['.py', '.js', '.ts'],
    }
    return extensions.get(framework.lower(), ['.py'])


def _convert_filename(path: Path, target_framework: str) -> Path:
    """Convert filename for target framework."""
    # Change extension


def _integrate_sidecar_hooks(
    target_framework: str,
    output_dir: Path,
    migrated_files: list,
    db_host: str,
    app_version: str,
    verbose: bool
):
    """Integrate sidecar hooks after migration."""
    try:
        from core.translation.migration_hooks import (
            integrate_hooks_after_migration,
            MigrationHookConfig
        )
        
        config = MigrationHookConfig(
            enable_hooks=True,
            db_host=db_host,
            application_version=app_version
        )
        
        result = integrate_hooks_after_migration(
            target_framework=target_framework,
            output_dir=output_dir,
            migrated_files=migrated_files,
            config=config
        )
        
        if result.get("enabled"):
            click.secho(f"   ✅ Sidecar hooks integrated ({result.get('type')})", fg='green')
            click.echo(f"   📁 Config: {Path(result.get('config_file', '')).name}")
            
            if verbose:
                click.echo(f"   📝 Instructions:")
                for line in result.get('instructions', '').strip().split('\n'):
                    click.echo(f"      {line}")
        else:
            reason = result.get('reason', 'unknown')
            if reason == 'disabled_by_config':
                click.echo(f"   ⏭️  Sidecar hooks disabled")
            elif reason == 'unsupported_framework':
                click.secho(f"   ⚠️  No sidecar hooks for {target_framework}", fg='yellow')
            else:
                click.secho(f"   ⚠️  Hook integration failed: {reason}", fg='yellow')
    
    except ImportError:
        click.secho("   ⚠️  Migration hooks module not available", fg='yellow')
    except Exception as e:
        click.secho(f"   ⚠️  Hook integration error: {e}", fg='yellow')
        if verbose:
            import traceback
            click.echo(traceback.format_exc())


def _convert_filename(path: Path, target_framework: str) -> Path:
    """Convert filename for target framework."""
    # Change extension
    if target_framework.endswith('-python'):
        new_ext = '.py'
    elif target_framework.endswith('-typescript'):
        new_ext = '.ts'
    elif target_framework == 'robot':
        new_ext = '.robot'
    else:
        new_ext = '.py'
    
    # Convert Java test class name to Python
    name = path.stem
    if name.endswith('Test'):
        name = 'test_' + name[:-4].lower()
    elif not name.startswith('test_'):
        name = 'test_' + name.lower()
    
    return path.parent / f"{name}{new_ext}"
