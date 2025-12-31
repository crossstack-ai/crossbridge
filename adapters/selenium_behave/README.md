# Selenium + Behave Adapter

Adapter for Selenium WebDriver tests using Behave (Python BDD framework).

## Overview

This adapter enables CrossBridge to work with Selenium WebDriver tests written in Gherkin (Given-When-Then) format using Behave as the BDD framework. It supports scenario discovery, execution, and metadata extraction for BDD UI automation tests.

## Features

- ✅ **Auto-detection**: Automatically detects Selenium + Behave projects
- ✅ **Scenario Discovery**: Discovers scenarios from .feature files
- ✅ **Gherkin Support**: Full support for Gherkin syntax
- ✅ **Tag Filtering**: Filters scenarios by tags
- ✅ **Step Definitions**: Python step definitions with Selenium
- ✅ **Context Sharing**: Share data between steps using context
- ✅ **Hooks**: before_all, before_scenario, after_scenario, etc.
- ✅ **Page Object Model**: Integrates with POM patterns
- ✅ **Multiple Drivers**: Supports Chrome, Firefox, Edge, Safari
- ✅ **Scenario Outline**: Parametrized scenarios with examples

## Installation

```bash
# Install Behave and Selenium
pip install behave selenium

# Optional: Additional tools
pip install selenium-webdriver webdriver-manager
```

## Project Structure

```
project/
├── features/
│   ├── login.feature         # Feature files (Gherkin)
│   ├── search.feature
│   ├── steps/                # Step definitions
│   │   ├── __init__.py
│   │   ├── login_steps.py
│   │   └── search_steps.py
│   ├── pages/                # Page Object Model (optional)
│   │   ├── __init__.py
│   │   ├── base_page.py
│   │   ├── login_page.py
│   │   └── search_page.py
│   └── environment.py        # Hooks and setup
├── behave.ini               # Behave configuration
└── requirements.txt
```

## Quick Start

### Basic Feature File

```gherkin
# features/login.feature
@smoke @authentication
Feature: User Login
    As a user
    I want to log into the application
    So that I can access my account

    Background:
        Given the browser is open
        And I am on the login page

    @critical @positive
    Scenario: Successful login with valid credentials
        When I enter "testuser" as username
        And I enter "password123" as password
        And I click the login button
        Then I should be redirected to the dashboard
        And I should see "Welcome, testuser"

    @negative
    Scenario: Failed login with invalid credentials
        When I enter "invalid" as username
        And I enter "wrongpass" as password
        And I click the login button
        Then I should see an error message "Invalid credentials"
        And I should remain on the login page
```

### Step Definitions

```python
# features/steps/login_steps.py
from behave import given, when, then
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@given('the browser is open')
def step_open_browser(context):
    """Initialize browser."""
    if not hasattr(context, 'driver'):
        context.driver = webdriver.Chrome()
        context.driver.implicitly_wait(10)

@given('I am on the login page')
def step_navigate_login(context):
    """Navigate to login page."""
    context.driver.get("https://example.com/login")

@when('I enter "{text}" as username')
def step_enter_username(context, text):
    """Enter username."""
    username_field = context.driver.find_element(By.ID, "username")
    username_field.clear()
    username_field.send_keys(text)

@when('I enter "{text}" as password')
def step_enter_password(context, text):
    """Enter password."""
    password_field = context.driver.find_element(By.ID, "password")
    password_field.clear()
    password_field.send_keys(text)

@when('I click the login button')
def step_click_login(context):
    """Click login button."""
    login_button = context.driver.find_element(By.ID, "login-button")
    login_button.click()

@then('I should be redirected to the dashboard')
def step_verify_dashboard(context):
    """Verify dashboard page."""
    WebDriverWait(context.driver, 10).until(
        EC.url_contains("/dashboard")
    )
    assert "/dashboard" in context.driver.current_url

@then('I should see "{expected_text}"')
def step_verify_text(context, expected_text):
    """Verify text is present."""
    body_text = context.driver.find_element(By.TAG_NAME, "body").text
    assert expected_text in body_text

@then('I should see an error message "{expected_error}"')
def step_verify_error(context, expected_error):
    """Verify error message."""
    error_element = context.driver.find_element(By.CLASS_NAME, "error-message")
    assert expected_error in error_element.text

@then('I should remain on the login page')
def step_verify_login_page(context):
    """Verify still on login page."""
    assert "/login" in context.driver.current_url
```

### Environment Hooks

```python
# features/environment.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def before_all(context):
    """Setup before all tests."""
    context.base_url = "https://example.com"
    context.timeout = 10

def before_scenario(context, scenario):
    """Setup before each scenario."""
    # Initialize driver
    options = Options()
    if context.config.userdata.get('headless', 'false') == 'true':
        options.add_argument('--headless')
    
    context.driver = webdriver.Chrome(options=options)
    context.driver.implicitly_wait(context.timeout)
    context.driver.maximize_window()

def after_scenario(context, scenario):
    """Cleanup after each scenario."""
    if hasattr(context, 'driver'):
        # Take screenshot on failure
        if scenario.status == 'failed':
            screenshot_name = f"{scenario.name.replace(' ', '_')}.png"
            context.driver.save_screenshot(f"screenshots/{screenshot_name}")
        
        context.driver.quit()

def after_all(context):
    """Cleanup after all tests."""
    pass
```

## Scenario Outline (Data-Driven Tests)

```gherkin
# features/login_variants.feature
@data-driven
Feature: Login with Multiple Credentials

    Scenario Outline: Login with different user types
        Given I am on the login page
        When I enter "<username>" as username
        And I enter "<password>" as password
        And I click the login button
        Then I should see "<result>"

        Examples: Valid Users
            | username | password    | result              |
            | admin    | admin123    | Welcome, admin      |
            | user     | user123     | Welcome, user       |
            | manager  | manager123  | Welcome, manager    |

        Examples: Invalid Users
            | username | password | result              |
            | invalid  | wrong    | Invalid credentials |
            | ""       | ""       | Fields required     |
```

## Page Object Model with Behave

```python
# features/pages/base_page.py
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class BasePage:
    """Base page object."""
    
    def __init__(self, driver):
        self.driver = driver
        self.timeout = 10
    
    def find_element(self, locator):
        """Find element with wait."""
        return WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located(locator)
        )
    
    def click(self, locator):
        """Click element."""
        element = self.find_element(locator)
        element.click()
    
    def enter_text(self, locator, text):
        """Enter text in element."""
        element = self.find_element(locator)
        element.clear()
        element.send_keys(text)
    
    def get_text(self, locator):
        """Get element text."""
        element = self.find_element(locator)
        return element.text

# features/pages/login_page.py
from selenium.webdriver.common.by import By
from .base_page import BasePage

class LoginPage(BasePage):
    """Login page object."""
    
    # Locators
    USERNAME_INPUT = (By.ID, "username")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.ID, "login-button")
    ERROR_MESSAGE = (By.CLASS_NAME, "error-message")
    
    def __init__(self, driver):
        super().__init__(driver)
        self.url = "https://example.com/login"
    
    def load(self):
        """Navigate to login page."""
        self.driver.get(self.url)
    
    def login(self, username, password):
        """Perform login."""
        self.enter_text(self.USERNAME_INPUT, username)
        self.enter_text(self.PASSWORD_INPUT, password)
        self.click(self.LOGIN_BUTTON)
    
    def get_error_message(self):
        """Get error message."""
        return self.get_text(self.ERROR_MESSAGE)

# features/steps/login_steps_pom.py
from behave import given, when, then
from features.pages.login_page import LoginPage

@given('I am on the login page')
def step_impl(context):
    context.login_page = LoginPage(context.driver)
    context.login_page.load()

@when('I login with username "{username}" and password "{password}"')
def step_impl(context, username, password):
    context.login_page.login(username, password)

@then('I should see login error "{expected_error}"')
def step_impl(context, expected_error):
    error = context.login_page.get_error_message()
    assert expected_error in error
```

## Configuration

### behave.ini

```ini
[behave]
# Paths
paths = features

# Output format
format = pretty
show_timings = true
show_skipped = false

# Logging
logging_level = INFO
logging_format = %(levelname)s: %(message)s

# Tags
default_tags = -wip -skip

# Color output
color = true

# Stop on first failure
stop = false
```

### behave.userdata (Runtime Configuration)

```bash
# Run with custom settings
behave -D headless=true -D base_url=https://staging.example.com

# Access in environment.py
headless = context.config.userdata.get('headless', 'false')
base_url = context.config.userdata.get('base_url', 'https://example.com')
```

## Usage with CrossBridge

### Discover Scenarios

```python
from adapters.selenium_behave import SeleniumBehaveAdapter

adapter = SeleniumBehaveAdapter(
    project_root="/path/to/project",
    driver_type="chrome"
)

# Discover all scenarios
scenarios = adapter.discover_tests()
print(f"Found {len(scenarios)} scenarios")
```

### Run Scenarios

```python
# Run all scenarios
results = adapter.run_tests()

# Run specific scenarios
results = adapter.run_tests(tests=[
    "features/login.feature:5",  # Line number
    "features/search.feature:12"
])

# Run by tags
results = adapter.run_tests(tags=["smoke", "critical"])

# Check results
for result in results:
    print(f"{result.name}: {result.status} ({result.duration_ms}ms)")
    if result.status == "fail":
        print(f"  Error: {result.message}")
```

### Extract Metadata

```python
from adapters.selenium_behave import SeleniumBehaveExtractor

extractor = SeleniumBehaveExtractor("/path/to/project")
scenarios = extractor.extract_tests()

for scenario in scenarios:
    print(f"Scenario: {scenario.test_name}")
    print(f"  File: {scenario.file_path}")
    print(f"  Tags: {scenario.tags}")
    print(f"  Type: {scenario.test_type}")  # 'bdd'

# Extract steps from scenarios
steps = extractor.extract_steps(Path("features/login.feature"))
for scenario_name, scenario_steps in steps.items():
    print(f"\n{scenario_name}:")
    for step in scenario_steps:
        print(f"  - {step}")
```

### Detect Projects

```python
from adapters.selenium_behave import SeleniumBehaveDetector

is_behave_project = SeleniumBehaveDetector.detect("/path/to/project")
if is_behave_project:
    print("Selenium + Behave project detected!")
```

## Tags and Filtering

### Tag Syntax

```gherkin
@smoke @critical
Feature: Critical Features

    @positive @ui
    Scenario: Happy path
        ...
    
    @negative @api
    Scenario: Error handling
        ...
```

### Running with Tags

```bash
# Run smoke tests
behave --tags=smoke

# Run critical and regression tests
behave --tags=critical,regression

# Exclude WIP tests
behave --tags=-wip

# Complex tag expressions
behave --tags="smoke and not slow"
behave --tags="(smoke or critical) and not wip"
```

## Integration with Execution Engine

```python
from core.execution import TestExecutor, TestExecutionRequest, ExecutionStrategy

# Execute Behave scenarios
request = TestExecutionRequest(
    framework="selenium-behave",
    project_root="/path/to/project",
    strategy=ExecutionStrategy.PARALLEL,
    max_workers=4,
    tags=["smoke"],
    timeout=60,
    framework_options={
        "format": "json",
        "no_capture": True
    }
)

executor = TestExecutor()
summary = executor.execute(request)

print(f"Scenarios: {summary.total_tests}")
print(f"Passed: {summary.passed}")
print(f"Failed: {summary.failed}")
```

## Best Practices

1. **Clear Scenarios**: Write readable, business-focused scenarios
2. **Reusable Steps**: Create generic, reusable step definitions
3. **Page Objects**: Use POM to separate UI logic
4. **Context Data**: Use context to share data between steps
5. **Hooks**: Centralize setup/teardown in environment.py
6. **Tags**: Tag scenarios for easy filtering
7. **Examples**: Use Scenario Outline for data-driven tests
8. **Screenshots**: Capture screenshots on failure

## Common Patterns

### Logging

```python
# features/environment.py
import logging

def before_all(context):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    context.logger = logging.getLogger('behave')

# In steps
def step_impl(context):
    context.logger.info("Executing step...")
```

### Database Setup

```python
# features/environment.py
import sqlite3

def before_all(context):
    context.db = sqlite3.connect('test.db')
    
def after_all(context):
    context.db.close()

def before_scenario(context, scenario):
    if 'database' in scenario.tags:
        # Reset database
        context.db.execute('DELETE FROM users')
        context.db.commit()
```

### API Integration

```python
# features/steps/api_steps.py
import requests

@given('the API is available')
def step_impl(context):
    response = requests.get(f"{context.base_url}/health")
    assert response.status_code == 200

@when('I create a user via API')
def step_impl(context):
    context.api_response = requests.post(
        f"{context.base_url}/api/users",
        json={"username": "testuser", "email": "test@example.com"}
    )
```

## Troubleshooting

### Scenarios Not Discovered

- Check `features/` directory exists
- Verify `.feature` file extension
- Check `Scenario:` or `Scenario Outline:` keywords
- Verify Gherkin syntax

### Step Definitions Not Found

- Check `features/steps/` directory exists
- Import behave decorators: `from behave import given, when, then`
- Match step text exactly (case-sensitive)
- Use regex for flexible matching:
  ```python
  @when('I enter "(?P<text>.*)" as (?P<field>.*)')
  def step_impl(context, text, field):
      ...
  ```

### Driver Issues

```python
# Use webdriver-manager
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def before_scenario(context, scenario):
    service = Service(ChromeDriverManager().install())
    context.driver = webdriver.Chrome(service=service)
```

## Examples

See [examples/selenium_behave/](../../examples/selenium_behave/) for complete working examples.

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.
