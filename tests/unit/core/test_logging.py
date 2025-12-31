"""
Unit tests for CrossStack-AI CrossBridge logging framework.

Tests all logging functionality:
- Logger creation and configuration
- Log levels and verbosity
- Formatters
- Handlers
- Filters
- AI-specific logging
"""

import pytest
import logging
import tempfile
from pathlib import Path
from io import StringIO
import json

from core.logging import (
    CrossBridgeLogger,
    LogLevel,
    LogCategory,
    get_logger,
    configure_logging,
    set_global_log_level,
    get_global_log_level,
)
from core.logging.formatters import (
    ConsoleFormatter,
    FileFormatter,
    JSONFormatter,
    AIFormatter,
)
from core.logging.handlers import (
    ConsoleHandler,
    RotatingFileHandler,
)
from core.logging.filters import (
    CategoryFilter,
    LevelFilter,
    AIOperationFilter,
    NoiseReductionFilter,
)


class TestLogLevels:
    """Test log level functionality."""
    
    def test_log_level_values(self):
        """Test log level numeric values."""
        assert LogLevel.TRACE.value == 5
        assert LogLevel.DEBUG.value == 10
        assert LogLevel.INFO.value == 20
        assert LogLevel.SUCCESS.value == 25
        assert LogLevel.WARNING.value == 30
        assert LogLevel.ERROR.value == 40
        assert LogLevel.CRITICAL.value == 50
    
    def test_log_level_ordering(self):
        """Test log levels are properly ordered."""
        assert LogLevel.TRACE.value < LogLevel.DEBUG.value
        assert LogLevel.DEBUG.value < LogLevel.INFO.value
        assert LogLevel.INFO.value < LogLevel.SUCCESS.value
        assert LogLevel.SUCCESS.value < LogLevel.WARNING.value
        assert LogLevel.WARNING.value < LogLevel.ERROR.value
        assert LogLevel.ERROR.value < LogLevel.CRITICAL.value


class TestLogCategories:
    """Test log category functionality."""
    
    def test_category_values(self):
        """Test category string values."""
        assert LogCategory.GENERAL.value == "general"
        assert LogCategory.AI.value == "ai"
        assert LogCategory.ADAPTER.value == "adapter"
        assert LogCategory.TESTING.value == "testing"
    
    def test_all_categories_exist(self):
        """Test all expected categories are defined."""
        expected = [
            "general", "ai", "adapter", "migration",
            "governance", "execution", "persistence",
            "orchestration", "testing", "performance", "security"
        ]
        actual = [cat.value for cat in LogCategory]
        assert set(expected) == set(actual)


class TestCrossBridgeLogger:
    """Test core logger functionality."""
    
    def test_logger_creation(self):
        """Test logger can be created."""
        logger = CrossBridgeLogger(
            name="test",
            level=LogLevel.INFO,
            category=LogCategory.GENERAL,
            enable_console=False,
            enable_file=False
        )
        assert logger.name == "test"
        assert logger.category == LogCategory.GENERAL
    
    def test_logger_name_prefixing(self):
        """Test logger names are prefixed with crossbridge."""
        logger = CrossBridgeLogger(
            name="test.module",
            enable_console=False,
            enable_file=False
        )
        assert logger._logger.name == "crossbridge.test.module"
    
    def test_set_level(self):
        """Test changing log level."""
        logger = CrossBridgeLogger(
            name="test",
            level=LogLevel.INFO,
            enable_console=False,
            enable_file=False
        )
        
        logger.set_level(LogLevel.DEBUG)
        assert logger._logger.level == LogLevel.DEBUG.value
        
        logger.set_level(LogLevel.ERROR)
        assert logger._logger.level == LogLevel.ERROR.value
    
    def test_context_management(self):
        """Test context addition and clearing."""
        logger = CrossBridgeLogger(
            name="test",
            enable_console=False,
            enable_file=False
        )
        
        # Initial context
        assert "category" in logger._context
        assert "brand" in logger._context
        
        # Add context
        logger.add_context(user="john", session="123")
        assert logger._context["user"] == "john"
        assert logger._context["session"] == "123"
        
        # Clear context
        logger.clear_context()
        assert "user" not in logger._context
        assert "session" not in logger._context
        assert "category" in logger._context  # Should remain
        assert "brand" in logger._context  # Should remain
    
    def test_basic_logging_methods(self):
        """Test all basic logging methods work."""
        logger = CrossBridgeLogger(
            name="test",
            enable_console=False,
            enable_file=False
        )
        
        # These should not raise exceptions
        logger.trace("trace message")
        logger.debug("debug message")
        logger.info("info message")
        logger.success("success message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")
    
    def test_ai_logging_methods(self):
        """Test AI-specific logging methods."""
        logger = CrossBridgeLogger(
            name="test",
            category=LogCategory.AI,
            enable_console=False,
            enable_file=False
        )
        
        # These should not raise exceptions
        logger.ai_operation("test", "started")
        logger.ai_prompt("test prompt", model="gpt-4")
        logger.ai_response("test response", tokens=100)
        logger.ai_error("test error", operation="completion")
    
    def test_adapter_logging_methods(self):
        """Test adapter-specific logging methods."""
        logger = CrossBridgeLogger(
            name="test",
            category=LogCategory.ADAPTER,
            enable_console=False,
            enable_file=False
        )
        
        # These should not raise exceptions
        logger.adapter_detection("selenium", detected=True)
        logger.adapter_operation("pytest", "discover", count=10)
    
    def test_test_logging_methods(self):
        """Test test execution logging methods."""
        logger = CrossBridgeLogger(
            name="test",
            category=LogCategory.TESTING,
            enable_console=False,
            enable_file=False
        )
        
        # These should not raise exceptions
        logger.test_started("test_foo")
        logger.test_passed("test_foo", duration=1.5)
        logger.test_failed("test_bar", reason="assertion failed")
    
    def test_performance_logging(self):
        """Test performance logging."""
        logger = CrossBridgeLogger(
            name="test",
            category=LogCategory.PERFORMANCE,
            enable_console=False,
            enable_file=False
        )
        
        # Should not raise exception
        logger.performance("database_query", 0.123, rows=50)


class TestFormatters:
    """Test log formatters."""
    
    def test_console_formatter(self):
        """Test console formatter."""
        formatter = ConsoleFormatter(use_colors=False, use_emojis=False)
        
        record = logging.LogRecord(
            name="crossbridge.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "INFO" in formatted
        assert "Test message" in formatted
        assert "[test]" in formatted
    
    def test_console_formatter_with_emojis(self):
        """Test console formatter includes emojis."""
        formatter = ConsoleFormatter(use_colors=False, use_emojis=True)
        
        record = logging.LogRecord(
            name="crossbridge.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "ℹ️" in formatted
    
    def test_file_formatter(self):
        """Test file formatter."""
        formatter = FileFormatter()
        
        record = logging.LogRecord(
            name="crossbridge.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "INFO" in formatted
        assert "crossbridge.test" in formatted
        assert "Test message" in formatted
    
    def test_json_formatter(self):
        """Test JSON formatter."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="crossbridge.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "crossbridge.test"
        assert data["message"] == "Test message"
        assert data["brand"] == "CrossStack-AI CrossBridge"
    
    def test_ai_formatter(self):
        """Test AI formatter."""
        formatter = AIFormatter()
        
        record = logging.LogRecord(
            name="crossbridge.ai",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="AI operation completed",
            args=(),
            exc_info=None
        )
        record.model = "gpt-4"
        record.tokens = 100
        
        formatted = formatter.format(record)
        assert "CrossStack-AI" in formatted
        assert "AI operation completed" in formatted
        assert "gpt-4" in formatted
        assert "100 tokens" in formatted


class TestFilters:
    """Test log filters."""
    
    def test_category_filter(self):
        """Test category filter."""
        filter_obj = CategoryFilter({LogCategory.AI, LogCategory.ADAPTER})
        
        # Should pass
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="", args=(), exc_info=None
        )
        record.category = "ai"
        assert filter_obj.filter(record) is True
        
        # Should block
        record.category = "general"
        assert filter_obj.filter(record) is False
    
    def test_level_filter(self):
        """Test level filter."""
        filter_obj = LevelFilter(
            min_level=LogLevel.INFO,
            max_level=LogLevel.ERROR
        )
        
        # Should pass
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="", args=(), exc_info=None
        )
        assert filter_obj.filter(record) is True
        
        # Should block (too low)
        record.levelno = LogLevel.DEBUG.value
        assert filter_obj.filter(record) is False
        
        # Should block (too high)
        record.levelno = LogLevel.CRITICAL.value
        assert filter_obj.filter(record) is False
    
    def test_ai_operation_filter(self):
        """Test AI operation filter."""
        filter_obj = AIOperationFilter()
        
        # Should pass
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="AI operation completed", args=(), exc_info=None
        )
        assert filter_obj.filter(record) is True
        
        # Should pass (different keyword)
        record.msg = "Sending prompt to model"
        assert filter_obj.filter(record) is True
        
        # Should block
        record.msg = "Regular operation"
        assert filter_obj.filter(record) is False
    
    def test_noise_reduction_filter(self):
        """Test noise reduction filter."""
        filter_obj = NoiseReductionFilter(max_repeats=3)
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Repetitive message", args=(), exc_info=None
        )
        
        # First 3 should pass
        assert filter_obj.filter(record) is True
        assert filter_obj.filter(record) is True
        assert filter_obj.filter(record) is True
        
        # 4th should be blocked
        assert filter_obj.filter(record) is False
        
        # Error should always pass
        record.levelno = logging.ERROR
        assert filter_obj.filter(record) is True


class TestHandlers:
    """Test log handlers."""
    
    def test_rotating_file_handler_creation(self):
        """Test rotating file handler can be created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            
            handler = RotatingFileHandler(
                filename=str(log_file),
                maxBytes=1024,
                backupCount=3
            )
            
            assert log_file.exists()
            handler.close()
    
    def test_console_handler_creation(self):
        """Test console handler can be created."""
        handler = ConsoleHandler()
        assert handler is not None
        handler.close()


class TestGlobalConfiguration:
    """Test global logger configuration."""
    
    def test_configure_logging(self):
        """Test global logging configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                level=LogLevel.DEBUG,
                log_dir=Path(tmpdir),
                enable_console=True,
                enable_file=True
            )
            
            # Check global level
            assert get_global_log_level() == LogLevel.DEBUG
    
    def test_set_global_log_level(self):
        """Test setting global log level."""
        set_global_log_level(LogLevel.WARNING)
        assert get_global_log_level() == LogLevel.WARNING
        
        set_global_log_level(LogLevel.INFO)
        assert get_global_log_level() == LogLevel.INFO
    
    def test_get_logger_singleton(self):
        """Test get_logger returns same instance for same name."""
        logger1 = get_logger("test.singleton")
        logger2 = get_logger("test.singleton")
        assert logger1 is logger2
    
    def test_get_logger_different_names(self):
        """Test get_logger returns different instances for different names."""
        logger1 = get_logger("test.one")
        logger2 = get_logger("test.two")
        assert logger1 is not logger2


class TestIntegration:
    """Integration tests for complete logging scenarios."""
    
    def test_complete_logging_scenario(self):
        """Test a complete logging scenario with all features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Configure
            configure_logging(
                level=LogLevel.TRACE,
                log_dir=Path(tmpdir),
                enable_console=False,
                enable_file=True
            )
            
            # Get loggers for different categories
            ai_logger = get_logger("test.ai", category=LogCategory.AI)
            test_logger = get_logger("test.testing", category=LogCategory.TESTING)
            
            # Log various operations
            ai_logger.ai_operation("translate", "started")
            ai_logger.ai_response("result", tokens=100)
            
            test_logger.test_started("test_foo")
            test_logger.test_passed("test_foo", duration=1.0)
            
            # Close all handlers before checking files (Windows file locking)
            for handler in ai_logger._handlers:
                handler.close()
            for handler in test_logger._handlers:
                handler.close()
            
            # Check log files were created
            ai_log = Path(tmpdir) / "ai.log"
            test_log = Path(tmpdir) / "testing.log"
            
            assert ai_log.exists()
            assert test_log.exists()
            
            # Verify content (use encoding to handle emojis)
            ai_content = ai_log.read_text(encoding='utf-8')
            assert "translate" in ai_content
            assert "tokens" in ai_content
            
            test_content = test_log.read_text(encoding='utf-8')
            assert "test_foo" in test_content
            assert "passed" in test_content
    
    def test_context_propagation(self):
        """Test context is properly propagated through logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_logging(
                level=LogLevel.INFO,
                log_dir=Path(tmpdir),
                enable_console=False,
                enable_file=True
            )
            
            logger = get_logger("test.context", category=LogCategory.GENERAL)
            
            # Add context
            logger.add_context(user_id="123", session="abc")
            logger.info("First message")
            logger.info("Second message")
            
            # Close handlers before reading (Windows file locking)
            for handler in logger._handlers:
                handler.close()
            
            # Check log file
            log_file = Path(tmpdir) / "general.log"
            content = log_file.read_text(encoding='utf-8')
            
            # Both messages should have context
            assert "user_id=123" in content
            assert "session=abc" in content
            assert content.count("user_id=123") == 2  # Both messages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
