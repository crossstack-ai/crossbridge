# Quick Start Guide - Bitbucket Migration Demo

## Immediate Usage (No Credentials Required)

You can explore the repository structure without credentials by running in dry-run mode with a public repository check:

```powershell
# Test the demo script (shows help)
python examples\bitbucket_migration_demo.py --help
```

## For Testing with Real Repository

### Step 1: Get Bitbucket App Password

1. Go to https://bitbucket.org/account/settings/app-passwords/
2. Click "Create app password"
3. Name it: "CrossBridge Migration"
4. Select permissions:
   - ✅ Repositories: Read, Write
   - ✅ Pull requests: Read, Write
5. Copy the generated password

### Step 2: Set Credentials

```powershell
# Windows PowerShell
$env:BITBUCKET_USERNAME = "your_bitbucket_username"
$env:BITBUCKET_TOKEN = "your_app_password"
```

```bash
# Linux/Mac
export BITBUCKET_USERNAME=your_bitbucket_username
export BITBUCKET_TOKEN=your_app_password
```

### Step 3: Run Demo

```powershell
# Dry run (analysis only, no changes)
python examples\bitbucket_migration_demo.py --dry-run

# Full demo (creates branch and PR)
python examples\bitbucket_migration_demo.py

# With AI enhancement
python examples\bitbucket_migration_demo.py --use-ai
```

## What You'll See

```
==================================================
🚀 Bitbucket Cloud Migration Demo
==================================================
Repository: https://bitbucket.org/arcservedev/cc-ui-automation
Migration: Selenium Java BDD → Robot Playwright
Mode: DRY RUN (preview only)
==================================================

🔌 Connecting to Bitbucket Cloud
Workspace: arcservedev
Repository: cc-ui-automation
✅ Connected successfully to arcservedev/cc-ui-automation

🔍 Analyzing Repository Structure
📋 Available Branches:
  1. main
  2. develop
  3. feature/login-tests
  ...

📁 Repository Structure (root level):
  📄 pom.xml
  📁 src/
  📁 target/
  📄 README.md
  ...

🔍 Discovering Java Test Files:
Found 15 Java test/step definition files:
  1. src/test/java/steps/LoginSteps.java
  2. src/test/java/steps/DashboardSteps.java
  ...

📝 Found 8 Gherkin feature files:
  1. src/test/resources/features/login.feature
  2. src/test/resources/features/dashboard.feature
  ...

👁️ Preview: src/test/java/steps/LoginSteps.java
  1 | package steps;
  2 | import org.openqa.selenium.WebDriver;
  3 | import cucumber.api.java.en.Given;
  ... (first 30 lines shown)

📋 Migration Plan: Selenium Java BDD → Robot Playwright
🎯 Migration Strategy:
  1. Feature Files (.feature) → Keep as-is (Gherkin is universal)
  2. Java Step Definitions (.java) → Python Robot Keywords
  3. Selenium WebDriver → Playwright Browser Library
  4. Java Page Objects → Python Page Object Models
  5. TestNG/JUnit → Robot Framework Test Suite

📊 Scope:
  • Java test files: 15
  • Feature files: 8
  • Target framework: Robot Framework + Playwright

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
--- Preview (first 15 lines) ---
  1 | *** Settings ***
  2 | Library    Browser    auto_closing_level=SUITE
  3 | Library    ./page_objects/LoginStepsPageObject.py
  4 | 
  5 | *** Test Cases ***
  6 | Sample Test Case
  7 |     [Documentation]    Migrated from src/test/java/steps/LoginSteps.java
  8 |     [Tags]    migrated    selenium-to-playwright
  9 |     Open Browser    ${BASE_URL}    chromium
  10 |     # Converted step definitions go here
  ...

==================================================
✨ Demo Complete!
==================================================
Repository analyzed: ✅
Test files discovered: ✅
Migration plan created: ✅
Sample transformation: ✅

ℹ️  Run without --dry-run to create actual branch and PR
```

## Expected Output (Full Run)

When run without `--dry-run`:

```
🌿 Creating Migration Branch
Branch name: feature/robot-playwright-migration
✅ Branch created: feature/robot-playwright-migration

💾 Would commit 15 transformed files...

📬 Creating Pull Request
✅ Pull request created!
  PR #42: Migrate Selenium Java BDD to Robot Playwright
  URL: https://bitbucket.org/arcservedev/cc-ui-automation/pull-requests/42
  Status: open

==================================================
✨ Demo Complete!
==================================================
Repository analyzed: ✅
Test files discovered: ✅
Migration plan created: ✅
Sample transformation: ✅
Branch created: ✅
Pull request: ✅
```

## Verifying the Results

After running the demo, you can:

1. **Check Bitbucket UI**
   - Visit: https://bitbucket.org/arcservedev/cc-ui-automation/branches
   - See the new branch: `feature/robot-playwright-migration`

2. **Review Pull Request**
   - Visit: https://bitbucket.org/arcservedev/cc-ui-automation/pull-requests
   - Find the PR titled "Migrate Selenium Java BDD to Robot Playwright"
   - Review the migration plan in the PR description

3. **Inspect Transformed Files**
   - Click through the PR to see proposed changes
   - Compare Java step definitions with Robot keywords
   - Verify Playwright usage

## Testing Different Repositories

To test with your own repository:

```powershell
python examples\bitbucket_migration_demo.py `
  --workspace your_workspace `
  --repo your_repo `
  --username your_username `
  --token your_token `
  --dry-run
```

## Troubleshooting

### Error: "Bitbucket credentials required"
- Set `BITBUCKET_USERNAME` and `BITBUCKET_TOKEN` environment variables
- Or pass `--username` and `--token` as command-line arguments

### Error: "Repository not found"
- Verify you have access to the repository
- Check workspace and repo names are correct
- Ensure your app password has repository read permissions

### Error: "Branch already exists"
- The demo will use the existing branch
- Or delete the branch in Bitbucket UI first
- Or change the branch name in the script

### Error: "atlassian-python-api not installed"
```powershell
pip install atlassian-python-api
```

## Next Steps

1. **Review the Demo Output** - Understand what files were discovered and how they would be transformed

2. **Examine Sample Transformations** - See the preview of Java → Robot conversions

3. **Run Full Migration** - Remove `--dry-run` to create actual branch and PR

4. **Integrate with CI/CD** - Use this workflow in your pipeline for automated migrations

5. **Customize Transformation** - Extend the demo for project-specific requirements

---

**Ready to try it?** Start with:
```powershell
python examples\bitbucket_migration_demo.py --dry-run
```

This will show you what the migration would do without making any changes!
