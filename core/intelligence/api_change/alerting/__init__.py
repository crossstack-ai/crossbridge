"""Alerting module for API Change Intelligence."""

from core.intelligence.api_change.alerting.base import AlertNotifier, AlertSeverity, Alert
from core.intelligence.api_change.alerting.email_notifier import EmailNotifier
from core.intelligence.api_change.alerting.slack_notifier import SlackNotifier
from core.intelligence.api_change.alerting.confluence_notifier import ConfluenceNotifier
from core.intelligence.api_change.alerting.alert_manager import AlertManager

__all__ = [
    'AlertNotifier',
    'AlertSeverity',
    'Alert',
    'EmailNotifier',
    'SlackNotifier',
    'ConfluenceNotifier',
    'AlertManager'
]
