"""
Comprehensive Unit Tests for JSON Structured Log Adapter

Tests all functionality with and without AI.
Covers multiple frameworks and log formats.
"""

import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, List

from core.execution.intelligence.log_adapters.json_adapter import JSONLogAdapter
from core.execution.intelligence.log_adapters.schema import (
    NormalizedLogEvent,
    LogLevel as SchemaLogLevel,
    ExtractedSignals
)
from core.execution.intelligence.log_adapters.correlation import LogCorrelator, CorrelationResult
from core.execution.intelligence.log_adapters.sampling import (
    LogSampler,
    SamplingConfig,
    AdaptiveSampler
)
from core.execution.intelligence.models import ExecutionEvent, LogLevel


class TestJSONLogAdapter:
    """Test JSON log adapter functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.adapter = JSONLogAdapter()
    
    def test_can_handle_json_files(self):
        """Test adapter recognizes JSON log files."""
        assert self.adapter.can_handle('app.log.json')
        assert self.adapter.can_handle('service.jsonl')
        assert self.adapter.can_handle('json')
        assert self.adapter.can_handle('elk')
        assert self.adapter.can_handle('fluentd')
        assert not self.adapter.can_handle('plain.txt')
        assert not self.adapter.can_handle('app.log')
    
    def test_parse_valid_json_log(self):
        """Test parsing valid JSON log."""
        log_line = json.dumps({
            'timestamp': '2024-01-30T10:30:00Z',
            'level': 'ERROR',
            'message': 'Database connection failed',
            'service': 'payment-api',
            'error_type': 'ConnectionException'
        })
        
        result = self.adapter.parse(log_line)
        
        assert result is not None
        assert result['level'] == 'ERROR'
        assert result['message'] == 'Database connection failed'
        assert result['service'] == 'payment-api'
        assert result['error_type'] == 'ConnectionException'
    
    def test_parse_invalid_json(self):
        """Test handling of invalid JSON."""
        result = self.adapter.parse('not valid json {')
        assert result is None
    
    def test_parse_empty_line(self):
        """Test handling of empty lines."""
        assert self.adapter.parse('') is None
        assert self.adapter.parse('   ') is None
    
    def test_timestamp_parsing_iso_format(self):
        """Test ISO timestamp parsing."""
        log_line = json.dumps({
            'timestamp': '2024-01-30T10:30:00Z',
            'level': 'INFO',
            'message': 'Test'
        })
        
        result = self.adapter.parse(log_line)
        assert result is not None
        assert isinstance(result['timestamp'], str)
    
    def test_timestamp_parsing_unix_seconds(self):
        """Test Unix timestamp parsing (seconds)."""
        log_line = json.dumps({
            'timestamp': 1706609400,  # Unix seconds
            'level': 'INFO',
            'message': 'Test'
        })
        
        result = self.adapter.parse(log_line)
        assert result is not None
    
    def test_timestamp_parsing_unix_milliseconds(self):
        """Test Unix timestamp parsing (milliseconds)."""
        log_line = json.dumps({
            'timestamp': 1706609400000,  # Unix milliseconds
            'level': 'INFO',
            'message': 'Test'
        })
        
        result = self.adapter.parse(log_line)
        assert result is not None
    
    def test_log_level_normalization(self):
        """Test log level normalization."""
        test_cases = [
            ('ERROR', SchemaLogLevel.ERROR),
            ('error', SchemaLogLevel.ERROR),
            ('WARN', SchemaLogLevel.WARN),
            ('WARNING', SchemaLogLevel.WARN),
            ('INFO', SchemaLogLevel.INFO),
            ('INFORMATION', SchemaLogLevel.INFO),
            ('DEBUG', SchemaLogLevel.DEBUG),
            ('FATAL', SchemaLogLevel.FATAL),
            ('CRITICAL', SchemaLogLevel.FATAL),
        ]
        
        for input_level, expected_level in test_cases:
            log_line = json.dumps({'level': input_level, 'message': 'Test'})
            result = self.adapter.parse(log_line)
            assert result['level'] == expected_level.value
    
    def test_extract_error_type_from_exception_field(self):
        """Test error type extraction from exception field."""
        log_line = json.dumps({
            'level': 'ERROR',
            'message': 'Error occurred',
            'exception': {
                'type': 'NullPointerException',
                'stack': 'at line 123'
            }
        })
        
        result = self.adapter.parse(log_line)
        assert result['error_type'] == 'NullPointerException'
    
    def test_extract_error_type_from_message(self):
        """Test error type extraction from message."""
        log_line = json.dumps({
            'level': 'ERROR',
            'message': 'java.sql.SQLException: Connection timeout'
        })
        
        result = self.adapter.parse(log_line)
        assert 'Exception' in result['error_type']
    
    def test_extract_trace_id(self):
        """Test distributed trace ID extraction."""
        log_line = json.dumps({
            'level': 'INFO',
            'message': 'Request processed',
            'trace_id': 'abc-123-def-456',
            'span_id': 'span-789'
        })
        
        result = self.adapter.parse(log_line)
        assert result['trace_id'] == 'abc-123-def-456'
        assert result['span_id'] == 'span-789'
    
    def test_extract_infrastructure_fields(self):
        """Test extraction of host, container, pod info."""
        log_line = json.dumps({
            'level': 'INFO',
            'message': 'Service started',
            'host': 'server-01',
            'container_id': 'docker-abc123',
            'pod_name': 'app-pod-1'
        })
        
        result = self.adapter.parse(log_line)
        assert result['host'] == 'server-01'
        assert result['container_id'] == 'docker-abc123'
        assert result['pod_name'] == 'app-pod-1'
    
    def test_extract_performance_metrics(self):
        """Test extraction of duration and response code."""
        log_line = json.dumps({
            'level': 'INFO',
            'message': 'Request completed',
            'duration_ms': 1523.5,
            'response_code': 200
        })
        
        result = self.adapter.parse(log_line)
        assert result['duration_ms'] == 1523.5
        assert result['response_code'] == 200
    
    def test_raw_payload_preserved(self):
        """Test that raw log payload is never lost."""
        original_data = {
            'timestamp': '2024-01-30T10:30:00Z',
            'level': 'INFO',
            'message': 'Test',
            'custom_field': 'custom_value',
            'nested': {'key': 'value'}
        }
        
        log_line = json.dumps(original_data)
        result = self.adapter.parse(log_line)
        
        assert result['raw'] == original_data
    
    def test_extract_signals_error_indicators(self):
        """Test signal extraction for error indicators."""
        log_event = {
            'level': 'ERROR',
            'message': 'connection timeout occurred, retrying...',
            'error_type': 'TimeoutException'
        }
        
        signals = self.adapter.extract_signals(log_event)
        
        assert signals['is_error'] is True
        assert signals['is_timeout'] is True
        assert signals['is_retry'] is True
        assert signals['error_type'] == 'TimeoutException'
    
    def test_extract_signals_performance(self):
        """Test signal extraction for performance metrics."""
        log_event = {
            'level': 'WARN',
            'message': 'Slow query detected',
            'duration_ms': 6000.0  # 6 seconds
        }
        
        signals = self.adapter.extract_signals(log_event)
        
        assert signals['is_slow'] is True
        assert signals['duration_ms'] == 6000.0
    
    def test_extract_signals_circuit_breaker(self):
        """Test signal extraction for circuit breaker events."""
        log_event = {
            'level': 'WARN',
            'message': 'circuit breaker opened due to high error rate'
        }
        
        signals = self.adapter.extract_signals(log_event)
        
        assert signals['is_circuit_breaker'] is True
    
    def test_error_categorization(self):
        """Test automatic error categorization."""
        test_cases = [
            ('connection timeout', 'network'),
            ('database error', 'database'),
            ('SQL exception', 'database'),
            ('authentication failed', 'auth'),
            ('permission denied', 'auth'),
            ('null pointer exception', 'null_reference'),
        ]
        
        for message, expected_category in test_cases:
            log_event = {'level': 'ERROR', 'message': message}
            signals = self.adapter.extract_signals(log_event)
            assert signals['error_category'] == expected_category
    
    def test_elk_format_compatibility(self):
        """Test compatibility with ELK/Elasticsearch log format."""
        elk_log = json.dumps({
            '@timestamp': '2024-01-30T10:30:00.000Z',
            'severity': 'ERROR',
            'msg': 'Service unavailable',
            'app': 'auth-service',
            'logger_name': 'com.example.AuthController'
        })
        
        result = self.adapter.parse(elk_log)
        
        assert result is not None
        assert result['level'] == 'ERROR'
        assert result['message'] == 'Service unavailable'
        assert result['service'] == 'auth-service'
        assert result['component'] == 'com.example.AuthController'
    
    def test_fluentd_format_compatibility(self):
        """Test compatibility with Fluentd log format."""
        fluentd_log = json.dumps({
            'time': 1706609400,
            'level': 'warn',
            'msg': 'High memory usage',
            'app_name': 'worker-service'
        })
        
        result = self.adapter.parse(fluentd_log)
        
        assert result is not None
        assert result['level'] == 'WARN'
        assert result['message'] == 'High memory usage'
    
    def test_custom_field_mapping(self):
        """Test custom field mapping configuration."""
        custom_config = {
            'timestamp_fields': ['event_time', 'timestamp'],
            'level_fields': ['log_level', 'level'],
            'message_fields': ['log_message', 'message']
        }
        
        adapter = JSONLogAdapter(config=custom_config)
        
        log_line = json.dumps({
            'event_time': '2024-01-30T10:30:00Z',
            'log_level': 'ERROR',
            'log_message': 'Custom format test'
        })
        
        result = adapter.parse(log_line)
        
        assert result is not None
        assert result['level'] == 'ERROR'
        assert result['message'] == 'Custom format test'


class TestLogCorrelation:
    """Test log correlation functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.correlator = LogCorrelator(timestamp_window_seconds=5)
    
    def test_correlate_by_trace_id(self):
        """Test correlation by trace ID (best method)."""
        test_event = ExecutionEvent(
            timestamp='2024-01-30T10:30:00Z',
            level=LogLevel.ERROR,
            source='test',
            message='Test failed',
            metadata={'trace_id': 'trace-123'}
        )
        test_event.trace_id = 'trace-123'  # Set as attribute
        
        app_logs = [
            {'trace_id': 'trace-123', 'message': 'Database error'},
            {'trace_id': 'trace-456', 'message': 'Other event'},
            {'trace_id': 'trace-123', 'message': 'Connection failed'}
        ]
        
        result = self.correlator.correlate(test_event, app_logs)
        
        assert len(result.correlated_logs) == 2
        assert result.correlation_method == 'trace_id'
        assert result.correlation_confidence == 1.0
    
    def test_correlate_by_timestamp_window(self):
        """Test correlation by timestamp window."""
        test_time = datetime(2024, 1, 30, 10, 30, 0)
        test_event = ExecutionEvent(
            timestamp=test_time.isoformat(),
            level=LogLevel.ERROR,
            source='test',
            message='Test failed'
        )
        
        app_logs = [
            {'timestamp': (test_time + timedelta(seconds=2)).isoformat(), 'message': 'Within window'},
            {'timestamp': (test_time + timedelta(seconds=10)).isoformat(), 'message': 'Outside window'},
        ]
        
        result = self.correlator.correlate(test_event, app_logs)
        
        assert len(result.correlated_logs) == 1
        assert result.correlation_method == 'timestamp'
        assert result.correlation_confidence == 0.7
    
    def test_correlate_by_service(self):
        """Test correlation by service name."""
        test_event = ExecutionEvent(
            timestamp='2024-01-30T10:30:00Z',
            level=LogLevel.ERROR,
            source='test',
            message='Test failed',
            service_name='payment-service'
        )
        
        app_logs = [
            {'service': 'payment-service', 'message': 'Payment processed'},
            {'service': 'user-service', 'message': 'User logged in'},
        ]
        
        result = self.correlator.correlate(test_event, app_logs)
        
        assert len(result.correlated_logs) == 1
        assert result.correlation_method == 'service'
    
    def test_correlate_batch(self):
        """Test batch correlation."""
        test_events = [
            ExecutionEvent(
                timestamp='2024-01-30T10:30:00Z',
                level=LogLevel.ERROR,
                source='test1',
                message='Test 1',
                metadata={'trace_id': 'trace-1'}
            ),
            ExecutionEvent(
                timestamp='2024-01-30T10:31:00Z',
                level=LogLevel.ERROR,
                source='test2',
                message='Test 2',
                metadata={'trace_id': 'trace-2'}
            )
        ]
        test_events[0].trace_id = 'trace-1'
        test_events[1].trace_id = 'trace-2'
        
        app_logs = [
            {'trace_id': 'trace-1', 'message': 'Error for test 1'},
            {'trace_id': 'trace-2', 'message': 'Error for test 2'}
        ]
        
        results = self.correlator.correlate_batch(test_events, app_logs)
        
        assert len(results) == 2
        assert all(len(r.correlated_logs) > 0 for r in results)
    
    def test_correlation_stats(self):
        """Test correlation statistics calculation."""
        results = [
            CorrelationResult(
                test_event=None,
                correlated_logs=[{}, {}],
                correlation_method='trace_id',
                correlation_confidence=1.0
            ),
            CorrelationResult(
                test_event=None,
                correlated_logs=[],
                correlation_method='none',
                correlation_confidence=0.0
            ),
        ]
        
        stats = self.correlator.get_correlation_stats(results)
        
        assert stats['total_events'] == 2
        assert stats['correlated_count'] == 1
        assert stats['correlation_rate'] == 0.5
        assert 'trace_id' in stats['method_distribution']


class TestLogSampling:
    """Test log sampling functionality."""
    
    def test_sampling_by_level(self):
        """Test level-based sampling rates."""
        config = SamplingConfig(
            debug_rate=0.0,   # 0% DEBUG
            info_rate=0.0,    # 0% INFO
            warn_rate=1.0,    # 100% WARN
            error_rate=1.0,   # 100% ERROR
        )
        
        sampler = LogSampler(config)
        
        # Test multiple events to account for randomness
        debug_sampled = sum(
            1 for _ in range(100)
            if sampler.should_sample({'level': 'DEBUG', 'message': 'test'})
        )
        
        warn_sampled = sum(
            1 for _ in range(100)
            if sampler.should_sample({'level': 'WARN', 'message': 'test'})
        )
        
        error_sampled = sum(
            1 for _ in range(100)
            if sampler.should_sample({'level': 'ERROR', 'message': 'test'})
        )
        
        assert debug_sampled == 0
        assert warn_sampled == 100
        assert error_sampled == 100
    
    def test_rate_limiting(self):
        """Test rate limiting enforcement."""
        config = SamplingConfig(
            info_rate=1.0,  # 100% sampling
            max_events_per_second=10
        )
        
        sampler = LogSampler(config)
        
        # Try to sample 20 events (only 10 should pass)
        sampled_count = sum(
            1 for _ in range(20)
            if sampler.should_sample({'level': 'INFO', 'message': 'test'})
        )
        
        assert sampled_count == 10
    
    def test_always_sample_patterns(self):
        """Test whitelist pattern sampling."""
        config = SamplingConfig(
            info_rate=0.0,  # 0% INFO normally
            always_sample_patterns=['critical', 'important']
        )
        
        sampler = LogSampler(config)
        
        # Should sample even though INFO rate is 0%
        assert sampler.should_sample({
            'level': 'INFO',
            'message': 'Critical system event'
        })
        
        # Should not sample
        assert not sampler.should_sample({
            'level': 'INFO',
            'message': 'Regular event'
        })
    
    def test_never_sample_patterns(self):
        """Test blacklist pattern sampling."""
        config = SamplingConfig(
            info_rate=1.0,  # 100% INFO normally
            never_sample_patterns=['noisy', 'spam']
        )
        
        sampler = LogSampler(config)
        
        # Should not sample even though INFO rate is 100%
        assert not sampler.should_sample({
            'level': 'INFO',
            'message': 'Noisy debug event'
        })
        
        # Should sample
        assert sampler.should_sample({
            'level': 'INFO',
            'message': 'Important event'
        })
    
    def test_sampling_statistics(self):
        """Test sampling statistics tracking."""
        config = SamplingConfig(error_rate=1.0, info_rate=0.5)
        sampler = LogSampler(config)
        
        # Sample some events
        for _ in range(10):
            sampler.should_sample({'level': 'ERROR', 'message': 'test'})
        
        for _ in range(10):
            sampler.should_sample({'level': 'INFO', 'message': 'test'})
        
        stats = sampler.get_statistics()
        
        assert stats['total_events'] == 20
        assert stats['by_level']['ERROR']['total'] == 10
        assert stats['by_level']['INFO']['total'] == 10
        assert stats['by_level']['ERROR']['sampled'] == 10  # 100% sampled
    
    def test_adaptive_sampling(self):
        """Test adaptive sampling under high load."""
        config = SamplingConfig(
            info_rate=1.0,
            max_events_per_second=100
        )
        
        sampler = AdaptiveSampler(config, adaptation_window=1)
        
        # Generate high load
        for _ in range(200):
            sampler.should_sample({'level': 'INFO', 'message': 'test'})
        
        # Adaptation factor should be reduced
        assert sampler._adaptation_factor < 1.0


class TestFrameworkCompatibility:
    """Test compatibility with all supported frameworks."""
    
    def test_rest_assured_java_logs(self):
        """Test compatibility with Rest Assured (Java) logs."""
        log_line = json.dumps({
            '@timestamp': '2024-01-30T10:30:00.123Z',
            'level': 'ERROR',
            'logger': 'io.restassured.RestAssured',
            'message': 'Expected status code <200> but was <500>',
            'thread': 'main',
            'class': 'com.example.ApiTest'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert result['level'] == 'ERROR'
        assert '500' in result['message']
    
    def test_cypress_logs(self):
        """Test compatibility with Cypress logs."""
        log_line = json.dumps({
            'timestamp': 1706609400000,
            'level': 'error',
            'message': 'CypressError: Timed out retrying',
            'name': 'login_test',
            'specFile': 'cypress/integration/auth.spec.js'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert result['level'] == 'ERROR'
        assert 'Timed out' in result['message']
    
    def test_playwright_logs(self):
        """Test compatibility with Playwright logs."""
        log_line = json.dumps({
            'time': '2024-01-30T10:30:00.000Z',
            'severity': 'error',
            'msg': 'page.click: Timeout 30000ms exceeded',
            'test': 'user login flow'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert 'Timeout' in result['message']
    
    def test_pytest_bdd_logs(self):
        """Test compatibility with Pytest BDD logs."""
        log_line = json.dumps({
            'timestamp': '2024-01-30 10:30:00',
            'level': 'ERROR',
            'message': 'AssertionError: Expected True but got False',
            'test': 'test_user_login',
            'feature': 'Authentication'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert 'AssertionError' in result['message']
    
    def test_robot_framework_logs(self):
        """Test compatibility with Robot Framework logs."""
        log_line = json.dumps({
            '@timestamp': '2024-01-30T10:30:00Z',
            'level': 'FAIL',
            'msg': 'Element not found: //button[@id="submit"]',
            'keyword': 'Click Button',
            'suite': 'Login Tests'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert 'Element not found' in result['message']
    
    def test_selenium_java_logs(self):
        """Test compatibility with Selenium Java logs."""
        log_line = json.dumps({
            'timestamp': '2024-01-30T10:30:00.456Z',
            'level': 'ERROR',
            'logger_name': 'org.openqa.selenium.remote.RemoteWebDriver',
            'message': 'NoSuchElementException: Unable to locate element',
            'thread': 'TestNG-test=1'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert 'NoSuchElementException' in result['message']
    
    def test_specflow_dotnet_logs(self):
        """Test compatibility with SpecFlow (.NET) logs."""
        log_line = json.dumps({
            'Timestamp': '2024-01-30T10:30:00.789Z',
            'Level': 'Error',
            'Message': 'ElementNotInteractableException: element not interactable',
            'Category': 'TechTalk.SpecFlow',
            'Scenario': 'User Registration'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert 'ElementNotInteractableException' in result['message']
    
    def test_testng_logs(self):
        """Test compatibility with TestNG logs."""
        log_line = json.dumps({
            'timestamp': '2024-01-30T10:30:00.123Z',
            'level': 'ERROR',
            'logger_name': 'org.testng.TestRunner',
            'message': 'Test method failed: testUserLogin',
            'thread': 'TestNG-pool-1-thread-1',
            'test_class': 'com.example.tests.LoginTest',
            'test_method': 'testUserLogin'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert 'testUserLogin' in result['message']
        assert result['level'] == 'ERROR'
    
    def test_cucumber_logs(self):
        """Test compatibility with Cucumber logs."""
        log_line = json.dumps({
            '@timestamp': '2024-01-30T10:30:00Z',
            'severity': 'error',
            'message': 'Scenario: User login - Step failed: Then user should see dashboard',
            'feature': 'User Authentication',
            'scenario': 'User login',
            'step': 'Then user should see dashboard',
            'error': 'AssertionError: Element not found'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert 'Step failed' in result['message']
        assert result['error_type'] == 'AssertionError'
    
    def test_karate_logs(self):
        """Test compatibility with Karate logs."""
        log_line = json.dumps({
            'timestamp': 1706612400000,
            'level': 'ERROR',
            'message': 'assertion failed: path: $.user.id expected: [123] but was: [null]',
            'feature': 'user-api.feature',
            'scenario': 'Get user by ID'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert 'assertion failed' in result['message']
    
    def test_webdriverio_logs(self):
        """Test compatibility with WebdriverIO logs."""
        log_line = json.dumps({
            'time': '2024-01-30T10:30:00.456Z',
            'log_level': 'ERROR',
            'msg': 'NoSuchElementError: Cannot find element with selector: #loginButton',
            'app': 'webdriverio-tests',
            'test': 'Login functionality'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert 'NoSuchElementError' in result['message']
    
    def test_nightwatch_logs(self):
        """Test compatibility with Nightwatch logs."""
        log_line = json.dumps({
            'timestamp': '2024-01-30T10:30:00.789Z',
            'level': 'error',
            'message': 'Element <#submit-button> was not found',
            'service': 'nightwatch-runner',
            'test_name': 'Login Test',
            'browser': 'chrome'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert 'not found' in result['message']
    
    def test_selenium_bdd_logs(self):
        """Test compatibility with Selenium BDD logs."""
        log_line = json.dumps({
            'timestamp': '2024-01-30T10:30:00Z',
            'level': 'ERROR',
            'message': 'StepDefinitionException: Step execution failed',
            'feature': 'Login',
            'scenario': 'Valid user login',
            'step': 'When user enters valid credentials',
            'logger': 'cucumber.runtime'
        })
        
        adapter = JSONLogAdapter()
        result = adapter.parse(log_line)
        
        assert result is not None
        assert 'StepDefinitionException' in result['message']


class TestAIIntegration:
    """Test log adapter behavior with and without AI."""
    
    def test_log_parsing_without_ai(self):
        """Test that log parsing works without AI enabled."""
        # Simulate AI disabled by not using AI-dependent features
        adapter = JSONLogAdapter()
        
        log_line = json.dumps({
            'timestamp': '2024-01-30T10:30:00Z',
            'level': 'ERROR',
            'message': 'Database connection timeout',
            'service': 'api-gateway'
        })
        
        result = adapter.parse(log_line)
        
        # Basic parsing should work without AI
        assert result is not None
        assert result['level'] == 'ERROR'
        assert 'timeout' in result['message'].lower()
    
    def test_signal_extraction_without_ai(self):
        """Test signal extraction works without AI."""
        adapter = JSONLogAdapter()
        
        log_event = {
            'level': 'ERROR',
            'message': 'Connection timeout after 30 seconds',
            'timestamp': '2024-01-30T10:30:00Z',
            'service': 'payment-api'
        }
        
        signals = adapter.extract_signals(log_event)
        
        # Pattern-based extraction works without AI
        assert signals['is_error'] is True
        assert signals['is_timeout'] is True
        assert signals['error_category'] == 'network'
    
    def test_correlation_without_ai(self):
        """Test log correlation works without AI."""
        from core.execution.intelligence.log_adapters.correlation import LogCorrelator
        from core.execution.intelligence.models import ExecutionEvent, LogLevel
        
        # Create test event
        test_event = ExecutionEvent(
            timestamp='2024-01-30T10:30:00Z',
            level=LogLevel.ERROR,
            source='test',
            message='Test failed',
            metadata={'trace_id': 'trace-123'}
        )
        test_event.trace_id = 'trace-123'
        
        # Application logs
        app_logs = [{
            'timestamp': '2024-01-30T10:30:01Z',
            'level': 'ERROR',
            'message': 'Database error',
            'trace_id': 'trace-123'
        }]
        
        correlator = LogCorrelator()
        result = correlator.correlate(test_event, app_logs)
        
        # Correlation works without AI (uses trace_id matching)
        assert len(result.correlated_logs) == 1
        assert result.correlation_confidence == 1.0


# Run tests with pytest
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
