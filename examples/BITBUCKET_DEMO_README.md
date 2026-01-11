# Bitbucket Cloud Migration Demo

This example demonstrates a complete workflow for migrating a Selenium Java BDD framework to Python Robot Framework with Playwright using an actual Bitbucket Cloud repository.

## Repository

**Source:** https://bitbucket.org/arcservedev/cc-ui-automation  
**Framework:** Selenium Java BDD  
**Target:** Python Robot Framework + Playwright

## Prerequisites

1. **Bitbucket App Password**
   - Go to: https://bitbucket.org/account/settings/app-passwords/
   - Click "Create app password"
   - Permissions needed:
     - ✅ Repositories: Read, Write
     - ✅ Pull requests: Read, Write
   - Copy the generated password

2. **Python Dependencies**
   ```bash
   pip install atlassian-python-api  # Bitbucket connector
   ```

3. **Set Environment Variables**
   ```bash
   # Windows PowerShell
   $env:BITBUCKET_USERNAME = "your_username"
   $env:BITBUCKET_TOKEN = "your_app_password"
   
   # Linux/Mac
   export BITBUCKET_USERNAME=your_username
   export BITBUCKET_TOKEN=your_app_password
   ```

## Usage

### 1. Dry Run (Preview Only)

Preview what the migration would do without making any changes:

```bash
python examples/bitbucket_migration_demo.py --dry-run
```

**Output:**
- ✅ Connects to Bitbucket repository
- ✅ Analyzes repository structure
- ✅ Discovers Java test files and feature files
- ✅ Shows sample file content
- ✅ Demonstrates transformation preview
- ❌ Does NOT create branches or PRs

### 2. Full Demo with Credentials

Run the complete workflow with environment variables:

```bash
python examples/bitbucket_migration_demo.py
```

Or provide credentials directly:

```bash
python examples/bitbucket_migration_demo.py --username your_username --token your_token
```

**Output:**
- ✅ All dry-run steps
- ✅ Creates migration branch: `feature/robot-playwright-migration`
- ✅ Creates pull request with description
- ✅ Provides PR URL for review

### 3. With AI Enhancement

Enable AI-powered transformation (requires AI module):

```bash
python examples/bitbucket_migration_demo.py --use-ai
```

## What The Demo Does

### Step 1: Connection
```
🔌 Connecting to Bitbucket Cloud
Workspace: arcservedev
Repository: cc-ui-automation
✅ Connected successfully
```

### Step 2: Repository Analysis
```
🔍 Analyzing Repository Structure
📋 Available Branches: main, develop, feature/...
📁 Repository Structure:
  📄 pom.xml
  📁 src/
  📁 target/
  📄 README.md

🔍 Discovering Java Test Files:
Found 15 Java test/step definition files:
  1. src/test/java/steps/LoginSteps.java
  2. src/test/java/steps/DashboardSteps.java
  ...

📝 Found 8 Gherkin feature files:
  1. src/test/resources/features/login.feature
  2. src/test/resources/features/dashboard.feature
  ...
```

### Step 3: File Preview
```
👁️ Preview: src/test/java/steps/LoginSteps.java
1 | package steps;
2 | 
3 | import org.openqa.selenium.WebDriver;
4 | import cucumber.api.java.en.Given;
5 | import cucumber.api.java.en.When;
... (shows first 30 lines)
```

### Step 4: Migration Plan
```
📋 Migration Plan: Selenium Java BDD → Robot Playwright
🎯 Migration Strategy:
  1. Feature Files (.feature) → Keep as-is (Gherkin is universal)
  2. Java Step Definitions (.java) → Python Robot Keywords (.robot/.py)
  3. Selenium WebDriver → Playwright Browser Library
  4. Java Page Objects → Python Page Object Models
  5. TestNG/JUnit → Robot Framework Test Suite

📊 Scope:
  • Java test files: 15
  • Feature files: 8
  • Target framework: Robot Framework + Playwright
```

### Step 5: Sample Transformation
```
🔄 Transforming Sample File
Source: src/test/java/steps/LoginSteps.java
Target: Robot Framework + Playwright

📝 Transformation Steps:
  1. ✓ Parsing Java source code
  2. ✓ Extracting step definitions
  3. ✓ Converting Selenium to Playwright
  4. ✓ Generating Robot Framework keywords
  5. ✓ Creating Python page objects

📤 Generated Output:
Target path: tests/LoginSteps.robot
--- Preview ---
*** Settings ***
Library    Browser    auto_closing_level=SUITE
Library    ./page_objects/LoginStepsPageObject.py

*** Test Cases ***
...
```

### Step 6: Branch Creation
```
🌿 Creating Migration Branch
Branch name: feature/robot-playwright-migration
✅ Branch created: feature/robot-playwright-migration
```

### Step 7: Pull Request
```
📬 Creating Pull Request
✅ Pull request created!
  PR #42: Migrate Selenium Java BDD to Robot Playwright
  URL: https://bitbucket.org/arcservedev/cc-ui-automation/pull-requests/42
  Status: open
```

## Migration Workflow

```
┌─────────────────────────────────────────────────────┐
│  Selenium Java BDD Framework                         │
│  ├── src/test/java/steps/*.java (Step Definitions)  │
│  ├── src/test/resources/features/*.feature          │
│  ├── src/main/java/pages/*.java (Page Objects)      │
│  └── pom.xml (Maven dependencies)                   │
└─────────────────────────────────────────────────────┘
                      │
                      │ CrossBridge Migration
                      ▼
┌─────────────────────────────────────────────────────┐
│  Robot Framework + Playwright                        │
│  ├── tests/*.robot (Test Suites)                    │
│  ├── resources/keywords/*.robot (Keywords)          │
│  ├── libraries/page_objects/*.py (Page Objects)     │
│  ├── resources/features/*.feature (Kept)            │
│  └── requirements.txt (Python dependencies)         │
└─────────────────────────────────────────────────────┘
```

## Mapping Examples

### Java Step Definition → Robot Keyword

**Before (Java):**
```java
@Given("^I am on the login page$")
public void i_am_on_the_login_page() {
    driver.get("https://example.com/login");
    wait.until(ExpectedConditions.visibilityOf(loginPage.usernameField));
}

@When("^I enter username \"([^\"]*)\" and password \"([^\"]*)\"$")
public void i_enter_credentials(String username, String password) {
    loginPage.enterUsername(username);
    loginPage.enterPassword(password);
    loginPage.clickLogin();
}
```

**After (Robot):**
```robot
*** Keywords ***
I Am On The Login Page
    [Documentation]    Navigate to login page
    New Page    https://example.com/login
    Wait For Elements State    id=username    visible

I Enter Username "${username}" And Password "${password}"
    [Documentation]    Enter login credentials
    Fill Text    id=username    ${username}
    Fill Text    id=password    ${password}
    Click    id=login-button
```

### Selenium WebDriver → Playwright

| Selenium | Playwright |
|----------|------------|
| `driver.findElement(By.id("btn"))` | `Click    id=btn` |
| `wait.until(ExpectedConditions.visibilityOf(element))` | `Wait For Elements State    selector    visible` |
| `driver.get(url)` | `New Page    ${url}` |
| `element.sendKeys(text)` | `Fill Text    selector    ${text}` |
| `element.click()` | `Click    selector` |
| `driver.switchTo().frame(frame)` | Auto-handled by Playwright |

## Command-Line Options

```
usage: bitbucket_migration_demo.py [-h] [--workspace WORKSPACE] [--repo REPO]
                                    [--username USERNAME] [--token TOKEN]
                                    [--dry-run] [--use-ai]

Options:
  -h, --help            Show help message
  --workspace WORKSPACE Bitbucket workspace (default: arcservedev)
  --repo REPO           Repository name (default: cc-ui-automation)
  --username USERNAME   Bitbucket username (or set BITBUCKET_USERNAME)
  --token TOKEN         Bitbucket app password (or set BITBUCKET_TOKEN)
  --dry-run             Preview only, do not create branch or PR
  --use-ai              Enable AI-enhanced transformation
```

## Troubleshooting

### "Authentication failed"
- Verify your app password is correct
- Check that the app password has repository read/write permissions
- Ensure you're using your Bitbucket username, not email

### "Repository not found"
- Verify the repository is public or you have access
- Check workspace and repo names are correct
- Try accessing the repo in a browser first

### "atlassian-python-api not found"
```bash
pip install atlassian-python-api
```

### "Rate limit exceeded"
- Bitbucket has API rate limits
- Wait a few minutes and try again
- Use `--dry-run` for testing without API calls

## Next Steps

After running the demo:

1. **Review the Pull Request**
   - Check transformed code in Bitbucket UI
   - Review test coverage
   - Validate Robot Framework syntax

2. **Test the Migration**
   ```bash
   # Install Robot Framework + Playwright
   pip install robotframework robotframework-browser
   rfbrowser init
   
   # Run migrated tests
   robot tests/
   ```

3. **Iterate if Needed**
   - Adjust transformation rules
   - Add custom mappings
   - Enhance with AI for better results

4. **Merge and Deploy**
   - Get team approval
   - Merge the PR
   - Update CI/CD pipelines

## Real-World Integration Test

This demo serves as an integration test for:
- ✅ Bitbucket Cloud connector functionality
- ✅ Repository analysis and file discovery
- ✅ Branch management operations
- ✅ Pull request creation workflow
- ✅ Java BDD framework detection
- ✅ Robot Playwright transformation planning

## See Also

- [Bitbucket Connector Documentation](../docs/REPO_NATIVE_TRANSFORMATION.md#4-bitbucket-connector)
- [Migration Guide](../docs/MIGRATION_GUIDE.md)
- [Robot Framework Documentation](https://robotframework.org/)
- [Playwright Browser Library](https://marketsquare.github.io/robotframework-browser/)

---

**Note:** This is a demonstration script. For production migrations, use the full CrossBridge transformation engine with proper error handling, rollback capabilities, and comprehensive testing.
