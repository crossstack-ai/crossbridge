"""
Slack notifier for sending alerts via Slack webhooks.
"""

import json
from typing import Dict, Any
import logging
import asyncio
import aiohttp
import time

from core.intelligence.api_change.alerting.base import AlertNotifier, Alert, AlertSeverity


logger = logging.getLogger(__name__)


class SlackNotifier(AlertNotifier):
    """Send alerts to Slack using incoming webhooks."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Slack notifier.
        
        Config keys:
            - webhook_url: Slack incoming webhook URL
            - channel: Override default channel (optional)
            - username: Bot username (default: "CrossBridge AI")
            - icon_emoji: Bot icon emoji (default: ":robot_face:")
            - mention_users: List of user IDs to mention for critical alerts
        """
        super().__init__(config)
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel')
        self.username = config.get('username', 'CrossBridge AI')
        self.icon_emoji = config.get('icon_emoji', ':robot_face:')
        self.mention_users = config.get('mention_users', [])
        
        if not self.webhook_url:
            logger.warning("Slack notifier missing webhook_url")
            self.enabled = False
    
    async def _send_with_retry(self, payload: Dict[str, Any], max_retries: int = 3) -> bool:
        """Send to Slack with retry logic."""
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.webhook_url,
                        json=payload,
                        headers={'Content-Type': 'application/json'},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            return True
                        elif response.status == 429:  # Rate limited
                            retry_after = int(response.headers.get('Retry-After', 5))
                            logger.warning(f"Slack rate limited, waiting {retry_after}s...")
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            error_text = await response.text()
                            if attempt == max_retries - 1:
                                logger.error(f"Slack API error: {response.status} - {error_text}")
                                return False
                            wait_time = 2 ** attempt
                            logger.warning(f"Slack send attempt {attempt + 1} failed: {response.status}. Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to send to Slack after {max_retries} attempts: {e}")
                    return False
                wait_time = 2 ** attempt
                logger.warning(f"Slack connection attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
        return False
    
    async def send(self, alert: Alert) -> bool:
        """
        Send alert to Slack.
        
        Args:
            alert: Alert to send
        
        Returns:
            True if sent successfully
        """
        if not self.should_send(alert):
            return False
        
        try:
            payload = self._build_slack_payload(alert)
            
            # Send to Slack with retry logic
            success = await self._send_with_retry(payload)
            
            if success:
                logger.info(f"Slack alert sent successfully: {alert.title}")
                return True
            else:
                logger.error(f"Failed to send Slack alert: {alert.title}")
                return False
                        
        except Exception as e:
            logger.error(f"Unexpected error sending Slack alert: {str(e)}", exc_info=True)
            return False
    
    def _build_slack_payload(self, alert: Alert) -> Dict[str, Any]:
        """Build Slack message payload."""
        # Severity colors
        severity_colors = {
            AlertSeverity.CRITICAL: 'danger',
            AlertSeverity.HIGH: 'warning',
            AlertSeverity.MEDIUM: '#FFC107',
            AlertSeverity.LOW: 'good',
            AlertSeverity.INFO: '#0DCAF0'
        }
        
        # Severity emojis
        severity_emojis = {
            AlertSeverity.CRITICAL: ':rotating_light:',
            AlertSeverity.HIGH: ':warning:',
            AlertSeverity.MEDIUM: ':large_orange_diamond:',
            AlertSeverity.LOW: ':information_source:',
            AlertSeverity.INFO: ':bulb:'
        }
        
        color = severity_colors.get(alert.severity, '#6C757D')
        emoji = severity_emojis.get(alert.severity, ':bell:')
        
        # Build text with mentions for critical alerts
        text = f"{emoji} *{alert.title}*"
        if alert.severity == AlertSeverity.CRITICAL and self.mention_users:
            mentions = ' '.join([f"<@{user_id}>" for user_id in self.mention_users])
            text = f"{mentions} {text}"
        
        # Build attachment fields
        fields = [
            {
                'title': 'Severity',
                'value': alert.severity.value.upper(),
                'short': True
            },
            {
                'title': 'Time',
                'value': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'short': True
            },
            {
                'title': 'Source',
                'value': alert.source,
                'short': True
            }
        ]
        
        # Add details as fields
        if alert.details:
            for key, value in alert.details.items():
                # Limit to important details (first 5)
                if len(fields) >= 8:
                    break
                fields.append({
                    'title': key.replace('_', ' ').title(),
                    'value': str(value),
                    'short': len(str(value)) < 50
                })
        
        # Build blocks (new Slack message format)
        blocks = [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': f"{emoji} {alert.title}",
                    'emoji': True
                }
            },
            {
                'type': 'section',
                'fields': [
                    {
                        'type': 'mrkdwn',
                        'text': f"*Severity:*\n{alert.severity.value.upper()}"
                    },
                    {
                        'type': 'mrkdwn',
                        'text': f"*Time:*\n{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': alert.message
                }
            }
        ]
        
        # Add details section
        if alert.details:
            details_text = '\n'.join([
                f"*{key.replace('_', ' ').title()}:* {value}"
                for key, value in list(alert.details.items())[:5]
            ])
            blocks.append({
                'type': 'section',
                'fields': [
                    {
                        'type': 'mrkdwn',
                        'text': details_text
                    }
                ]
            })
        
        # Add tags
        if alert.tags:
            blocks.append({
                'type': 'context',
                'elements': [
                    {
                        'type': 'mrkdwn',
                        'text': f"Tags: {', '.join([f'`{tag}`' for tag in alert.tags])}"
                    }
                ]
            })
        
        # Build final payload
        payload = {
            'username': self.username,
            'icon_emoji': self.icon_emoji,
            'text': text,
            'blocks': blocks,
            # Fallback to attachments for older Slack versions
            'attachments': [
                {
                    'color': color,
                    'title': alert.title,
                    'text': alert.message,
                    'fields': fields,
                    'footer': alert.source,
                    'ts': int(alert.timestamp.timestamp())
                }
            ]
        }
        
        # Add channel override if specified
        if self.channel:
            payload['channel'] = self.channel
        
        return payload
