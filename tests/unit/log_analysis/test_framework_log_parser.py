"""
Unit Tests for Framework Log Parser

Tests parsing of log4j/slf4j/logback framework logs.
"""

import pytest
from pathlib import Path
from textwrap import dedent

from core.log_analysis.ingestion.framework_log_parser import (
    FrameworkLogParser,
    FrameworkLogEntry
)


class TestFrameworkLogParser:
    """Test framework log parsing functionality"""
    
    @pytest.fixture
    def sample_log_file(self, tmp_path):
        """Create a sample framework log file"""
        log_content = dedent('''
            2024-01-15 10:00:00,123 INFO [com.example.TestRunner] - Starting test execution
            2024-01-15 10:00:05,456 ERROR [com.example.DatabaseTest] - Connection failed
            java.sql.SQLException: Connection refused
                at java.sql.DriverManager.getConnection(DriverManager.java:664)
                at com.example.DatabaseTest.setup(DatabaseTest.java:23)
            2024-01-15 10:00:10,789 WARN [com.example.LoginTest] - Slow response detected
            2024-01-15 10:00:15,012 ERROR [org.openqa.selenium.WebDriver] - Session not created
            org.openqa.selenium.SessionNotCreatedException: Could not start session
                at org.openqa.selenium.remote.ProtocolHandshake.createSession
            2024-01-15 10:00:20,345 INFO [com.example.TestRunner] - Test execution completed
        ''').strip()
        
        log_file = tmp_path / "framework.log"
        log_file.write_text(log_content)
        return log_file
    
    def test_parse_basic_structure(self, sample_log_file):
        """Test parsing basic log structure"""
        parser = FrameworkLogParser()
        entries = parser.parse(sample_log_file)
        
        # Should parse all log entries
        assert len(entries) == 6
        
        # Check summary
        summary = parser.get_summary()
        assert summary['total_entries'] == 6
        assert summary['error_count'] == 2
        assert summary['warning_count'] == 1
    
    def test_parse_error_entry(self, sample_log_file):
        """Test parsing ERROR level entries"""
        parser = FrameworkLogParser()
        parser.parse(sample_log_file)
        
        errors = parser.get_errors()
        assert len(errors) == 2
        
        first_error = errors[0]
        assert first_error.level == 'ERROR'
        assert first_error.logger_name == 'com.example.DatabaseTest'
        assert first_error.message == 'Connection failed'
        assert first_error.exception is not None
        assert 'SQLException' in first_error.exception
        assert 'DatabaseTest.java:23' in first_error.exception
    
    def test_parse_warning_entry(self, sample_log_file):
        """Test parsing WARN level entries"""
        parser = FrameworkLogParser()
        parser.parse(sample_log_file)
        
        warnings = parser.get_warnings()
        assert len(warnings) == 1
        
        warning = warnings[0]
        assert warning.level == 'WARN'
        assert warning.logger_name == 'com.example.LoginTest'
        assert warning.message == 'Slow response detected'
    
    def test_parse_multiline_exception(self, sample_log_file):
        """Test parsing multi-line stack traces"""
        parser = FrameworkLogParser()
        parser.parse(sample_log_file)
        
        errors = parser.get_errors()
        selenium_error = [
            e for e in errors 
            if 'WebDriver' in e.logger_name
        ][0]
        
        assert selenium_error.exception is not None
        assert 'SessionNotCreatedException' in selenium_error.exception
        assert 'ProtocolHandshake' in selenium_error.exception
    
    def test_infra_error_detection(self, sample_log_file):
        """Test infrastructure error detection"""
        parser = FrameworkLogParser()
        parser.parse(sample_log_file)
        
        infra_errors = parser.get_infra_errors()
        assert len(infra_errors) == 1
        
        # Session not created is infra-related
        assert 'session' in infra_errors[0].message.lower()
    
    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing nonexistent file"""
        parser = FrameworkLogParser()
        nonexistent = tmp_path / "does-not-exist.log"
        
        entries = parser.parse(nonexistent)
        assert len(entries) == 0
    
    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty file"""
        empty_file = tmp_path / "empty.log"
        empty_file.write_text("")
        
        parser = FrameworkLogParser()
        entries = parser.parse(empty_file)
        
        assert len(entries) == 0
    
    def test_alternative_log_format(self, tmp_path):
        """Test parsing alternative log format"""
        log_content = dedent('''
            [ERROR] 2024-01-15 10:00:00 com.example.Test - Error occurred
            ERROR [main] 2024-01-15 10:00:01 com.example.Test2 - Another error
        ''').strip()
        
        log_file = tmp_path / "alt-format.log"
        log_file.write_text(log_content)
        
        parser = FrameworkLogParser()
        entries = parser.parse(log_file)
        
        assert len(entries) == 2
        assert all(e.level == 'ERROR' for e in entries)
    
    def test_infra_patterns_connection(self, tmp_path):
        """Test infrastructure pattern detection - connection issues"""
        log_content = dedent('''
            2024-01-15 10:00:00,000 ERROR [Test] - Connection reset by peer
            2024-01-15 10:00:01,000 ERROR [Test] - Connection refused
            2024-01-15 10:00:02,000 ERROR [Test] - Connection timeout occurred
        ''').strip()
        
        log_file = tmp_path / "conn-errors.log"
        log_file.write_text(log_content)
        
        parser = FrameworkLogParser()
        parser.parse(log_file)
        
        infra_errors = parser.get_infra_errors()
        assert len(infra_errors) == 3
    
    def test_infra_patterns_webdriver(self, tmp_path):
        """Test infrastructure pattern detection - WebDriver issues"""
        log_content = dedent('''
            2024-01-15 10:00:00,000 ERROR [Test] - WebDriver exception occurred
            2024-01-15 10:00:01,000 ERROR [Test] - Session not created
            2024-01-15 10:00:02,000 ERROR [Test] - No such session: invalid session id
        ''').strip()
        
        log_file = tmp_path / "webdriver-errors.log"
        log_file.write_text(log_content)
        
        parser = FrameworkLogParser()
        parser.parse(log_file)
        
        infra_errors = parser.get_infra_errors()
        assert len(infra_errors) == 3
    
    def test_log_entry_repr(self):
        """Test log entry string representation"""
        entry = FrameworkLogEntry(
            timestamp="2024-01-15 10:00:00",
            level="ERROR",
            logger_name="com.example.Test",
            message="This is a long error message that should be truncated in repr",
            line_number=42
        )
        
        repr_str = repr(entry)
        assert "ERROR" in repr_str
        assert "2024-01-15" in repr_str
        assert len(repr_str) < 200  # Should be truncated


class TestFrameworkLogEntry:
    """Test FrameworkLogEntry class"""
    
    def test_basic_entry_creation(self):
        """Test creating basic log entry"""
        entry = FrameworkLogEntry(
            timestamp="2024-01-15 10:00:00,123",
            level="ERROR",
            logger_name="com.example.Test",
            message="Test error message",
            line_number=10
        )
        
        assert entry.timestamp == "2024-01-15 10:00:00,123"
        assert entry.level == "ERROR"
        assert entry.logger_name == "com.example.Test"
        assert entry.message == "Test error message"
        assert entry.exception is None
        assert entry.line_number == 10
    
    def test_entry_with_exception(self):
        """Test entry with exception stack trace"""
        entry = FrameworkLogEntry(
            timestamp="2024-01-15 10:00:00",
            level="ERROR",
            logger_name="com.example.Test",
            message="Error occurred",
            exception="java.lang.Exception: Stack trace\n\tat Method(File.java:10)"
        )
        
        assert entry.exception is not None
        assert "Stack trace" in entry.exception
