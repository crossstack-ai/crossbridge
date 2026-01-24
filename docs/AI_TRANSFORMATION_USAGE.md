# AI Transformation Usage Guide

## Overview

CrossBridge supports both **AI-powered** and **pattern-based** transformation modes. This document clarifies when each mode is used and how to enable AI features.

**NEW:** After migration completes, an AI-specific summary displays token usage, costs, and transformation statistics. See [AI Transformation Summary](#ai-transformation-summary) section below.

## Operation Types and AI Support

CrossBridge supports three main operation types:

| Operation Type | Description | AI Support | Use Case |
|----------------|-------------|------------|----------|
| **MIGRATION** | Copy source files to target branch without transformation | ❌ No transformation | Quick backup/copy |
| **TRANSFORMATION** | Re-transform existing .robot files on target branch | 🟡 Limited* | Refresh already-migrated files |
| **MIGRATION_AND_TRANSFORMATION** | Migrate source + transform to Robot Framework | ✅ **Full AI** | New migrations (primary use case) |

**\*Note on TRANSFORMATION:** This operation re-formats already-migrated `.robot` files using tier-based enhancements (header updates, validation, etc.). Since input files are already Robot Framework (not Java), AI isn't needed. However, Phase 2.5 Locator Modernization can still use AI for quality analysis.

**Primary AI Use Case:** **MIGRATION_AND_TRANSFORMATION** (Java/Cucumber → Robot Framework)

This is where AI provides maximum value:
- ✅ Step definitions: Cucumber → Robot Framework
- ✅ Page objects: Selenium → Playwright
- ✅ Locators: Quality analysis + self-healing

## Transformation Modes Comparison

### 🤖 AI-Powered Transformation

**When Used:**
- `ENHANCED` or `HYBRID` mode is selected
- `use_ai=True` in migration request
- Valid AI configuration with API key is provided
- Source file is identified as step definition, page object, or locator file

**Benefits:**
- ✅ Intelligent context-aware code conversion
- ✅ Better Cucumber pattern recognition
- ✅ More natural Playwright action generation
- ✅ Improved parameter handling
- ✅ Natural language documentation
- ✅ Smart wait strategies
- ✅ Best practice implementations
- ✅ Locator quality analysis with self-healing recommendations
- ✅ Automatic detection of brittle XPath patterns
- ✅ Suggestions for alternative locator strategies

**File Types Supported:**
- ✅ **Step definition files** (`*StepDefinitions.java`, `*Steps.java`, `*StepDef.java`)
- ✅ **Page objects** (`*Page.java`, `*PageObject.java`, files with `@FindBy`)
- ✅ **Locator files** (`*Locators.java`, `*Elements.java`, `*Selectors.java`)
- ✅ **Mixed files** (auto-detected by content: `@Given`, `@When`, `@Then`, `@FindBy`, `WebElement`)

**Self-Healing Capabilities:**

AI-powered locator transformation includes quality analysis:

- **HIGH QUALITY** locators (data-testid, id, ARIA) - marked as stable
- **MODERATE QUALITY** locators (CSS classes) - flagged with warnings
- **POOR QUALITY** locators (XPath, positional) - suggestions for alternatives

For brittle locators, AI provides:
- 2-3 alternative locator strategies
- Recommendations to add data-testid attributes
- Migration path from XPath to CSS selectors
- Resilience scoring and self-healing suggestions

**Requirements:**
```python
# In CLI or API call
request = MigrationRequest(
    use_ai=True,
    ai_config={
        'provider': 'openai',  # or 'anthropic'
        'api_key': 'sk-...',
        'model': 'gpt-3.5-turbo',  # Most economical efficient default
        # Alternative models:
        # OpenAI: 'gpt-4', 'gpt-4-turbo'
        # Anthropic: 'claude-3-sonnet-20240229', 'claude-3-opus-20240229'
        'temperature': 0.3,
        'region': 'US'
    }
)
```

**Model Selection:**

The CLI now prompts for model selection with economical defaults:

**OpenAI Models:**
- `gpt-3.5-turbo` (Default) - Most economical, efficient for most transformations (~$0.002/1K tokens)
- `gpt-4` - More capable, higher cost (~$0.03/1K tokens, 15x more expensive)
- `gpt-4-turbo` - Latest GPT-4, faster and more capable

**Anthropic Models:**
- `claude-3-sonnet-20240229` (Default) - Balanced performance, economical (~$0.003/1K tokens)
- `claude-3-opus-20240229` - Most capable, higher cost

**Cost Considerations:**
- OpenAI GPT-3.5-turbo: ~$0.002 per 1K tokens
- OpenAI GPT-4: ~$0.03 per 1K tokens (15x more expensive than GPT-3.5)
- Anthropic Claude 3 Sonnet: ~$0.003 per 1K tokens
- Average step definition file: 500-2000 tokens
- **Recommendation:** Start with gpt-3.5-turbo for most migrations; use gpt-4 only for complex transformations

### 🔧 Pattern-Based Transformation

**When Used:**
- Default mode (no AI configuration provided)
- AI transformation fails or times out (automatic fallback)
- Non-step-definition files (page objects, utilities, etc.)
- `use_ai=False` explicitly set

**How It Works:**
- AST (Abstract Syntax Tree) parsing using JavaStepDefinitionParser
- Regex-based Cucumber annotation extraction: `@(Given|When|Then)`
- Hardcoded Selenium → Playwright action mapping
- Template-based keyword generation

**Benefits:**
- ✅ Fast and deterministic
- ✅ No API costs
- ✅ No network dependencies
- ✅ Works offline
- ✅ Predictable output

**Limitations:**
- ❌ Less intelligent pattern recognition
- ❌ May miss complex Cucumber patterns
- ❌ Generic Playwright implementations
- ❌ Basic parameter handling
- ❌ Limited context awareness

## Configuration Examples

### 1. Enable AI in CLI (Migration + Transformation)

```bash
python run_cli.py

# In the menu:
# 1. Select operation type: "Migration + Transformation" (default)
# 2. Select "Enable AI-powered migration" → Yes
# 3. Choose AI mode: "Public Cloud" or "On-prem"
# 4. Choose provider: OpenAI or Anthropic (Claude)
# 5. Enter API key
# 6. Select AI model (NEW!):
#    For OpenAI:
#      - [1] gpt-3.5-turbo (Default - Most economical)
#      - [2] gpt-4 (More capable, 15x higher cost)
#      - [3] gpt-4-turbo (Latest, faster)
#    For Anthropic:
#      - [1] claude-3-sonnet-20240229 (Default - Balanced)
#      - [2] claude-3-opus-20240229 (Most capable)
# 7. Proceed with migration
```

**CLI Model Selection Example:**

```
🤖 Enable AI-powered migration?
[1] Yes
[2] No

Your choice: 1

AI Mode:
[1] Public Cloud (OpenAI/Anthropic)
[2] On-prem

Your choice: 1

AI Provider:
[1] OpenAI
[2] Anthropic (Claude)

Your choice: 1

OpenAI API Key: ****

Available AI Models:
[1] gpt-3.5-turbo (Default - Most economical, efficient for most tasks)
[2] gpt-4 (More capable, higher cost)
[3] gpt-4-turbo (Latest GPT-4, faster and more capable)

Select AI Model [1]: 1

✓ AI configured with OpenAI gpt-3.5-turbo
```

### 2. Enable AI in Code (Migration + Transformation)

```python
from core.orchestration.orchestrator import MigrationOrchestrator
from core.repo import MigrationRequest, OperationType

request = MigrationRequest(
    source_repo_url="https://github.com/user/project",
    source_branch="main",
    target_branch="robot-migration",
    operation_type=OperationType.MIGRATION_AND_TRANSFORMATION,  # AI works here
    transformation_mode="ENHANCED",  # or "HYBRID"
    use_ai=True,  # KEY FLAG
    ai_config={
        'provider': 'openai',
        'api_key': 'YOUR_API_KEY',
        'model': 'gpt-3.5-turbo'
    }
)

orchestrator = MigrationOrchestrator()
result = orchestrator.migrate(request)
```

### 3. Transformation-Only Operation (Limited AI)

```python
# Re-transform existing .robot files on target branch
request = MigrationRequest(
    source_repo_url="https://github.com/user/project",
    target_branch="robot-migration",
    operation_type=OperationType.TRANSFORMATION,  # No AI transformation
    transformation_mode="ENHANCED",
    transformation_tier=TransformationTier.TIER_1,  # Header updates only
    # AI not needed here - files are already Robot Framework
)

# However, you can still enable Phase 2.5 for locator analysis:
request.enable_modernization = True
request.use_ai = True  # For locator quality analysis
request.ai_config = {...}
```

### 4. Migration-Only Operation (No AI)

```python
# Just copy files without transformation
request = MigrationRequest(
    source_repo_url="https://github.com/user/project",
    source_branch="main",
    target_branch="backup-branch",
    operation_type=OperationType.MIGRATION,  # No transformation = No AI
    # AI not applicable - no transformation happening
)
```

### 5. Disable AI (Pattern-Based Only)

```python
request = MigrationRequest(
    source_repo_url="https://github.com/user/project",
    source_branch="main",
    target_branch="robot-migration",
    operation_type=OperationType.MIGRATION_AND_TRANSFORMATION,
    transformation_mode="ENHANCED",
    use_ai=False,  # Explicitly disable
    ai_config=None
)
```

## How to Verify AI is Being Used

### 1. Check Logs

Look for these log messages:

```
🤖 AI-POWERED transformation mode enabled for path/to/StepDefinitions.java
   Detected: Step Definition file
🤖 Using AI to transform step definitions: path/to/StepDefinitions.java
Calling openai with model gpt-3.5-turbo...
✅ AI step definition transformation successful! Tokens: 1234, Cost: $0.0025
```

For page objects:

```
🤖 AI-POWERED transformation mode enabled for path/to/LoginPage.java
   Detected: Page Object file
🤖 Using AI to transform page object: path/to/LoginPage.java
Calling openai with model gpt-3.5-turbo...
✅ AI page object transformation successful! Tokens: 987, Cost: $0.0020
```

For locators with self-healing analysis:

```
🤖 AI-POWERED transformation mode enabled for path/to/LoginLocators.java
   Detected: Locator file
🤖 Using AI to transform locators: path/to/LoginLocators.java
Calling openai with model gpt-3.5-turbo...
✅ AI locator transformation successful! Tokens: 543, Cost: $0.0011
```

If AI is NOT being used, you'll see:

```
PATTERN-BASED TRANSFORMATION (fallback or default)
```

Or:

```
AI transformation failed for path/to/file.java, falling back to pattern-based
Falling back to pattern-based transformation
```

### 2. Check Generated Files

**AI-generated step definition files** include comments:

```robot
*** Settings ***
Documentation    LoginSteps - Step Definitions
...              Migrated from Java Cucumber step definitions
...              AI-powered transformation
Library          Browser
```

**AI-generated page object files** include:

```robot
*** Settings ***
Documentation    LoginPage - Page Object
...              Migrated from Java Selenium Page Object
...              AI-powered transformation
Library          Browser

*** Variables ***
${USERNAME_FIELD}    id=username
${PASSWORD_FIELD}    id=password
${LOGIN_BUTTON}      data-testid=login-btn
```

**AI-generated locator files with self-healing analysis**:

```robot
*** Settings ***
Documentation    Locators: LoginLocators
...              AI-enhanced with quality analysis
...              Includes self-healing recommendations
Library          Browser

*** Variables ***
# HIGH QUALITY: Stable data-testid locator
${LOGIN_BUTTON}    data-testid=login-btn

# MODERATE QUALITY: Class-based, may break with style changes
# RECOMMENDATION: Add data-testid attribute to source HTML
${USERNAME_FIELD}    css=.username-input

# POOR QUALITY: Positional XPath (BRITTLE!)
# ALTERNATIVES:
#   1. css=[name="password"]
#   2. data-testid=password-field (ADD THIS!)
#   3. id=passwordInput
${PASSWORD_FIELD}    xpath=//form/div[2]/input
```

**Pattern-based files** lack AI-specific comments and self-healing analysis:

```robot
*** Settings ***
Documentation    Migrated from: src/test/java/steps/LoginSteps.java
...              Generated: 2024-01-15 10:30:00
Library          Browser
```

### 3. Compare Output Quality

**AI Output Example:**
```robot
*** Keywords ***
User Enters Valid Credentials
    [Arguments]    ${username}    ${password}
    [Documentation]    When user enters username {string} and password {string}
    [Tags]    when
    Fill Text    id=username    ${username}
    Fill Text    id=password    ${password}
    Wait For Elements State    id=loginButton    enabled    timeout=5s
```

**Pattern-Based Output Example:**
```robot
*** Keywords ***
User Enters Username And Password
    [Arguments]    ${username}    ${password}
    [Documentation]    When: user enters username {string} and password {string}
    # Original Java method body not parsed - add implementation
    # Step pattern: user enters username {string} and password {string}
    Log    TODO: Implement step 'User Enters Username And Password'
```

## Code Flow Diagram

```
┌─────────────────────────────────────────┐
│ Migration Request with AI Config        │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ _transform_java_to_robot_keywords()     │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Check: request.use_ai == True?      │ │
│ │        request.ai_config exists?    │ │
│ └──────────┬──────────────────────────┘ │
│            │                             │
│     ┌──────┴──────┐                     │
│     ▼             ▼                     │
│   YES            NO                     │
│     │             │                     │
│     ▼             ▼                     │
│  ┌──────────────────────┐  ┌─────────┐ │
│  │ Detect File Type:    │  │ Pattern │ │
│  │ • Filename pattern   │  │  Based  │ │
│  │ • Content analysis   │  └────┬────┘ │
│  │   (@Given, @FindBy)  │       │      │
│  └──────┬───────────────┘       │      │
│         │                       │      │
│   ┌─────┼─────┬─────────┐       │      │
│   ▼     ▼     ▼         ▼       │      │
│ ┌────┐┌────┐┌────┐   ┌────┐    │      │
│ │Step││Page││Loc │   │Auto│    │      │
│ │Def ││Obj ││ator│   │Det │    │      │
│ └─┬──┘└─┬──┘└─┬──┘   └─┬──┘    │      │
│   │     │     │        │        │      │
│   ▼     ▼     ▼        ▼        │      │
│ ┌──────────────────────────┐    │      │
│ │ Call OpenAI/Anthropic     │    │      │
│ │ • Step: gherkin→robot     │    │      │
│ │ • Page: selenium→pw       │    │      │
│ │ • Locator: quality check  │    │      │
│ └──┬───────────────────────┘    │      │
│    │                            │      │
│    ├─ Success ─────────┐        │      │
│    │                   │        │      │
│    └─ Failure ─────────┤        │      │
│                        │        │      │
│                        ▼        ▼      │
│          ┌──────────────────────────┐  │
│          │   Pattern-Based          │  │
│          │   Fallback               │  │
│          └──────────────────────────┘  │
└─────────────────────────────────────────┘
```

**File Type Detection Logic:**

1. **By Filename:**
   - `*Steps.java`, `*StepDef*.java` → Step Definition
   - `*Page.java`, `*PageObject.java` → Page Object
   - `*Locator*.java`, `*Element*.java` → Locators

2. **By Content (if filename unclear):**
   - Contains `@Given`, `@When`, `@Then` → Step Definition
   - Contains `@FindBy`, `WebElement` → Page Object
   - Contains `By.id`, `By.xpath` → Locators

3. **Default:** Attempt as Step Definition

## Troubleshooting

### AI Not Being Used?

**Check:**

1. ✅ Operation type is `MIGRATION_AND_TRANSFORMATION` (not just TRANSFORMATION or MIGRATION)?
2. ✅ `use_ai=True` in request?
3. ✅ `ai_config` provided with valid API key?
4. ✅ File is Java source (not already .robot)?
5. ✅ Network connectivity to API endpoint?
6. ✅ API key has sufficient quota?

**Common Scenarios:**

| Scenario | AI Used? | Reason |
|----------|----------|---------|
| Java → Robot (new migration) | ✅ YES | Primary use case |
| .robot → .robot (re-transform) | ❌ NO | Files already Robot Framework |
| Copy files (migration-only) | ❌ NO | No transformation occurring |
| Phase 2.5 locator analysis | ✅ YES | AI analyzes locator quality |

### AI Calls Failing?

**Common Issues:**

- **Invalid API Key**: Check key format and permissions
- **Quota Exceeded**: Check OpenAI/Anthropic billing
- **Network Timeout**: Increase timeout in config
- **Rate Limiting**: Add delays between files

### Performance Optimization

**Tips:**

1. Use GPT-3.5-turbo for cost efficiency (vs GPT-4)
2. Process files in batches to avoid rate limits
3. Cache AI results for repeated migrations
4. Use pattern-based for simple files, AI for complex ones

## API Providers

### OpenAI

- **Models**: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`
- **Cost**: GPT-3.5: $0.002/1K tokens, GPT-4: $0.03/1K tokens
- **Setup**: https://platform.openai.com/api-keys
- **Limits**: 3 RPM (free tier), 60 RPM (paid tier)

### Anthropic

- **Models**: `claude-3-sonnet-20240229`, `claude-3-opus-20240229`
- **Cost**: Sonnet: $0.003/1K tokens, Opus: $0.015/1K tokens
- **Setup**: https://console.anthropic.com/
- **Limits**: 5 RPM (free tier), 50 RPM (paid tier)

## Best Practices

1. **Start with Pattern-Based**: Test migration flow without AI costs
2. **Enable AI for Complex Files**: Use AI for intricate step definitions
3. **Monitor Costs**: Track API usage and set budgets
4. **Review AI Output**: Always review AI-generated code before deployment
5. **Use Hybrid Mode**: Combine AI intelligence with manual review markers
6. **Fallback Strategy**: AI automatically falls back to pattern-based on failure

## Future Enhancements

Planned AI features:

- [x] AI-powered step definition transformation
- [x] AI-powered page object transformation
- [x] AI-powered locator transformation with self-healing analysis
- [ ] AI-driven test data generation
- [ ] AI-suggested test coverage improvements
- [ ] AI-based flaky test detection
- [ ] AI-powered documentation generation
- [ ] Custom AI prompts per project
- [ ] Integration with locator modernization Phase 2.5 for runtime self-healing

## Integration with Locator Modernization

CrossBridge includes a dedicated **Phase 2.5: Locator Modernization** module that works alongside AI transformation:

### Phase 2.5 Features

Located in `core/locator_modernization/`:

- **Heuristic Analysis** (always active):
  - Pattern-based locator quality detection
  - Risk scoring (HIGH/MEDIUM/LOW)
  - Brittle selector identification

- **AI Analysis** (optional):
  - Deep quality assessment
  - Alternative strategy suggestions
  - Self-healing recommendations

- **Auto-Fix Capability**:
  - Automatic locator improvements (with approval)
  - Batch modernization
  - Impact analysis

### Using Both Together

**Recommended Workflow:**

1. **Initial Migration (AI-powered):**
   ```python
   request = MigrationRequest(
       use_ai=True,
       ai_config={'provider': 'openai', 'api_key': '...'},
       transformation_mode='ENHANCED'
   )
   ```
   
   Result: Initial transformation with basic self-healing comments

2. **Phase 2.5 Modernization:**
   ```python
   request = MigrationRequest(
       operation_type='transformation',
       enable_modernization=True,  # Enable Phase 2.5
       use_ai=True  # For deeper analysis
   )
   ```
   
   Result: Comprehensive locator quality report with fixes

3. **Iterative Improvement:**
   - Review AI recommendations
   - Apply suggested alternatives
   - Re-run modernization to validate

### Phase 2.5 Configuration

```python
from core.locator_modernization.engine import ModernizationEngine
from core.locator_modernization.ai_analyzer import AIModernizationAnalyzer

# Initialize with AI
ai_analyzer = AIModernizationAnalyzer(
    provider='openai',
    api_key='...',
    model='gpt-3.5-turbo'
)

engine = ModernizationEngine(
    enable_ai=True,
    ai_analyzer=ai_analyzer,
    min_confidence_threshold=0.7,
    auto_fix_enabled=False  # Set to True for automatic fixes
)

# Analyze locators
recommendations = engine.analyze_batch(locators)
```

### Self-Healing at Runtime

Future integration will enable:

- **Fallback Locator Chains**: Try primary, then alternatives
- **Dynamic Locator Selection**: Choose best locator at runtime
- **Learning from Failures**: Update locator preferences based on test results
- **Cross-Browser Resilience**: Different strategies per browser

---

## AI Transformation Summary

**NEW FEATURE:** After completing an AI-powered migration, CrossBridge automatically displays a comprehensive summary showing:

### What's Included

1. **AI Configuration**
   - Provider used (OpenAI/Anthropic)
   - Model used (gpt-3.5-turbo, gpt-4, claude-3-sonnet, etc.)

2. **Transformation Statistics**
   - Total files transformed with AI
   - Breakdown by type (step definitions, page objects, locators)

3. **Token Usage & Cost**
   - Total tokens consumed
   - Total cost in USD
   - Average tokens/cost per file

4. **Cost Breakdown by Type**
   - Separate costs for step definitions, page objects, locators

5. **Top Cost Files**
   - Lists 5 most expensive transformations with token counts

6. **Cost Comparison**
   - For gpt-3.5-turbo: Shows savings vs gpt-4 (93% reduction)
   - For gpt-4: Shows economical alternative (15x cheaper)

### Example Output

```
╭─────────────────────────────────────────────────────────╮
│           🤖 AI TRANSFORMATION SUMMARY                  │
╰─────────────────────────────────────────────────────────╯

⚙️  AI Configuration:
  • Provider: Openai
  • Model: gpt-3.5-turbo

📊 AI Transformation Statistics:
  ✓ Total Files Transformed: 12
  ✓ Step Definitions: 5
  ✓ Page Objects: 4
  ✓ Locators: 3

💰 Token Usage & Cost:
  • Total Tokens: 15,450
  • Total Cost: $0.0309
  • Avg Tokens/File: 1,288
  • Avg Cost/File: $0.0026

📈 Cost Breakdown by Type:
  • Step Definitions: $0.0191
  • Page Objects: $0.0094
  • Locators: $0.0044

💵 Top Cost Files:
  1. CheckoutSteps.java (Step Definition): $0.0050 (2,500 tokens)
  2. UserManagementSteps.java (Step Definition): $0.0042 (2,100 tokens)
  3. LoginStepDefinitions.java (Step Definition): $0.0037 (1,850 tokens)
  4. RegistrationSteps.java (Step Definition): $0.0036 (1,800 tokens)
  5. DashboardPage.java (Page Object): $0.0029 (1,450 tokens)

💡 Cost Savings:
  • Using gpt-3.5-turbo: $0.0309
  • Same with gpt-4: ~$0.46
  • Savings: ~$0.43 (93% reduction)

╰─────────────────────────────────────────────────────────╯
```

### Benefits

✅ **Transparency**: See exactly what you're paying for  
✅ **Optimization**: Make informed decisions about model selection  
✅ **Budgeting**: Predict costs for future migrations  
✅ **Validation**: Confirm economical model is sufficient  
✅ **ROI**: Compare AI costs vs manual effort ($0.03 vs 6 hours)

### When It Appears

The AI summary displays automatically:
- After migration/transformation completes
- Only if AI transformation was enabled
- Only if at least one file was transformed using AI
- After the regular migration and transformation summaries

Summary order:
1. Migration Summary (detection results)
2. Transformation Summary (file breakdown)
3. **AI Transformation Summary** (tokens, costs) ← NEW!
4. Locator Modernization Report (if enabled)

### Use Cases

**Cost Monitoring**: Track spending per migration run  
**Model Validation**: Verify gpt-3.5-turbo is sufficient (or justify gpt-4)  
**Budget Planning**: Estimate costs for future migrations  
**Optimization**: Identify expensive files for review

For complete details, see [AI_TRANSFORMATION_SUMMARY.md](../AI_TRANSFORMATION_SUMMARY.md)

---

**Note**: AI transformation is currently in **ALPHA** stage. While it provides superior results compared to pattern-based transformation, always review generated code before deployment to production.
