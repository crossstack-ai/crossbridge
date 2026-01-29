"""
Confluence notifier for publishing alerts to Confluence pages.
"""

import json
from typing import Dict, Any, Optional
import logging
import time
import requests
from requests.auth import HTTPBasicAuth

from core.intelligence.api_change.alerting.base import AlertNotifier, Alert, AlertSeverity


logger = logging.getLogger(__name__)


class ConfluenceNotifier(AlertNotifier):
    """Send alerts to Confluence by creating or updating pages."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Confluence notifier.
        
        Config keys:
            - url: Confluence base URL (e.g., https://your-domain.atlassian.net)
            - username: Confluence username/email
            - auth_token: Confluence API token
            - space_key: Confluence space key where pages will be created
            - parent_page_id: ID of parent page (optional)
            - page_title_prefix: Prefix for created pages (default: "API Change Alert")
            - update_mode: 'create' or 'update' - create new pages or update existing
            - max_retries: Maximum retry attempts (default: 3)
            - retry_backoff: Retry backoff factor (default: 2)
        """
        super().__init__(config)
        self.url = config.get('url', '').rstrip('/')
        self.username = config.get('username')
        self.auth_token = config.get('auth_token')
        self.space_key = config.get('space_key')
        self.parent_page_id = config.get('parent_page_id')
        self.page_title_prefix = config.get('page_title_prefix', 'API Change Alert')
        self.update_mode = config.get('update_mode', 'create')
        self.max_retries = config.get('max_retries', 3)
        self.retry_backoff = config.get('retry_backoff', 2)
        
        # Validate required config
        if not all([self.url, self.username, self.auth_token, self.space_key]):
            logger.warning("Confluence notifier missing required config (url, username, auth_token, space_key)")
            self.enabled = False
        
        # Setup authentication
        self.auth = HTTPBasicAuth(self.username, self.auth_token)
        
        # API endpoints
        self.api_base = f"{self.url}/rest/api"
        self.content_url = f"{self.api_base}/content"
    
    def _send_with_retry(self, alert: Alert) -> bool:
        """Send to Confluence with retry logic."""
        for attempt in range(self.max_retries):
            try:
                # Check if page exists (in update mode)
                if self.update_mode == 'update':
                    page_id = self._find_existing_page(alert)
                    if page_id:
                        return self._update_page(page_id, alert)
                
                # Create new page
                return self._create_page(alert)
                
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to send to Confluence after {self.max_retries} attempts: {e}")
                    return False
                wait_time = self.retry_backoff ** attempt
                logger.warning(f"Confluence connection attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error sending to Confluence: {e}", exc_info=True)
                return False
        
        return False
    
    async def send(self, alert: Alert) -> bool:
        """
        Send alert to Confluence.
        
        Args:
            alert: Alert to send
        
        Returns:
            True if sent successfully
        """
        if not self.should_send(alert):
            return False
        
        try:
            success = self._send_with_retry(alert)
            
            if success:
                logger.info(f"Confluence alert sent successfully: {alert.title}")
                return True
            else:
                logger.error(f"Failed to send Confluence alert: {alert.title}")
                return False
                        
        except Exception as e:
            logger.error(f"Unexpected error sending Confluence alert: {str(e)}", exc_info=True)
            return False
    
    def _find_existing_page(self, alert: Alert) -> Optional[str]:
        """Find existing page by title."""
        page_title = self._build_page_title(alert)
        
        try:
            params = {
                'spaceKey': self.space_key,
                'title': page_title,
                'expand': 'version'
            }
            
            response = requests.get(
                self.content_url,
                params=params,
                auth=self.auth,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    return data['results'][0]['id']
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding Confluence page: {e}")
            return None
    
    def _create_page(self, alert: Alert) -> bool:
        """Create new Confluence page."""
        page_title = self._build_page_title(alert)
        page_content = self._build_page_content(alert)
        
        payload = {
            'type': 'page',
            'title': page_title,
            'space': {
                'key': self.space_key
            },
            'body': {
                'storage': {
                    'value': page_content,
                    'representation': 'storage'
                }
            }
        }
        
        # Add parent page if specified
        if self.parent_page_id:
            payload['ancestors'] = [{'id': str(self.parent_page_id)}]
        
        try:
            response = requests.post(
                self.content_url,
                json=payload,
                auth=self.auth,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                page_url = f"{self.url}{data['_links']['webui']}"
                logger.info(f"Created Confluence page: {page_url}")
                return True
            else:
                logger.error(f"Failed to create Confluence page: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating Confluence page: {e}")
            return False
    
    def _update_page(self, page_id: str, alert: Alert) -> bool:
        """Update existing Confluence page."""
        try:
            # Get current version
            response = requests.get(
                f"{self.content_url}/{page_id}",
                params={'expand': 'version,body.storage'},
                auth=self.auth,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get page version: {response.status_code}")
                return False
            
            current_data = response.json()
            current_version = current_data['version']['number']
            
            # Build updated content
            page_title = self._build_page_title(alert)
            page_content = self._build_page_content(alert, append_mode=True)
            
            # Append to existing content
            existing_content = current_data['body']['storage']['value']
            updated_content = f"{existing_content}\n\n<hr/>\n\n{page_content}"
            
            # Update payload
            payload = {
                'type': 'page',
                'title': page_title,
                'version': {
                    'number': current_version + 1,
                    'message': f'Updated by CrossBridge AI - {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")}'
                },
                'body': {
                    'storage': {
                        'value': updated_content,
                        'representation': 'storage'
                    }
                }
            }
            
            # Update page
            response = requests.put(
                f"{self.content_url}/{page_id}",
                json=payload,
                auth=self.auth,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                page_url = f"{self.url}{data['_links']['webui']}"
                logger.info(f"Updated Confluence page: {page_url}")
                return True
            else:
                logger.error(f"Failed to update Confluence page: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating Confluence page: {e}")
            return False
    
    def _build_page_title(self, alert: Alert) -> str:
        """Build page title from alert."""
        timestamp = alert.timestamp.strftime('%Y-%m-%d %H:%M')
        return f"{self.page_title_prefix} - {alert.title} ({timestamp})"
    
    def _build_page_content(self, alert: Alert, append_mode: bool = False) -> str:
        """Build Confluence page content (storage format)."""
        # Severity colors and icons
        severity_colors = {
            AlertSeverity.CRITICAL: 'Red',
            AlertSeverity.HIGH: 'Yellow',
            AlertSeverity.MEDIUM: 'Blue',
            AlertSeverity.LOW: 'Green',
            AlertSeverity.INFO: 'Grey'
        }
        
        severity_emojis = {
            AlertSeverity.CRITICAL: '🔴',
            AlertSeverity.HIGH: '⚠️',
            AlertSeverity.MEDIUM: '🔶',
            AlertSeverity.LOW: 'ℹ️',
            AlertSeverity.INFO: '💡'
        }
        
        color = severity_colors.get(alert.severity, 'Grey')
        emoji = severity_emojis.get(alert.severity, '🔔')
        
        # Build content in Confluence storage format (HTML-like)
        content_parts = []
        
        # Header
        if not append_mode:
            content_parts.append(f'<h1>{emoji} {alert.title}</h1>')
        else:
            content_parts.append(f'<h2>{emoji} {alert.title}</h2>')
        
        # Status macro for severity
        content_parts.append(
            f'<ac:structured-macro ac:name="status" ac:schema-version="1">'
            f'<ac:parameter ac:name="colour">{color}</ac:parameter>'
            f'<ac:parameter ac:name="title">{alert.severity.value.upper()}</ac:parameter>'
            f'</ac:structured-macro>'
        )
        
        # Timestamp
        content_parts.append(f'<p><strong>Time:</strong> {alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}</p>')
        content_parts.append(f'<p><strong>Source:</strong> {alert.source}</p>')
        
        # Message
        content_parts.append(f'<h3>Message</h3>')
        content_parts.append(f'<p>{alert.message.replace(chr(10), "<br/>")}</p>')
        
        # Details as table
        if alert.details:
            content_parts.append('<h3>Details</h3>')
            content_parts.append('<table>')
            content_parts.append('<tbody>')
            for key, value in alert.details.items():
                content_parts.append(
                    f'<tr>'
                    f'<td><strong>{key.replace("_", " ").title()}</strong></td>'
                    f'<td>{self._escape_html(str(value))}</td>'
                    f'</tr>'
                )
            content_parts.append('</tbody>')
            content_parts.append('</table>')
        
        # Tags
        if alert.tags:
            content_parts.append('<h3>Tags</h3>')
            content_parts.append('<p>')
            for tag in alert.tags:
                content_parts.append(
                    f'<ac:structured-macro ac:name="status" ac:schema-version="1">'
                    f'<ac:parameter ac:name="colour">Grey</ac:parameter>'
                    f'<ac:parameter ac:name="title">{tag}</ac:parameter>'
                    f'</ac:structured-macro> '
                )
            content_parts.append('</p>')
        
        # Info panel with timestamp
        content_parts.append(
            f'<ac:structured-macro ac:name="info" ac:schema-version="1">'
            f'<ac:rich-text-body>'
            f'<p>This alert was automatically generated by CrossBridge AI on '
            f'{alert.timestamp.strftime("%Y-%m-%d at %H:%M:%S UTC")}</p>'
            f'</ac:rich-text-body>'
            f'</ac:structured-macro>'
        )
        
        return '\n'.join(content_parts)
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
    
    def test_connection(self) -> bool:
        """Test Confluence connection."""
        try:
            response = requests.get(
                f"{self.api_base}/space/{self.space_key}",
                auth=self.auth,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Confluence connection successful: {self.space_key}")
                return True
            else:
                logger.error(f"Confluence connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Confluence connection test failed: {e}")
            return False
