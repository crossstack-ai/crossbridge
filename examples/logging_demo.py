"""
Demo of CrossStack-AI CrossBridge Logging Framework.

Demonstrates all logging features:
- Multiple verbosity levels
- Console and file output
- AI-specific logging
- Category-based organization
- Context management
- Performance tracking
"""

from pathlib import Path
import time
from core.logging import (
    configure_logging,
    get_logger,
    LogLevel,
    LogCategory,
    set_global_log_level,
)


def demo_basic_logging():
    """Demonstrate basic logging features."""
    print("\n" + "="*70)
    print("1. BASIC LOGGING - All Levels")
    print("="*70 + "\n")
    
    logger = get_logger("demo.basic", category=LogCategory.GENERAL)
    
    logger.trace("This is a TRACE message - most detailed")
    logger.debug("This is a DEBUG message - for debugging")
    logger.info("This is an INFO message - general information")
    logger.success("This is a SUCCESS message - operation succeeded")
    logger.warning("This is a WARNING message - something to watch")
    logger.error("This is an ERROR message - something went wrong")
    logger.critical("This is a CRITICAL message - urgent attention needed")


def demo_ai_logging():
    """Demonstrate AI-specific logging."""
    print("\n" + "="*70)
    print("2. AI-SPECIFIC LOGGING - CrossStack-AI Operations")
    print("="*70 + "\n")
    
    logger = get_logger("demo.ai", category=LogCategory.AI)
    
    # AI operations
    logger.ai_operation("text_generation", "started", model="gpt-4")
    time.sleep(0.1)  # Simulate work
    
    # Prompt logging
    prompt = "Translate the following test case to Python..."
    logger.ai_prompt(prompt, model="gpt-4")
    
    # Response logging
    response = "Here is the translated test case..."
    logger.ai_response(response, tokens=150)
    
    logger.ai_operation("text_generation", "completed", model="gpt-4", tokens=150)
    
    # AI error
    logger.ai_error("Rate limit exceeded", operation="completion")


def demo_adapter_logging():
    """Demonstrate adapter logging."""
    print("\n" + "="*70)
    print("3. ADAPTER LOGGING - Framework Detection & Operations")
    print("="*70 + "\n")
    
    logger = get_logger("demo.adapter", category=LogCategory.ADAPTER)
    
    # Detection
    logger.adapter_detection("selenium", detected=True)
    logger.adapter_detection("cypress", detected=False)
    logger.adapter_detection("playwright", detected=True)
    
    # Operations
    logger.adapter_operation("selenium", "extracting tests", file_count=15)
    logger.adapter_operation("playwright", "migration started", tests=25)
    logger.adapter_operation("pytest", "test discovery", tests_found=42)


def demo_test_logging():
    """Demonstrate test execution logging."""
    print("\n" + "="*70)
    print("4. TEST EXECUTION LOGGING")
    print("="*70 + "\n")
    
    logger = get_logger("demo.testing", category=LogCategory.TESTING)
    
    # Test lifecycle
    tests = [
        ("test_user_login", True, 1.2),
        ("test_user_logout", True, 0.8),
        ("test_checkout_process", False, 2.5),
        ("test_payment_validation", True, 1.5),
    ]
    
    for test_name, should_pass, duration in tests:
        logger.test_started(test_name)
        time.sleep(0.1)  # Simulate test execution
        
        if should_pass:
            logger.test_passed(test_name, duration=duration)
        else:
            logger.test_failed(test_name, reason="Assertion error: Element not found")


def demo_context_logging():
    """Demonstrate context management."""
    print("\n" + "="*70)
    print("5. CONTEXT MANAGEMENT - Automatic Context Tracking")
    print("="*70 + "\n")
    
    logger = get_logger("demo.context", category=LogCategory.GENERAL)
    
    # Add context
    logger.add_context(user_id="user_12345", session="abc-def-ghi")
    
    logger.info("User logged in")
    logger.info("User viewed product page")
    logger.info("User added item to cart")
    
    # Clear context
    logger.clear_context()
    logger.info("Context cleared - no user info")


def demo_performance_logging():
    """Demonstrate performance tracking."""
    print("\n" + "="*70)
    print("6. PERFORMANCE TRACKING")
    print("="*70 + "\n")
    
    logger = get_logger("demo.performance", category=LogCategory.PERFORMANCE)
    
    operations = [
        ("database_query", 0.045),
        ("api_request", 0.523),
        ("file_processing", 1.234),
        ("cache_lookup", 0.002),
    ]
    
    for operation, duration in operations:
        logger.performance(operation, duration)


def demo_categories():
    """Demonstrate different log categories."""
    print("\n" + "="*70)
    print("7. LOG CATEGORIES - Organized by Purpose")
    print("="*70 + "\n")
    
    categories = [
        (LogCategory.GENERAL, "General application logging"),
        (LogCategory.AI, "AI and machine learning operations"),
        (LogCategory.ADAPTER, "Test adapter operations"),
        (LogCategory.MIGRATION, "Code migration processes"),
        (LogCategory.GOVERNANCE, "Policy and compliance"),
        (LogCategory.EXECUTION, "Test execution"),
        (LogCategory.PERSISTENCE, "Database operations"),
    ]
    
    for category, description in categories:
        logger = get_logger(f"demo.{category.value}", category=category)
        logger.info(f"{category.value.upper()}: {description}")


def demo_verbosity_levels():
    """Demonstrate verbosity level control."""
    print("\n" + "="*70)
    print("8. VERBOSITY LEVELS - Dynamic Level Control")
    print("="*70 + "\n")
    
    logger = get_logger("demo.verbosity", category=LogCategory.GENERAL)
    
    levels = [
        (LogLevel.CRITICAL, "CRITICAL: Only critical errors"),
        (LogLevel.ERROR, "ERROR: Errors and critical"),
        (LogLevel.WARNING, "WARNING: Warnings, errors, critical"),
        (LogLevel.INFO, "INFO: Info and above (default)"),
        (LogLevel.DEBUG, "DEBUG: Debug info and above"),
        (LogLevel.TRACE, "TRACE: Everything (most verbose)"),
    ]
    
    for level, description in levels:
        print(f"\nSetting level to {level.name}:")
        set_global_log_level(level)
        logger.info(description)
        logger.debug("Debug message")
        logger.trace("Trace message")


def demo_error_logging():
    """Demonstrate error and exception logging."""
    print("\n" + "="*70)
    print("9. ERROR & EXCEPTION LOGGING")
    print("="*70 + "\n")
    
    logger = get_logger("demo.errors", category=LogCategory.GENERAL)
    
    # Simple error
    logger.error("Configuration file not found")
    
    # Error with context
    logger.error("Failed to connect to database", 
                 host="localhost", port=5432, retry=3)
    
    # Exception with traceback
    try:
        result = 10 / 0
    except ZeroDivisionError:
        logger.exception("Math operation failed")


def demo_rich_messages():
    """Demonstrate rich formatted messages."""
    print("\n" + "="*70)
    print("10. RICH MESSAGES - Emojis & Formatting")
    print("="*70 + "\n")
    
    logger = get_logger("demo.rich", category=LogCategory.GENERAL)
    
    logger.info("🚀 Application starting up")
    logger.success("✅ Configuration loaded successfully")
    logger.info("📊 Processing 1,000 records")
    logger.success("💾 Data saved to database")
    logger.info("🔄 Synchronizing with remote server")
    logger.success("🎉 Migration completed successfully")


def main():
    """Run all logging demos."""
    print("\n" + "="*70)
    print(" " * 10 + "CrossStack-AI CrossBridge Logging Framework Demo")
    print("="*70)
    
    # Configure logging
    configure_logging(
        level=LogLevel.TRACE,  # Show everything
        log_dir=Path("logs_demo"),
        enable_console=True,
        enable_file=True
    )
    
    # Run demos
    demo_basic_logging()
    demo_ai_logging()
    demo_adapter_logging()
    demo_test_logging()
    demo_context_logging()
    demo_performance_logging()
    demo_categories()
    demo_verbosity_levels()
    demo_error_logging()
    demo_rich_messages()
    
    print("\n" + "="*70)
    print("Demo completed! Check logs_demo/ for log files.")
    print("="*70 + "\n")
    
    print("📁 Log files created:")
    log_dir = Path("logs_demo")
    if log_dir.exists():
        for log_file in sorted(log_dir.glob("*.log")):
            size_kb = log_file.stat().st_size / 1024
            print(f"  - {log_file.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
