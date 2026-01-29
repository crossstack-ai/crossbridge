"""
Email notifier for sending alerts via SMTP.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
import logging
import time
from functools import wraps

from core.intelligence.api_change.alerting.base import AlertNotifier, Alert, AlertSeverity


logger = logging.getLogger(__name__)


class EmailNotifier(AlertNotifier):
    """Send alerts via email using SMTP."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize email notifier.
        
        Config keys:
            - smtp_host: SMTP server host
            - smtp_port: SMTP server port (default: 587)
            - smtp_user: SMTP username
            - smtp_password: SMTP password
            - use_tls: Whether to use TLS (default: True)
            - from_email: Sender email address
            - to_emails: List of recipient email addresses
            - subject_prefix: Prefix for email subjects (default: "[CrossBridge Alert]")
        """
        super().__init__(config)
        self.smtp_host = config.get('smtp_host')
        self.smtp_port = config.get('smtp_port', 587)
        self.smtp_user = config.get('smtp_user')
        self.smtp_password = config.get('smtp_password')
        self.use_tls = config.get('use_tls', True)
        self.from_email = config.get('from_email')
        self.to_emails = config.get('to_emails', [])
        self.subject_prefix = config.get('subject_prefix', '[CrossBridge Alert]')
        
        # Validate required config
        if not all([self.smtp_host, self.smtp_user, self.smtp_password, self.from_email]):
            logger.warning("Email notifier missing required configuration")
            self.enabled = False
    
    def _send_with_retry(self, msg: MIMEMultipart, max_retries: int = 3) -> bool:
        """Send email with retry logic."""
        for attempt in range(max_retries):
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
                return True
            except (smtplib.SMTPException, ConnectionError, TimeoutError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to send email after {max_retries} attempts: {e}")
                    return False
                wait_time = 2 ** attempt
                logger.warning(f"Email send attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        return False
    
    async def send(self, alert: Alert) -> bool:
        """
        Send alert via email.
        
        Args:
            alert: Alert to send
        
        Returns:
            True if sent successfully
        """
        if not self.should_send(alert):
            return False
        
        if not self.to_emails:
            logger.warning("No recipient emails configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"{self.subject_prefix} {alert.title}"
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # Create HTML and plain text versions
            text_body = self._format_text_body(alert)
            html_body = self._format_html_body(alert)
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email with retry logic
            success = self._send_with_retry(msg)
            
            if success:
                logger.info(f"Email alert sent successfully: {alert.title}")
                return True
            else:
                logger.error(f"Failed to send email alert: {alert.title}")
                return False
            
        except Exception as e:
            logger.error(f"Unexpected error sending email alert: {str(e)}", exc_info=True)
            return False
    
    def _format_text_body(self, alert: Alert) -> str:
        """Format plain text email body."""
        lines = [
            f"Alert: {alert.title}",
            f"Severity: {alert.severity.value.upper()}",
            f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Source: {alert.source}",
            "",
            "Message:",
            alert.message,
            ""
        ]
        
        if alert.details:
            lines.append("Details:")
            for key, value in alert.details.items():
                lines.append(f"  {key}: {value}")
            lines.append("")
        
        if alert.tags:
            lines.append(f"Tags: {', '.join(alert.tags)}")
        
        return '\n'.join(lines)
    
    def _format_html_body(self, alert: Alert) -> str:
        """Format HTML email body."""
        severity_colors = {
            AlertSeverity.CRITICAL: '#DC3545',
            AlertSeverity.HIGH: '#FD7E14',
            AlertSeverity.MEDIUM: '#FFC107',
            AlertSeverity.LOW: '#20C997',
            AlertSeverity.INFO: '#0DCAF0'
        }
        
        color = severity_colors.get(alert.severity, '#6C757D')
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .alert-box {{ 
                    border-left: 4px solid {color}; 
                    padding: 15px; 
                    margin: 20px 0;
                    background-color: #f8f9fa;
                }}
                .alert-title {{ 
                    font-size: 20px; 
                    font-weight: bold; 
                    color: {color};
                    margin-bottom: 10px;
                }}
                .alert-meta {{ 
                    color: #6c757d; 
                    font-size: 14px; 
                    margin-bottom: 15px;
                }}
                .alert-message {{ 
                    font-size: 16px; 
                    margin: 15px 0;
                    white-space: pre-wrap;
                }}
                .details-table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin: 15px 0;
                }}
                .details-table td {{ 
                    padding: 8px; 
                    border: 1px solid #dee2e6;
                }}
                .details-table td:first-child {{ 
                    font-weight: bold; 
                    background-color: #e9ecef;
                    width: 150px;
                }}
                .tags {{ 
                    margin-top: 15px;
                }}
                .tag {{ 
                    display: inline-block; 
                    background-color: #e9ecef; 
                    padding: 4px 12px; 
                    border-radius: 12px; 
                    margin-right: 5px;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="alert-box">
                <div class="alert-title">{alert.title}</div>
                <div class="alert-meta">
                    <strong>Severity:</strong> {alert.severity.value.upper()} | 
                    <strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | 
                    <strong>Source:</strong> {alert.source}
                </div>
                <div class="alert-message">{alert.message}</div>
        """
        
        if alert.details:
            html += '<table class="details-table">'
            for key, value in alert.details.items():
                html += f'<tr><td>{key}</td><td>{value}</td></tr>'
            html += '</table>'
        
        if alert.tags:
            html += '<div class="tags">'
            for tag in alert.tags:
                html += f'<span class="tag">{tag}</span>'
            html += '</div>'
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html
