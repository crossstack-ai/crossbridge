# Post-Migration Testing Guide: Robot Framework + Playwright

## Overview
After migration completes, your source tests have been transformed to Robot Framework with Playwright (Browser library). This guide covers setup, validation, and execution.

---

## 1. Migration Output Structure

Your migrated code follows this structure:

```
<target-repo>/
├── tests/                          # Test suites (.robot files)
│   └── test_suite.robot
├── resources/                      # Page objects and keywords
│   ├── LoginPage.robot
│   ├── HomePage.robot
│   └── CommonKeywords.robot
└── README.md                       # Auto-generated setup guide
```

**Key Components:**
- **tests/**: Contains test cases using Robot Framework syntax
- **resources/**: Reusable keywords (page objects, actions)
- **Locators**: Stored as variables (`${USERNAME_LOCATOR}`) in resource files

---

## 2. Environment Setup

### Prerequisites
- Python 3.8+ (Python 3.9-3.11 recommended)
- pip package manager
- Git (to clone migrated repository)

### Installation Steps

#### Step 1: Clone Migrated Repository
```bash
# Clone the target branch where migration created the PR
git clone <repo-url>
cd <repo-name>
git checkout <migration-branch>  # e.g., crossbridge-migration-robot
```

#### Step 2: Install Robot Framework & Playwright
```bash
# Install Robot Framework core
pip install robotframework

# Install Playwright browser library for Robot Framework
pip install robotframework-browser

# Initialize Playwright browsers (downloads Chromium, Firefox, WebKit)
rfbrowser init
```

**Alternative: Using requirements.txt**
```bash
# If migration generated requirements.txt
pip install -r requirements.txt
rfbrowser init
```

#### Step 3: Verify Installation
```bash
# Check Robot Framework version
robot --version

# Check Browser library installation
python -c "import Browser; print(Browser.__version__)"
```

---

## 3. Pre-Execution Validation

### Manual Review Checklist

Before running tests, review these migrated elements:

#### ✅ **Locators** (in `resources/*.robot`)
```robotframework
*** Variables ***
${USERNAME_LOCATOR}    id=username        # ✅ Verify selector is correct
${LOGIN_BTN}           css=button.login   # ✅ Check against actual app
```

**Action**: Compare locators against your application's HTML to ensure accuracy.

#### ✅ **TODO Comments** (in `tests/*.robot`)
```robotframework
User Is On The Login Page
    [Documentation]    Given: user is on the login page
    # TODO: Implement step - user is on the login page  # ⚠️ Needs implementation
```

**Action**: Implement missing step definitions flagged with `# TODO`.

#### ✅ **Test Data** (hardcoded values)
```robotframework
User Enters Username {String}
    Enter Username    username  # ⚠️ May need to parameterize
```

**Action**: Replace hardcoded values with variables or data-driven inputs.

#### ✅ **Browser Context** (setup/teardown)
Check if migrated tests include browser lifecycle management:
```robotframework
*** Settings ***
Suite Setup       Open Browser To Login Page
Suite Teardown    Close Browser
```

**Action**: Add if missing (see Section 4.3 below).

---

## 4. Test Execution

### 4.1 Basic Execution

#### Run All Tests
```bash
robot tests/
```

**Output:**
- Console: Real-time test execution logs
- `log.html`: Detailed execution log with screenshots
- `report.html`: Summary report with pass/fail statistics
- `output.xml`: Machine-readable results (for CI/CD)

#### Run Specific Test Suite
```bash
robot tests/test_suite.robot
```

#### Run Single Test Case
```bash
robot --test "User Is On The Login Page" tests/
```

### 4.2 Advanced Options

#### Headless Execution (for CI/CD)
```bash
robot --variable HEADLESS:True tests/
```

#### Custom Browser
```bash
robot --variable BROWSER:firefox tests/
```

#### Generate Results in Custom Directory
```bash
robot --outputdir results tests/
```

#### Parallel Execution (Pabot)
```bash
# Install pabot
pip install robotframework-pabot

# Run tests in parallel (4 threads)
pabot --processes 4 tests/
```

### 4.3 Adding Browser Setup (If Missing)

If tests don't include browser initialization, add to test suite:

**Option A: In Test Suite** (`tests/test_suite.robot`)
```robotframework
*** Settings ***
Documentation    Migrated from Java Selenium BDD
Library    Browser
Resource    ../resources/LoginPage.robot
Resource    ../resources/HomePage.robot

Suite Setup       New Browser    chromium    headless=False
Suite Teardown    Close Browser

*** Test Cases ***
# ... existing tests
```

**Option B: In Resource File** (`resources/CommonSetup.robot`)
```robotframework
*** Settings ***
Library    Browser

*** Keywords ***
Open Browser To Login Page
    New Browser    chromium    headless=False
    New Page    https://your-app-url.com
    Set Viewport Size    1920    1080

Close Browser
    Close Browser
```

Then import in test suites:
```robotframework
*** Settings ***
Resource    ../resources/CommonSetup.robot
Suite Setup       Open Browser To Login Page
Suite Teardown    Close Browser
```

---

## 5. Validation & Troubleshooting

### Expected First Run Results

**✅ Normal Scenarios:**
1. **Some failures**: Common due to locator mismatches or TODO steps
2. **Screenshots in logs**: Browser library captures screenshots on failure
3. **Execution time**: Slower than unit tests (browser-based)

**❌ Red Flags:**
- Import errors → Check resource file paths
- Locator not found → Verify selectors in `resources/*.robot`
- Timeout errors → Increase waits or check app availability

### Common Issues

#### Issue 1: Import Errors
```
Error: Resource file '../resources/LoginPage.robot' does not exist
```
**Solution**: Verify file paths and directory structure. Robot Framework uses relative paths from test file location.

#### Issue 2: Locator Not Found
```
Error: TimeoutError: Locator 'id=username' not found
```
**Solution**: 
1. Open `log.html` and check screenshot of page
2. Update locator in `resources/*.robot`
3. Use Browser library's auto-wait (default 10s timeout)

#### Issue 3: TODO Steps Fail
```
Error: No keyword with name '# TODO: Implement step' found
```
**Solution**: Implement missing keywords in resource files.

#### Issue 4: Playwright Not Initialized
```
Error: Playwright browsers are not installed
```
**Solution**: Run `rfbrowser init`

### Debugging Tips

#### Enable Verbose Logging
```bash
robot --loglevel DEBUG tests/
```

#### Pause Test for Inspection
Add to test case:
```robotframework
Sleep    30s    # Pause for 30 seconds to inspect browser
```

#### Interactive Mode (RF Explorer)
```bash
pip install robotframework-debugger

# Add to test
Set Breakpoint  # Execution pauses here
```

---

## 6. CI/CD Integration

### Jenkins Example
```groovy
pipeline {
    agent any
    stages {
        stage('Setup') {
            steps {
                sh 'pip install robotframework robotframework-browser'
                sh 'rfbrowser init'
            }
        }
        stage('Test') {
            steps {
                sh 'robot --variable HEADLESS:True --outputdir results tests/'
            }
        }
        stage('Publish') {
            steps {
                publishHTML([
                    reportDir: 'results',
                    reportFiles: 'report.html',
                    reportName: 'Robot Framework Report'
                ])
            }
        }
    }
}
```

### GitHub Actions Example
```yaml
name: Robot Framework Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install robotframework robotframework-browser
          rfbrowser init
      
      - name: Run tests
        run: robot --variable HEADLESS:True --outputdir results tests/
      
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: robot-results
          path: results/
```

### Azure Pipelines Example
```yaml
trigger:
- main

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.10'

- script: |
    pip install robotframework robotframework-browser
    rfbrowser init
  displayName: 'Install Robot Framework'

- script: |
    robot --variable HEADLESS:True --outputdir $(Build.ArtifactStagingDirectory) tests/
  displayName: 'Run Tests'

- task: PublishTestResults@2
  inputs:
    testResultsFormat: 'JUnit'
    testResultsFiles: '$(Build.ArtifactStagingDirectory)/output.xml'
  condition: always()
```

---

## 7. Iterative Improvement

### Step 1: Fix Immediate Failures
1. Run tests: `robot tests/`
2. Open `log.html` in browser
3. Fix failures (locators, TODOs, data)
4. Re-run until all pass

### Step 2: Refactor for Maintainability
- Extract common keywords to `resources/CommonKeywords.robot`
- Parameterize test data using variables
- Add setup/teardown for browser management

### Step 3: Enhance Test Coverage
- Add new test cases using migrated page objects
- Implement data-driven tests with `[Template]`
- Add assertions for edge cases

---

## 8. Documentation References

### Robot Framework
- **Official Docs**: https://robotframework.org/robotframework/
- **User Guide**: https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html

### Browser Library (Playwright)
- **Keyword Docs**: https://marketsquare.github.io/robotframework-browser/Browser.html
- **GitHub**: https://github.com/MarketSquare/robotframework-browser

### Community Resources
- **Robot Framework Slack**: https://robotframework-slack-invite.herokuapp.com/
- **Forum**: https://forum.robotframework.org/

---

## 9. Quick Reference

### Essential Robot Commands
```bash
# Run all tests
robot tests/

# Run with tags
robot --include smoke tests/

# Run and exclude slow tests
robot --exclude slow tests/

# Generate XUnit output for CI
robot --xunit xunit.xml tests/

# Run with custom variables
robot --variable BASE_URL:https://staging.app.com tests/

# Rerun failed tests
robot --rerunfailed output.xml tests/
```

### Browser Library Key Keywords
```robotframework
# Navigation
New Browser       chromium    headless=False
New Page          https://example.com

# Interactions
Click             css=button.submit
Fill Text         id=username    myuser
Select Options By    id=dropdown    value    option1

# Assertions
Get Text          css=.message    ==    Welcome!
Get Element Count    css=.item     ==    5

# Waits
Wait For Elements State    css=.loader    detached    timeout=30s
```

---

## 10. Migration-Specific Notes

### What CrossBridge Handles Automatically
✅ BDD step definitions → Robot Framework keywords  
✅ Page Object Model → Resource files with keywords  
✅ Selenium locators → Browser library selectors  
✅ Assertions → Browser library verification keywords  
✅ File naming (spaces → underscores for imports)  

### What Requires Manual Attention
⚠️ Custom framework utilities (requires case-by-case adaptation)  
⚠️ Database connections (need Robot Framework Database Library)  
⚠️ API calls (need Robot Framework Requests Library)  
⚠️ Dynamic locators (may need parameterization)  
⚠️ Test data files (need conversion to Robot variables/resources)  

---

## Need Help?

- **Check the auto-generated README.md** in your migrated repository
- **Review log.html** after test runs for detailed execution traces
- **Inspect the Draft PR** created by CrossBridge for migration summary
- **Consult Robot Framework docs** for syntax and best practices

**Happy Testing! 🤖🎭**
