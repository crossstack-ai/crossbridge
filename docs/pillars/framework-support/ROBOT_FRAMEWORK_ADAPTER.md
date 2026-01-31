# Robot Framework Adapter

Adapter for Robot Framework test automation.

## Overview

This adapter enables CrossBridge to work with Robot Framework tests, providing test discovery, execution, and metadata extraction for keyword-driven test automation.

## Features

- ✅ **Auto-detection**: Automatically detects Robot Framework projects
- ✅ **Test Discovery**: Discovers tests using `--dryrun` mode
- ✅ **Test Execution**: Runs tests with full Robot Framework integration
- ✅ **Tag Support**: Filters tests by Robot Framework tags
- ✅ **Resource Files**: Works with resource files and libraries
- ✅ **Page Object Pattern**: Supports resource-based Page Object patterns
- ✅ **Multiple Libraries**: Compatible with SeleniumLibrary, RequestsLibrary, etc.
- ✅ **Result Parsing**: Parses output.xml for detailed results
- ✅ **Force Tags**: Supports suite-level tags

## Installation

```bash
# Install Robot Framework
pip install robotframework

# Common libraries
pip install robotframework-seleniumlibrary
pip install robotframework-requests
pip install robotframework-databaselibrary
```

## Project Structure

```
project/
├── tests/
│   ├── test_login.robot
│   ├── test_search.robot
│   └── test_api.robot
├── resources/
│   ├── common.robot        # Shared keywords
│   ├── login_page.robot    # Page Object
│   └── variables.robot     # Variables
├── libraries/
│   └── CustomLibrary.py    # Custom Python libraries
└── requirements.txt
```

## Quick Start

### Basic Test Example

```robot
*** Settings ***
Library    SeleniumLibrary

*** Variables ***
${URL}         https://example.com
${BROWSER}     chrome

*** Test Cases ***
Valid Login Test
    [Tags]    smoke    login
    Open Browser    ${URL}/login    ${BROWSER}
    Input Text    id=username    testuser
    Input Text    id=password    password123
    Click Button    id=login-button
    Title Should Be    Dashboard
    Close Browser

Invalid Login Test
    [Tags]    negative    login
    Open Browser    ${URL}/login    ${BROWSER}
    Input Text    id=username    invalid
    Input Text    id=password    wrong
    Click Button    id=login-button
    Element Should Be Visible    css=.error-message
    Element Text Should Be    css=.error-message    Invalid credentials
    Close Browser
```

### Resource File (Page Object)

```robot
*** Settings ***
Library    SeleniumLibrary

*** Variables ***
${LOGIN_URL}    https://example.com/login
${USERNAME_FIELD}    id=username
${PASSWORD_FIELD}    id=password
${LOGIN_BUTTON}      id=login-button

*** Keywords ***
Open Login Page
    Open Browser    ${LOGIN_URL}    ${BROWSER}
    Title Should Be    Login

Input Username
    [Arguments]    ${username}
    Input Text    ${USERNAME_FIELD}    ${username}

Input Password
    [Arguments]    ${password}
    Input Text    ${PASSWORD_FIELD}    ${password}

Submit Credentials
    Click Button    ${LOGIN_BUTTON}

Login With Credentials
    [Arguments]    ${username}    ${password}
    Open Login Page
    Input Username    ${username}
    Input Password    ${password}
    Submit Credentials

Close Login Page
    Close Browser
```

### Test Using Resources

```robot
*** Settings ***
Resource    ../resources/login_page.robot
Force Tags    integration

*** Test Cases ***
User Can Login With Valid Credentials
    [Tags]    smoke    critical
    Login With Credentials    testuser    password123
    Title Should Be    Dashboard
    [Teardown]    Close Login Page

User Cannot Login With Invalid Credentials
    [Tags]    negative
    Login With Credentials    invalid    wrong
    Element Should Be Visible    css=.error-message
    [Teardown]    Close Login Page
```

### Data-Driven Tests

```robot
*** Settings ***
Library    SeleniumLibrary

*** Test Cases ***
Login With Multiple Users
    [Template]    Attempt Login
    testuser     password123    success
    admin        admin123       success
    guest        wrong          error
    invalid      invalid        error

*** Keywords ***
Attempt Login
    [Arguments]    ${username}    ${password}    ${expected}
    Open Browser    https://example.com/login    chrome
    Input Text    id=username    ${username}
    Input Text    id=password    ${password}
    Click Button    id=login-button
    
    Run Keyword If    '${expected}' == 'success'    
    ...    Title Should Be    Dashboard
    ...    ELSE    Element Should Be Visible    css=.error-message
    
    Close Browser
```

## Configuration

### Command Line Options

```bash
# Run all tests
robot tests/

# Run specific test
robot tests/test_login.robot

# Run by tag
robot --include smoke tests/

# Run with variables
robot --variable BROWSER:firefox tests/

# Generate reports
robot --outputdir results --report report.html --log log.html tests/
```

### Robot Configuration File

```yaml
# robot.yaml
output-dir: ./results
log-level: INFO
variables:
  BROWSER: chrome
  URL: https://example.com
```

### Suite Setup/Teardown

```robot
*** Settings ***
Suite Setup       Open Browser    ${URL}    ${BROWSER}
Suite Teardown    Close Browser
Test Setup        Go To    ${URL}
Test Teardown     Capture Page Screenshot

*** Test Cases ***
Test One
    # Browser already open from Suite Setup
    Click Element    id=button1

Test Two
    # Same browser instance
    Click Element    id=button2
```

## Usage with CrossBridge

### Discover Tests

```python
from adapters.robot import RobotAdapter, RobotConfig

# With defaults
adapter = RobotAdapter("/path/to/project")

# With custom config
config = RobotConfig(
    tests_path="/path/to/project/tests",
    pythonpath="/path/to/project/resources"
)
adapter = RobotAdapter("/path/to/project", config=config)

# Discover all tests
tests = adapter.discover_tests()
print(f"Found {len(tests)} tests")
```

### Run Tests

```python
# Run all tests
results = adapter.run_tests()

# Run specific tests
results = adapter.run_tests(tests=["Valid Login Test", "Search Test"])

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
from adapters.robot import RobotExtractor

extractor = RobotExtractor("/path/to/project")
tests = extractor.extract_tests()

for test in tests:
    print(f"Test: {test.test_name}")
    print(f"  File: {test.file_path}")
    print(f"  Tags: {test.tags}")
    print(f"  Framework: {test.framework}")
```

### Detect Projects

```python
from adapters.robot import RobotDetector

is_robot_project = RobotDetector.detect("/path/to/project")
if is_robot_project:
    print("Robot Framework project detected!")
```

## Robot Framework Tags

### Common Tags

```robot
*** Test Cases ***
Critical Test
    [Tags]    critical    smoke
    Log    Important test

Slow Test
    [Tags]    slow    regression
    Log    Takes time

API Test
    [Tags]    api    integration
    Log    Tests API
```

### Force Tags (Suite Level)

```robot
*** Settings ***
Force Tags    regression    nightly

*** Test Cases ***
Test One
    # Automatically has: regression, nightly
    Log    Test one

Test Two
    [Tags]    critical
    # Has: regression, nightly, critical
    Log    Test two
```

### Tag Filtering

```bash
# Include specific tags
robot --include smoke tests/

# Exclude tags
robot --exclude slow tests/

# Complex expressions
robot --include smokeANDcritical tests/
robot --include smokeORregression tests/
robot --include smoke --exclude slow tests/
```

## Keywords and Libraries

### Custom Python Library

```python
# libraries/CustomLibrary.py
class CustomLibrary:
    """Custom Robot Framework library."""
    
    def calculate_sum(self, a, b):
        """Calculate sum of two numbers."""
        return int(a) + int(b)
    
    def verify_text_contains(self, text, substring):
        """Verify text contains substring."""
        if substring not in text:
            raise AssertionError(f"'{text}' does not contain '{substring}'")
```

### Using Custom Library

```robot
*** Settings ***
Library    ../libraries/CustomLibrary.py

*** Test Cases ***
Use Custom Keywords
    ${result}=    Calculate Sum    5    3
    Should Be Equal As Numbers    ${result}    8
    
    ${text}=    Set Variable    Hello World
    Verify Text Contains    ${text}    World
```

## Variables

### Variable Files

```python
# resources/variables.py
URL = "https://example.com"
BROWSER = "chrome"
TIMEOUT = 30

USERS = {
    'admin': 'admin123',
    'test': 'test123'
}
```

### Using Variables

```robot
*** Settings ***
Variables    ../resources/variables.py

*** Test Cases ***
Use Variables
    Open Browser    ${URL}    ${BROWSER}
    Set Selenium Timeout    ${TIMEOUT}
    Input Text    id=username    ${USERS}[admin]
```

## Integration with Execution Engine

```python
from core.execution import TestExecutor, TestExecutionRequest, ExecutionStrategy

# Execute Robot Framework tests
request = TestExecutionRequest(
    framework="robot",
    project_root="/path/to/project",
    strategy=ExecutionStrategy.PARALLEL,
    max_workers=4,
    tags=["smoke", "critical"],
    timeout=120
)

executor = TestExecutor()
summary = executor.execute(request)

print(f"Total: {summary.total_tests}")
print(f"Passed: {summary.passed}")
print(f"Failed: {summary.failed}")
print(f"Success Rate: {summary.success_rate}%")
```

## Best Practices

1. **Use Resources**: Centralize keywords in resource files
2. **Page Objects**: Create resource files for each page/component
3. **Descriptive Names**: Use clear, readable test and keyword names
4. **Tags**: Tag tests appropriately for filtering
5. **Setup/Teardown**: Use suite and test setup/teardown
6. **Variables**: Externalize configuration in variable files
7. **Documentation**: Document tests and keywords
8. **Error Handling**: Use Run Keyword And Return Status for conditional logic

## Advanced Features

### Parallel Execution with Pabot

```bash
# Install pabot
pip install robotframework-pabot

# Run tests in parallel
pabot --processes 4 tests/
```

### Custom Listeners

```python
# listeners/TestListener.py
class TestListener:
    ROBOT_LISTENER_API_VERSION = 3
    
    def start_test(self, data, result):
        print(f"Starting test: {data.name}")
    
    def end_test(self, data, result):
        print(f"Test {data.name}: {result.status}")
```

### Using Listener

```bash
robot --listener listeners/TestListener.py tests/
```

### Screenshot on Failure

```robot
*** Settings ***
Library    SeleniumLibrary
Test Teardown    Run Keyword If Test Failed    Capture Page Screenshot

*** Test Cases ***
Test With Auto Screenshot
    Open Browser    ${URL}    chrome
    Click Element    id=invalid-element    # Will fail and capture screenshot
```

## Troubleshooting

### Tests Not Discovered

- Check file naming: `*.robot`
- Check Test Cases section exists
- Verify proper indentation (2 or 4 spaces)
- Check for syntax errors

### Import Errors

```robot
# Use correct paths
Resource    ../resources/common.robot           # Relative path
Resource    ${EXECDIR}/resources/common.robot   # From execution directory
```

### Element Not Found

```robot
# Use explicit waits
Wait Until Element Is Visible    id=element    timeout=10s
```

### Library Import Failed

```bash
# Check Python path
robot --pythonpath ./libraries tests/

# Verify library is importable
python -c "import CustomLibrary"
```

## Examples

See [examples/robot_tests/](../../examples/robot_tests/) for complete working examples including:
- Basic test suites
- Page Object Model patterns
- API testing examples
- Database testing examples
- Custom library examples

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines on extending the Robot Framework adapter.

## Resources

- [Robot Framework User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
- [SeleniumLibrary Documentation](https://robotframework.org/SeleniumLibrary/)
- [Robot Framework GitHub](https://github.com/robotframework/robotframework)
- [Awesome Robot Framework](https://github.com/fkromer/awesome-robotframework)
