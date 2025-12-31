# Selenium + SpecFlow + .NET Adapter

Comprehensive adapter for C# BDD test automation using Selenium WebDriver, SpecFlow, and .NET test frameworks (NUnit, MSTest, or xUnit).

## Overview

This adapter enables CrossBridge to understand, analyze, and execute SpecFlow-based BDD tests written in C#. It provides complete support for:

- **BDD Frameworks**: SpecFlow with Gherkin syntax
- **Test Frameworks**: NUnit, MSTest, xUnit
- **Automation**: Selenium WebDriver for C#
- **Build System**: .NET SDK (.NET Core / .NET 5+)

## Features

### Automatic Project Detection
- Scans .csproj files for SpecFlow and test framework references
- Detects Features directory (case-insensitive)
- Identifies step definition locations
- Determines test framework (NUnit/MSTest/xUnit)

### Feature File Parsing
- Parses Gherkin .feature files
- Extracts scenarios and scenario outlines
- Captures feature/scenario tags (@smoke, @regression, etc.)
- Handles scenario backgrounds and data tables

### Step Definition Analysis
- Parses C# step definition files
- Extracts [Given], [When], [Then] attributes
- Handles regex patterns with escaped quotes
- Supports async step methods

### Test Execution
- Runs tests via `dotnet test`
- Supports tag-based filtering
- Parses TRX (Visual Studio Test Results) output
- Provides detailed test results with duration

### Metadata Extraction
- Extracts test metadata from scenarios
- Maps step definitions to implementations
- Identifies Page Object patterns
- Analyzes Selenium WebDriver usage

## Installation Requirements

### .NET SDK
```powershell
# Check .NET installation
dotnet --version

# Install .NET SDK if needed (version 6.0 or higher recommended)
# Download from: https://dotnet.microsoft.com/download
```

### SpecFlow Project Setup
```xml
<!-- .csproj file should include -->
<ItemGroup>
  <!-- SpecFlow -->
  <PackageReference Include="SpecFlow" Version="3.9.0" />
  <PackageReference Include="SpecFlow.Tools.MsBuild.Generation" Version="3.9.0" />
  
  <!-- Test Framework (choose one) -->
  <PackageReference Include="NUnit" Version="3.13.3" />
  <PackageReference Include="NUnit3TestAdapter" Version="4.2.1" />
  
  <!-- OR -->
  <PackageReference Include="MSTest.TestFramework" Version="3.0.0" />
  <PackageReference Include="MSTest.TestAdapter" Version="3.0.0" />
  
  <!-- OR -->
  <PackageReference Include="xunit" Version="2.4.2" />
  <PackageReference Include="xunit.runner.visualstudio" Version="2.4.5" />
  
  <!-- Selenium -->
  <PackageReference Include="Selenium.WebDriver" Version="4.15.0" />
  <PackageReference Include="Selenium.Support" Version="4.15.0" />
</ItemGroup>
```

## Usage

### Basic Usage

```python
from adapters.selenium_specflow_dotnet import (
    SeleniumSpecFlowAdapter,
    SpecFlowProjectDetector
)

# Auto-detect project configuration
detector = SpecFlowProjectDetector("/path/to/specflow/project")
config = detector.detect()

if config:
    print(f"Detected {config.test_framework.value} project")
    print(f"Features: {config.features_dir}")
    print(f"Step Definitions: {config.step_definitions_dir}")
    
    # Create adapter
    adapter = SeleniumSpecFlowAdapter("/path/to/specflow/project")
    
    # Discover all test scenarios
    tests = adapter.discover_tests()
    print(f"Found {len(tests)} scenarios")
    
    # Run all tests
    results = adapter.run_tests()
    
    for result in results:
        print(f"{result.test_name}: {result.status} ({result.duration}s)")
```

### Manual Configuration

```python
from adapters.selenium_specflow_dotnet import (
    SeleniumSpecFlowAdapter,
    SpecFlowProjectConfig,
    DotNetTestFramework
)
from pathlib import Path

# Manual configuration
config = SpecFlowProjectConfig(
    project_file=Path("/path/to/project.csproj"),
    test_framework=DotNetTestFramework.NUNIT,
    features_dir=Path("/path/to/Features"),
    step_definitions_dir=Path("/path/to/StepDefinitions"),
    project_root=Path("/path/to/project")
)

adapter = SeleniumSpecFlowAdapter(
    "/path/to/project",
    config=config
)
```

### Tag-Based Filtering

```python
# Run only tests tagged with @smoke
results = adapter.run_tests(
    test_filter={"tags": ["@smoke"]}
)

# Run tests tagged @regression but not @slow
results = adapter.run_tests(
    test_filter={
        "tags": ["@regression"],
        "exclude_tags": ["@slow"]
    }
)
```

### Metadata Extraction

```python
from adapters.selenium_specflow_dotnet import SeleniumSpecFlowExtractor

extractor = SeleniumSpecFlowExtractor("/path/to/project")

# Extract all test metadata
tests = extractor.extract_tests()
for test in tests:
    print(f"Scenario: {test.test_name}")
    print(f"  File: {test.file_path}")
    print(f"  Tags: {test.tags}")

# Extract step definitions
step_defs = extractor.extract_step_definitions()
for step in step_defs:
    print(f"{step['keyword']}: {step['pattern']}")
    print(f"  Method: {step['method']}")
    print(f"  File: {step['file']}")

# Extract Page Objects
page_objects = extractor.extract_page_objects()
for po in page_objects:
    print(f"Page Object: {po['class_name']}")
    print(f"  Elements: {len(po['elements'])}")
```

## Project Structure

### Typical SpecFlow Project Layout

```
MySpecFlowProject/
├── MyProject.csproj              # Project file with NuGet references
├── Features/                     # Feature files
│   ├── Login.feature
│   ├── Registration.feature
│   └── Search.feature
├── StepDefinitions/              # Step definition implementations
│   ├── LoginSteps.cs
│   ├── RegistrationSteps.cs
│   └── SearchSteps.cs
├── PageObjects/                  # Page Object Model (optional)
│   ├── LoginPage.cs
│   └── HomePage.cs
├── Hooks/                        # BeforeScenario/AfterScenario
│   └── Hooks.cs
└── Drivers/                      # WebDriver setup
    └── WebDriverFactory.cs
```

### Feature File Example

```gherkin
@smoke @login
Feature: User Login
    As a registered user
    I want to log in to the application
    So that I can access my account

Background:
    Given I am on the login page

@valid-credentials
Scenario: Successful login with valid credentials
    When I enter username "testuser" and password "TestPass123!"
    And I click the login button
    Then I should see the dashboard
    And I should see a welcome message

@invalid-credentials
Scenario Outline: Failed login with invalid credentials
    When I enter username "<username>" and password "<password>"
    And I click the login button
    Then I should see an error message "<error>"
    
    Examples:
      | username  | password | error                    |
      | invalid   | wrong    | Invalid credentials      |
      |           | empty    | Username is required     |
      | testuser  |          | Password is required     |
```

### Step Definitions Example

```csharp
using TechTalk.SpecFlow;
using OpenQA.Selenium;

[Binding]
public class LoginSteps
{
    private readonly IWebDriver _driver;
    private readonly LoginPage _loginPage;
    
    public LoginSteps(IWebDriver driver)
    {
        _driver = driver;
        _loginPage = new LoginPage(driver);
    }
    
    [Given(@"I am on the login page")]
    public void GivenIAmOnTheLoginPage()
    {
        _driver.Navigate().GoToUrl("https://example.com/login");
    }
    
    [When(@"I enter username ""(.*)"" and password ""(.*)""")]
    public void WhenIEnterCredentials(string username, string password)
    {
        _loginPage.EnterUsername(username);
        _loginPage.EnterPassword(password);
    }
    
    [When(@"I click the login button")]
    public void WhenIClickLoginButton()
    {
        _loginPage.ClickLoginButton();
    }
    
    [Then(@"I should see the dashboard")]
    public async Task ThenIShouldSeeDashboard()
    {
        await Task.Delay(1000); // Wait for navigation
        Assert.That(_driver.Url, Does.Contain("/dashboard"));
    }
    
    [Then(@"I should see a welcome message")]
    public void ThenIShouldSeeWelcomeMessage()
    {
        var message = _driver.FindElement(By.Id("welcome-message"));
        Assert.That(message.Displayed, Is.True);
    }
    
    [Then(@"I should see an error message ""(.*)""")]
    public void ThenIShouldSeeErrorMessage(string expectedError)
    {
        var errorElement = _driver.FindElement(By.ClassName("error"));
        Assert.That(errorElement.Text, Does.Contain(expectedError));
    }
}
```

### Page Object Example

```csharp
using OpenQA.Selenium;
using OpenQA.Selenium.Support.UI;

public class LoginPage
{
    private readonly IWebDriver _driver;
    
    // Element locators
    private By UsernameField => By.Id("username");
    private By PasswordField => By.Id("password");
    private By LoginButton => By.CssSelector("button[type='submit']");
    
    public LoginPage(IWebDriver driver)
    {
        _driver = driver;
    }
    
    public void EnterUsername(string username)
    {
        _driver.FindElement(UsernameField).SendKeys(username);
    }
    
    public void EnterPassword(string password)
    {
        _driver.FindElement(PasswordField).SendKeys(password);
    }
    
    public void ClickLoginButton()
    {
        _driver.FindElement(LoginButton).Click();
    }
}
```

## Configuration

### Test Framework Detection

The adapter automatically detects the test framework from .csproj:

- **NUnit**: `<PackageReference Include="NUnit" />`
- **MSTest**: `<PackageReference Include="MSTest.TestFramework" />`
- **xUnit**: `<PackageReference Include="xunit" />`

### Features Directory

Searches for feature files in:
1. `Features/` (case-insensitive)
2. Directory with .feature files referenced in .csproj
3. Root directory scan for .feature files

### Step Definitions Directory

Searches for step definitions in:
1. `StepDefinitions/` or `Steps/` (case-insensitive)
2. Same directory as features
3. Root directory scan for [Binding] classes

## Test Execution

### Command Line
```powershell
# Run all tests
dotnet test MyProject.csproj

# Run with filter
dotnet test --filter "TestCategory=smoke"

# Run specific test
dotnet test --filter "FullyQualifiedName~Login"

# Generate TRX results
dotnet test --logger "trx;LogFileName=results.trx"
```

### Via Adapter
```python
# Run all tests
results = adapter.run_tests()

# Run with timeout
results = adapter.run_tests(timeout=300)

# Run with tag filter
results = adapter.run_tests(
    test_filter={"tags": ["@smoke"]}
)

# Custom test command
results = adapter.run_tests(
    test_command="dotnet test --configuration Release"
)
```

## Troubleshooting

### Project Not Detected
**Problem**: `SpecFlowProjectDetector` returns `None`

**Solutions**:
1. Verify .csproj contains SpecFlow reference
2. Check test framework package is installed
3. Ensure Features directory exists with .feature files
4. Use manual configuration as fallback

### Step Definitions Not Found
**Problem**: Step definitions parsing returns empty list

**Solutions**:
1. Verify [Binding] attribute on step classes
2. Check [Given], [When], [Then] attributes are present
3. Ensure step definition files are in correct directory
4. Check for syntax errors in C# files

### Test Execution Fails
**Problem**: `run_tests()` returns failed results

**Solutions**:
1. Verify .NET SDK is installed: `dotnet --version`
2. Check project builds: `dotnet build`
3. Run tests manually: `dotnet test`
4. Review error messages in TestResult objects
5. Check TRX file for detailed errors

### TRX Parsing Issues
**Problem**: Test results not parsed correctly

**Solutions**:
1. Verify TRX file is generated in project directory
2. Check TRX XML structure
3. Ensure test names match scenario names
4. Look for XML parsing errors in logs

## Integration with CrossBridge

### CLI Integration

```bash
# Auto-detect and run SpecFlow tests
crossbridge test selenium-specflow --path /path/to/project

# Run with tags
crossbridge test selenium-specflow --path /path/to/project --tags @smoke

# Extract metadata
crossbridge extract selenium-specflow --path /path/to/project
```

### Pipeline Integration

```python
from core.orchestration import TestOrchestrator

orchestrator = TestOrchestrator()

# Register SpecFlow adapter
orchestrator.register_adapter("selenium-specflow", SeleniumSpecFlowAdapter)

# Run in pipeline
results = orchestrator.execute_tests(
    adapter_type="selenium-specflow",
    project_path="/path/to/project",
    filters={"tags": ["@regression"]}
)
```

## API Reference

### Classes

#### `SeleniumSpecFlowAdapter`
Main adapter for SpecFlow test execution.

**Methods**:
- `discover_tests()` → List[TestMetadata]
- `run_tests(test_filter=None, timeout=None)` → List[TestResult]
- `get_config_info()` → Dict

#### `SeleniumSpecFlowExtractor`
Extracts metadata from SpecFlow projects.

**Methods**:
- `extract_tests()` → List[TestMetadata]
- `extract_step_definitions()` → List[Dict]
- `extract_page_objects()` → List[Dict]

#### `SpecFlowProjectDetector`
Detects and analyzes SpecFlow project configuration.

**Methods**:
- `detect()` → Optional[SpecFlowProjectConfig]

#### `SpecFlowFeatureParser`
Parses Gherkin feature files.

**Methods**:
- `parse_feature(feature_file: Path)` → Dict

#### `SpecFlowStepDefinitionParser`
Parses C# step definition files.

**Methods**:
- `parse_step_definitions(cs_file: Path)` → List[Dict]

### Data Classes

#### `SpecFlowProjectConfig`
```python
@dataclass
class SpecFlowProjectConfig:
    project_file: Path          # .csproj file
    test_framework: DotNetTestFramework
    features_dir: Path          # Features directory
    step_definitions_dir: Path  # Step definitions directory
    project_root: Path          # Project root directory
```

#### `DotNetTestFramework`
```python
class DotNetTestFramework(Enum):
    NUNIT = "nunit"
    MSTEST = "mstest"
    XUNIT = "xunit"
```

## Best Practices

### Feature Files
- Use descriptive feature and scenario names
- Apply consistent tagging strategy (@smoke, @regression, @integration)
- Keep scenarios focused and independent
- Use Background for common setup steps
- Leverage Scenario Outline for data-driven tests

### Step Definitions
- Follow one step definition per method
- Use regex patterns for parameterized steps
- Keep step implementations simple and focused
- Share context via dependency injection
- Use async/await for async operations

### Page Objects
- Encapsulate page interactions in Page Object classes
- Use descriptive method names (e.g., `ClickLoginButton()`)
- Keep locators private and centralized
- Return Page Objects for fluent API (method chaining)
- Add wait logic in Page Object methods

### Test Organization
- Group related features in subdirectories
- Use consistent naming conventions
- Keep step definition files aligned with features
- Maintain hooks for setup/teardown
- Separate test data from test logic

## Performance Considerations

### Test Execution
- Use parallel execution: `dotnet test --parallel`
- Set reasonable timeouts
- Clean up resources in AfterScenario hooks
- Reuse WebDriver instances when possible

### CI/CD Integration
- Cache NuGet packages
- Use headless browsers for faster execution
- Run smoke tests before full suite
- Generate TRX reports for build systems
- Implement retry logic for flaky tests

## Limitations

- Requires .NET SDK 6.0 or higher
- Only supports SpecFlow 3.x+
- TRX parsing requires specific output format
- Step definition regex must follow C# verbatim string format
- No support for dynamic step definitions (runtime-generated)

## Support

For issues, questions, or contributions:
- GitHub Issues: [CrossBridge Repository]
- Documentation: See `/docs/adapters/selenium-specflow-dotnet.md`
- Examples: See `/examples/selenium-specflow-sample/`

## License

This adapter is part of the CrossBridge project and follows the same license terms.
