"""
Unit Tests for Correlation Engine

Tests correlation of TestNG failures with framework logs.
"""

import pytest
from pathlib import Path

from core.log_analysis.ingestion import (
    CorrelationEngine,
    CorrelatedFailure,
    StructuredFailure,
    FailureCategory
)
from core.log_analysis.ingestion.framework_log_parser import (
    FrameworkLogParser,
    FrameworkLogEntry
)


class TestCorrelationEngine:
    """Test failure correlation functionality"""
    
    @pytest.fixture
    def sample_failures(self):
        """Create sample structured failures"""
        return [
            StructuredFailure(
                test_name="com.example.LoginTest.testValidLogin",
                class_name="com.example.LoginTest",
                method_name="testValidLogin",
                status="PASS",
                duration_ms=1000
            ),
            StructuredFailure(
                test_name="com.example.DatabaseTest.testConnection",
                class_name="com.example.DatabaseTest",
                method_name="testConnection",
                status="FAIL",
                failure_type="java.sql.SQLException",
                error_message="Connection failed",
                stack_trace="at DatabaseTest.testConnection(DatabaseTest.java:45)",
                duration_ms=500,
                category=FailureCategory.INFRASTRUCTURE
            ),
            StructuredFailure(
                test_name="com.example.UITest.testButton",
                class_name="com.example.UITest",
                method_name="testButton",
                status="FAIL",
                failure_type="java.lang.AssertionError",
                error_message="Button not visible",
                duration_ms=2000,
                category=FailureCategory.TEST_ASSERTION
            ),
        ]
    
    @pytest.fixture
    def sample_framework_errors(self):
        """Create sample framework log entries"""
        return [
            FrameworkLogEntry(
                timestamp="2024-01-15 10:00:00",
                level="ERROR",
                logger_name="com.example.DatabaseTest",
                message="Database connection pool exhausted",
                exception="java.sql.SQLException: Cannot get connection"
            ),
            FrameworkLogEntry(
                timestamp="2024-01-15 10:00:05",
                level="ERROR",
                logger_name="org.openqa.selenium.WebDriver",
                message="Session not created",
                exception="SessionNotCreatedException: Unable to create session"
            ),
            FrameworkLogEntry(
                timestamp="2024-01-15 10:00:10",
                level="WARN",
                logger_name="com.example.UITest",
                message="Element lookup took longer than expected"
            ),
        ]
    
    def test_correlate_without_framework_logs(self, sample_failures):
        """Test correlation without framework logs"""
        engine = CorrelationEngine()
        correlated = engine.correlate(sample_failures, None)
        
        # Should return correlated failures (minus passed tests)
        assert len(correlated) == 2  # Only failed tests
        
        # Check that all have low confidence without logs
        for failure in correlated:
            assert failure.correlation_confidence <= 0.6
            assert not failure.has_logs()
    
    def test_correlate_with_framework_logs(self, sample_failures):
        """Test correlation with framework logs"""
        # Create parser with errors
        parser = FrameworkLogParser()
        parser.error_entries = [
            FrameworkLogEntry(
                timestamp="2024-01-15 10:00:00",
                level="ERROR",
                logger_name="com.example.DatabaseTest",
                message="Connection failed",
                exception="SQLException"
            )
        ]
        
        engine = CorrelationEngine()
        correlated = engine.correlate(sample_failures, parser)
        
        # Should correlate DatabaseTest failure with log
        db_failure = [
            c for c in correlated 
            if "DatabaseTest" in c.structured_failure.test_name
        ][0]
        
        assert db_failure.has_logs()
        assert len(db_failure.framework_errors) > 0
        assert db_failure.correlation_confidence > 0.5
    
    def test_infra_failure_detection(self, sample_failures):
        """Test infrastructure failure detection"""
        parser = FrameworkLogParser()
        parser.error_entries = [
            FrameworkLogEntry(
                timestamp="2024-01-15 10:00:00",
                level="ERROR",
                logger_name="com.example.DatabaseTest",
                message="Connection timeout occurred",
                exception="TimeoutException"
            )
        ]
        
        engine = CorrelationEngine()
        correlated = engine.correlate(sample_failures, parser)
        
        infra_failures = engine.get_infra_failures()
        assert len(infra_failures) > 0
    
    def test_test_assertion_failures(self, sample_failures):
        """Test test assertion failure extraction"""
        engine = CorrelationEngine()
        engine.correlate(sample_failures, None)
        
        test_failures = engine.get_test_failures()
        assert len(test_failures) == 1
        
        failure = test_failures[0]
        assert failure.category == FailureCategory.TEST_ASSERTION
    
    def test_correlation_summary(self, sample_failures):
        """Test correlation summary generation"""
        parser = FrameworkLogParser()
        parser.error_entries = [
            FrameworkLogEntry(
                timestamp="2024-01-15 10:00:00",
                level="ERROR",
                logger_name="com.example.DatabaseTest",
                message="Error",
                exception="Exception"
            )
        ]
        
        engine = CorrelationEngine()
        engine.correlate(sample_failures, parser)
        
        summary = engine.get_summary()
        assert summary['total_failures'] == 2
        assert 'with_logs' in summary
        assert 'infra_related' in summary
        assert 'avg_confidence' in summary
        assert 0.0 <= summary['avg_confidence'] <= 1.0
    
    def test_root_cause_extraction_from_logs(self):
        """Test root cause extraction prioritizes framework logs"""
        failure = StructuredFailure(
            test_name="test",
            class_name="TestClass",
            error_message="Test failed"
        )
        
        log_entry = FrameworkLogEntry(
            timestamp="2024-01-15 10:00:00",
            level="ERROR",
            logger_name="TestClass",
            message="Database connection failed",
            exception="SQLException: Cannot connect"
        )
        
        engine = CorrelationEngine()
        root_cause = engine._extract_root_cause(failure, [log_entry])
        
        assert "Database connection failed" in root_cause
        assert "SQLException" in root_cause
    
    def test_root_cause_extraction_from_failure(self):
        """Test root cause extraction falls back to failure"""
        failure = StructuredFailure(
            test_name="test",
            class_name="TestClass",
            error_message="Assertion failed: expected true"
        )
        
        engine = CorrelationEngine()
        root_cause = engine._extract_root_cause(failure, [])
        
        assert "Assertion failed" in root_cause
    
    def test_confidence_score_calculation(self):
        """Test confidence score calculation"""
        failure = StructuredFailure(
            test_name="com.example.Test.testMethod",
            class_name="com.example.Test",
            method_name="testMethod",
            failure_type="AssertionError"
        )
        
        # Matching framework error
        matching_error = FrameworkLogEntry(
            timestamp="2024-01-15 10:00:00",
            level="ERROR",
            logger_name="com.example.Test",
            message="Test failed",
            exception="AssertionError: values differ"
        )
        
        engine = CorrelationEngine()
        confidence = engine._calculate_confidence(failure, [matching_error])
        
        # High confidence with matching class and exception
        assert confidence >= 0.8
    
    def test_confidence_score_no_logs(self):
        """Test confidence score with no framework logs"""
        failure = StructuredFailure(
            test_name="test",
            class_name="TestClass"
        )
        
        engine = CorrelationEngine()
        confidence = engine._calculate_confidence(failure, [])
        
        # Low confidence without logs
        assert confidence == 0.5
    
    def test_skip_passed_tests(self, sample_failures):
        """Test that passed tests are not correlated"""
        engine = CorrelationEngine()
        correlated = engine.correlate(sample_failures, None)
        
        # Should only have failed tests
        assert all(
            c.structured_failure.is_failed() 
            for c in correlated
        )
        
        # Passed test should be excluded
        assert len(correlated) < len(sample_failures)
    
    def test_refine_category_from_logs(self):
        """Test category refinement based on logs"""
        failure = StructuredFailure(
            test_name="test",
            class_name="TestClass",
            category=FailureCategory.UNKNOWN
        )
        
        infra_log = FrameworkLogEntry(
            timestamp="2024-01-15 10:00:00",
            level="ERROR",
            logger_name="TestClass",
            message="Connection timeout occurred"
        )
        
        engine = CorrelationEngine()
        refined = engine._refine_category(failure, [infra_log])
        
        assert refined == FailureCategory.INFRASTRUCTURE
    
    def test_combined_context_generation(self):
        """Test combined context generation"""
        failure = StructuredFailure(
            test_name="test",
            class_name="TestClass",
            error_message="Test assertion failed"
        )
        
        log_error = FrameworkLogEntry(
            timestamp="2024-01-15 10:00:00",
            level="ERROR",
            logger_name="TestClass",
            message="Database error occurred"
        )
        
        log_warning = FrameworkLogEntry(
            timestamp="2024-01-15 10:00:00",
            level="WARN",
            logger_name="TestClass",
            message="Slow query detected"
        )
        
        correlated = CorrelatedFailure(
            structured_failure=failure,
            framework_errors=[log_error],
            framework_warnings=[log_warning]
        )
        
        context = correlated.get_combined_context()
        
        assert "Test assertion failed" in context
        assert "Database error occurred" in context
        assert "Slow query detected" in context
        assert "Framework Errors" in context
        assert "Framework Warnings" in context
