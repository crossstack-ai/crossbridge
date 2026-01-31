# Selenium .NET Adapter

Comprehensive support for pure Selenium .NET tests (non-BDD) in CrossBridge.

## Overview

This adapter provides full support for Selenium WebDriver tests written in C# using popular .NET test frameworks:
- NUnit
- MSTest  
- xUnit

**Note**: This is separate from the `selenium_specflow_dotnet` adapter which handles BDD/SpecFlow tests.

## Features

### Gap Implementations

This adapter addresses gaps identified in the Framework Gap Analysis:

#### Gap 5.1: Selenium .NET Adapter Implementation ✅
- Auto-detection of Selenium .NET projects
- Support for NUnit, MSTest, and xUnit test frameworks
- Test discovery using `dotnet test --list-tests`
- Test execution with TRX result parsing
- Page Object pattern support

#### Gap 5.2: Failure Classification ✅
- Intelligent categorization of WebDriver failures
- .NET exception mapping (NoSuchElementException, StaleElementReferenceException, etc.)
- C# stack trace parsing
- Locator extraction (By.Id, By.XPath, By.CssSelector, etc.)
- Page Object detection
- Intermittent failure detection

## Supported Test Frameworks

### NUnit
```csharp
[TestFixture]
public class LoginTests
{
    [Test]
    public void TestValidLogin()
    {
        // Test code
    }
}
```

### MSTest
```csharp
[TestClass]
public class LoginTests
{
    [TestMethod]
    public void TestValidLogin()
    {
        // Test code
    }
}
```

### xUnit
```csharp
public class LoginTests
{
    [Fact]
    public void TestValidLogin()
    {
        // Test code
    }
}
```

## Usage

### Basic Usage

```python
from adapters.selenium_dotnet import SeleniumDotNetAdapter

# Auto-detect project
adapter = SeleniumDotNetAdapter(project_root="path/to/project")

# Discover tests
tests = adapter.discover_tests()

# Run all tests
results = adapter.run_tests()

# Run specific tests
results = adapter.run_tests(tests=["MyNamespace.LoginTests.TestValidLogin"])
```

### With Configuration

```python
from adapters.selenium_dotnet import (
    SeleniumDotNetAdapter,
    SeleniumDotNetProjectConfig,
    DotNetTestFramework
)
from pathlib import Path

config = SeleniumDotNetProjectConfig(
    project_file=Path("MyTests/MyTests.csproj"),
    test_framework=DotNetTestFramework.NUNIT,
    project_root=Path("MyTests"),
    tests_dir=Path("MyTests/Tests"),
)

adapter = SeleniumDotNetAdapter(
    project_root="path/to/project",
    config=config
)
```

### Failure Classification

```python
from adapters.selenium_dotnet.failure_classifier import classify_selenium_dotnet_failure

classification = classify_selenium_dotnet_failure(
    error_message="OpenQA.Selenium.NoSuchElementException: no such element: Unable to locate element: {\"method\":\"id\",\"selector\":\"submit-btn\"}",
    stack_trace=stack_trace,
    test_name="TestUserLogin",
    exception_type="NoSuchElementException"
)

print(f"Failure Type: {classification.failure_type}")
# Output: no_such_element

print(f"Locator: {classification.locator}")
# Output: submit-btn

print(f"Strategy: {classification.locator_strategy}")
# Output: Id

print(f"Page Object: {classification.page_object}")
# Output: LoginPage (if detected in stack trace)

print(f"Intermittent: {classification.is_intermittent}")
# Output: False

print(f"Confidence: {classification.confidence}")
# Output: 0.9
```

## Failure Types

The adapter classifies 15+ failure types:

### Locator/Element Failures
- `no_such_element` - Element not found
- `stale_element` - Element reference is stale
- `element_not_visible` - Element exists but not visible
- `element_not_interactable` - Element not clickable/interactable
- `invalid_selector` - Invalid CSS/XPath selector

### Timeout Failures
- `timeout` - Generic timeout
- `element_timeout` - Wait for element timeout
- `page_load_timeout` - Page load timeout
- `script_timeout` - JavaScript execution timeout

### Window/Frame Failures
- `no_such_window` - Window/tab not found
- `no_such_frame` - Frame not found
- `no_alert` - No alert present

### Driver/Session Failures
- `session_not_created` - Failed to create WebDriver session
- `invalid_session` - WebDriver session invalid
- `driver_error` - WebDriver/ChromeDriver error
- `browser_crash` - Browser crashed

### Other
- `network_error` - Network connection error
- `assertion` - Test assertion failed
- `javascript_error` - JavaScript execution error

## Project Detection

The adapter auto-detects Selenium .NET projects by:

1. Finding `.csproj` files
2. Checking for `Selenium.WebDriver` package reference
3. Excluding SpecFlow projects (handled by separate adapter)
4. Detecting test framework (NUnit/MSTest/xUnit)
5. Locating test directories and Page Objects

## Requirements

- .NET SDK 6.0 or higher
- Selenium.WebDriver NuGet package
- One of: NUnit, MSTest, or xUnit test framework

## Completeness

**Current Status**: 98% Complete

### Implemented Features ✅
- Project detection
- Test discovery
- Test execution
- TRX result parsing
- Failure classification (Gap 5.2)
- Stack trace parsing
- Locator extraction
- Page Object detection
- Component attribution

### Future Enhancements
- Visual Studio Test Explorer integration
- Code coverage support
- Parallel execution optimization

## Related Adapters

- `selenium_specflow_dotnet` - For BDD/SpecFlow tests with Selenium
- `selenium_java` - For Java Selenium tests
- `selenium_pytest` - For Python Selenium tests
