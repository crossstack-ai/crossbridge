"""
Unit tests for Alert Manager with Confluence integration.

Tests alert_manager.py functionality including:
- Notifier initialization (Email, Slack, Confluence)
- Multi-channel alert sending
- Alert routing
- Bulk alerts
- Graceful degradation
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from core.intelligence.api_change.alerting.alert_manager import AlertManager
from core.intelligence.api_change.alerting.base import Alert, AlertSeverity
from core.intelligence.api_change.models.api_change import APIChangeEvent, RiskLevel, ChangeType, EntityType


class TestAlertManagerInitialization:
    """Test alert manager initialization."""
    
    def test_init_no_notifiers(self):
        """Test initialization with no notifiers configured."""
        config = {}
        manager = AlertManager(config)
        
        assert len(manager.notifiers) == 0
    
    def test_init_with_email(self):
        """Test initialization with email notifier."""
        config = {
            'email': {
                'enabled': True,
                'smtp_host': 'smtp.test.com',
                'smtp_port': 587,
                'smtp_user': 'test@example.com',
                'smtp_password': 'password',
                'from_email': 'test@example.com',
                'to_emails': ['recipient@example.com']
            }
        }
        
        manager = AlertManager(config)
        
        assert len(manager.notifiers) == 1
        assert manager.notifiers[0].__class__.__name__ == 'EmailNotifier'
    
    def test_init_with_slack(self):
        """Test initialization with Slack notifier."""
        config = {
            'slack': {
                'enabled': True,
                'webhook_url': 'https://hooks.slack.com/services/TEST'
            }
        }
        
        manager = AlertManager(config)
        
        assert len(manager.notifiers) == 1
        assert manager.notifiers[0].__class__.__name__ == 'SlackNotifier'
    
    def test_init_with_confluence(self):
        """Test initialization with Confluence notifier."""
        config = {
            'confluence': {
                'enabled': True,
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'auth_token': 'test-token',
                'space_key': 'TEST'
            }
        }
        
        manager = AlertManager(config)
        
        assert len(manager.notifiers) == 1
        assert manager.notifiers[0].__class__.__name__ == 'ConfluenceNotifier'
    
    def test_init_with_all_notifiers(self):
        """Test initialization with all notifiers enabled."""
        config = {
            'email': {
                'enabled': True,
                'smtp_host': 'smtp.test.com',
                'smtp_port': 587,
                'smtp_user': 'test@example.com',
                'smtp_password': 'password',
                'from_email': 'test@example.com',
                'to_emails': ['recipient@example.com']
            },
            'slack': {
                'enabled': True,
                'webhook_url': 'https://hooks.slack.com/services/TEST'
            },
            'confluence': {
                'enabled': True,
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'auth_token': 'test-token',
                'space_key': 'TEST'
            }
        }
        
        manager = AlertManager(config)
        
        assert len(manager.notifiers) == 3
        notifier_types = [n.__class__.__name__ for n in manager.notifiers]
        assert 'EmailNotifier' in notifier_types
        assert 'SlackNotifier' in notifier_types
        assert 'ConfluenceNotifier' in notifier_types


class TestAlertManagerSendAlert:
    """Test alert sending functionality."""
    
    @pytest.mark.asyncio
    async def test_send_alert_no_notifiers(self):
        """Test sending alert with no notifiers."""
        config = {}
        manager = AlertManager(config)
        
        alert = Alert(
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.HIGH,
            timestamp=datetime.utcnow(),
            source="Test"
        )
        
        result = await manager.send_alert(alert)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_alert_single_notifier_success(self):
        """Test sending alert with single notifier succeeding."""
        config = {
            'confluence': {
                'enabled': True,
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'auth_token': 'test-token',
                'space_key': 'TEST'
            }
        }
        
        manager = AlertManager(config)
        
        # Mock the notifier's send method
        mock_send = AsyncMock(return_value=True)
        manager.notifiers[0].send = mock_send
        
        alert = Alert(
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.HIGH,
            timestamp=datetime.utcnow(),
            source="Test"
        )
        
        result = await manager.send_alert(alert)
        
        assert result is True
        mock_send.assert_called_once_with(alert)
    
    @pytest.mark.asyncio
    async def test_send_alert_multiple_notifiers(self):
        """Test sending alert with multiple notifiers."""
        config = {
            'slack': {
                'enabled': True,
                'webhook_url': 'https://hooks.slack.com/services/TEST'
            },
            'confluence': {
                'enabled': True,
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'auth_token': 'test-token',
                'space_key': 'TEST'
            }
        }
        
        manager = AlertManager(config)
        
        # Mock both notifiers
        mock_send_1 = AsyncMock(return_value=True)
        mock_send_2 = AsyncMock(return_value=True)
        manager.notifiers[0].send = mock_send_1
        manager.notifiers[1].send = mock_send_2
        
        alert = Alert(
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.CRITICAL,
            timestamp=datetime.utcnow(),
            source="Test"
        )
        
        result = await manager.send_alert(alert)
        
        assert result is True
        mock_send_1.assert_called_once()
        mock_send_2.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_alert_partial_success(self):
        """Test graceful degradation when some notifiers fail."""
        config = {
            'slack': {
                'enabled': True,
                'webhook_url': 'https://hooks.slack.com/services/TEST'
            },
            'confluence': {
                'enabled': True,
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'auth_token': 'test-token',
                'space_key': 'TEST'
            }
        }
        
        manager = AlertManager(config)
        
        # Mock: Slack succeeds, Confluence fails
        mock_send_slack = AsyncMock(return_value=True)
        mock_send_confluence = AsyncMock(return_value=False)
        manager.notifiers[0].send = mock_send_slack
        manager.notifiers[1].send = mock_send_confluence
        
        alert = Alert(
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.HIGH,
            timestamp=datetime.utcnow(),
            source="Test"
        )
        
        result = await manager.send_alert(alert)
        
        # Should still return True because at least one succeeded
        assert result is True


class TestAlertManagerChangeAlerts:
    """Test API change alert functionality."""
    
    @pytest.mark.asyncio
    async def test_send_change_alert(self):
        """Test sending alert from API change event."""
        config = {
            'confluence': {
                'enabled': True,
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'auth_token': 'test-token',
                'space_key': 'TEST'
            }
        }
        
        manager = AlertManager(config)
        
        # Mock notifier
        mock_send = AsyncMock(return_value=True)
        manager.notifiers[0].send = mock_send
        
        # Create API change event
        change = APIChangeEvent(
            change_type=ChangeType.REMOVED,
            entity_type=EntityType.ENDPOINT,
            entity_name='users',
            path='/api/users',
            http_method='GET',
            breaking=True,
            risk_level=RiskLevel.CRITICAL,
            old_value={'field': 'phoneNumber'},
            new_value=None,
            detected_at=datetime.utcnow()
        )
        
        result = await manager.send_change_alert(change)
        
        assert result is True
        mock_send.assert_called_once()
        
        # Verify alert was created from change
        call_args = mock_send.call_args[0][0]
        assert call_args.title
        assert call_args.severity == AlertSeverity.CRITICAL
        assert 'breaking' in call_args.tags
    
    @pytest.mark.asyncio
    async def test_send_bulk_alerts_summary(self):
        """Test sending bulk alerts in summary mode."""
        config = {
            'confluence': {
                'enabled': True,
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'auth_token': 'test-token',
                'space_key': 'TEST'
            }
        }
        
        manager = AlertManager(config)
        
        # Mock notifier
        mock_send = AsyncMock(return_value=True)
        manager.notifiers[0].send = mock_send
        
        # Create multiple changes
        changes = [
            APIChangeEvent(
                change_type=ChangeType.REMOVED,
                entity_type=EntityType.ENDPOINT,
                entity_name='users',
                path='/api/users',
                breaking=True,
                risk_level=RiskLevel.HIGH,
                detected_at=datetime.utcnow()
            ),
            APIChangeEvent(
                change_type=ChangeType.ADDED,
                entity_type=EntityType.ENDPOINT,
                entity_name='orders',
                path='/api/orders',
                breaking=False,
                risk_level=RiskLevel.LOW,
                detected_at=datetime.utcnow()
            )
        ]
        
        result = await manager.send_bulk_alerts(changes, summary_mode=True)
        
        assert result == 1  # One summary alert
        mock_send.assert_called_once()
        
        # Verify summary alert
        call_args = mock_send.call_args[0][0]
        assert 'API Changes Detected' in call_args.title
        assert '2 total' in call_args.title
    
    @pytest.mark.asyncio
    async def test_send_bulk_alerts_individual(self):
        """Test sending bulk alerts individually."""
        config = {
            'confluence': {
                'enabled': True,
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'auth_token': 'test-token',
                'space_key': 'TEST'
            }
        }
        
        manager = AlertManager(config)
        
        # Mock notifier
        mock_send = AsyncMock(return_value=True)
        manager.notifiers[0].send = mock_send
        
        # Create multiple changes
        changes = [
            APIChangeEvent(
                change_type=ChangeType.REMOVED,
                entity_type=EntityType.ENDPOINT,
                entity_name='users',
                path='/api/users',
                breaking=True,
                risk_level=RiskLevel.HIGH,
                detected_at=datetime.utcnow()
            ),
            APIChangeEvent(
                change_type=ChangeType.ADDED,
                entity_type=EntityType.ENDPOINT,
                entity_name='orders',
                path='/api/orders',
                breaking=False,
                risk_level=RiskLevel.LOW,
                detected_at=datetime.utcnow()
            )
        ]
        
        result = await manager.send_bulk_alerts(changes, summary_mode=False)
        
        assert result == 2  # Two individual alerts
        assert mock_send.call_count == 2


class TestAlertManagerHelpers:
    """Test helper methods."""
    
    def test_map_risk_to_severity(self):
        """Test risk level to severity mapping."""
        config = {}
        manager = AlertManager(config)
        
        assert manager._map_risk_to_severity(RiskLevel.CRITICAL) == AlertSeverity.CRITICAL
        assert manager._map_risk_to_severity(RiskLevel.HIGH) == AlertSeverity.HIGH
        assert manager._map_risk_to_severity(RiskLevel.MEDIUM) == AlertSeverity.MEDIUM
        assert manager._map_risk_to_severity(RiskLevel.LOW) == AlertSeverity.LOW
        assert manager._map_risk_to_severity(None) == AlertSeverity.INFO
    
    def test_add_notifier(self):
        """Test adding custom notifier."""
        config = {}
        manager = AlertManager(config)
        
        assert len(manager.notifiers) == 0
        
        # Add custom notifier
        mock_notifier = Mock()
        mock_notifier.enabled = True
        manager.add_notifier(mock_notifier)
        
        assert len(manager.notifiers) == 1
    
    def test_get_notifier_count(self):
        """Test getting active notifier count."""
        config = {
            'confluence': {
                'enabled': True,
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'auth_token': 'test-token',
                'space_key': 'TEST'
            }
        }
        
        manager = AlertManager(config)
        
        assert manager.get_notifier_count() == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
