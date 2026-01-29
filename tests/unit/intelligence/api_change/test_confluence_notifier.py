"""
Unit tests for Confluence notifier.

Tests confluence_notifier.py functionality including:
- Configuration validation
- Connection testing
- Page creation
- Page updates
- Retry logic
- Error handling
- Rich formatting
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import requests

from core.intelligence.api_change.alerting.confluence_notifier import ConfluenceNotifier
from core.intelligence.api_change.alerting.base import Alert, AlertSeverity


class TestConfluenceNotifierConfiguration:
    """Test configuration and initialization."""
    
    def test_init_with_valid_config(self):
        """Test initialization with valid configuration."""
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST'
        }
        
        notifier = ConfluenceNotifier(config)
        
        assert notifier.url == 'https://test.atlassian.net'
        assert notifier.username == 'test@example.com'
        assert notifier.auth_token == 'test-token'
        assert notifier.space_key == 'TEST'
        assert notifier.enabled is True
    
    def test_init_with_missing_required_config(self):
        """Test initialization fails gracefully with missing config."""
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            # Missing username, auth_token, space_key
        }
        
        notifier = ConfluenceNotifier(config)
        
        assert notifier.enabled is False
    
    def test_init_with_optional_config(self):
        """Test initialization with optional configuration."""
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST',
            'parent_page_id': '123456',
            'page_title_prefix': 'Custom Alert',
            'update_mode': 'update',
            'max_retries': 5,
            'retry_backoff': 3
        }
        
        notifier = ConfluenceNotifier(config)
        
        assert notifier.parent_page_id == '123456'
        assert notifier.page_title_prefix == 'Custom Alert'
        assert notifier.update_mode == 'update'
        assert notifier.max_retries == 5
        assert notifier.retry_backoff == 3
    
    def test_url_trailing_slash_removed(self):
        """Test URL trailing slash is removed."""
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net/',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST'
        }
        
        notifier = ConfluenceNotifier(config)
        
        assert notifier.url == 'https://test.atlassian.net'


class TestConfluenceNotifierConnection:
    """Test connection and authentication."""
    
    @patch('requests.get')
    def test_connection_success(self, mock_get):
        """Test successful connection."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST'
        }
        
        notifier = ConfluenceNotifier(config)
        result = notifier.test_connection()
        
        assert result is True
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_connection_failure_401(self, mock_get):
        """Test connection failure with 401 Unauthorized."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'wrong-token',
            'space_key': 'TEST'
        }
        
        notifier = ConfluenceNotifier(config)
        result = notifier.test_connection()
        
        assert result is False
    
    @patch('requests.get')
    def test_connection_failure_404(self, mock_get):
        """Test connection failure with 404 Space Not Found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'NOTFOUND'
        }
        
        notifier = ConfluenceNotifier(config)
        result = notifier.test_connection()
        
        assert result is False
    
    @patch('requests.get')
    def test_connection_exception(self, mock_get):
        """Test connection handles exceptions gracefully."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
        
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST'
        }
        
        notifier = ConfluenceNotifier(config)
        result = notifier.test_connection()
        
        assert result is False


class TestConfluenceNotifierPageCreation:
    """Test page creation functionality."""
    
    @pytest.mark.asyncio
    @patch('core.intelligence.api_change.alerting.confluence_notifier.requests.post')
    async def test_create_page_success(self, mock_post):
        """Test successful page creation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '12345',
            '_links': {
                'webui': '/spaces/TEST/pages/12345'
            }
        }
        mock_post.return_value = mock_response
        
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST'
        }
        
        notifier = ConfluenceNotifier(config)
        
        alert = Alert(
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.HIGH,
            timestamp=datetime.utcnow(),
            source="Test"
        )
        
        result = await notifier.send(alert)
        
        assert result is True
        mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('core.intelligence.api_change.alerting.confluence_notifier.requests.post')
    async def test_create_page_with_parent(self, mock_post):
        """Test page creation with parent page."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '12345',
            '_links': {'webui': '/spaces/TEST/pages/12345'}
        }
        mock_post.return_value = mock_response
        
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST',
            'parent_page_id': '999'
        }
        
        notifier = ConfluenceNotifier(config)
        
        alert = Alert(
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.INFO,
            timestamp=datetime.utcnow(),
            source="Test"
        )
        
        result = await notifier.send(alert)
        
        assert result is True
        # Verify payload includes parent
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert 'ancestors' in payload
        assert payload['ancestors'][0]['id'] == '999'
    
    @pytest.mark.asyncio
    @patch('core.intelligence.api_change.alerting.confluence_notifier.requests.post')
    async def test_create_page_failure(self, mock_post):
        """Test page creation failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response
        
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST',
            'max_retries': 1  # Reduce retries for faster test
        }
        
        notifier = ConfluenceNotifier(config)
        
        alert = Alert(
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.CRITICAL,
            timestamp=datetime.utcnow(),
            source="Test"
        )
        
        result = await notifier.send(alert)
        
        assert result is False


class TestConfluenceNotifierPageUpdate:
    """Test page update functionality."""
    
    @pytest.mark.asyncio
    @patch('core.intelligence.api_change.alerting.confluence_notifier.requests.get')
    @patch('core.intelligence.api_change.alerting.confluence_notifier.requests.put')
    async def test_update_existing_page(self, mock_put, mock_get):
        """Test updating an existing page."""
        # Mock finding existing page
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            'version': {'number': 1},
            'body': {'storage': {'value': 'Existing content'}}
        }
        mock_get.return_value = mock_get_response
        
        # Mock update success
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {
            'id': '12345',
            '_links': {'webui': '/spaces/TEST/pages/12345'}
        }
        mock_put.return_value = mock_put_response
        
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST',
            'update_mode': 'update'
        }
        
        notifier = ConfluenceNotifier(config)
        
        # Mock finding page
        with patch.object(notifier, '_find_existing_page', return_value='12345'):
            alert = Alert(
                title="Test Alert",
                message="Test message",
                severity=AlertSeverity.MEDIUM,
                timestamp=datetime.utcnow(),
                source="Test"
            )
            
            result = await notifier.send(alert)
            
            assert result is True
            mock_put.assert_called_once()


class TestConfluenceNotifierRetryLogic:
    """Test retry logic and error handling."""
    
    @pytest.mark.asyncio
    @patch('time.sleep')
    async def test_retry_on_connection_error(self, mock_sleep):
        """Test retry logic on connection error."""
        # Mock _create_page to fail twice then succeed
        with patch.object(ConfluenceNotifier, '_create_page') as mock_create:
            mock_create.side_effect = [
                requests.exceptions.ConnectionError("Connection failed"),
                requests.exceptions.ConnectionError("Connection failed"),
                True
            ]
            
            config = {
                'enabled': True,
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'auth_token': 'test-token',
                'space_key': 'TEST',
                'max_retries': 3,
                'retry_backoff': 2
            }
            
            notifier = ConfluenceNotifier(config)
            
            alert = Alert(
                title="Test Alert",
                message="Test message",
                severity=AlertSeverity.HIGH,
                timestamp=datetime.utcnow(),
                source="Test"
            )
            
            result = await notifier.send(alert)
            
            assert result is True
            assert mock_create.call_count == 3
            assert mock_sleep.call_count == 2  # 2 retries = 2 sleeps
    
    @pytest.mark.asyncio
    @patch('time.sleep')
    async def test_retry_exhausted(self, mock_sleep):
        """Test all retries exhausted."""
        # Mock _create_page to always fail
        with patch.object(ConfluenceNotifier, '_create_page') as mock_create:
            mock_create.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            config = {
                'enabled': True,
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'auth_token': 'test-token',
                'space_key': 'TEST',
                'max_retries': 3,
                'retry_backoff': 2
            }
            
            notifier = ConfluenceNotifier(config)
            
            alert = Alert(
                title="Test Alert",
                message="Test message",
                severity=AlertSeverity.CRITICAL,
                timestamp=datetime.utcnow(),
                source="Test"
            )
            
            result = await notifier.send(alert)
            
            assert result is False
            assert mock_create.call_count == 3
            assert mock_sleep.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self):
        """Test exponential backoff timing."""
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST',
            'max_retries': 3,
            'retry_backoff': 2
        }
        
        notifier = ConfluenceNotifier(config)
        
        # Expected wait times: 2^0=1s, 2^1=2s, 2^2=4s
        expected_waits = [1, 2, 4]
        
        for attempt in range(3):
            wait_time = notifier.retry_backoff ** attempt
            assert wait_time == expected_waits[attempt]


class TestConfluenceNotifierFormatting:
    """Test rich content formatting."""
    
    def test_build_page_title(self):
        """Test page title generation."""
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST',
            'page_title_prefix': 'Alert'
        }
        
        notifier = ConfluenceNotifier(config)
        
        alert = Alert(
            title="Breaking Change",
            message="Test",
            severity=AlertSeverity.CRITICAL,
            timestamp=datetime(2026, 1, 29, 12, 30),
            source="Test"
        )
        
        title = notifier._build_page_title(alert)
        
        assert 'Alert' in title
        assert 'Breaking Change' in title
        assert '2026-01-29' in title
        assert '12:30' in title
    
    def test_build_page_content_critical(self):
        """Test page content for CRITICAL severity."""
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST'
        }
        
        notifier = ConfluenceNotifier(config)
        
        alert = Alert(
            title="Critical Alert",
            message="This is a critical message",
            severity=AlertSeverity.CRITICAL,
            timestamp=datetime.utcnow(),
            source="API Change Intelligence",
            details={'Endpoint': 'GET /api/users', 'Impact': 'High'},
            tags=['breaking', 'api']
        )
        
        content = notifier._build_page_content(alert)
        
        # Check for severity
        assert 'CRITICAL' in content
        assert 'Red' in content  # Color
        assert '🔴' in content  # Emoji
        
        # Check for message
        assert 'This is a critical message' in content
        
        # Check for details table
        assert 'Endpoint' in content
        assert 'GET /api/users' in content
        
        # Check for tags
        assert 'breaking' in content
        assert 'api' in content
    
    def test_build_page_content_info(self):
        """Test page content for INFO severity."""
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST'
        }
        
        notifier = ConfluenceNotifier(config)
        
        alert = Alert(
            title="Info Alert",
            message="This is informational",
            severity=AlertSeverity.INFO,
            timestamp=datetime.utcnow(),
            source="Test"
        )
        
        content = notifier._build_page_content(alert)
        
        assert 'INFO' in content
        assert 'Grey' in content
        assert '💡' in content
    
    def test_escape_html_special_chars(self):
        """Test HTML escaping."""
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST'
        }
        
        notifier = ConfluenceNotifier(config)
        
        text = '<script>alert("XSS")</script> & "quotes" \'single\''
        escaped = notifier._escape_html(text)
        
        assert '&lt;' in escaped
        assert '&gt;' in escaped
        assert '&amp;' in escaped
        assert '&quot;' in escaped
        assert '&#39;' in escaped
        assert '<script>' not in escaped


class TestConfluenceNotifierMinSeverity:
    """Test minimum severity filtering."""
    
    @pytest.mark.asyncio
    async def test_send_below_min_severity(self):
        """Test alert below minimum severity is not sent."""
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST',
            'min_severity': 'high'
        }
        
        notifier = ConfluenceNotifier(config)
        
        alert = Alert(
            title="Low Priority",
            message="This should not be sent",
            severity=AlertSeverity.LOW,
            timestamp=datetime.utcnow(),
            source="Test"
        )
        
        with patch.object(notifier, '_send_with_retry') as mock_send:
            result = await notifier.send(alert)
            
            # Should return False and not call _send_with_retry
            assert result is False
            mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('core.intelligence.api_change.alerting.confluence_notifier.requests.post')
    async def test_send_above_min_severity(self, mock_post):
        """Test alert above minimum severity is sent."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '123',
            '_links': {'webui': '/page'}
        }
        mock_post.return_value = mock_response
        
        config = {
            'enabled': True,
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'auth_token': 'test-token',
            'space_key': 'TEST',
            'min_severity': 'medium'
        }
        
        notifier = ConfluenceNotifier(config)
        
        alert = Alert(
            title="High Priority",
            message="This should be sent",
            severity=AlertSeverity.HIGH,
            timestamp=datetime.utcnow(),
            source="Test"
        )
        
        result = await notifier.send(alert)
        
        assert result is True
        mock_post.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
