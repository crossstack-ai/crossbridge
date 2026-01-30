"""
Sample Test Fixtures

Canonical test objects for consistent testing across all frameworks.

These are regular functions (not pytest fixtures) that return deterministic test data.
"""

from datetime import datetime
from typing import Dict, Any, List


# Fixed timestamp for deterministic tests
FIXED_TIMESTAMP = "2026-01-31T10:00:00Z"
FIXED_DATETIME = datetime(2026, 1, 31, 10, 0, 0)


def sample_test() -> Dict[str, Any]:
    """
    Basic test fixture with minimal required fields.
    
    Use this for generic testing scenarios.
    """
    return {
        'name': 'test_valid_login',
        'framework': 'pytest',
        'file_path': '/tests/test_login.py',
        'steps': [
            'open page',
            'login',
            'verify dashboard'
        ],
        'intent': 'verify valid login',
        'status': 'passed',
        'duration': 2.5,
        'timestamp': FIXED_TIMESTAMP
    }


def sample_pytest_test() -> Dict[str, Any]:
    """Pytest-specific test fixture."""
    return {
        'name': 'test_user_registration',
        'framework': 'pytest',
        'file_path': '/tests/test_auth.py',
        'class_name': 'TestUserAuthentication',
        'steps': [
            'navigate to registration page',
            'fill registration form',
            'submit form',
            'verify success message'
        ],
        'intent': 'verify user can register successfully',
        'status': 'passed',
        'duration': 3.2,
        'timestamp': FIXED_TIMESTAMP,
        'markers': ['smoke', 'auth'],
        'parametrize': None
    }


def sample_selenium_test() -> Dict[str, Any]:
    """Selenium test with locators."""
    return {
        'name': 'test_checkout_flow',
        'framework': 'selenium',
        'file_path': '/tests/test_checkout.py',
        'steps': [
            'add item to cart',
            'proceed to checkout',
            'enter shipping info',
            'complete payment'
        ],
        'intent': 'verify checkout process',
        'status': 'passed',
        'duration': 8.5,
        'timestamp': FIXED_TIMESTAMP,
        'locators': [
            {'type': 'ID', 'value': 'add-to-cart-btn'},
            {'type': 'CSS_SELECTOR', 'value': '.checkout-button'},
            {'type': 'XPATH', 'value': '//input[@name="shipping"]'},
            {'type': 'NAME', 'value': 'payment-method'}
        ]
    }


def sample_robot_test() -> Dict[str, Any]:
    """Robot Framework test."""
    return {
        'name': 'Verify Login With Valid Credentials',
        'framework': 'robot',
        'file_path': '/tests/login.robot',
        'keywords': [
            'Open Browser',
            'Input Text',
            'Click Button',
            'Page Should Contain'
        ],
        'intent': 'verify valid login credentials work',
        'status': 'passed',
        'duration': 4.1,
        'timestamp': FIXED_TIMESTAMP
    }


def sample_cypress_test() -> Dict[str, Any]:
    """Cypress E2E test."""
    return {
        'name': 'should display dashboard after login',
        'framework': 'cypress',
        'file_path': '/cypress/e2e/login.cy.js',
        'steps': [
            'cy.visit(\'/login\')',
            'cy.get(\'[data-cy=username]\').type(\'user\')',
            'cy.get(\'[data-cy=password]\').type(\'pass\')',
            'cy.get(\'[data-cy=submit]\').click()',
            'cy.url().should(\'include\', \'/dashboard\')'
        ],
        'intent': 'verify login redirects to dashboard',
        'status': 'passed',
        'duration': 2.8,
        'timestamp': FIXED_TIMESTAMP
    }


def sample_rest_assured_test() -> Dict[str, Any]:
    """REST Assured API test."""
    return {
        'name': 'test_get_user_by_id',
        'framework': 'rest_assured',
        'file_path': '/tests/api/TestUserAPI.java',
        'endpoint': '/api/v1/users/123',
        'method': 'GET',
        'steps': [
            'send GET request',
            'verify status 200',
            'verify response body'
        ],
        'intent': 'verify GET user endpoint',
        'status': 'passed',
        'duration': 1.2,
        'timestamp': FIXED_TIMESTAMP
    }


def sample_playwright_test() -> Dict[str, Any]:
    """Playwright test."""
    return {
        'name': 'test search functionality',
        'framework': 'playwright',
        'file_path': '/tests/test_search.py',
        'steps': [
            'navigate to homepage',
            'enter search term',
            'click search button',
            'verify results displayed'
        ],
        'intent': 'verify search returns results',
        'status': 'passed',
        'duration': 3.5,
        'timestamp': FIXED_TIMESTAMP,
        'selectors': [
            {'type': 'text', 'value': 'Search'},
            {'type': 'placeholder', 'value': 'Enter search term'},
            {'type': 'role', 'value': 'button', 'name': 'Search'}
        ]
    }


def sample_test_with_parameters() -> Dict[str, Any]:
    """Parametrized test."""
    return {
        'name': 'test_login_with_credentials',
        'framework': 'pytest',
        'file_path': '/tests/test_parametrized.py',
        'parameters': [
            {'username': 'admin', 'password': 'admin123', 'expected': 'success'},
            {'username': 'user', 'password': 'user123', 'expected': 'success'},
            {'username': 'invalid', 'password': 'wrong', 'expected': 'failure'}
        ],
        'intent': 'verify login with different credentials',
        'status': 'passed',
        'duration': 6.0,
        'timestamp': FIXED_TIMESTAMP
    }


def sample_test_batch() -> List[Dict[str, Any]]:
    """Batch of 20 tests for bulk operations."""
    return [
        {
            'name': f'test_operation_{i}',
            'framework': 'pytest',
            'file_path': f'/tests/test_batch.py',
            'intent': f'verify operation {i}',
            'status': 'passed' if i % 10 != 0 else 'failed',
            'duration': float(i) * 0.1,
            'timestamp': FIXED_TIMESTAMP
        }
        for i in range(1, 21)
    ]


def sample_test_metadata() -> Dict[str, Any]:
    """Test with rich metadata."""
    return {
        'name': 'test_critical_user_flow',
        'framework': 'pytest',
        'file_path': '/tests/critical/test_flows.py',
        'steps': ['step1', 'step2', 'step3'],
        'intent': 'verify critical user journey',
        'status': 'passed',
        'duration': 12.5,
        'timestamp': FIXED_TIMESTAMP,
        'metadata': {
            'priority': 'P0',
            'team': 'platform',
            'jira_ticket': 'PLAT-1234',
            'coverage': ['api', 'ui', 'database'],
            'dependencies': ['auth', 'payment'],
            'environments': ['staging', 'production']
        }
    }
