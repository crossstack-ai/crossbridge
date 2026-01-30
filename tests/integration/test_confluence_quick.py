"""Quick test runner for Confluence notifier - isolated tests without full dependencies."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that we can import the modules."""
    try:
        from core.intelligence.api_change.alerting.confluence_notifier import ConfluenceNotifier
        from core.intelligence.api_change.alerting.base import Alert, AlertSeverity
        print("✅ Imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_configuration():
    """Test Confluence notifier configuration."""
    from core.intelligence.api_change.alerting.confluence_notifier import ConfluenceNotifier
    
    # Test valid config
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
    assert notifier.space_key == 'TEST'
    assert notifier.enabled is True
    print("✅ Configuration test passed")
    
    # Test missing config
    config_missing = {'enabled': True, 'url': 'https://test.atlassian.net'}
    notifier_missing = ConfluenceNotifier(config_missing)
    assert notifier_missing.enabled is False
    print("✅ Missing config handled correctly")
    
    return True


def test_formatting():
    """Test page formatting."""
    from core.intelligence.api_change.alerting.confluence_notifier import ConfluenceNotifier
    from core.intelligence.api_change.alerting.base import Alert, AlertSeverity
    from datetime import datetime
    
    config = {
        'url': 'https://test.atlassian.net',
        'username': 'test@example.com',
        'auth_token': 'test-token',
        'space_key': 'TEST'
    }
    
    notifier = ConfluenceNotifier(config)
    
    # Test page title
    alert = Alert(
        title="Breaking Change",
        message="Test",
        severity=AlertSeverity.CRITICAL,
        timestamp=datetime(2026, 1, 29, 12, 30),
        source="Test"
    )
    
    title = notifier._build_page_title(alert)
    assert 'API Change Alert' in title
    assert 'Breaking Change' in title
    assert '2026-01-29' in title
    print("✅ Page title formatting passed")
    
    # Test page content
    alert_with_details = Alert(
        title="Critical Alert",
        message="This is a critical message",
        severity=AlertSeverity.CRITICAL,
        timestamp=datetime.utcnow(),
        source="API Change Intelligence",
        details={'Endpoint': 'GET /api/users', 'Impact': 'High'},
        tags=['breaking', 'api']
    )
    
    content = notifier._build_page_content(alert_with_details)
    assert 'CRITICAL' in content
    assert 'Red' in content
    assert '🔴' in content
    assert 'GET /api/users' in content
    assert 'breaking' in content
    print("✅ Page content formatting passed")
    
    # Test HTML escaping
    text = '<script>alert("XSS")</script>'
    escaped = notifier._escape_html(text)
    assert '&lt;' in escaped
    assert '&gt;' in escaped
    assert '<script>' not in escaped
    print("✅ HTML escaping passed")
    
    return True


def test_alert_manager_init():
    """Test alert manager with Confluence."""
    from core.intelligence.api_change.alerting.alert_manager import AlertManager
    
    # Test with Confluence enabled
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
    print("✅ Alert manager initialization passed")
    
    # Test with multiple notifiers
    config_multi = {
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
    
    manager_multi = AlertManager(config_multi)
    assert len(manager_multi.notifiers) == 2
    notifier_types = [n.__class__.__name__ for n in manager_multi.notifiers]
    assert 'SlackNotifier' in notifier_types
    assert 'ConfluenceNotifier' in notifier_types
    print("✅ Multi-notifier initialization passed")
    
    return True


def run_all_tests():
    """Run all quick tests."""
    print("\n" + "="*70)
    print("Running Confluence Notifier Quick Tests")
    print("="*70 + "\n")
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Formatting", test_formatting),
        ("Alert Manager", test_alert_manager_init),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\n[*] Testing: {name}")
        print("-" * 70)
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"[FAIL] {name} failed")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70 + "\n")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
