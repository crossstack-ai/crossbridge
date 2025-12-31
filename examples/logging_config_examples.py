"""
Logging configuration examples for CrossStack-AI CrossBridge.

Shows different configuration patterns for various use cases.
"""

from pathlib import Path
from core.logging import (
    configure_logging,
    get_logger,
    LogLevel,
    LogCategory,
    set_global_log_level,
)


# ============================================================================
# Configuration Patterns
# ============================================================================

def config_development():
    """
    Development configuration - verbose logging, console output.
    
    Use during development for maximum visibility.
    """
    configure_logging(
        level=LogLevel.DEBUG,          # Show debug messages
        log_dir=Path("logs"),          # Save to logs directory
        enable_console=True,           # Console with colors
        enable_file=True               # Also save to files
    )


def config_testing():
    """
    Testing configuration - errors only, minimal output.
    
    Use during test execution to reduce noise.
    """
    configure_logging(
        level=LogLevel.ERROR,          # Only errors and critical
        log_dir=None,                  # No file output
        enable_console=True,           # Console only
        enable_file=False              # No file clutter during tests
    )


def config_production():
    """
    Production configuration - balanced logging, file output.
    
    Use in production for operational visibility without clutter.
    """
    configure_logging(
        level=LogLevel.INFO,           # Info and above
        log_dir=Path("/var/log/crossbridge"),  # Standard log location
        enable_console=False,          # No console in production
        enable_file=True               # Files with rotation
    )


def config_debug_session():
    """
    Debug session configuration - maximum verbosity.
    
    Use when debugging a specific issue.
    """
    configure_logging(
        level=LogLevel.TRACE,          # Everything
        log_dir=Path("debug_logs"),    # Separate debug directory
        enable_console=True,           # Console for live monitoring
        enable_file=True               # Files for later analysis
    )


def config_ci_cd():
    """
    CI/CD configuration - structured output for automation.
    
    Use in CI/CD pipelines for machine-readable logs.
    """
    configure_logging(
        level=LogLevel.INFO,           # Normal verbosity
        log_dir=Path("build/logs"),    # Build artifacts
        enable_console=True,           # Console for CI output
        enable_file=True               # Files for archiving
    )


def config_minimal():
    """
    Minimal configuration - warnings and errors only.
    
    Use when you want to suppress most output.
    """
    configure_logging(
        level=LogLevel.WARNING,        # Only warnings, errors, critical
        log_dir=None,                  # No files
        enable_console=True,           # Console only
        enable_file=False              # No files
    )


# ============================================================================
# Dynamic Configuration Examples
# ============================================================================

def example_verbosity_from_cli():
    """
    Set log level based on CLI arguments.
    
    Example: python main.py --verbose --verbose  # DEBUG level
    """
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0,
                       help="Increase verbosity (can be repeated)")
    parser.add_argument("-q", "--quiet", action="store_true",
                       help="Quiet mode (warnings and errors only)")
    args = parser.parse_args()
    
    if args.quiet:
        level = LogLevel.WARNING
    else:
        # Map verbosity count to log level
        level_map = {
            0: LogLevel.INFO,      # Default
            1: LogLevel.DEBUG,     # -v
            2: LogLevel.TRACE,     # -vv
        }
        level = level_map.get(args.verbose, LogLevel.TRACE)
    
    configure_logging(
        level=level,
        log_dir=Path("logs"),
        enable_console=True,
        enable_file=True
    )


def example_verbosity_from_env():
    """
    Set log level from environment variable.
    
    Example: export CROSSBRIDGE_LOG_LEVEL=DEBUG
    """
    import os
    
    level_name = os.getenv("CROSSBRIDGE_LOG_LEVEL", "INFO").upper()
    
    level_map = {
        "TRACE": LogLevel.TRACE,
        "DEBUG": LogLevel.DEBUG,
        "INFO": LogLevel.INFO,
        "WARNING": LogLevel.WARNING,
        "ERROR": LogLevel.ERROR,
        "CRITICAL": LogLevel.CRITICAL,
    }
    
    level = level_map.get(level_name, LogLevel.INFO)
    
    configure_logging(
        level=level,
        log_dir=Path("logs"),
        enable_console=True,
        enable_file=True
    )


def example_runtime_level_change():
    """
    Change log level at runtime based on conditions.
    """
    # Start with normal logging
    configure_logging(level=LogLevel.INFO)
    
    logger = get_logger(__name__)
    
    try:
        # Normal operation
        logger.info("Application running normally")
        
        # If something goes wrong, increase verbosity
        if detect_problem():
            logger.warning("Problem detected, enabling debug logging")
            set_global_log_level(LogLevel.DEBUG)
            
        # Continue with debug logging
        logger.debug("Now showing debug information")
        
    except Exception:
        # On error, enable trace logging
        logger.error("Error occurred, enabling trace logging")
        set_global_log_level(LogLevel.TRACE)
        logger.exception("Detailed error information")


def detect_problem():
    """Dummy function for example."""
    return False


# ============================================================================
# Module-Specific Configuration Examples
# ============================================================================

def example_module_specific_loggers():
    """
    Configure different loggers for different modules.
    """
    # Configure global settings
    configure_logging(
        level=LogLevel.INFO,
        log_dir=Path("logs"),
        enable_console=True,
        enable_file=True
    )
    
    # Get loggers for different modules with different categories
    adapter_logger = get_logger(
        "crossbridge.adapters.selenium",
        category=LogCategory.ADAPTER
    )
    
    ai_logger = get_logger(
        "crossbridge.ai.translator",
        category=LogCategory.AI
    )
    
    test_logger = get_logger(
        "crossbridge.execution.runner",
        category=LogCategory.TESTING
    )
    
    # Each logger will write to its own category file
    adapter_logger.info("Adapter logs go to adapter.log")
    ai_logger.info("AI logs go to ai.log")
    test_logger.info("Test logs go to testing.log")


# ============================================================================
# Special Use Cases
# ============================================================================

def example_temporary_debug_mode():
    """
    Temporarily enable debug mode, then restore.
    """
    from core.logging import get_global_log_level
    
    logger = get_logger(__name__)
    
    # Save current level
    original_level = get_global_log_level()
    
    try:
        # Enable debug temporarily
        set_global_log_level(LogLevel.DEBUG)
        logger.debug("Temporary debug information")
        
        # Do something that needs debugging
        complex_operation()
        
    finally:
        # Restore original level
        set_global_log_level(original_level)
        logger.info("Debug mode disabled")


def complex_operation():
    """Dummy function for example."""
    pass


def example_context_tracking():
    """
    Use context for tracking operations.
    """
    logger = get_logger(__name__, category=LogCategory.GENERAL)
    
    # Add request context
    request_id = "req-12345"
    user_id = "user-67890"
    
    logger.add_context(request_id=request_id, user_id=user_id)
    
    # All subsequent logs will include context
    logger.info("Processing request")
    logger.info("Validating input")
    logger.info("Executing operation")
    logger.success("Request completed")
    
    # Clear context when done
    logger.clear_context()


def example_performance_monitoring():
    """
    Track performance across operations.
    """
    import time
    
    logger = get_logger(__name__, category=LogCategory.PERFORMANCE)
    
    operations = {
        "database_query": 0.5,
        "api_call": 1.2,
        "processing": 0.8,
    }
    
    for operation, duration in operations.items():
        start = time.time()
        # ... do operation ...
        actual_duration = time.time() - start
        
        logger.performance(operation, actual_duration)


# ============================================================================
# Integration Examples
# ============================================================================

def example_flask_integration():
    """
    Configure logging for Flask application.
    """
    from flask import Flask
    
    app = Flask(__name__)
    
    # Configure at startup
    configure_logging(
        level=LogLevel.INFO,
        log_dir=Path("logs"),
        enable_console=True,
        enable_file=True
    )
    
    logger = get_logger(__name__, category=LogCategory.GENERAL)
    
    @app.before_request
    def log_request():
        from flask import request
        logger.info(f"Request: {request.method} {request.path}")
    
    @app.after_request
    def log_response(response):
        logger.info(f"Response: {response.status_code}")
        return response
    
    return app


def example_cli_integration():
    """
    Configure logging for CLI application.
    """
    import click
    
    @click.command()
    @click.option("--verbose", "-v", count=True, help="Increase verbosity")
    @click.option("--log-file", type=click.Path(), help="Log file path")
    def main(verbose, log_file):
        """CLI application with logging."""
        # Map verbosity to log level
        levels = [LogLevel.WARNING, LogLevel.INFO, LogLevel.DEBUG, LogLevel.TRACE]
        level = levels[min(verbose, len(levels) - 1)]
        
        # Configure
        configure_logging(
            level=level,
            log_dir=Path(log_file).parent if log_file else None,
            enable_console=True,
            enable_file=bool(log_file)
        )
        
        logger = get_logger(__name__)
        logger.info("CLI application started")
        
        # Your CLI logic here
        
        logger.success("CLI application completed")


# ============================================================================
# Best Practices
# ============================================================================

def best_practice_example():
    """
    Example following all best practices.
    """
    # 1. Configure once at application startup
    configure_logging(
        level=LogLevel.INFO,
        log_dir=Path("logs"),
        enable_console=True,
        enable_file=True
    )
    
    # 2. Get logger per module with appropriate category
    logger = get_logger(__name__, category=LogCategory.GENERAL)
    
    # 3. Use appropriate log levels
    logger.trace("Function entered with args: ...")  # Very detailed
    logger.debug("Processing record 5/100")          # Debug info
    logger.info("Service started")                   # Normal operations
    logger.success("Migration completed")            # Milestones
    logger.warning("Retry attempt 3/5")             # Warnings
    logger.error("Connection failed")                # Errors
    
    # 4. Add context for related operations
    logger.add_context(operation="data_migration", batch=1)
    logger.info("Starting batch")
    logger.info("Processing records")
    logger.success("Batch completed")
    logger.clear_context()
    
    # 5. Log exceptions properly
    try:
        risky_operation()
    except Exception:
        logger.exception("Operation failed")  # Includes traceback
    
    # 6. Use specialized methods
    logger.ai_operation("translate", "started", model="gpt-4")
    logger.test_passed("test_login", duration=1.5)
    logger.performance("database_query", 0.123)


def risky_operation():
    """Dummy function for example."""
    pass


if __name__ == "__main__":
    print("This file contains configuration examples.")
    print("Import and use the functions in your application.")
