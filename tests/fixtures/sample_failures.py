"""
Sample Failure Fixtures

Canonical failure scenarios for failure analysis testing.
"""

from typing import Dict, Any, List


FIXED_TIMESTAMP = "2026-01-31T10:00:00Z"


def sample_timeout_failure() -> Dict[str, Any]:
    """Timeout failure."""
    return {
        'name': 'test_slow_api_call',
        'framework': 'pytest',
        'failure_type': 'ENVIRONMENT_ISSUE',
        'error_type': 'TimeoutError',
        'error_message': 'Request timed out after 30 seconds',
        'stack_trace': 'TimeoutError: Request timed out\n  at api_client.py:45\n  at test_api.py:12',
        'duration': 30.0,
        'timestamp': FIXED_TIMESTAMP,
        'signals': {
            'is_timeout': True,
            'is_network': True,
            'is_flaky': True
        }
    }


def sample_assertion_failure() -> Dict[str, Any]:
    """Assertion failure."""
    return {
        'name': 'test_user_count',
        'framework': 'pytest',
        'failure_type': 'PRODUCT_DEFECT',
        'error_type': 'AssertionError',
        'error_message': 'Expected 200, got 201',
        'stack_trace': 'AssertionError: Expected 200, got 201\n  at test_api.py:25',
        'expected': 200,
        'actual': 201,
        'duration': 1.5,
        'timestamp': FIXED_TIMESTAMP,
        'signals': {
            'is_assertion': True,
            'is_product_issue': True
        }
    }


def sample_locator_failure() -> Dict[str, Any]:
    """Element not found failure."""
    return {
        'name': 'test_click_submit',
        'framework': 'selenium',
        'failure_type': 'LOCATOR_ISSUE',
        'error_type': 'NoSuchElementException',
        'error_message': 'Unable to locate element: button#submit-order',
        'stack_trace': 'NoSuchElementException\n  at selenium_driver.py:123\n  at test_ui.py:34',
        'locator': {
            'type': 'CSS_SELECTOR',
            'value': 'button#submit-order'
        },
        'duration': 3.2,
        'timestamp': FIXED_TIMESTAMP,
        'signals': {
            'is_locator_issue': True,
            'needs_update': True
        }
    }


def sample_network_failure() -> Dict[str, Any]:
    """Network connection failure."""
    return {
        'name': 'test_external_api',
        'framework': 'pytest',
        'failure_type': 'ENVIRONMENT_ISSUE',
        'error_type': 'ConnectionError',
        'error_message': 'HTTPSConnectionPool: Max retries exceeded',
        'stack_trace': 'ConnectionError\n  at requests.py:456\n  at test_integration.py:67',
        'duration': 15.0,
        'timestamp': FIXED_TIMESTAMP,
        'signals': {
            'is_network': True,
            'is_external_dependency': True,
            'is_flaky': True
        }
    }


def sample_import_failure() -> Dict[str, Any]:
    """Import/module error."""
    return {
        'name': 'test_module_import',
        'framework': 'pytest',
        'failure_type': 'AUTOMATION_ISSUE',
        'error_type': 'ImportError',
        'error_message': 'cannot import name MyClass from my_module',
        'stack_trace': 'ImportError\n  at test_imports.py:5',
        'duration': 0.1,
        'timestamp': FIXED_TIMESTAMP,
        'signals': {
            'is_import_error': True,
            'blocks_execution': True
        }
    }


def sample_flaky_failure() -> Dict[str, Any]:
    """Flaky test failure (30% failure rate)."""
    return {
        'name': 'test_race_condition',
        'framework': 'pytest',
        'failure_type': 'FLAKY_TEST',
        'error_type': 'AssertionError',
        'error_message': 'Race condition: data not ready',
        'stack_trace': 'AssertionError\n  at test_async.py:89',
        'duration': 2.1,
        'timestamp': FIXED_TIMESTAMP,
        'history': {
            'total_runs': 10,
            'failures': 3,
            'failure_rate': 0.3
        },
        'signals': {
            'is_flaky': True,
            'is_timing_issue': True,
            'needs_stabilization': True
        }
    }


def sample_database_failure() -> Dict[str, Any]:
    """Database connection failure."""
    return {
        'name': 'test_database_query',
        'framework': 'pytest',
        'failure_type': 'ENVIRONMENT_ISSUE',
        'error_type': 'OperationalError',
        'error_message': 'Connection refused: localhost:5432',
        'stack_trace': 'OperationalError\n  at psycopg2.py:234\n  at test_db.py:45',
        'duration': 5.0,
        'timestamp': FIXED_TIMESTAMP,
        'signals': {
            'is_database_issue': True,
            'is_environment': True
        }
    }


def sample_permission_failure() -> Dict[str, Any]:
    """Permission/authorization failure."""
    return {
        'name': 'test_admin_access',
        'framework': 'pytest',
        'failure_type': 'PRODUCT_DEFECT',
        'error_type': 'HTTPError',
        'error_message': '403 Forbidden: insufficient permissions',
        'stack_trace': 'HTTPError\n  at requests.py:789\n  at test_auth.py:56',
        'http_status': 403,
        'duration': 1.2,
        'timestamp': FIXED_TIMESTAMP,
        'signals': {
            'is_permission_issue': True,
            'is_product_issue': True
        }
    }


def sample_failure_batch() -> List[Dict[str, Any]]:
    """Batch of 5 different failure types."""
    return [
        sample_timeout_failure(),
        sample_assertion_failure(),
        sample_locator_failure(),
        sample_network_failure(),
        sample_import_failure()
    ]


def sample_failure_with_context() -> Dict[str, Any]:
    """Failure with rich contextual information."""
    return {
        'name': 'test_payment_processing',
        'framework': 'pytest',
        'failure_type': 'PRODUCT_DEFECT',
        'error_type': 'ValueError',
        'error_message': 'Invalid payment method: crypto',
        'stack_trace': 'ValueError\n  at payment.py:123\n  at test_payment.py:78',
        'duration': 4.5,
        'timestamp': FIXED_TIMESTAMP,
        'context': {
            'browser': 'Chrome 120',
            'os': 'Windows 11',
            'test_data': {'amount': 100, 'currency': 'USD'},
            'environment': 'staging',
            'build_id': 'build-456'
        },
        'screenshots': [
            '/screenshots/payment-error-1.png',
            '/screenshots/payment-error-2.png'
        ],
        'logs': {
            'application_logs': ['ERROR: Payment validation failed'],
            'network_logs': ['POST /api/payments - 400'],
            'test_logs': ['FAIL: test_payment_processing']
        },
        'signals': {
            'is_product_issue': True,
            'has_screenshots': True,
            'has_logs': True
        }
    }
