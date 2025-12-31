"""
Quick start example for CrossStack-AI CrossBridge logging.

Shows how to quickly integrate logging into your modules.
"""

from pathlib import Path
from core.logging import configure_logging, get_logger, LogLevel, LogCategory


# ============================================================================
# Step 1: Configure logging at application startup
# ============================================================================

def setup_logging():
    """Call this once at application startup."""
    configure_logging(
        level=LogLevel.INFO,           # Set global level
        log_dir=Path("logs"),          # Where to save logs
        enable_console=True,           # Console output with colors
        enable_file=True               # File output with rotation
    )


# ============================================================================
# Step 2: Get logger in each module
# ============================================================================

# In your adapter module:
adapter_logger = get_logger(__name__, category=LogCategory.ADAPTER)

# In your AI module:
ai_logger = get_logger(__name__, category=LogCategory.AI)

# In your test execution module:
test_logger = get_logger(__name__, category=LogCategory.TESTING)


# ============================================================================
# Step 3: Use the logger
# ============================================================================

def example_adapter_usage():
    """Example of adapter logging."""
    adapter_logger.info("Starting test discovery")
    adapter_logger.adapter_detection("selenium", detected=True)
    adapter_logger.adapter_operation("selenium", "extract_tests", count=25)
    adapter_logger.success("Test discovery completed")


def example_ai_usage():
    """Example of AI logging."""
    ai_logger.info("Starting AI translation")
    ai_logger.ai_operation("translate", "started")
    ai_logger.ai_prompt("Translate this test...", model="gpt-4")
    ai_logger.ai_response("Here is the translation...", tokens=120)
    ai_logger.ai_operation("translate", "completed", tokens=120)


def example_test_usage():
    """Example of test execution logging."""
    test_logger.test_started("test_user_login")
    # ... run test ...
    test_logger.test_passed("test_user_login", duration=1.5)


def example_error_handling():
    """Example of error logging."""
    try:
        # Some risky operation
        result = perform_operation()
    except Exception as e:
        adapter_logger.exception("Operation failed")
        # or
        adapter_logger.error("Operation failed", exc_info=True)


def example_context():
    """Example of context management."""
    # Add context for all subsequent logs
    adapter_logger.add_context(user="john", project="web-app")
    
    adapter_logger.info("Processing started")
    adapter_logger.info("Step 1 completed")
    adapter_logger.info("Step 2 completed")
    
    # Clear context when done
    adapter_logger.clear_context()


def example_performance():
    """Example of performance tracking."""
    import time
    
    start = time.time()
    # ... perform operation ...
    duration = time.time() - start
    
    adapter_logger.performance("database_query", duration, rows=100)


# ============================================================================
# Step 4: Adjust verbosity at runtime
# ============================================================================

def set_verbose_mode():
    """Enable verbose logging for debugging."""
    from core.logging import set_global_log_level
    set_global_log_level(LogLevel.DEBUG)


def set_quiet_mode():
    """Reduce logging noise in production."""
    from core.logging import set_global_log_level
    set_global_log_level(LogLevel.WARNING)


# ============================================================================
# Main example
# ============================================================================

def main():
    """Run quick start example."""
    # Setup (call once at startup)
    setup_logging()
    
    print("="*70)
    print("Quick Start Example - CrossStack-AI CrossBridge Logging")
    print("="*70 + "\n")
    
    # Use logging in your code
    example_adapter_usage()
    print()
    
    example_ai_usage()
    print()
    
    example_test_usage()
    print()
    
    example_context()
    print()
    
    print("="*70)
    print("That's it! Check the logs/ directory for output files.")
    print("="*70)


if __name__ == "__main__":
    main()
