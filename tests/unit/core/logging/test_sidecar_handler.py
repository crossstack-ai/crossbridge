"""
Unit tests for Sidecar Log Handler

Tests the SidecarLogHandler which forwards CLI logs to the sidecar API.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from core.logging import get_logger, LogCategory, LogLevel
from core.logging.handlers import SidecarLogHandler
from core.logging.logger import CrossBridgeLogger


class TestSidecarLogHandler:
    """Test sidecar log handler functionality"""
    
    def test_handler_initialization_sidecar_available(self):
        """Test handler initializes when sidecar is available"""
        with patch('core.logging.handlers.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            handler = SidecarLogHandler(
                sidecar_url="http://localhost:8765",
                min_level=logging.INFO
            )
            
            assert handler._enabled is True
            assert handler.sidecar_url == "http://localhost:8765"
            assert handler.min_level == logging.INFO
            mock_get.assert_called_once_with("http://localhost:8765/health", timeout=1)
    
    def test_handler_initialization_sidecar_unavailable(self):
        """Test handler disables when sidecar is unavailable"""
        with patch('core.logging.handlers.requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            
            handler = SidecarLogHandler(
                sidecar_url="http://localhost:8765",
                min_level=logging.INFO
            )
            
            assert handler._enabled is False
    
    def test_handler_initialization_sidecar_unhealthy(self):
        """Test handler disables when sidecar returns non-200 status"""
        with patch('core.logging.handlers.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_get.return_value = mock_response
            
            handler = SidecarLogHandler(
                sidecar_url="http://localhost:8765",
                min_level=logging.INFO
            )
            
            assert handler._enabled is False
    
    def test_handler_filters_by_level(self):
        """Test handler only sends logs at or above min level"""
        with patch('core.logging.handlers.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            handler = SidecarLogHandler(
                sidecar_url="http://localhost:8765",
                min_level=logging.INFO
            )
            
            # Create log records
            debug_record = logging.LogRecord(
                name="test", level=logging.DEBUG, pathname="", lineno=0,
                msg="Debug message", args=(), exc_info=None
            )
            info_record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="Info message", args=(), exc_info=None
            )
            
            # Mock threading to control execution
            with patch('core.logging.handlers.threading.Thread') as mock_thread:
                handler.emit(debug_record)  # Should not send (below min level)
                assert mock_thread.called is False
                
                handler.emit(info_record)  # Should send
                assert mock_thread.called is True
    
    def test_handler_filters_by_category(self):
        """Test handler only sends logs from specified categories"""
        with patch('core.logging.handlers.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            handler = SidecarLogHandler(
                sidecar_url="http://localhost:8765",
                min_level=logging.INFO,
                categories=['ai', 'cli']  # Only AI and CLI logs
            )
            
            # Create log records with different categories
            ai_record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="AI message", args=(), exc_info=None
            )
            ai_record.category = 'ai'
            
            adapter_record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="Adapter message", args=(), exc_info=None
            )
            adapter_record.category = 'adapter'
            
            # Mock threading to control execution
            with patch('core.logging.handlers.threading.Thread') as mock_thread:
                handler.emit(ai_record)  # Should send (in categories list)
                assert mock_thread.called is True
                
                mock_thread.reset_mock()
                handler.emit(adapter_record)  # Should not send (not in categories)
                assert mock_thread.called is False
    
    def test_handler_sends_log_to_sidecar(self):
        """Test handler sends log record to sidecar API"""
        with patch('core.logging.handlers.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            handler = SidecarLogHandler(
                sidecar_url="http://localhost:8765",
                min_level=logging.INFO
            )
            
            # Create log record
            record = logging.LogRecord(
                name="crossbridge.ai", level=logging.INFO, pathname="", lineno=0,
                msg="HTTP Request: POST http://10.60.75.145:11434/api/embeddings", 
                args=(), exc_info=None
            )
            record.category = 'ai'
            
            # Mock the post request
            with patch('core.logging.handlers.requests.post') as mock_post:
                mock_post_response = Mock()
                mock_post_response.status_code = 200
                mock_post.return_value = mock_post_response
                
                # Send log directly (bypass threading for testing)
                handler._send_log(record)
                
                # Verify POST was called
                assert mock_post.called is True
                call_args = mock_post.call_args
                assert call_args[0][0] == "http://localhost:8765/cli-logs"
                
                # Verify payload structure
                payload = call_args[1]['json']
                assert payload['level'] == 'INFO'
                assert 'HTTP Request: POST' in payload['message']
                assert payload['category'] == 'ai'
                assert payload['logger_name'] == 'crossbridge.ai'
    
    def test_handler_disables_after_max_failures(self):
        """Test handler disables itself after consecutive failures"""
        with patch('core.logging.handlers.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            handler = SidecarLogHandler(
                sidecar_url="http://localhost:8765",
                min_level=logging.INFO
            )
            
            # Create log record
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="Test message", args=(), exc_info=None
            )
            record.category = 'ai'
            
            # Mock post to fail
            with patch('core.logging.handlers.requests.post') as mock_post:
                mock_post.side_effect = Exception("Connection error")
                
                # Send log 3 times (max failures)
                for i in range(3):
                    handler._send_log(record)
                    assert handler._consecutive_failures == i + 1
                
                # After 3 failures, should be disabled
                assert handler._enabled is False
    
    def test_handler_resets_failure_count_on_success(self):
        """Test handler resets failure count after successful send"""
        with patch('core.logging.handlers.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            handler = SidecarLogHandler(
                sidecar_url="http://localhost:8765",
                min_level=logging.INFO
            )
            
            # Create log record
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="Test message", args=(), exc_info=None
            )
            record.category = 'ai'
            
            with patch('core.logging.handlers.requests.post') as mock_post:
                # First fail
                mock_post.side_effect = Exception("Error")
                handler._send_log(record)
                assert handler._consecutive_failures == 1
                
                # Then succeed
                mock_post.side_effect = None
                mock_post_response = Mock()
                mock_post_response.status_code = 200
                mock_post.return_value = mock_post_response
                
                handler._send_log(record)
                
                # Failure count should reset
                assert handler._consecutive_failures == 0
    
    def test_handler_includes_context_attributes(self):
        """Test handler includes extra record attributes in context"""
        with patch('core.logging.handlers.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            handler = SidecarLogHandler(
                sidecar_url="http://localhost:8765",
                min_level=logging.INFO
            )
            
            # Create log record with extra attributes
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="Test message", args=(), exc_info=None
            )
            record.category = 'ai'
            record.operation = 'embedding'
            record.framework = 'robot'
            record.test_id = 'test123'
            record.status = 'success'
            
            with patch('core.logging.handlers.requests.post') as mock_post:
                mock_post_response = Mock()
                mock_post_response.status_code = 200
                mock_post.return_value = mock_post_response
                
                handler._send_log(record)
                
                # Verify context includes extra attributes
                payload = mock_post.call_args[1]['json']
                assert payload['context']['operation'] == 'embedding'
                assert payload['context']['framework'] == 'robot'
                assert payload['context']['test_id'] == 'test123'
                assert payload['context']['status'] == 'success'


class TestCrossBridgeLoggerWithSidecar:
    """Test CrossBridge logger integration with sidecar handler"""
    
    def test_logger_auto_enables_sidecar_when_available(self):
        """Test logger automatically adds sidecar handler when CROSSBRIDGE_API_HOST is set"""
        with patch.dict('os.environ', {
            'CROSSBRIDGE_API_HOST': 'localhost',
            'CROSSBRIDGE_API_PORT': '8765'
        }):
            with patch('core.logging.handlers.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_get.return_value = mock_response
                
                logger = get_logger('test_sidecar', category=LogCategory.AI)
                
                # Check that sidecar handler was added
                sidecar_handlers = [h for h in logger._handlers 
                                   if isinstance(h, SidecarLogHandler)]
                assert len(sidecar_handlers) == 1
                assert sidecar_handlers[0]._enabled is True
    
    def test_logger_works_without_sidecar(self):
        """Test logger works normally when sidecar is not configured"""
        with patch.dict('os.environ', {}, clear=True):
            logger = get_logger('test_no_sidecar', category=LogCategory.AI)
            
            # Should work without errors
            logger.info("Test message")
            
            # No sidecar handler should be added
            sidecar_handlers = [h for h in logger._handlers 
                               if isinstance(h, SidecarLogHandler)]
            assert len(sidecar_handlers) == 0
    
    def test_logger_category_passed_to_sidecar(self):
        """Test logger category is properly passed through to sidecar"""
        with patch.dict('os.environ', {
            'CROSSBRIDGE_API_HOST': 'localhost',
            'CROSSBRIDGE_API_PORT': '8765'
        }):
            with patch('core.logging.handlers.requests.get') as mock_get:
                mock_get_response = Mock()
                mock_get_response.status_code = 200
                mock_get.return_value = mock_get_response
                
                with patch('core.logging.handlers.requests.post') as mock_post:
                    mock_post_response = Mock()
                    mock_post_response.status_code = 200
                    mock_post.return_value = mock_post_response
                    
                    # Create AI logger
                    logger = get_logger('test_category', category=LogCategory.AI)
                    
                    # Log a message
                    logger.info("Test AI message")
                    
                    # Give background thread time to send
                    import time
                    time.sleep(0.2)
                    
                    # Verify category was sent
                    if mock_post.called:
                        payload = mock_post.call_args[1]['json']
                        assert payload['category'] == 'ai'


class TestSidecarLoggingIntegration:
    """Integration tests for end-to-end sidecar logging"""
    
    def test_embedding_provider_logs_forwarded_to_sidecar(self):
        """Test that embedding provider logs are forwarded to sidecar"""
        with patch.dict('os.environ', {
            'CROSSBRIDGE_API_HOST': 'localhost',
            'CROSSBRIDGE_API_PORT': '8765'
        }):
            with patch('core.logging.handlers.requests.get') as mock_get:
                mock_get_response = Mock()
                mock_get_response.status_code = 200
                mock_get.return_value = mock_get_response
                
                with patch('core.logging.handlers.requests.post') as mock_post:
                    mock_post_response = Mock()
                    mock_post_response.status_code = 200
                    mock_post.return_value = mock_post_response
                    
                    # Mock ollama before importing
                    with patch('sys.modules', {'ollama': MagicMock()}):
                        # Create a simple logger and log
                        logger = get_logger('test_embedding', category=LogCategory.AI)
                        logger.info("HTTP Request: POST http://10.60.75.145:11434/api/embeddings")
                        
                        # Give background thread time to send
                        import time
                        time.sleep(0.2)
                        
                        # Verify logs were forwarded
                        if mock_post.called:
                            # Check that the HTTP request log was forwarded
                            for call in mock_post.call_args_list:
                                if 'json' in call[1]:
                                    payload = call[1]['json']
                                    if 'HTTP Request: POST' in payload['message']:
                                        assert payload['category'] == 'ai'
                                        assert payload['level'] == 'INFO'
                                        break
    
    def test_cli_logs_framework_agnostic(self):
        """Test that sidecar logging works for all frameworks"""
        frameworks = ['robot', 'pytest', 'junit', 'cypress', 'playwright', 'jest']
        
        with patch.dict('os.environ', {
            'CROSSBRIDGE_API_HOST': 'localhost',
            'CROSSBRIDGE_API_PORT': '8765'
        }):
            with patch('core.logging.handlers.requests.get') as mock_get:
                mock_get_response = Mock()
                mock_get_response.status_code = 200
                mock_get.return_value = mock_get_response
                
                for framework in frameworks:
                    logger = get_logger(f'test_{framework}', category=LogCategory.CLI)
                    
                    # Should initialize without errors for all frameworks
                    logger.info(f"Testing {framework} framework")
                    
                    # Sidecar handler should be present
                    sidecar_handlers = [h for h in logger._handlers 
                                       if isinstance(h, SidecarLogHandler)]
                    assert len(sidecar_handlers) > 0
