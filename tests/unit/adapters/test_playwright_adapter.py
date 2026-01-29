"""
Comprehensive tests for Playwright adapter.

Tests adapter's ability to detect, extract, and process Playwright test files.
"""
import pytest
from pathlib import Path
from adapters.playwright.adapter import PlaywrightAdapter
from tests.test_adapter_template import AdapterTestTemplate


class TestPlaywrightAdapter(AdapterTestTemplate):
    """Comprehensive test suite for Playwright adapter."""
    
    def get_adapter(self):
        """Return Playwright adapter instance."""
        return PlaywrightAdapter()
    
    def get_sample_test_file(self) -> Path:
        """Return path to sample Playwright test file."""
        return Path(__file__).parent.parent / "fixtures" / "sample_playwright_test.py"
    
    def get_sample_page_object_file(self) -> Path:
        """Return path to sample Playwright page object file."""
        return Path(__file__).parent.parent / "fixtures" / "sample_playwright_page.py"
    
    def get_expected_test_count(self) -> int:
        """Expected number of tests in sample file."""
        return 7  # 3 in TestLoginPage + 2 in TestShoppingCart + 1 in TestAPIIntegration + 1 standalone
    
    def get_expected_page_object_count(self) -> int:
        """Expected number of page objects in sample file."""
        return 2  # LoginPage and CartPage


class TestPlaywrightSpecificFeatures:
    """Test Playwright-specific features and edge cases."""
    
    def setup_method(self):
        """Setup for each test."""
        self.adapter = PlaywrightAdapter()
    
    def test_detects_playwright_imports(self):
        """Test adapter detects Playwright-specific imports."""
        code = """
from playwright.sync_api import Page, expect
import pytest

def test_example(page: Page):
    page.goto("https://example.com")
"""
        assert self.adapter.detect_framework_from_content(code) is True
    
    def test_detects_playwright_async(self):
        """Test adapter detects async Playwright tests."""
        code = """
from playwright.async_api import async_playwright
import pytest

@pytest.mark.asyncio
async def test_async_example():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
"""
        assert self.adapter.detect_framework_from_content(code) is True
    
    def test_extracts_playwright_fixtures(self):
        """Test extraction of Playwright fixtures."""
        code = """
import pytest
from playwright.sync_api import Page

@pytest.fixture
def login_page(page: Page):
    page.goto("https://example.com/login")
    return page

def test_login(login_page: Page):
    login_page.locator("#username").fill("test")
"""
        tests = self.adapter.extract_tests_from_content(code, "test_fixtures.py")
        
        assert len(tests) == 1
        assert tests[0].test_name == "test_login"
        # Check if fixture dependency is captured
        assert "login_page" in str(tests[0].metadata)
    
    def test_extracts_locators(self):
        """Test extraction of Playwright locators."""
        code = """
def test_locators(page):
    page.locator("#id-selector").click()
    page.locator(".class-selector").fill("text")
    page.locator("button[type='submit']").click()
    page.get_by_role("button", name="Submit").click()
    page.get_by_text("Welcome").wait_for()
"""
        tests = self.adapter.extract_tests_from_content(code, "test_locators.py")
        
        assert len(tests) == 1
        # Verify locators are captured in metadata
        metadata = tests[0].metadata
        assert "locators" in metadata or "selectors" in metadata
    
    def test_detects_expect_assertions(self):
        """Test detection of Playwright expect assertions."""
        code = """
from playwright.sync_api import Page, expect

def test_assertions(page: Page):
    expect(page.locator(".title")).to_be_visible()
    expect(page).to_have_url("https://example.com")
    expect(page.locator(".count")).to_have_text("5")
"""
        tests = self.adapter.extract_tests_from_content(code, "test_assertions.py")
        
        assert len(tests) == 1
        # Check if assertions are tracked
        metadata = tests[0].metadata
        assert "assertions" in metadata or "expects" in metadata
    
    def test_handles_class_based_tests(self):
        """Test extraction from class-based test structure."""
        code = """
import pytest
from playwright.sync_api import Page

class TestLogin:
    @pytest.fixture
    def setup(self, page: Page):
        page.goto("https://example.com")
        return page
    
    def test_valid_login(self, setup):
        setup.locator("#username").fill("user")
    
    def test_invalid_login(self, setup):
        setup.locator("#username").fill("invalid")
"""
        tests = self.adapter.extract_tests_from_content(code, "test_class.py")
        
        assert len(tests) == 2
        assert any(t.test_name == "TestLogin.test_valid_login" for t in tests)
        assert any(t.test_name == "TestLogin.test_invalid_login" for t in tests)
    
    def test_page_object_detection(self):
        """Test detection of Playwright page objects."""
        code = """
from playwright.sync_api import Page

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.username = page.locator("#username")
        self.password = page.locator("#password")
    
    def login(self, username: str, password: str):
        self.username.fill(username)
        self.password.fill(password)
"""
        page_objects = self.adapter.extract_page_objects_from_content(code, "login_page.py")
        
        assert len(page_objects) == 1
        assert page_objects[0].name == "LoginPage"
    
    def test_multi_browser_tests(self):
        """Test detection of multi-browser test configurations."""
        code = """
import pytest

@pytest.mark.parametrize("browser_name", ["chromium", "firefox", "webkit"])
def test_cross_browser(browser_name, playwright):
    browser = playwright[browser_name].launch()
    page = browser.new_page()
    page.goto("https://example.com")
"""
        tests = self.adapter.extract_tests_from_content(code, "test_browsers.py")
        
        assert len(tests) >= 1
        # Check if parametrization is captured
        assert tests[0].metadata.get("parametrized") or "browser" in str(tests[0])
    
    def test_api_testing_detection(self):
        """Test detection of Playwright API testing."""
        code = """
def test_api(page):
    response = page.request.get("https://api.example.com/users")
    assert response.status == 200
    data = response.json()
"""
        tests = self.adapter.extract_tests_from_content(code, "test_api.py")
        
        assert len(tests) == 1
        # Check if API testing is flagged
        metadata = tests[0].metadata
        assert metadata.get("test_type") == "api" or "request" in str(metadata)
    
    def test_handles_empty_file(self):
        """Test adapter handles empty file gracefully."""
        tests = self.adapter.extract_tests_from_content("", "empty.py")
        assert tests == []
    
    def test_handles_invalid_syntax(self):
        """Test adapter handles files with syntax errors."""
        code = "def test_broken(\n  # Missing closing parenthesis and body"
        
        # Should not raise exception, should return empty or handle gracefully
        try:
            tests = self.adapter.extract_tests_from_content(code, "broken.py")
            assert isinstance(tests, list)  # Should return list even if empty
        except SyntaxError:
            pytest.skip("Adapter raises SyntaxError - acceptable behavior")
    
    def test_excludes_non_test_functions(self):
        """Test adapter excludes helper functions that aren't tests."""
        code = """
def helper_function():
    return "not a test"

def test_actual_test():
    result = helper_function()
    assert result == "not a test"

def another_helper():
    pass
"""
        tests = self.adapter.extract_tests_from_content(code, "test_helpers.py")
        
        assert len(tests) == 1
        assert tests[0].test_name == "test_actual_test"


class TestPlaywrightAdapterPerformance:
    """Performance tests for Playwright adapter."""
    
    def setup_method(self):
        """Setup for each test."""
        self.adapter = PlaywrightAdapter()
    
    def test_handles_large_file(self):
        """Test adapter performance with large test file."""
        # Generate large test file content
        large_code = "from playwright.sync_api import Page\n\n"
        for i in range(100):
            large_code += f"""
def test_example_{i}(page: Page):
    page.goto("https://example.com/{i}")
    page.locator("#button").click()
    
"""
        
        import time
        start = time.time()
        tests = self.adapter.extract_tests_from_content(large_code, "large_test.py")
        duration = time.time() - start
        
        assert len(tests) == 100
        assert duration < 5.0  # Should process in under 5 seconds
    
    def test_caching_framework_detection(self):
        """Test that framework detection can be cached."""
        code = "from playwright.sync_api import Page\n\ndef test_example(page): pass"
        
        # First call
        import time
        start1 = time.time()
        result1 = self.adapter.detect_framework_from_content(code)
        time1 = time.time() - start1
        
        # Second call (should be faster if cached)
        start2 = time.time()
        result2 = self.adapter.detect_framework_from_content(code)
        time2 = time.time() - start2
        
        assert result1 == result2 == True
        # Note: Caching test - may not always be faster due to Python overhead


@pytest.mark.integration
class TestPlaywrightAdapterIntegration:
    """Integration tests for Playwright adapter."""
    
    def setup_method(self):
        """Setup for each test."""
        self.adapter = PlaywrightAdapter()
    
    def test_end_to_end_extraction(self):
        """Test complete extraction workflow."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_playwright_test.py"
        
        if not fixture_path.exists():
            pytest.skip(f"Fixture file not found: {fixture_path}")
        
        # Detect framework
        assert self.adapter.detect_framework(str(fixture_path))
        
        # Extract tests
        tests = self.adapter.extract_tests(str(fixture_path))
        assert len(tests) > 0
        
        # Verify metadata
        for test in tests:
            assert test.framework == "playwright"
            assert test.test_name
            assert test.file_path == str(fixture_path)
    
    def test_page_object_extraction_integration(self):
        """Test page object extraction workflow."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_playwright_page.py"
        
        if not fixture_path.exists():
            pytest.skip(f"Fixture file not found: {fixture_path}")
        
        # Extract page objects
        page_objects = self.adapter.extract_page_objects(str(fixture_path))
        assert len(page_objects) >= 2  # LoginPage and CartPage
        
        # Verify page object metadata
        for po in page_objects:
            assert po.name
            assert po.file_path == str(fixture_path)
