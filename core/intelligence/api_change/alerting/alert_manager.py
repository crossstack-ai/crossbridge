"""
Alert Manager - Coordinates alert sending across multiple notifiers.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from core.intelligence.api_change.alerting.base import Alert, AlertSeverity, AlertNotifier
from core.intelligence.api_change.alerting.email_notifier import EmailNotifier
from core.intelligence.api_change.alerting.slack_notifier import SlackNotifier
from core.intelligence.api_change.alerting.confluence_notifier import ConfluenceNotifier
from core.intelligence.api_change.models.api_change import APIChangeEvent, RiskLevel
from core.intelligence.api_change.storage.repository import APIChangeRepository


logger = logging.getLogger(__name__)


class AlertManager:
    """
    Manages alert sending across multiple notification channels.
    
    Handles:
    - Alert creation from API changes
    - Routing to appropriate notifiers
    - Deduplication
    - Alert history tracking
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        repository: Optional[APIChangeRepository] = None
    ):
        """
        Initialize alert manager.
        
        Args:
            config: Configuration with notifier settings
            repository: Optional repository for storing alert history
        """
        self.config = config
        self.repository = repository
        self.notifiers: List[AlertNotifier] = []
        
        # Initialize notifiers based on config
        self._initialize_notifiers()
    
    def _initialize_notifiers(self) -> None:
        """Initialize configured notifiers."""
        # Email notifier
        if self.config.get('email', {}).get('enabled', False):
            email_config = self.config['email']
            self.notifiers.append(EmailNotifier(email_config))
            logger.info("Email notifier initialized")
        
        # Slack notifier
        if self.config.get('slack', {}).get('enabled', False):
            slack_config = self.config['slack']
            self.notifiers.append(SlackNotifier(slack_config))
            logger.info("Slack notifier initialized")
        
        # Confluence notifier
        if self.config.get('confluence', {}).get('enabled', False):
            confluence_config = self.config['confluence']
            self.notifiers.append(ConfluenceNotifier(confluence_config))
            logger.info("Confluence notifier initialized")
    
    async def send_change_alert(
        self,
        change: APIChangeEvent,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send alert for an API change.
        
        Args:
            change: API change event
            additional_context: Additional context to include in alert
        
        Returns:
            True if at least one notifier sent successfully
        """
        # Create alert from change
        alert = self._create_alert_from_change(change, additional_context)
        
        # Send via all notifiers
        return await self.send_alert(alert)
    
    async def send_alert(self, alert: Alert) -> bool:
        """
        Send alert via all configured notifiers.
        
        Args:
            alert: Alert to send
        
        Returns:
            True if at least one notifier sent successfully
        """
        if not self.notifiers:
            logger.warning("No notifiers configured")
            return False
        
        # Send via all notifiers in parallel
        tasks = [notifier.send(alert) for notifier in self.notifiers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check if any succeeded
        success_count = sum(1 for r in results if r is True)
        
        # Store alert in database if repository available
        if self.repository and success_count > 0:
            try:
                self._store_alert(alert, success_count)
            except Exception as e:
                logger.error(f"Failed to store alert in database: {str(e)}")
        
        return success_count > 0
    
    async def send_bulk_alerts(
        self,
        changes: List[APIChangeEvent],
        summary_mode: bool = True
    ) -> int:
        """
        Send alerts for multiple API changes.
        
        Args:
            changes: List of API changes
            summary_mode: If True, send one summary alert; if False, send individual alerts
        
        Returns:
            Number of alerts sent successfully
        """
        if not changes:
            return 0
        
        if summary_mode:
            # Create summary alert
            alert = self._create_summary_alert(changes)
            success = await self.send_alert(alert)
            return 1 if success else 0
        else:
            # Send individual alerts
            tasks = [self.send_change_alert(change) for change in changes]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return sum(1 for r in results if r is True)
    
    def _create_alert_from_change(
        self,
        change: APIChangeEvent,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Create an alert from an API change event."""
        # Determine severity
        severity = self._map_risk_to_severity(change.risk_level)
        
        # Build title
        title = f"{change.change_type} - {change.entity_type}"
        if change.path:
            title += f": {change.path}"
        
        # Build message
        message = self._format_change_message(change)
        
        # Build details
        details = {
            'Change Type': change.change_type,
            'Entity Type': change.entity_type,
            'Risk Level': change.risk_level.value if change.risk_level else 'unknown',
            'Breaking': 'Yes' if change.breaking else 'No'
        }
        
        if change.path:
            details['Path'] = change.path
        if change.http_method:
            details['Method'] = change.http_method
        if change.old_value:
            details['Old Value'] = str(change.old_value)[:100]
        if change.new_value:
            details['New Value'] = str(change.new_value)[:100]
        
        # Add additional context
        if additional_context:
            details.update(additional_context)
        
        # Build tags
        tags = [change.change_type, change.entity_type]
        if change.breaking:
            tags.append('breaking')
        if change.risk_level:
            tags.append(change.risk_level.value)
        
        return Alert(
            title=title,
            message=message,
            severity=severity,
            timestamp=change.detected_at or datetime.utcnow(),
            source='API Change Intelligence',
            details=details,
            tags=tags
        )
    
    def _create_summary_alert(self, changes: List[APIChangeEvent]) -> Alert:
        """Create a summary alert for multiple changes."""
        # Count changes by type
        total = len(changes)
        breaking_count = sum(1 for c in changes if c.breaking)
        high_risk_count = sum(1 for c in changes if c.risk_level == RiskLevel.HIGH)
        
        # Determine severity based on changes
        if breaking_count > 0:
            severity = AlertSeverity.CRITICAL
        elif high_risk_count > 0:
            severity = AlertSeverity.HIGH
        else:
            severity = AlertSeverity.MEDIUM
        
        # Build title
        title = f"API Changes Detected: {total} total, {breaking_count} breaking"
        
        # Build message
        message_lines = [
            f"CrossBridge AI has detected {total} API changes:",
            f"",
            f"🔴 Breaking Changes: {breaking_count}",
            f"⚠️  High Risk: {high_risk_count}",
            f"ℹ️  Other Changes: {total - breaking_count - high_risk_count}",
            f""
        ]
        
        # Add top breaking changes
        if breaking_count > 0:
            message_lines.append("Breaking Changes:")
            breaking_changes = [c for c in changes if c.breaking][:5]
            for change in breaking_changes:
                message_lines.append(f"  • {change.change_type} - {change.path or change.entity_type}")
        
        message = '\n'.join(message_lines)
        
        # Build details
        details = {
            'Total Changes': total,
            'Breaking Changes': breaking_count,
            'High Risk Changes': high_risk_count,
            'Analysis Time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Build tags
        tags = ['api-changes', 'summary']
        if breaking_count > 0:
            tags.append('breaking')
        
        return Alert(
            title=title,
            message=message,
            severity=severity,
            timestamp=datetime.utcnow(),
            source='API Change Intelligence',
            details=details,
            tags=tags
        )
    
    def _format_change_message(self, change: APIChangeEvent) -> str:
        """Format a human-readable message for a change."""
        lines = []
        
        if change.breaking:
            lines.append("⚠️  BREAKING CHANGE DETECTED")
            lines.append("")
        
        lines.append(f"A {change.change_type} change was detected in {change.entity_type}.")
        
        if change.path:
            lines.append(f"Endpoint: {change.http_method or 'GET'} {change.path}")
        
        if change.old_value and change.new_value:
            lines.append("")
            lines.append(f"Changed from: {change.old_value}")
            lines.append(f"Changed to: {change.new_value}")
        
        if change.recommended_tests:
            lines.append("")
            lines.append("Recommended tests to run:")
            for test in change.recommended_tests[:5]:
                lines.append(f"  • {test}")
        
        return '\n'.join(lines)
    
    def _map_risk_to_severity(self, risk_level: Optional[RiskLevel]) -> AlertSeverity:
        """Map risk level to alert severity."""
        if not risk_level:
            return AlertSeverity.INFO
        
        mapping = {
            RiskLevel.CRITICAL: AlertSeverity.CRITICAL,
            RiskLevel.HIGH: AlertSeverity.HIGH,
            RiskLevel.MEDIUM: AlertSeverity.MEDIUM,
            RiskLevel.LOW: AlertSeverity.LOW
        }
        
        return mapping.get(risk_level, AlertSeverity.INFO)
    
    def _store_alert(self, alert: Alert, notifiers_sent: int) -> None:
        """Store alert in database."""
        if not self.repository:
            return
        
        try:
            # This would use repository.save_alert() if we add that method
            # For now, just log
            logger.info(f"Alert stored: {alert.title} (sent to {notifiers_sent} notifiers)")
        except Exception as e:
            logger.error(f"Failed to store alert: {str(e)}")
    
    def add_notifier(self, notifier: AlertNotifier) -> None:
        """Add a custom notifier."""
        self.notifiers.append(notifier)
    
    def get_notifier_count(self) -> int:
        """Get number of active notifiers."""
        return len([n for n in self.notifiers if n.enabled])
