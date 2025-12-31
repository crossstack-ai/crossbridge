# Selenium + Pytest Adapter

Adapter for Selenium WebDriver tests using pytest as the test runner.

## Overview

This adapter enables CrossBridge to work with Selenium WebDriver tests that use pytest as their test framework. It supports test discovery, execution, and metadata extraction for UI automation tests.

## Features

- ✅ **Auto-detection**: Automatically detects Selenium + pytest projects
- ✅ **Test Discovery**: Discovers tests using pytest's collection mechanism
- ✅ **Test Execution**: Runs tests with full pytest integration
- ✅ **Marker Support**: Filters tests by pytest markers/tags
- ✅ **Page Object Model**: Supports POM patterns
- ✅ **Parametrization**: Handles parametrized tests
- ✅ **Fixtures**: Works with pytest fixtures for driver management
- ✅ **Multiple Drivers**: Supports Chrome, Firefox, Edge, Safari
- ✅ **Reporting**: Integrates with pytest-json-report for detailed results

## Installation

```bash
# Install pytest and selenium
pip install pytest selenium

# Optional: pytest plugins
pip install pytest-selenium pytest-html pytest-json-report pytest-xdist
```

## Project Structure

```
project/
├── tests/
│   ├── test_login.py
│   ├── test_search.py
│   └── conftest.py          # Fixtures and configuration
├── pages/                    # Page Object Model (optional)
│   ├── __init__.py
│   ├── login_page.py
│   └── search_page.py
├── pytest.ini               # Pytest configuration
└── requirements.txt
```

## Quick Start

### Basic Test Example

```python
# tests/test_login.py
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By

@pytest.fixture
def driver():
    """WebDriver fixture."""
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

@pytest.mark.smoke
def test_valid_login(driver):
    """Test login with valid credentials."""
    driver.get("https://example.com/login")
    
    driver.find_element(By.ID, "username").send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("password123")
    driver.find_element(By.ID, "login-button").click()
    
    assert "Dashboard" in driver.title

@pytest.mark.regression
def test_invalid_login(driver):
    """Test login with invalid credentials."""
    driver.get("https://example.com/login")
    
    driver.find_element(By.ID, "username").send_keys("invalid")
    driver.find_element(By.ID, "password").send_keys("wrong")
    driver.find_element(By.ID, "login-button").click()
    
    error = driver.find_element(By.CLASS_NAME, "error-message")
    assert "Invalid credentials" in error.text
```

### Test Class Example

```python
# tests/test_search.py
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By

@pytest.mark.search
class TestSearch:
    """Search functionality tests."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test."""
        self.driver = webdriver.Chrome()
        yield
        self.driver.quit()
    
    @pytest.mark.smoke
    def test_search_with_results(self):
        """Test search with valid keyword."""
        self.driver.get("https://example.com")
        
        search_box = self.driver.find_element(By.NAME, "q")
        search_box.send_keys("laptop")
        search_box.submit()
        
        results = self.driver.find_elements(By.CLASS_NAME, "product")
        assert len(results) > 0
    
    @pytest.mark.regression
    def test_search_no_results(self):
        """Test search with no results."""
        self.driver.get("https://example.com")
        
        search_box = self.driver.find_element(By.NAME, "q")
        search_box.send_keys("nonexistentproduct12345")
        search_box.submit()
        
        no_results = self.driver.find_element(By.CLASS_NAME, "no-results")
        assert "No products found" in no_results.text
```

### Page Object Model Example

```python
# pages/login_page.py
from selenium.webdriver.common.by import By

class LoginPage:
    """Login page object."""
    
    def __init__(self, driver):
        self.driver = driver
        self.url = "https://example.com/login"
    
    def load(self):
        """Navigate to login page."""
        self.driver.get(self.url)
    
    def login(self, username, password):
        """Perform login."""
        self.driver.find_element(By.ID, "username").send_keys(username)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.ID, "login-button").click()
    
    def get_error_message(self):
        """Get error message."""
        return self.driver.find_element(By.CLASS_NAME, "error").text

# tests/test_login_pom.py
import pytest
from pages.login_page import LoginPage

@pytest.mark.smoke
def test_login_with_pom(driver):
    """Test login using Page Object Model."""
    login_page = LoginPage(driver)
    login_page.load()
    login_page.login("testuser", "password123")
    
    assert "Dashboard" in driver.title
```

## Configuration

### pytest.ini

```ini
[pytest]
# Markers
markers =
    smoke: Quick smoke tests
    regression: Full regression suite
    critical: Critical functionality
    slow: Tests that take longer to run

# Test discovery
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# Output
addopts = 
    -v
    --tb=short
    --strict-markers
    
# Selenium
driver = chrome
base_url = https://example.com
```

### conftest.py (Shared Fixtures)

```python
# tests/conftest.py
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

@pytest.fixture(scope="session")
def browser():
    """Browser type fixture."""
    return "chrome"

@pytest.fixture
def driver(browser):
    """WebDriver fixture with cleanup."""
    if browser == "chrome":
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=options)
    elif browser == "firefox":
        driver = webdriver.Firefox()
    else:
        raise ValueError(f"Unsupported browser: {browser}")
    
    driver.implicitly_wait(10)
    yield driver
    driver.quit()

@pytest.fixture
def base_url():
    """Base URL fixture."""
    return "https://example.com"
```

## Usage with CrossBridge

### Discover Tests

```python
from adapters.selenium_pytest import SeleniumPytestAdapter

adapter = SeleniumPytestAdapter(
    project_root="/path/to/project",
    driver_type="chrome"
)

# Discover all tests
tests = adapter.discover_tests()
print(f"Found {len(tests)} tests")
```

### Run Tests

```python
# Run all tests
results = adapter.run_tests()

# Run specific tests
results = adapter.run_tests(tests=[
    "tests/test_login.py::test_valid_login",
    "tests/test_search.py::TestSearch::test_search_with_results"
])

# Run by markers
results = adapter.run_tests(tags=["smoke"])

# Check results
for result in results:
    print(f"{result.name}: {result.status} ({result.duration_ms}ms)")
```

### Extract Metadata

```python
from adapters.selenium_pytest import SeleniumPytestExtractor

extractor = SeleniumPytestExtractor("/path/to/project")
tests = extractor.extract_tests()

for test in tests:
    print(f"Test: {test.test_name}")
    print(f"  File: {test.file_path}")
    print(f"  Tags: {test.tags}")
    print(f"  Type: {test.test_type}")
```

### Detect Projects

```python
from adapters.selenium_pytest import SeleniumPytestDetector

is_selenium_pytest = SeleniumPytestDetector.detect("/path/to/project")
if is_selenium_pytest:
    print("Selenium + pytest project detected!")
```

## Pytest Markers

### Common Markers

```python
@pytest.mark.smoke          # Smoke tests
@pytest.mark.regression     # Regression tests
@pytest.mark.critical       # Critical functionality
@pytest.mark.slow           # Slow-running tests
@pytest.mark.skip           # Skip test
@pytest.mark.skipif         # Conditional skip
@pytest.mark.xfail          # Expected to fail
@pytest.mark.parametrize    # Parametrized tests
```

### Custom Markers

```python
# pytest.ini
[pytest]
markers =
    ui: UI tests
    api: API tests
    database: Database tests
    integration: Integration tests

# Use in tests
@pytest.mark.ui
@pytest.mark.integration
def test_full_workflow(driver):
    pass
```

## Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("username,password,expected", [
    ("admin", "admin123", "success"),
    ("user", "user123", "success"),
    ("guest", "wrong", "error"),
])
def test_login_variants(driver, username, password, expected):
    """Test login with different credentials."""
    driver.get("https://example.com/login")
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "login-button").click()
    
    if expected == "success":
        assert "Dashboard" in driver.title
    else:
        error = driver.find_element(By.CLASS_NAME, "error")
        assert error.is_displayed()
```

## Browser Configuration

### Multiple Browsers

```python
@pytest.fixture(params=["chrome", "firefox"])
def driver(request):
    """Multi-browser fixture."""
    browser = request.param
    
    if browser == "chrome":
        driver = webdriver.Chrome()
    elif browser == "firefox":
        driver = webdriver.Firefox()
    
    yield driver
    driver.quit()

# Test runs on both Chrome and Firefox
def test_cross_browser(driver):
    driver.get("https://example.com")
    assert "Example" in driver.title
```

### Headless Mode

```python
from selenium.webdriver.chrome.options import Options

@pytest.fixture
def driver():
    """Headless Chrome fixture."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()
```

## Integration with Execution Engine

```python
from core.execution import TestExecutor, TestExecutionRequest, ExecutionStrategy

# Execute Selenium + pytest tests
request = TestExecutionRequest(
    framework="selenium-pytest",
    project_root="/path/to/project",
    strategy=ExecutionStrategy.PARALLEL,
    max_workers=4,
    tags=["smoke", "critical"],
    timeout=60
)

executor = TestExecutor()
summary = executor.execute(request)

print(f"Total: {summary.total_tests}")
print(f"Passed: {summary.passed}")
print(f"Failed: {summary.failed}")
print(f"Success Rate: {summary.success_rate}%")
```

## Best Practices

1. **Use Fixtures**: Centralize driver setup/teardown in fixtures
2. **Page Object Model**: Separate page logic from tests
3. **Explicit Waits**: Use WebDriverWait instead of implicit waits
4. **Markers**: Tag tests appropriately for filtering
5. **Headless Mode**: Run tests headless in CI/CD
6. **Screenshots**: Capture screenshots on failure
7. **Clean Data**: Reset test data between tests
8. **Parallel Execution**: Use pytest-xdist for faster execution

## Troubleshooting

### Tests Not Discovered

- Check file naming: `test_*.py` or `*_test.py`
- Check function naming: `test_*`
- Check class naming: `Test*`
- Verify pytest.ini configuration

### Driver Not Found

```bash
# Install ChromeDriver
pip install webdriver-manager

# Use in tests
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
```

### Element Not Found

- Use explicit waits:
```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

element = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "element-id"))
)
```

## Examples

See [examples/selenium_pytest/](../../examples/selenium_pytest/) for complete working examples.

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.
