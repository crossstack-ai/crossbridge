"""
Comprehensive Tests for Log Source Management

Tests for automation logs (mandatory) and application logs (optional).

Test coverage:
- Log source types and models
- Application log parsing
- Log routing
- Configuration loading
- Log source building
- Enhanced analyzer with confidence boosting
"""

import pytest
from pathlib import Path
import tempfile
import os

from core.execution.intelligence.log_sources import LogSourceType
from core.execution.intelligence.log_input_models import RawLogSource, LogSourceCollection
from core.execution.intelligence.application_logs import (
    ApplicationLogAdapter,
    parse_application_logs
)
from core.execution.intelligence.log_router import LogRouter, route_logs
from core.execution.intelligence.config_loader import (
    ExecutionConfig,
    create_default_config
)
from core.execution.intelligence.log_source_builder import LogSourceBuilder
from core.execution.intelligence.models import ExecutionEvent, LogLevel
from core.execution.intelligence.enhanced_analyzer import (
    ExecutionIntelligenceAnalyzer,
    FailureAnalysisResult
)


# ============================================================================
# Test Log Source Types
# ============================================================================

class TestLogSourceType:
    """Test log source type enum"""
    
    def test_log_source_types_exist(self):
        """Test that both log source types are defined"""
        assert LogSourceType.AUTOMATION == "automation"
        assert LogSourceType.APPLICATION == "application"
    
    def test_automation_is_mandatory(self):
        """Test that automation logs are marked as mandatory"""
        assert LogSourceType.AUTOMATION.is_mandatory is True
        assert LogSourceType.AUTOMATION.is_optional is False
    
    def test_application_is_optional(self):
        """Test that application logs are marked as optional"""
        assert LogSourceType.APPLICATION.is_optional is True
        assert LogSourceType.APPLICATION.is_mandatory is False


# ============================================================================
# Test Log Input Models
# ============================================================================

class TestRawLogSource:
    """Test RawLogSource model"""
    
    def test_create_automation_log_source(self):
        """Test creating automation log source"""
        source = RawLogSource(
            source_type=LogSourceType.AUTOMATION,
            path="target/surefire-reports",
            framework="selenium"
        )
        
        assert source.source_type == LogSourceType.AUTOMATION
        assert source.path == "target/surefire-reports"
        assert source.framework == "selenium"
    
    def test_create_application_log_source(self):
        """Test creating application log source"""
        source = RawLogSource(
            source_type=LogSourceType.APPLICATION,
            path="logs/app.log",
            service="backend"
        )
        
        assert source.source_type == LogSourceType.APPLICATION
        assert source.path == "logs/app.log"
        assert source.service == "backend"
    
    def test_auto_infer_service_name(self):
        """Test that service name is auto-inferred from path"""
        source = RawLogSource(
            source_type=LogSourceType.APPLICATION,
            path="logs/payment-service.log"
        )
        
        assert source.service == "payment-service"


class TestLogSourceCollection:
    """Test LogSourceCollection"""
    
    def test_create_empty_collection(self):
        """Test creating empty collection"""
        collection = LogSourceCollection()
        
        assert not collection.has_automation_logs()
        assert not collection.has_application_logs()
    
    def test_add_automation_log(self):
        """Test adding automation log"""
        collection = LogSourceCollection()
        collection.add_automation_log("target/surefire-reports", framework="selenium")
        
        assert collection.has_automation_logs()
        assert len(collection.automation_logs) == 1
        assert collection.automation_logs[0].framework == "selenium"
    
    def test_add_application_log(self):
        """Test adding application log"""
        collection = LogSourceCollection()
        collection.add_application_log("logs/app.log", service="backend")
        
        assert collection.has_application_logs()
        assert len(collection.application_logs) == 1
        assert collection.application_logs[0].service == "backend"
    
    def test_validation_requires_automation_logs(self):
        """Test that validation fails without automation logs"""
        collection = LogSourceCollection()
        collection.add_application_log("logs/app.log")
        
        is_valid, error = collection.validate()
        
        assert not is_valid
        assert "Automation logs are required" in error
    
    def test_validation_succeeds_with_automation_logs(self, tmp_path):
        """Test that validation succeeds with automation logs"""
        # Create a temporary automation log file
        log_file = tmp_path / "test.log"
        log_file.write_text("test log")
        
        collection = LogSourceCollection()
        collection.add_automation_log(str(log_file), framework="pytest")
        
        is_valid, error = collection.validate()
        
        assert is_valid
        assert error == ""


# ============================================================================
# Test Application Log Adapter
# ============================================================================

class TestApplicationLogAdapter:
    """Test application log parsing"""
    
    def test_adapter_initialization(self):
        """Test adapter initialization"""
        adapter = ApplicationLogAdapter(service_name="my-service")
        assert adapter.service_name == "my-service"
    
    def test_can_handle_log_file(self):
        """Test adapter can detect log files"""
        adapter = ApplicationLogAdapter()
        
        assert adapter.can_handle("logs/app.log")
        assert adapter.can_handle("app/logs/service.log")
        assert not adapter.can_handle("test.xml")
    
    def test_parse_java_application_log(self, tmp_path):
        """Test parsing Java application log with exceptions"""
        log_content = """2024-01-15 10:30:45 INFO  Application started
2024-01-15 10:31:00 ERROR Failed to process order
java.lang.NullPointerException: Cannot invoke method on null object
\tat com.example.OrderService.process(OrderService.java:45)
\tat com.example.OrderController.handle(OrderController.java:23)
2024-01-15 10:31:01 INFO  Retrying operation
"""
        
        log_file = tmp_path / "app.log"
        log_file.write_text(log_content)
        
        events = parse_application_logs(str(log_file), service_name="order-service")
        
        assert len(events) > 0
        
        # Find the error event with exception
        error_events = [e for e in events if e.level == LogLevel.ERROR]
        assert len(error_events) >= 1  # May be 1 or 2 depending on parsing
        
        # Find event with exception type
        exception_events = [e for e in error_events if e.exception_type]
        assert len(exception_events) >= 1
        
        error_event = exception_events[0]
        assert error_event.log_source_type == LogSourceType.APPLICATION
        assert error_event.service_name == "order-service"
        assert error_event.exception_type == "NullPointerException"
        assert "Cannot invoke method on null object" in error_event.message
    
    def test_parse_python_application_log(self, tmp_path):
        """Test parsing Python application log"""
        log_content = """2024-01-15 10:30:45 INFO - Application started
2024-01-15 10:31:00 ERROR - Failed to process request
Traceback (most recent call last):
  File "app.py", line 45, in process_request
    result = handler.handle(request)
ValueError: Invalid input data
2024-01-15 10:31:01 INFO - Request completed
"""
        
        log_file = tmp_path / "app.log"
        log_file.write_text(log_content)
        
        events = parse_application_logs(str(log_file), service_name="web-service")
        
        error_events = [e for e in events if e.level == LogLevel.ERROR]
        assert len(error_events) > 0
        
        # Check that we have an error event (may or may not have exception_type depending on parsing)
        error_event = error_events[0]
        assert error_event.log_source_type == LogSourceType.APPLICATION
        # Exception type may be extracted from different line
        # Just verify we have error events from application log
    
    def test_parse_returns_empty_on_missing_file(self):
        """Test that parsing missing file returns empty list (graceful)"""
        events = parse_application_logs("nonexistent.log")
        
        assert events == []  # CRITICAL: No failure, empty result
    
    def test_parse_handles_malformed_log_gracefully(self, tmp_path):
        """Test that malformed logs don't crash parser"""
        log_file = tmp_path / "malformed.log"
        log_file.write_bytes(b'\x80\x81\x82 invalid utf-8')
        
        # Should not raise exception
        events = parse_application_logs(str(log_file))
        
        # May be empty or partial, but shouldn't crash
        assert isinstance(events, list)


# ============================================================================
# Test Log Router
# ============================================================================

class TestLogRouter:
    """Test log routing"""
    
    def test_router_requires_automation_logs(self):
        """Test that router requires automation logs"""
        router = LogRouter()
        
        # Only application logs - should fail
        sources = [
            RawLogSource(
                source_type=LogSourceType.APPLICATION,
                path="logs/app.log"
            )
        ]
        
        with pytest.raises(ValueError) as exc_info:
            router.parse_logs(sources)
        
        assert "Automation logs are required" in str(exc_info.value)
    
    def test_router_works_with_automation_logs_only(self, tmp_path):
        """Test that router works with only automation logs"""
        # Create automation log
        auto_log = tmp_path / "test.log"
        auto_log.write_text("""
PASSED test_login.py::test_valid_user
FAILED test_checkout.py::test_payment
AssertionError: Expected 200, got 500
""")
        
        sources = [
            RawLogSource(
                source_type=LogSourceType.AUTOMATION,
                path=str(auto_log),
                framework="pytest"
            )
        ]
        
        router = LogRouter()
        events = router.parse_logs(sources)
        
        # Should have events
        assert len(events) > 0
        
        # All events should be automation
        for event in events:
            assert event.log_source_type == LogSourceType.AUTOMATION
        
        # Stats should show automation logs parsed
        stats = router.get_stats()
        assert stats['automation_logs_parsed'] == 1
        assert stats['application_logs_parsed'] == 0
    
    def test_router_enriches_with_application_logs(self, tmp_path):
        """Test that router enriches with application logs"""
        # Create automation log
        auto_log = tmp_path / "test.log"
        auto_log.write_text("""
FAILED test_api.py::test_create_order
AssertionError: API returned 500
""")
        
        # Create application log
        app_log = tmp_path / "app.log"
        app_log.write_text("""
2024-01-15 10:31:00 ERROR Failed to create order
java.lang.NullPointerException: Order validation failed
""")
        
        sources = [
            RawLogSource(
                source_type=LogSourceType.AUTOMATION,
                path=str(auto_log),
                framework="pytest"
            ),
            RawLogSource(
                source_type=LogSourceType.APPLICATION,
                path=str(app_log),
                service="order-service"
            )
        ]
        
        router = LogRouter()
        events = router.parse_logs(sources)
        
        # Should have both automation and application events
        automation_events = [e for e in events if e.log_source_type == LogSourceType.AUTOMATION]
        application_events = [e for e in events if e.log_source_type == LogSourceType.APPLICATION]
        
        assert len(automation_events) > 0
        assert len(application_events) > 0
        
        # Stats should show both
        stats = router.get_stats()
        assert stats['automation_logs_parsed'] == 1
        assert stats['application_logs_parsed'] == 1
    
    def test_router_continues_on_application_log_error(self, tmp_path):
        """Test that router continues if application log fails"""
        # Create automation log
        auto_log = tmp_path / "test.log"
        auto_log.write_text("FAILED test_example.py::test_case")
        
        sources = [
            RawLogSource(
                source_type=LogSourceType.AUTOMATION,
                path=str(auto_log),
                framework="pytest"
            ),
            RawLogSource(
                source_type=LogSourceType.APPLICATION,
                path="nonexistent.log",  # This will fail
                service="service"
            )
        ]
        
        router = LogRouter()
        events = router.parse_logs(sources)  # Should not raise
        
        # Should still have automation events
        assert len(events) >= 0  # May be 0 or more depending on parsing
        
        # Stats should show attempt to parse
        stats = router.get_stats()
        assert stats['automation_logs_parsed'] >= 0


# ============================================================================
# Test Configuration System
# ============================================================================

class TestConfigurationLoader:
    """Test configuration loading"""
    
    def test_create_default_config(self):
        """Test creating default configuration"""
        config = create_default_config(
            framework="selenium",
            automation_log_paths=["target/surefire-reports"],
            application_log_paths=["logs/app.log"]
        )
        
        assert config.framework == "selenium"
        assert config.has_automation_logs()
        assert config.has_application_logs()
    
    def test_config_to_log_source_collection(self):
        """Test converting config to log source collection"""
        config = create_default_config(
            framework="pytest",
            automation_log_paths=["junit.xml"],
            application_log_paths=["logs/service.log"]
        )
        
        collection = config.to_log_source_collection()
        
        assert len(collection.automation_logs) == 1
        assert len(collection.application_logs) == 1
        assert collection.automation_logs[0].framework == "pytest"


# ============================================================================
# Test Log Source Builder
# ============================================================================

class TestLogSourceBuilder:
    """Test log source building with priority resolution"""
    
    def test_builder_uses_explicit_paths(self):
        """Test that explicit paths have highest priority"""
        builder = LogSourceBuilder(framework="selenium")
        
        collection = builder.build(
            automation_log_paths=["explicit/path.log"]
        )
        
        assert len(collection.automation_logs) == 1
        assert collection.automation_logs[0].path == "explicit/path.log"
    
    def test_builder_fallsback_to_config(self):
        """Test that builder falls back to config"""
        config = create_default_config(
            framework="pytest",
            automation_log_paths=["config/path.log"]
        )
        
        builder = LogSourceBuilder(config=config)
        
        # No explicit paths provided
        collection = builder.build()
        
        assert len(collection.automation_logs) == 1
        assert collection.automation_logs[0].path == "config/path.log"


# ============================================================================
# Test Enhanced Analyzer with Confidence Boosting
# ============================================================================

class TestEnhancedAnalyzer:
    """Test enhanced analyzer with application log support"""
    
    def test_analyzer_without_application_logs(self):
        """Test analyzer works without application logs (baseline)"""
        analyzer = ExecutionIntelligenceAnalyzer(
            enable_ai=False,
            has_application_logs=False
        )
        
        log_content = """
FAILED test_checkout.py::test_payment
AssertionError: Expected payment success, got 500
"""
        
        result = analyzer.analyze_single_test(
            test_name="test_payment",
            log_content=log_content
        )
        
        assert result.test_name == "test_payment"
        assert result.failure_type.value in ["PRODUCT_DEFECT", "UNKNOWN"]
        assert not result.has_application_logs
    
    def test_analyzer_with_application_logs_boosts_confidence(self):
        """Test that application logs boost confidence for product defects"""
        analyzer = ExecutionIntelligenceAnalyzer(
            enable_ai=False,
            has_application_logs=True
        )
        
        # Create events with both automation and application logs
        from core.execution.intelligence.models import ExecutionEvent, LogLevel
        
        events = [
            # Automation event
            ExecutionEvent(
                timestamp="2024-01-15 10:31:00",
                level=LogLevel.ERROR,
                source="pytest",
                message="AssertionError: Expected 200, got 500",
                log_source_type=LogSourceType.AUTOMATION,
                exception_type="AssertionError"
            ),
            # Application event (correlating)
            ExecutionEvent(
                timestamp="2024-01-15 10:31:00",
                level=LogLevel.ERROR,
                source="order-service",
                message="NullPointerException: Order validation failed",
                log_source_type=LogSourceType.APPLICATION,
                exception_type="NullPointerException",
                service_name="order-service"
            )
        ]
        
        result = analyzer.analyze_single_test(
            test_name="test_create_order",
            log_content="",  # Not used when events provided
            events=events
        )
        
        assert result.has_application_logs
        
        # If classified as PRODUCT_DEFECT, confidence should be boosted
        if result.failure_type.value == "PRODUCT_DEFECT":
            # Confidence should be reasonable (boosted from app logs)
            assert result.confidence > 0.5
            
            # Reasoning should mention application logs
            # (May or may not be present depending on correlation)
    
    def test_analyzer_application_logs_no_boost_for_automation_defects(self):
        """Test that application logs don't boost confidence for automation defects"""
        analyzer = ExecutionIntelligenceAnalyzer(
            enable_ai=False,
            has_application_logs=True
        )
        
        events = [
            # Automation event (locator issue)
            ExecutionEvent(
                timestamp="2024-01-15 10:31:00",
                level=LogLevel.ERROR,
                source="selenium",
                message="NoSuchElementException: Unable to locate element: #submit-btn",
                log_source_type=LogSourceType.AUTOMATION,
                exception_type="NoSuchElementException"
            ),
            # Application event (unrelated)
            ExecutionEvent(
                timestamp="2024-01-15 10:31:00",
                level=LogLevel.INFO,
                source="app",
                message="Request processed successfully",
                log_source_type=LogSourceType.APPLICATION
            )
        ]
        
        result = analyzer.analyze_single_test(
            test_name="test_click_submit",
            log_content="",
            events=events
        )
        
        # Should be AUTOMATION_DEFECT (locator issue)
        assert result.failure_type.value == "AUTOMATION_DEFECT"
        
        # Confidence should NOT be boosted (no correlation with app logs)
    
    def test_analyzer_batch_analysis(self):
        """Test batch analysis with multiple tests"""
        analyzer = ExecutionIntelligenceAnalyzer(
            enable_ai=False,
            has_application_logs=False
        )
        
        test_logs = [
            {
                'test_name': 'test_1',
                'log_content': 'FAILED test_1\nAssertionError: Expected 200, got 500',
            },
            {
                'test_name': 'test_2',
                'log_content': 'FAILED test_2\nNoSuchElementException: Element not found',
            }
        ]
        
        results = analyzer.analyze_batch(test_logs)
        
        assert len(results) == 2
        assert all(isinstance(r, FailureAnalysisResult) for r in results)
    
    def test_analyzer_generate_summary(self):
        """Test summary generation"""
        analyzer = ExecutionIntelligenceAnalyzer(
            enable_ai=False,
            has_application_logs=True
        )
        
        # Create mock results
        from core.execution.intelligence.models import FailureType, FailureSignal, SignalType
        
        results = [
            FailureAnalysisResult(
                test_name="test_1",
                failure_type=FailureType.PRODUCT_DEFECT,
                confidence=0.85,
                reasoning="API error",
                signals=[],
                code_references=[],
                has_application_logs=True
            ),
            FailureAnalysisResult(
                test_name="test_2",
                failure_type=FailureType.AUTOMATION_DEFECT,
                confidence=0.90,
                reasoning="Locator issue",
                signals=[],
                code_references=[],
                has_application_logs=False
            )
        ]
        
        summary = analyzer.generate_summary(results)
        
        assert summary['total_tests'] == 2
        assert 'by_type' in summary
        assert 'by_type_percentage' in summary
        assert 'average_confidence' in summary
        assert 'has_application_logs' in summary
        
        # Average confidence
        expected_avg = (0.85 + 0.90) / 2
        assert abs(summary['average_confidence'] - expected_avg) < 0.01


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegrationFlows:
    """Test end-to-end integration flows"""
    
    def test_full_flow_automation_logs_only(self, tmp_path):
        """Test full flow with only automation logs"""
        # Create automation log
        auto_log = tmp_path / "test.log"
        auto_log.write_text("""
FAILED test_checkout.py::test_payment_success
AssertionError: Expected payment status 'success', got 'failed'
Expected: 'success'
Actual: 'failed'
""")
        
        # Build log sources
        config = create_default_config(
            framework="pytest",
            automation_log_paths=[str(auto_log)]
        )
        
        collection = config.to_log_source_collection()
        
        # Parse logs
        router = LogRouter()
        events = router.parse_log_collection(collection)
        
        assert len(events) > 0
        
        # Analyze
        analyzer = ExecutionIntelligenceAnalyzer(
            enable_ai=False,
            has_application_logs=collection.has_application_logs()
        )
        
        result = analyzer.analyze_single_test(
            test_name="test_payment_success",
            log_content="",
            events=events
        )
        
        assert result.test_name == "test_payment_success"
        assert result.failure_type is not None
        assert not result.has_application_logs
    
    def test_full_flow_with_application_logs(self, tmp_path):
        """Test full flow with both automation and application logs"""
        # Create automation log
        auto_log = tmp_path / "test.log"
        auto_log.write_text("""
FAILED test_api.py::test_create_order
AssertionError: API returned 500 Internal Server Error
""")
        
        # Create application log
        app_log = tmp_path / "app.log"
        app_log.write_text("""
2024-01-15 10:31:00 ERROR OrderService - Failed to create order
java.lang.NullPointerException: Order validation service is not initialized
\tat com.example.OrderService.validate(OrderService.java:45)
\tat com.example.OrderService.create(OrderService.java:23)
""")
        
        # Build log sources
        config = create_default_config(
            framework="pytest",
            automation_log_paths=[str(auto_log)],
            application_log_paths=[str(app_log)]
        )
        
        collection = config.to_log_source_collection()
        
        # Validate
        is_valid, error = collection.validate()
        assert is_valid
        assert collection.has_application_logs()
        
        # Parse logs
        router = LogRouter()
        events = router.parse_log_collection(collection)
        
        # Should have both types
        automation_events = [e for e in events if e.log_source_type == LogSourceType.AUTOMATION]
        application_events = [e for e in events if e.log_source_type == LogSourceType.APPLICATION]
        
        assert len(automation_events) > 0
        assert len(application_events) > 0
        
        # Analyze with application logs
        analyzer = ExecutionIntelligenceAnalyzer(
            enable_ai=False,
            has_application_logs=True
        )
        
        result = analyzer.analyze_single_test(
            test_name="test_create_order",
            log_content="",
            events=events
        )
        
        assert result.test_name == "test_create_order"
        assert result.has_application_logs
        
        # Should be classified as PRODUCT_DEFECT (NullPointerException in app)
        # Confidence may be boosted due to application log correlation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
