"""
Example: Integrating Unified Config with CLI Commands

This demonstrates how to use crossbridge.yml values as default inputs
for CLI commands, with CLI arguments overriding config file values.
"""

import click
from pathlib import Path
from core.config import get_config


# ============================================================================
# EXAMPLE 1: Simple CLI Integration
# ============================================================================

@click.command()
@click.option(
    '--mode',
    type=click.Choice(['assistive', 'automated', 'batch']),
    default=None,  # Will use config if not provided
    help='Translation mode (overrides config)'
)
@click.option(
    '--use-ai/--no-ai',
    default=None,  # Will use config if not provided
    help='Enable AI enhancement (overrides config)'
)
@click.option(
    '--max-credits',
    type=int,
    default=None,  # Will use config if not provided
    help='Maximum AI credits (overrides config)'
)
@click.option(
    '--validation',
    type=click.Choice(['strict', 'lenient', 'skip']),
    default=None,  # Will use config if not provided
    help='Validation level (overrides config)'
)
def translate_with_config(mode, use_ai, max_credits, validation):
    """
    Translation command that uses config as defaults.
    
    Priority: CLI args > Config file > Hardcoded defaults
    """
    # Load config
    config = get_config()
    
    # Apply defaults from config (CLI args override)
    final_mode = mode if mode is not None else config.translation.mode
    final_use_ai = use_ai if use_ai is not None else config.translation.use_ai
    final_max_credits = max_credits if max_credits is not None else config.translation.max_credits
    final_validation = validation if validation is not None else config.translation.validation_level
    
    click.echo("=" * 60)
    click.echo("Translation Configuration")
    click.echo("=" * 60)
    click.echo(f"Config File: {config._config_file or 'Using defaults'}")
    click.echo(f"Mode: {final_mode}")
    click.echo(f"AI Enabled: {final_use_ai}")
    click.echo(f"Max Credits: {final_max_credits}")
    click.echo(f"Validation: {final_validation}")
    click.echo("=" * 60)


# ============================================================================
# EXAMPLE 2: Helper Function for Config Integration
# ============================================================================

def get_config_value(cli_value, config_value, default_value=None):
    """
    Get effective configuration value with priority:
    1. CLI argument (if provided and not None)
    2. Config file value
    3. Default value
    
    Args:
        cli_value: Value from CLI argument
        config_value: Value from config file
        default_value: Fallback default
    
    Returns:
        Effective configuration value
    """
    if cli_value is not None:
        return cli_value
    if config_value is not None:
        return config_value
    return default_value


@click.command()
@click.option('--db-host', default=None)
@click.option('--db-port', type=int, default=None)
@click.option('--db-name', default=None)
@click.option('--verbose', is_flag=True)
def run_with_db_config(db_host, db_port, db_name, verbose):
    """Command using database config with helper function"""
    config = get_config()
    
    # Apply config values with priority
    host = get_config_value(db_host, config.database.host, 'localhost')
    port = get_config_value(db_port, config.database.port, 5432)
    database = get_config_value(db_name, config.database.database, 'crossbridge')
    
    if verbose:
        click.echo(f"Database: {host}:{port}/{database}")
        click.echo(f"Connection String: {config.database.connection_string}")


# ============================================================================
# EXAMPLE 3: Main Program with Config-Driven Defaults
# ============================================================================

@click.group()
@click.pass_context
def cli_main(ctx):
    """
    CrossBridge CLI - All defaults from crossbridge.yml
    
    Place crossbridge.yml in your project root to configure defaults.
    CLI arguments override config file values.
    """
    # Load config once and make available to all subcommands
    ctx.ensure_object(dict)
    ctx.obj['config'] = get_config()
    
    # Show config file location in verbose mode
    config = ctx.obj['config']
    if config._config_file:
        click.secho(f"📄 Using config: {config._config_file}", fg='green', dim=True)
    else:
        click.secho("📄 Using default configuration (no config file found)", fg='yellow', dim=True)


@cli_main.command()
@click.pass_context
@click.option('--source', type=str, required=True, help='Source framework')
@click.option('--target', type=str, required=True, help='Target framework')
@click.option('--mode', type=click.Choice(['assistive', 'automated', 'batch']), default=None)
@click.option('--use-ai/--no-ai', default=None)
@click.option('--confidence-threshold', type=float, default=None)
def translate(ctx, source, target, mode, use_ai, confidence_threshold):
    """Translate tests between frameworks"""
    config = ctx.obj['config']
    
    # Build effective configuration
    effective_config = {
        'source': source,
        'target': target,
        'mode': mode or config.translation.mode,
        'use_ai': use_ai if use_ai is not None else config.translation.use_ai,
        'confidence_threshold': confidence_threshold or config.translation.confidence_threshold,
        'validation_level': config.translation.validation_level,
        'max_workers': config.translation.max_workers,
    }
    
    click.echo("\n🔄 Translation Configuration:")
    for key, value in effective_config.items():
        source_indicator = "🖥️  CLI" if key in ['source', 'target', 'mode', 'use_ai', 'confidence_threshold'] and locals()[key] is not None else "📄 Config"
        click.echo(f"  {key}: {value} {source_indicator}")
    
    click.echo(f"\n✨ Translating from {source} to {target}...")


@cli_main.command()
@click.pass_context
@click.option('--level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), default=None)
def show_config(ctx, level):
    """Display current configuration"""
    config = ctx.obj['config']
    
    # Apply log level override
    log_level = level or config.logging.level
    
    click.echo("\n" + "=" * 60)
    click.echo("CROSSBRIDGE CONFIGURATION")
    click.echo("=" * 60)
    
    click.echo(f"\n📁 Config File: {config._config_file or 'Using defaults'}")
    click.echo(f"🎯 Mode: {config.mode}")
    
    click.echo(f"\n📊 Application:")
    click.echo(f"  Product: {config.application.product_name}")
    click.echo(f"  Version: {config.application.application_version}")
    click.echo(f"  Environment: {config.application.environment}")
    
    click.echo(f"\n🗄️  Database:")
    click.echo(f"  Host: {config.database.host}")
    click.echo(f"  Port: {config.database.port}")
    click.echo(f"  Database: {config.database.database}")
    
    click.echo(f"\n🤖 AI:")
    click.echo(f"  Enabled: {config.ai.enabled}")
    click.echo(f"  Provider: {config.ai.provider}")
    click.echo(f"  Model: {config.ai.model}")
    
    click.echo(f"\n🔄 Translation:")
    click.echo(f"  Mode: {config.translation.mode}")
    click.echo(f"  AI Enhancement: {config.translation.use_ai}")
    click.echo(f"  Max Credits: {config.translation.max_credits}")
    click.echo(f"  Validation: {config.translation.validation_level}")
    
    click.echo(f"\n📝 Logging:")
    click.echo(f"  Level: {log_level} {'🖥️  (CLI override)' if level else '📄 (from config)'}")
    click.echo(f"  Format: {config.logging.format}")
    click.echo(f"  File: {config.logging.log_file_path}")
    click.echo(f"  Console: {config.logging.log_to_console}")
    
    click.echo("=" * 60 + "\n")


# ============================================================================
# EXAMPLE 4: Logging Setup Using Config
# ============================================================================

import logging
from logging.handlers import RotatingFileHandler


def setup_logging_from_config():
    """
    Configure Python logging using settings from crossbridge.yml
    
    This should be called at application startup.
    """
    config = get_config()
    log_config = config.logging
    
    # Map string levels to logging constants
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    
    # Get log level
    log_level = level_map.get(log_config.level.upper(), logging.INFO)
    
    # Choose format
    if log_config.format == 'simple':
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
    elif log_config.format == 'json':
        log_format = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}'
    else:  # detailed
        log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    
    # Create formatter
    formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    
    # Console handler
    if log_config.log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_config.log_to_file:
        log_file = Path(log_config.log_file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=log_config.max_file_size_mb * 1024 * 1024,
            backupCount=log_config.backup_count
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Component-specific loggers
    component_loggers = {
        'translation': log_config.translation_level,
        'ai': log_config.ai_level,
        'database': log_config.database_level,
        'observer': log_config.observer_level,
    }
    
    for component, level_str in component_loggers.items():
        if level_str:
            component_level = level_map.get(level_str.upper(), log_level)
            logging.getLogger(f'crossbridge.{component}').setLevel(component_level)
    
    logging.info(f"Logging configured: level={log_config.level}, format={log_config.format}")
    if log_config.log_to_file:
        logging.info(f"Logging to file: {log_config.log_file_path}")


# ============================================================================
# EXAMPLE 5: Complete Application Startup
# ============================================================================

def main():
    """
    Complete application startup with config integration
    
    This is what should happen when CrossBridge starts:
    1. Load configuration from crossbridge.yml
    2. Setup logging based on config
    3. Run CLI with config-driven defaults
    """
    # Step 1: Load config (happens automatically via get_config())
    config = get_config()
    
    # Step 2: Setup logging from config
    setup_logging_from_config()
    
    # Step 3: Show startup info
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("CrossBridge Starting")
    logger.info("=" * 60)
    logger.info(f"Config file: {config._config_file or 'defaults'}")
    logger.info(f"Mode: {config.mode}")
    logger.info(f"Application: {config.application.product_name} {config.application.application_version}")
    logger.info("=" * 60)
    
    # Step 4: Run CLI
    cli_main()


if __name__ == '__main__':
    # For testing individual commands
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'translate':
        translate_with_config()
    elif len(sys.argv) > 1 and sys.argv[1] == 'db':
        run_with_db_config()
    elif len(sys.argv) > 1 and sys.argv[1] == 'main':
        main()
    else:
        click.echo("Usage examples:")
        click.echo("  python cli_config_integration.py translate --mode automated")
        click.echo("  python cli_config_integration.py db --db-host localhost --verbose")
        click.echo("  python cli_config_integration.py main show-config")
        click.echo("  python cli_config_integration.py main translate --source selenium --target playwright")
