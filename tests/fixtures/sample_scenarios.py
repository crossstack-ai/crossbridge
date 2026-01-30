"""
Sample Scenario Fixtures

Complete test scenarios representing common testing patterns.
"""

from typing import Dict, Any, List


FIXED_TIMESTAMP = "2026-01-31T10:00:00Z"


def sample_login_scenario() -> Dict[str, Any]:
    """Multi-case login scenario."""
    return {
        'scenario_name': 'User Login',
        'cases': [
            {
                'name': 'test_valid_login',
                'credentials': {'username': 'admin', 'password': 'admin123'},
                'expected': 'success',
                'status': 'passed',
                'duration': 2.5
            },
            {
                'name': 'test_invalid_password',
                'credentials': {'username': 'admin', 'password': 'wrong'},
                'expected': 'failure',
                'status': 'passed',
                'duration': 1.8
            },
            {
                'name': 'test_empty_credentials',
                'credentials': {'username': '', 'password': ''},
                'expected': 'validation_error',
                'status': 'passed',
                'duration': 1.2
            }
        ],
        'total_duration': 5.5,
        'timestamp': FIXED_TIMESTAMP
    }


def sample_api_scenario() -> Dict[str, Any]:
    """CRUD API testing scenario."""
    return {
        'scenario_name': 'User API CRUD',
        'operations': [
            {
                'name': 'test_create_user',
                'method': 'POST',
                'endpoint': '/api/v1/users',
                'status_code': 201,
                'duration': 0.8
            },
            {
                'name': 'test_get_user',
                'method': 'GET',
                'endpoint': '/api/v1/users/123',
                'status_code': 200,
                'duration': 0.3
            },
            {
                'name': 'test_update_user',
                'method': 'PUT',
                'endpoint': '/api/v1/users/123',
                'status_code': 200,
                'duration': 0.6
            },
            {
                'name': 'test_delete_user',
                'method': 'DELETE',
                'endpoint': '/api/v1/users/123',
                'status_code': 204,
                'duration': 0.4
            }
        ],
        'total_duration': 2.1,
        'timestamp': FIXED_TIMESTAMP
    }


def sample_bdd_scenario() -> Dict[str, Any]:
    """BDD-style scenario."""
    return {
        'feature': 'Shopping Cart',
        'scenario': 'Add item to cart',
        'steps': [
            {
                'type': 'Given',
                'text': 'user is on the product page',
                'status': 'passed'
            },
            {
                'type': 'When',
                'text': 'user clicks add to cart',
                'status': 'passed'
            },
            {
                'type': 'Then',
                'text': 'cart count should increase by 1',
                'status': 'passed'
            }
        ],
        'status': 'passed',
        'duration': 3.2,
        'timestamp': FIXED_TIMESTAMP
    }


def sample_e2e_scenario() -> Dict[str, Any]:
    """End-to-end user journey."""
    return {
        'journey': 'Complete Purchase Flow',
        'phases': [
            {
                'phase': 'Registration',
                'tests': ['test_signup', 'test_email_verification'],
                'duration': 5.2
            },
            {
                'phase': 'Product Discovery',
                'tests': ['test_search', 'test_filter', 'test_product_details'],
                'duration': 8.1
            },
            {
                'phase': 'Shopping',
                'tests': ['test_add_to_cart', 'test_update_quantity'],
                'duration': 6.5
            },
            {
                'phase': 'Checkout',
                'tests': ['test_shipping', 'test_payment', 'test_order_confirmation'],
                'duration': 12.3
            },
            {
                'phase': 'Post-Purchase',
                'tests': ['test_order_history', 'test_tracking'],
                'duration': 4.8
            }
        ],
        'total_duration': 36.9,
        'status': 'passed',
        'timestamp': FIXED_TIMESTAMP
    }


def sample_regression_suite() -> Dict[str, Any]:
    """Regression test suite."""
    return {
        'suite_name': 'Core Regression Suite',
        'categories': [
            {
                'category': 'Authentication',
                'tests': ['test_login', 'test_logout', 'test_session'],
                'passed': 3,
                'failed': 0
            },
            {
                'category': 'Payments',
                'tests': ['test_checkout', 'test_refund', 'test_subscription'],
                'passed': 2,
                'failed': 1
            },
            {
                'category': 'Search',
                'tests': ['test_basic_search', 'test_advanced_search'],
                'passed': 2,
                'failed': 0
            }
        ],
        'total_duration': 45.2,
        'timestamp': FIXED_TIMESTAMP
    }


def sample_smoke_test_suite() -> Dict[str, Any]:
    """Quick smoke test suite (< 5 minutes)."""
    return {
        'suite_name': 'Smoke Tests',
        'tests': [
            {'name': 'test_homepage_loads', 'duration': 1.2, 'status': 'passed'},
            {'name': 'test_login_works', 'duration': 2.3, 'status': 'passed'},
            {'name': 'test_api_health', 'duration': 0.5, 'status': 'passed'},
            {'name': 'test_database_connection', 'duration': 0.8, 'status': 'passed'},
            {'name': 'test_cache_available', 'duration': 0.3, 'status': 'passed'}
        ],
        'total_duration': 5.1,
        'all_passed': True,
        'timestamp': FIXED_TIMESTAMP
    }


def sample_performance_scenario() -> Dict[str, Any]:
    """Performance testing scenario."""
    return {
        'scenario_name': 'Load Testing',
        'benchmarks': [
            {
                'name': 'homepage_response_time',
                'target': 200,  # ms
                'actual': 185,
                'status': 'passed'
            },
            {
                'name': 'api_throughput',
                'target': 1000,  # requests/sec
                'actual': 1250,
                'status': 'passed'
            },
            {
                'name': 'database_query_time',
                'target': 50,  # ms
                'actual': 42,
                'status': 'passed'
            }
        ],
        'duration': 300.0,  # 5 minutes
        'timestamp': FIXED_TIMESTAMP
    }
