# CrossBridge AI Guide

**Version:** 0.2.0  
**Last Updated:** January 2026  
**Status:** ✅ Production Ready

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [AI Setup & Configuration](#ai-setup--configuration)
4. [Operation Types & AI Support](#operation-types--ai-support)
5. [AI Features](#ai-features)
6. [Model Selection](#model-selection)
7. [Transformation Modes](#transformation-modes)
8. [Usage Examples](#usage-examples)
9. [AI-Powered Test Generation](#ai-powered-test-generation)
10. [Cost Management](#cost-management)
11. [Troubleshooting](#troubleshooting)

---

## Overview

CrossBridge's AI capabilities provide intelligent code transformation, test generation, and quality analysis. AI is primarily used for migrating Java/Cucumber tests to Robot Framework with Playwright, offering context-aware code conversion that significantly improves migration quality.

### When is AI Used?

```
┌─────────────────────────────────────────────────────────────┐
│                    Operation Types                           │
└─────────────────────────────────────────────────────────────┘

1. MIGRATION_AND_TRANSFORMATION (Java → Robot)
   ✅ AI FULLY SUPPORTED
   • Step definitions: Cucumber → Robot Framework
   • Page objects: Selenium → Playwright
   • Locators: Quality analysis + self-healing
   👉 PRIMARY USE CASE FOR AI

2. TRANSFORMATION (.robot → .robot refresh)
   🟡 LIMITED AI (Phase 2.5 only)
   • Tier-based formatting (no AI)
   • Phase 2.5 locator modernization (AI optional)
   👉 For refreshing already-migrated files

3. MIGRATION (copy-only)
   ❌ NO AI
   • Just copies files, no transformation
   👉 Backup/branch copy operations
```

### Key Benefits

- ✅ **Intelligent context-aware code conversion**
- ✅ **Better Cucumber pattern recognition**
- ✅ **Natural Playwright action generation**
- ✅ **Locator quality analysis with self-healing**
- ✅ **Automatic fallback to pattern-based transformation**
- ✅ **Multi-provider support** (OpenAI, Anthropic, Gemini)
- ✅ **Test generation from natural language**

---

## Quick Start

### Enable AI in 3 Steps

#### 1. Set API Key
```bash
# Linux/Mac
export OPENAI_API_KEY='sk-proj-...'

# Windows PowerShell
$env:OPENAI_API_KEY='sk-proj-...'

# Windows CMD
set OPENAI_API_KEY=sk-proj-...
```

#### 2. Configure Request
```python
from core.models import MigrationRequest, OperationType

request = MigrationRequest(
    operation_type=OperationType.MIGRATION_AND_TRANSFORMATION,
    use_ai=True,
    ai_config={
        'provider': 'openai',
        'api_key': os.environ.get('OPENAI_API_KEY'),
        'model': 'gpt-3.5-turbo'  # Most economical
    }
)
```

#### 3. Run Migration
```bash
python run_cli.py
# Select "Migration + Transformation" (default)
# Select "Enable AI-powered migration"
# Choose provider and model
```

---

## AI Setup & Configuration

### Prerequisites

Install required AI libraries:
```bash
pip install openai anthropic google-generativeai
```

### Getting API Keys

#### OpenAI
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Navigate to **API Keys** section
3. Click **"Create new secret key"**
4. Copy the key (starts with `sk-proj-` or `sk-`)

#### Anthropic (Claude)
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Navigate to **API Keys**
3. Create a new key
4. Copy the key (starts with `sk-ant-`)

#### Google Gemini
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key

### Configuration Methods

#### Option 1: Environment Variables (Recommended for Testing)

**Linux/Mac:**
```bash
export OPENAI_API_KEY='sk-...'
export ANTHROPIC_API_KEY='sk-ant-...'
export GEMINI_API_KEY='...'
```

**Windows PowerShell:**
```powershell
$env:OPENAI_API_KEY='sk-...'
$env:ANTHROPIC_API_KEY='sk-ant-...'
$env:GEMINI_API_KEY='...'
```

#### Option 2: .env File (Recommended for Development)

Create `.env` in project root:
```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

**Important:** Ensure `.env` is in `.gitignore`!

#### Option 3: System Environment Variables (Permanent)

**Windows:**
1. System Properties → Advanced → Environment Variables
2. Add new User or System variable
3. Restart terminal/IDE

**Linux/Mac:**
Add to `~/.bashrc` or `~/.zshrc`:
```bash
export OPENAI_API_KEY='sk-...'
```

### Verification

Verify AI setup:
```bash
python scripts/verify_openai.py
```

Expected output:
```
✅ OpenAI library installed
✅ API key found: sk-proj...
✅ API connection successful!
✅ OpenAI Integration Verified Successfully!
```

---

## Operation Types & AI Support

CrossBridge supports three main operation types with different AI applicability:

### 1. MIGRATION_AND_TRANSFORMATION ✅ **Full AI Support**

**Primary use case for AI transformation**

- **What it does:** Migrates Java/Cucumber source files to target branch AND transforms to Robot Framework
- **AI applies to:** Step definitions, page objects, locators (Java → Robot)
- **When to use:** New migrations, framework modernization
- **AI benefit:** Maximum value - intelligent code conversion

**Supported File Types:**
| File Type | Detection | AI Features |
|-----------|-----------|-------------|
| **Step Definitions** | `*Steps.java`, `@Given/@When/@Then` | Cucumber→Robot, Playwright actions |
| **Page Objects** | `*Page.java`, `@FindBy` | Locator extraction, keyword conversion |
| **Locators** | `*Locator*.java`, `By.*` | Quality analysis, self-healing suggestions |

### 2. TRANSFORMATION 🟡 **Limited AI (Phase 2.5 Only)**

**Re-transform existing Robot Framework files**

- **What it does:** Re-processes already-migrated `.robot` files on target branch
- **AI applies to:** Locator modernization (Phase 2.5) only
- **Primary method:** Tier-based formatting (no AI needed for .robot → .robot)
- **When to use:** Refresh headers, validate syntax, apply new formatting
- **Note:** Input files are already Robot Framework, so Java→Robot AI transformation doesn't apply

### 3. MIGRATION ❌ **No AI**

**Copy-only operation**

- **What it does:** Copies source files to target branch without any transformation
- **AI applies to:** N/A (no transformation)
- **When to use:** Quick backup, branch copy operations

---

## AI Features

### 1. AI-Powered Step Definition Transformation

Intelligent conversion of Cucumber/Java step definitions to Robot Framework keywords.

**Features:**
- Context-aware Cucumber pattern recognition
- Natural language documentation extraction
- Smart parameter handling
- Playwright best practices
- Automatic wait strategies

**Example Input (Java):**
```java
@Given("user enters username {string} and password {string}")
public void userEntersCredentials(String username, String password) {
    driver.findElement(By.id("username")).sendKeys(username);
    driver.findElement(By.id("password")).sendKeys(password);
}
```

**AI-Generated Output (Robot Framework):**
```robot
*** Keywords ***
User Enters Credentials
    [Arguments]    ${username}    ${password}
    [Documentation]    User enters username and password
    Fill Text    id=username    ${username}
    Fill Text    id=password    ${password}
```

### 2. AI-Powered Page Object Transformation

Intelligent locator strategy selection and keyword naming.

**Features:**
- Intelligent locator strategy selection (data-testid > id > CSS > XPath)
- Better keyword naming following Robot Framework conventions
- JavaDoc extraction for documentation
- Smart parameter handling
- Playwright-specific best practices (waits, error handling)

**Example Input (Java):**
```java
public class LoginPage {
    @FindBy(id = "username")
    private WebElement usernameField;
    
    public void enterUsername(String username) {
        usernameField.sendKeys(username);
    }
}
```

**AI-Generated Output (Robot Framework):**
```robot
*** Settings ***
Documentation    Login page object
Library          Browser

*** Variables ***
${USERNAME_FIELD}    id=username

*** Keywords ***
Enter Username
    [Arguments]    ${username}
    [Documentation]    Enter username in the username field
    Fill Text    ${USERNAME_FIELD}    ${username}
```

### 3. AI-Powered Locator Analysis with Self-Healing

Quality analysis and self-healing recommendations for locators.

**Features:**
- **Locator quality rating** (HIGH/MODERATE/POOR)
- **Self-healing recommendations:**
  - Identifies brittle XPath patterns
  - Suggests 2-3 alternative strategies
  - Recommends data-testid additions
  - Provides fallback locator chains
- Playwright-compatible syntax
- Migration paths from brittle to stable selectors

**Quality Levels:**
- ✅ **HIGH**: data-testid, id, unique CSS, ARIA
- ⚠️ **MODERATE**: class names, tag+attribute combos
- ❌ **POOR**: absolute XPath, text-based, positional

**Example Output:**
```robot
*** Variables ***
# Quality: POOR - XPath is brittle
# RECOMMENDATION: Use data-testid="login-btn" or id="login"
# Alternative strategies:
#   1. css=button.login-button
#   2. css=[type="submit"][value="Login"]
${LOGIN_BUTTON}    xpath=//div[@class="container"]/button[1]
```

### 4. File Type Detection

Intelligent detection of Java file types for appropriate AI processing.

**Detection Strategy:**

1. **By Filename Pattern:**
   - Step Definitions: `*Steps.java`, `*StepDef*.java`, `*StepDefinitions.java`
   - Page Objects: `*Page.java`, `*PageObject.java`
   - Locators: `*Locator*.java`, `*Element*.java`, `*Selector*.java`

2. **By Content Analysis:**
   - Step Definitions: `@Given`, `@When`, `@Then` annotations
   - Page Objects: `@FindBy`, `WebElement` declarations
   - Locators: `By.id`, `By.xpath`, `By.css` usage

3. **Default Fallback:** Attempt as step definition

---

## Model Selection

### Supported Providers

#### OpenAI Models
| Model | Cost per 1K tokens | Use Case | Recommendation |
|-------|-------------------|----------|----------------|
| `gpt-3.5-turbo` | ~$0.002 | Most transformations | ✅ **Default** - Most economical |
| `gpt-4o` | ~$0.005 | Better quality | Good balance |
| `gpt-4` | ~$0.03 | Complex transformations | 15x more expensive |
| `gpt-4-turbo` | ~$0.01 | Latest GPT-4 | Faster, capable |

#### Anthropic Models
| Model | Cost per 1K tokens | Use Case | Recommendation |
|-------|-------------------|----------|----------------|
| `claude-3-haiku-20240307` | ~$0.00025 | Simple transformations | Most economical |
| `claude-3-sonnet-20240229` | ~$0.003 | Balanced performance | ✅ **Default** |
| `claude-3-opus-20240229` | ~$0.015 | Most capable | Premium option |

#### Google Gemini Models
| Model | Cost per 1K tokens | Use Case | Recommendation |
|-------|-------------------|----------|----------------|
| `gemini-pro` | ~$0.0005 | General use | ✅ **Default** - Very economical |
| `gemini-pro-vision` | ~$0.002 | With image analysis | Special cases |

### Model Selection Guidance

**For Most Migrations:**
- Start with `gpt-3.5-turbo` (OpenAI) or `claude-3-sonnet` (Anthropic)
- Average step definition: 500-2000 tokens
- Typical project (100 files): $1-5 with GPT-3.5

**For Complex Transformations:**
- Use `gpt-4o` or `claude-3-opus`
- Complex business logic, nested conditions
- Custom framework patterns

**For Budget-Conscious:**
- `gemini-pro` - Very economical
- `claude-3-haiku` - Fast and cheap
- Pattern-based fallback (free)

---

## Transformation Modes

### 🤖 AI-Powered Transformation

**When Used:**
- `ENHANCED` or `HYBRID` mode is selected
- `use_ai=True` in migration request
- Valid AI configuration with API key is provided
- Source file is identified as step definition, page object, or locator file

**Requirements:**
```python
request = MigrationRequest(
    use_ai=True,
    ai_config={
        'provider': 'openai',  # or 'anthropic', 'gemini'
        'api_key': 'sk-...',
        'model': 'gpt-3.5-turbo',
        'temperature': 0.3,  # Lower = more deterministic
        'max_tokens': 2000,
        'region': 'US'  # For on-prem deployments
    }
)
```

**Automatic Fallback:**
If AI transformation fails, CrossBridge automatically falls back to pattern-based transformation.

### 🔧 Pattern-Based Transformation

**When Used:**
- Default mode (no AI configuration provided)
- AI transformation fails or times out (automatic fallback)
- `use_ai=False` explicitly set

**How It Works:**
- AST (Abstract Syntax Tree) parsing
- Regex-based Cucumber annotation extraction
- Hardcoded Selenium → Playwright action mapping
- Template-based keyword generation

**Benefits:**
- ✅ Fast and deterministic
- ✅ No API costs
- ✅ No network dependencies
- ✅ Works offline
- ✅ Predictable output

---

## Usage Examples

### CLI Interactive Mode

```bash
python run_cli.py

# Menu options:
# 1. Select operation: "Migration + Transformation"
# 2. Enable AI: Yes
# 3. Choose mode: "Public Cloud"
# 4. Choose provider: OpenAI
# 5. Select model: gpt-3.5-turbo
# 6. API key: (auto-detected from environment or prompt)
```

### Programmatic Usage

```python
from core.orchestrator import MigrationOrchestrator
from core.models import MigrationRequest, OperationType
import os

# Configure AI
ai_config = {
    'provider': 'openai',
    'api_key': os.environ.get('OPENAI_API_KEY'),
    'model': 'gpt-3.5-turbo',
    'temperature': 0.3
}

# Create migration request
request = MigrationRequest(
    operation_type=OperationType.MIGRATION_AND_TRANSFORMATION,
    use_ai=True,
    ai_config=ai_config,
    source_path='/path/to/java/tests',
    target_path='/path/to/robot/tests',
    framework='java-cucumber'
)

# Execute migration
orchestrator = MigrationOrchestrator()
result = orchestrator.migrate(request)

# Check AI summary
if result.ai_summary:
    print(f"Tokens used: {result.ai_summary.total_tokens}")
    print(f"Estimated cost: ${result.ai_summary.estimated_cost:.4f}")
    print(f"Files transformed: {result.ai_summary.files_transformed}")
```

### Repo-Native Mode with AI

```python
request = MigrationRequest(
    operation_type=OperationType.MIGRATION_AND_TRANSFORMATION,
    repo_native=True,  # Enable repo-native transformation
    use_ai=True,
    ai_config={
        'provider': 'anthropic',
        'api_key': os.environ.get('ANTHROPIC_API_KEY'),
        'model': 'claude-3-sonnet-20240229'
    }
)
```

---

## AI-Powered Test Generation

### Overview

Generate tests from natural language descriptions using AI.

### Features

1. **Natural Language to Test Code**
2. **Intelligent Assertion Generation**
3. **Context-Aware Page Object Usage**
4. **Test Enhancement**

### Usage

```python
from services.ai.test_generator import AITestGenerator

generator = AITestGenerator(
    provider='openai',
    api_key=os.environ.get('OPENAI_API_KEY'),
    model='gpt-4o'
)

# Generate test from description
test_code = generator.generate_test(
    description="""
    Test user login:
    1. Navigate to login page
    2. Enter username 'testuser'
    3. Enter password 'password123'
    4. Click login button
    5. Verify dashboard is displayed
    """,
    framework='robot-framework',
    style='keyword-driven'
)

print(test_code)
```

### Example Output

```robot
*** Test Cases ***
Test User Login
    [Documentation]    Verify user can successfully log in
    [Tags]    login    smoke
    
    Open Browser    https://example.com/login    chromium
    Enter Username    testuser
    Enter Password    password123
    Click Login Button
    Wait Until Page Contains    Dashboard
    [Teardown]    Close Browser

*** Keywords ***
Enter Username
    [Arguments]    ${username}
    Fill Text    id=username    ${username}

Enter Password
    [Arguments]    ${password}
    Fill Text    id=password    ${password}

Click Login Button
    Click    id=login-btn
```

---

## Cost Management

### Estimating Costs

**Average Token Usage:**
- Simple step definition: 500-1000 tokens
- Complex step definition: 1000-2000 tokens
- Page object: 800-1500 tokens
- Locator file: 300-800 tokens

**Example Project (100 files):**
- With GPT-3.5-turbo: $1-5
- With GPT-4: $15-75
- With Claude Sonnet: $2-8
- With Gemini Pro: $0.50-2

### Cost Optimization Tips

1. **Start with economical models** (gpt-3.5-turbo, gemini-pro)
2. **Use pattern-based for simple files** (disable AI for utilities)
3. **Batch processing** reduces overhead
4. **Cache transformations** to avoid re-processing
5. **Monitor token usage** via AI summary reports

### AI Transformation Summary

After migration, CrossBridge displays an AI-specific summary:

```
╔══════════════════════════════════════════════════════════╗
║            AI TRANSFORMATION SUMMARY                     ║
╚══════════════════════════════════════════════════════════╝

Provider: OpenAI (gpt-3.5-turbo)

Tokens Used:
  • Total: 45,230 tokens
  • Input: 38,100 tokens
  • Output: 7,130 tokens

Cost Estimate:
  • Input:  $0.076 (38,100 tokens × $0.002/1K)
  • Output: $0.014 (7,130 tokens × $0.002/1K)
  • Total:  $0.090

Files Processed:
  • Step Definitions: 23 files (AI)
  • Page Objects: 12 files (AI)
  • Locators: 8 files (AI)
  • Other: 15 files (Pattern-based)
  • Total: 58 files

Success Rate: 43/43 (100%) AI transformations successful
Fallback: 0 files fell back to pattern-based
```

---

## Troubleshooting

### Common Issues

#### 1. API Key Not Found

**Error:** `OpenAI API key not found`

**Solution:**
```bash
# Verify environment variable
echo $OPENAI_API_KEY  # Linux/Mac
echo %OPENAI_API_KEY%  # Windows

# Set if missing
export OPENAI_API_KEY='sk-...'
```

#### 2. API Rate Limits

**Error:** `Rate limit exceeded`

**Solutions:**
- Use exponential backoff (automatic in CrossBridge)
- Reduce concurrent AI calls
- Upgrade API tier
- Switch to different provider temporarily

#### 3. Transformation Quality Issues

**Problem:** AI output not meeting expectations

**Solutions:**
- Try a more capable model (gpt-4o, claude-3-opus)
- Adjust temperature (lower = more deterministic)
- Increase max_tokens for complex files
- Review and refine prompts in `orchestrator.py`

#### 4. Timeout Errors

**Error:** `AI request timed out`

**Solutions:**
- Increase timeout in configuration
- Use faster model (gpt-3.5-turbo)
- Enable automatic fallback to pattern-based
- Check network connectivity

#### 5. Fallback to Pattern-Based

**Notice:** `AI transformation failed, falling back to pattern-based`

**This is normal!** CrossBridge automatically falls back for reliability.

**Check:**
- AI configuration correctness
- API key validity
- Network connectivity
- Model availability

### Debug Mode

Enable debug logging to troubleshoot AI issues:

```bash
export CROSSBRIDGE_LOG_LEVEL=DEBUG
python run_cli.py
```

Or in code:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Related Documentation

- **[AI Model Selection](AI_MODEL_SELECTION_ENHANCEMENT.md)** - Detailed model comparison
- **[AI Summary Implementation](AI_SUMMARY_IMPLEMENTATION.md)** - Token tracking details
- **[Configuration Guide](../configuration/ENVIRONMENT_VARIABLES.md)** - Environment setup
- **[Troubleshooting](../configuration/TROUBLESHOOTING.md)** - Common issues

---

**For questions or issues, see:**
- [Troubleshooting Guide](../configuration/TROUBLESHOOTING.md)
- [Community Support](../community/CONTRIBUTING.md)
- [GitHub Issues](https://github.com/your-org/crossbridge/issues)
