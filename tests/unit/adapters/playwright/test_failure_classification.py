"""
Comprehensive tests for Playwright failure classification (Gap 2.1).

Tests cover:
- All browser-specific failure types (timeout, locator, navigation, crashes)
- Multi-language stack trace parsing (JS/TS, Python, Java, .NET)
- Locator extraction and strategy detection
- Component detection (page objects, fixtures, test code)
- Confidence scoring
- Intermittent failure detection
"""

import pytest
from adapters.playwright.failure_classifier import (
    PlaywrightFailureClassifier,
    BrowserFailureType,
    BrowserComponentType,
    classify_playwright_failure,
)


class TestBrowserFailureClassification:
    """Test Playwright-specific failure classification"""
    
    def test_locator_timeout_classification(self):
        """Test timeout on locator action"""
        error = """Locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("button#submit")
"""
        
        result = classify_playwright_failure(error)
        
        assert result.failure_type == BrowserFailureType.LOCATOR_TIMEOUT
        assert result.action == "click"
        assert result.timeout_duration == 30000
        assert result.is_intermittent is True
        assert result.confidence >= 0.6
    
    def test_navigation_timeout_classification(self):
        """Test navigation timeout"""
        error = "Navigation timeout of 30000ms exceeded"
        
        result = classify_playwright_failure(error, page_url="https://example.com")
        
        assert result.failure_type == BrowserFailureType.NAVIGATION_TIMEOUT
        assert result.timeout_duration == 30000
        assert result.is_intermittent is True
        assert result.page_url == "https://example.com"
    
    def test_wait_timeout_classification(self):
        """Test waitForSelector timeout"""
        error = "waitForSelector timed out after 5000ms"
        
        result = classify_playwright_failure(error)
        
        assert result.failure_type == BrowserFailureType.WAIT_TIMEOUT
        assert result.timeout_duration == 5000
        assert result.is_intermittent is True
    
    def test_strict_mode_violation(self):
        """Test strict mode violation (multiple elements)"""
        error = """Error: strict mode violation: locator("button") resolved to 5 elements"""
        
        result = classify_playwright_failure(error)
        
        assert result.failure_type == BrowserFailureType.STRICT_MODE_VIOLATION
        assert result.element_count == 5
        assert result.is_intermittent is False
    
    def test_locator_not_found(self):
        """Test element not found"""
        error = "Error: locator resolved to 0 elements"
        
        result = classify_playwright_failure(error)
        
        assert result.failure_type == BrowserFailureType.LOCATOR_NOT_FOUND
        assert result.element_count == 0
    
    def test_detached_element(self):
        """Test element detached from DOM"""
        error = "Element is not attached to the DOM"
        
        result = classify_playwright_failure(error)
        
        assert result.failure_type == BrowserFailureType.DETACHED_ELEMENT
        assert result.is_intermittent is True
    
    def test_page_crash(self):
        """Test browser page crash"""
        error = "Navigation failed because page crashed!"
        
        result = classify_playwright_failure(error)
        
        assert result.failure_type == BrowserFailureType.PAGE_CRASH
        assert result.is_intermittent is True
    
    def test_browser_disconnected(self):
        """Test browser disconnection"""
        error = "Browser has been closed"
        
        result = classify_playwright_failure(error)
        
        assert result.failure_type == BrowserFailureType.BROWSER_DISCONNECTED
        assert result.is_intermittent is True
    
    def test_network_error(self):
        """Test network failure"""
        error = "net::ERR_CONNECTION_REFUSED at https://api.example.com"
        
        result = classify_playwright_failure(error)
        
        assert result.failure_type == BrowserFailureType.NETWORK_ERROR
        assert result.is_intermittent is True
    
    def test_expect_assertion_failed(self):
        """Test Playwright expect() assertion"""
        error = """expect(locator).toBeVisible - Expected visible, but was hidden"""
        
        result = classify_playwright_failure(error)
        
        assert result.failure_type == BrowserFailureType.EXPECT_FAILED
        assert result.is_intermittent is False
    
    def test_generic_assertion(self):
        """Test generic assertion failure"""
        error = "AssertionError: Expected 'John' but got 'Jane'"
        
        result = classify_playwright_failure(error)
        
        assert result.failure_type == BrowserFailureType.ASSERTION
        assert result.is_intermittent is False


class TestLocatorExtraction:
    """Test locator and selector extraction"""
    
    def test_extract_getbyrole(self):
        """Test getByRole locator extraction"""
        error = """Locator.click: Timeout
page.getByRole('button', { name: 'Submit' })"""
        
        result = classify_playwright_failure(error)
        
        assert result.locator is not None
        assert "button" in result.locator
        assert "Submit" in result.locator
        assert result.locator_strategy == "role"
    
    def test_extract_getbytext(self):
        """Test getByText locator extraction"""
        error = """page.getByText('Login').click()"""
        
        result = classify_playwright_failure(error)
        
        assert result.locator == "Login"
        assert result.locator_strategy == "text"
    
    def test_extract_getbytestid(self):
        """Test getByTestId locator extraction"""
        error = """page.getByTestId('submit-button')"""
        
        result = classify_playwright_failure(error)
        
        assert result.locator == "submit-button"
        assert result.locator_strategy == "testid"
    
    def test_extract_css_selector(self):
        """Test CSS selector extraction"""
        error = """page.locator('button.submit#primary')"""
        
        result = classify_playwright_failure(error)
        
        assert result.locator == "button.submit#primary"
        assert result.locator_strategy == "css"
    
    def test_extract_xpath(self):
        """Test XPath extraction"""
        error = """page.locator('xpath=//button[@id="submit"]')"""
        
        result = classify_playwright_failure(error)
        
        assert "//button" in result.locator
        assert result.locator_strategy == "xpath"
    
    def test_extract_action_click(self):
        """Test action extraction"""
        error = "Locator.click: Timeout 30000ms exceeded"
        
        result = classify_playwright_failure(error)
        
        assert result.action == "click"
    
    def test_extract_action_fill(self):
        """Test fill action extraction"""
        error = "Locator.fill: Element is not visible"
        
        result = classify_playwright_failure(error)
        
        assert result.action == "fill"


class TestMultiLanguageSupport:
    """Test stack trace parsing for different Playwright language bindings"""
    
    def test_javascript_stack_trace(self):
        """Test JavaScript stack trace parsing"""
        error = "Locator.click: Timeout 30000ms exceeded"
        stack = """    at Page.click (/project/tests/login.spec.ts:25:5)
    at test (/project/pages/LoginPage.ts:42:10)
    at WorkerRunner.runTest (node_modules/@playwright/test/lib/worker/workerRunner.js:445:26)"""
        
        result = classify_playwright_failure(error, stack_trace=stack, language="javascript")
        
        assert result.location is not None
        assert "login.spec.ts" in result.location.file_path
        assert result.location.line_number == 25
        assert result.component == BrowserComponentType.TEST_CODE
    
    def test_python_stack_trace(self):
        """Test Python stack trace parsing"""
        error = "TimeoutError: Locator.click: Timeout 30000ms exceeded"
        stack = """  File "/project/tests/test_login.py", line 45, in test_user_login
    page.get_by_role("button", name="Login").click()
  File "/project/pages/login_page.py", line 30, in click_login
    self.login_button.click()"""
        
        result = classify_playwright_failure(error, stack_trace=stack, language="python")
        
        assert result.location is not None
        assert "test_login.py" in result.location.file_path
        assert result.location.line_number == 45
        assert result.component == BrowserComponentType.TEST_CODE
        assert result.exception_type == "TimeoutError"
    
    def test_java_stack_trace(self):
        """Test Java stack trace parsing"""
        error = "com.microsoft.playwright.TimeoutError: Locator.click: Timeout 30000ms exceeded"
        stack = """	at com.microsoft.playwright.impl.LocatorImpl.click(LocatorImpl.java:234)
	at pages.LoginPage.clickLogin(LoginPage.java:42)
	at tests.LoginTest.testUserLogin(LoginTest.java:25)"""
        
        result = classify_playwright_failure(error, stack_trace=stack, language="java")
        
        assert result.location is not None
        assert "LoginPage.java" in result.location.file_path
        assert result.location.line_number == 42
        assert result.component == BrowserComponentType.PAGE_OBJECT
        assert "TimeoutError" in result.exception_type
    
    def test_dotnet_stack_trace(self):
        """Test .NET stack trace parsing"""
        error = "Microsoft.Playwright.TimeoutException: Locator.click: Timeout 30000ms exceeded"
        stack = """   at Microsoft.Playwright.Core.Locator.ClickAsync() in Locator.cs:line 156
   at Pages.LoginPage.ClickLogin() in LoginPage.cs:line 42
   at Tests.LoginTest.TestUserLogin() in LoginTest.cs:line 25"""
        
        result = classify_playwright_failure(error, stack_trace=stack, language="csharp")
        
        assert result.location is not None
        assert "LoginPage.cs" in result.location.file_path
        assert result.location.line_number == 42
        assert result.component == BrowserComponentType.PAGE_OBJECT
        assert "TimeoutException" in result.exception_type


class TestComponentDetection:
    """Test component type detection from stack traces"""
    
    def test_detect_page_object(self):
        """Test page object detection"""
        error = "Locator.click: Timeout"
        stack = """    at LoginPage.clickSubmit (/project/pages/LoginPage.ts:42:5)
    at test (/project/tests/login.spec.ts:15:5)"""
        
        result = classify_playwright_failure(error, stack_trace=stack, language="javascript")
        
        assert result.component == BrowserComponentType.PAGE_OBJECT
    
    def test_detect_fixture(self):
        """Test fixture detection (Python)"""
        error = "Error in fixture setup"
        stack = """  File "/project/tests/conftest.py", line 20, in browser_context
    context = browser.new_context()"""
        
        result = classify_playwright_failure(error, stack_trace=stack, language="python")
        
        assert result.component == BrowserComponentType.FIXTURE
    
    def test_detect_test_code(self):
        """Test code detection"""
        error = "Assertion failed"
        stack = """    at test (/project/tests/user.spec.ts:45:5)"""
        
        result = classify_playwright_failure(error, stack_trace=stack, language="javascript")
        
        assert result.component == BrowserComponentType.TEST_CODE
    
    def test_detect_helper(self):
        """Test helper/utility detection"""
        error = "Helper failed"
        stack = """  File "/project/tests/helpers/auth_helper.py", line 15, in login_user
    page.fill("#username", username)"""
        
        result = classify_playwright_failure(error, stack_trace=stack, language="python")
        
        # Helper is in tests/helpers, so could be classified as TEST_CODE or HELPER
        assert result.component in (BrowserComponentType.HELPER, BrowserComponentType.TEST_CODE)


class TestConfidenceScoring:
    """Test confidence scoring for classifications"""
    
    def test_high_confidence_with_all_details(self):
        """Test high confidence when all details present"""
        error = "Locator.click: Timeout 30000ms exceeded"
        stack = """    at LoginPage.clickSubmit (/project/pages/LoginPage.ts:42:5)"""
        
        result = classify_playwright_failure(
            error,
            stack_trace=stack,
            test_name="test_login",
            page_url="https://example.com/login"
        )
        
        # Has failure type match, action extracted, location, component
        assert result.confidence >= 0.7
    
    def test_medium_confidence_partial_details(self):
        """Test medium confidence with partial details"""
        error = "Timeout 5000ms exceeded"
        
        result = classify_playwright_failure(error)
        
        # Has failure type but missing location and component
        assert 0.3 <= result.confidence <= 0.8
    
    def test_low_confidence_minimal_details(self):
        """Test low confidence with minimal details"""
        error = "Unknown error occurred"
        
        result = classify_playwright_failure(error)
        
        # Unknown type, no details
        assert result.confidence < 0.5


class TestIntermittentDetection:
    """Test detection of intermittent/flaky failures"""
    
    def test_timeout_is_intermittent(self):
        """Test that timeouts are marked intermittent"""
        error = "Timeout 30000ms exceeded"
        
        result = classify_playwright_failure(error)
        
        assert result.is_intermittent is True
    
    def test_network_error_is_intermittent(self):
        """Test that network errors are intermittent"""
        error = "net::ERR_CONNECTION_REFUSED"
        
        result = classify_playwright_failure(error)
        
        assert result.is_intermittent is True
    
    def test_browser_crash_is_intermittent(self):
        """Test that browser crashes are intermittent"""
        error = "Browser has been closed"
        
        result = classify_playwright_failure(error)
        
        assert result.is_intermittent is True
    
    def test_detached_element_is_intermittent(self):
        """Test that detached elements are intermittent"""
        error = "Element is not attached to the DOM"
        
        result = classify_playwright_failure(error)
        
        assert result.is_intermittent is True
    
    def test_assertion_not_intermittent(self):
        """Test that assertions are not intermittent"""
        error = "expect(locator).toHaveText - Expected 'foo' but got 'bar'"
        
        result = classify_playwright_failure(error)
        
        assert result.is_intermittent is False
    
    def test_strict_mode_not_intermittent(self):
        """Test that strict mode violations are not intermittent"""
        error = "strict mode violation: locator resolved to 3 elements"
        
        result = classify_playwright_failure(error)
        
        assert result.is_intermittent is False


class TestSerializationToDict:
    """Test conversion to dictionary for storage"""
    
    def test_to_dict_complete(self):
        """Test serialization with all fields"""
        error = "Locator.click: Timeout 30000ms exceeded"
        stack = """    at LoginPage.clickSubmit (/project/pages/LoginPage.ts:42:5)"""
        
        result = classify_playwright_failure(
            error,
            stack_trace=stack,
            page_url="https://example.com/login",
            browser_type="chromium"
        )
        
        data = result.to_dict()
        
        assert data["failure_type"] == "locator_timeout"
        assert data["action"] == "click"
        assert data["timeout_duration"] == 30000
        assert data["page_url"] == "https://example.com/login"
        assert data["browser_type"] == "chromium"
        assert data["is_intermittent"] is True
        assert "location" in data
        assert data["component"] in ["page_object", "unknown"]
    
    def test_to_dict_minimal(self):
        """Test serialization with minimal fields"""
        error = "Unknown error"
        
        result = classify_playwright_failure(error)
        
        data = result.to_dict()
        
        assert data["failure_type"] == "unknown"
        assert data["error_message"] == "Unknown error"
        assert "locator" not in data  # None values excluded
        assert "page_url" not in data
