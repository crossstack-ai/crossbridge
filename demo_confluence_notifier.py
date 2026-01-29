"""
Demo script for testing Confluence notifier.

This script tests the Confluence integration by:
1. Testing connection to Confluence
2. Sending a sample alert
3. Verifying page creation

Usage:
    python demo_confluence_notifier.py

Environment Variables Required:
    CONFLUENCE_URL: Your Confluence base URL
    CONFLUENCE_USER: Your Confluence username/email
    CONFLUENCE_TOKEN: Your Confluence API token
    CONFLUENCE_SPACE: Your Confluence space key
"""

import asyncio
import os
from datetime import datetime

from core.intelligence.api_change.alerting.confluence_notifier import ConfluenceNotifier
from core.intelligence.api_change.alerting.base import Alert, AlertSeverity


def test_confluence_connection():
    """Test Confluence connection."""
    print("=" * 70)
    print("Testing Confluence Connection")
    print("=" * 70)
    
    # Get config from environment
    config = {
        'url': os.getenv('CONFLUENCE_URL'),
        'username': os.getenv('CONFLUENCE_USER'),
        'auth_token': os.getenv('CONFLUENCE_TOKEN'),
        'space_key': os.getenv('CONFLUENCE_SPACE', 'API'),
        'page_title_prefix': 'Test Alert',
        'update_mode': 'create',
        'max_retries': 3,
        'retry_backoff': 2
    }
    
    # Validate config
    if not all([config['url'], config['username'], config['auth_token']]):
        print("❌ Missing required environment variables:")
        print("   - CONFLUENCE_URL")
        print("   - CONFLUENCE_USER")
        print("   - CONFLUENCE_TOKEN")
        print("\nExample:")
        print('   export CONFLUENCE_URL="https://your-domain.atlassian.net"')
        print('   export CONFLUENCE_USER="your-email@example.com"')
        print('   export CONFLUENCE_TOKEN="your-api-token"')
        print('   export CONFLUENCE_SPACE="API"')
        return False
    
    print(f"URL: {config['url']}")
    print(f"User: {config['username']}")
    print(f"Space: {config['space_key']}")
    print()
    
    # Create notifier
    notifier = ConfluenceNotifier(config)
    
    if not notifier.enabled:
        print("❌ Notifier not enabled - check configuration")
        return False
    
    # Test connection
    print("Testing connection...")
    if notifier.test_connection():
        print("✅ Connection successful!")
        return True
    else:
        print("❌ Connection failed")
        return False


async def send_test_alert():
    """Send a test alert to Confluence."""
    print("\n" + "=" * 70)
    print("Sending Test Alert")
    print("=" * 70)
    
    # Get config from environment
    config = {
        'url': os.getenv('CONFLUENCE_URL'),
        'username': os.getenv('CONFLUENCE_USER'),
        'auth_token': os.getenv('CONFLUENCE_TOKEN'),
        'space_key': os.getenv('CONFLUENCE_SPACE', 'API'),
        'page_title_prefix': 'CrossBridge Test Alert',
        'update_mode': 'create',
        'max_retries': 3,
        'retry_backoff': 2
    }
    
    # Create notifier
    notifier = ConfluenceNotifier(config)
    
    if not notifier.enabled:
        print("❌ Notifier not enabled - check configuration")
        return False
    
    # Create sample alert
    alert = Alert(
        title="API Breaking Change Detected",
        message=(
            "CrossBridge AI has detected a breaking change in your API:\n\n"
            "The endpoint GET /api/users has a removed field 'phoneNumber' "
            "which is used by 12 tests in your test suite.\n\n"
            "Recommended actions:\n"
            "  • Review the change impact\n"
            "  • Update affected tests\n"
            "  • Consider versioning strategy"
        ),
        severity=AlertSeverity.CRITICAL,
        timestamp=datetime.utcnow(),
        source="API Change Intelligence - Demo",
        details={
            'Change Type': 'field_removed',
            'Endpoint': 'GET /api/users',
            'Field': 'phoneNumber',
            'Risk Level': 'CRITICAL',
            'Breaking': 'Yes',
            'Affected Tests': 12,
            'Confidence': '85%'
        },
        tags=['breaking', 'api-change', 'critical', 'demo']
    )
    
    print(f"Title: {alert.title}")
    print(f"Severity: {alert.severity.value}")
    print(f"Message: {alert.message[:50]}...")
    print()
    
    # Send alert
    print("Sending alert to Confluence...")
    success = await notifier.send(alert)
    
    if success:
        print("✅ Alert sent successfully!")
        print(f"\nCheck your Confluence space: {config['space_key']}")
        print(f"Look for page: {notifier.page_title_prefix} - {alert.title}")
        return True
    else:
        print("❌ Failed to send alert")
        return False


async def send_multiple_severity_alerts():
    """Send alerts of different severities."""
    print("\n" + "=" * 70)
    print("Sending Multiple Alerts (Different Severities)")
    print("=" * 70)
    
    config = {
        'url': os.getenv('CONFLUENCE_URL'),
        'username': os.getenv('CONFLUENCE_USER'),
        'auth_token': os.getenv('CONFLUENCE_TOKEN'),
        'space_key': os.getenv('CONFLUENCE_SPACE', 'API'),
        'page_title_prefix': 'API Change Alert',
        'update_mode': 'create',
        'max_retries': 3,
        'retry_backoff': 2
    }
    
    notifier = ConfluenceNotifier(config)
    
    if not notifier.enabled:
        print("❌ Notifier not enabled")
        return False
    
    # Create alerts with different severities
    alerts = [
        Alert(
            title="Critical: Breaking Change in Authentication",
            message="OAuth endpoint changed, all auth flows affected",
            severity=AlertSeverity.CRITICAL,
            timestamp=datetime.utcnow(),
            source="API Change Intelligence",
            details={'Endpoint': 'POST /auth/token', 'Impact': 'All users'},
            tags=['breaking', 'auth']
        ),
        Alert(
            title="High: New Required Parameter",
            message="Endpoint now requires 'apiVersion' parameter",
            severity=AlertSeverity.HIGH,
            timestamp=datetime.utcnow(),
            source="API Change Intelligence",
            details={'Endpoint': 'GET /api/data', 'Parameter': 'apiVersion'},
            tags=['parameter-added']
        ),
        Alert(
            title="Medium: Response Format Change",
            message="Date fields now in ISO8601 format",
            severity=AlertSeverity.MEDIUM,
            timestamp=datetime.utcnow(),
            source="API Change Intelligence",
            details={'Format': 'ISO8601', 'Fields': '12'},
            tags=['format-change']
        ),
        Alert(
            title="Info: New Endpoint Available",
            message="New endpoint GET /api/v2/stats added",
            severity=AlertSeverity.INFO,
            timestamp=datetime.utcnow(),
            source="API Change Intelligence",
            details={'Endpoint': 'GET /api/v2/stats'},
            tags=['addition']
        )
    ]
    
    success_count = 0
    for i, alert in enumerate(alerts, 1):
        print(f"\n[{i}/{len(alerts)}] Sending {alert.severity.value} alert...")
        success = await notifier.send(alert)
        if success:
            print(f"  ✅ Sent: {alert.title}")
            success_count += 1
        else:
            print(f"  ❌ Failed: {alert.title}")
    
    print(f"\n{'='*70}")
    print(f"Summary: {success_count}/{len(alerts)} alerts sent successfully")
    print(f"{'='*70}")
    
    return success_count == len(alerts)


async def main():
    """Main test function."""
    print("\n🚀 CrossBridge AI - Confluence Notifier Demo")
    print("=" * 70)
    
    # Test 1: Connection
    if not test_confluence_connection():
        print("\n❌ Connection test failed. Please check your configuration.")
        return
    
    # Test 2: Send single alert
    await send_test_alert()
    
    # Test 3: Send multiple alerts (optional)
    print("\n" + "=" * 70)
    response = input("\nSend multiple test alerts? (y/n): ").strip().lower()
    if response == 'y':
        await send_multiple_severity_alerts()
    
    print("\n" + "=" * 70)
    print("✅ Demo Complete!")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. Check your Confluence space for created pages")
    print("2. Review the alert formatting and content")
    print("3. Configure in crossbridge.yml for production use")
    print("\nConfiguration example:")
    print("""
    alerts:
      confluence:
        enabled: true
        url: ${CONFLUENCE_URL}
        username: ${CONFLUENCE_USER}
        auth_token: ${CONFLUENCE_TOKEN}
        space_key: API
        page_title_prefix: "API Change Alert"
        update_mode: create
        min_severity: high
    """)


if __name__ == '__main__':
    asyncio.run(main())
