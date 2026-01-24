# Quick Reference: AI Transformation

## � When is AI Used?

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

---

## 🚀 Enable AI in 3 Steps

### 1. Set API Key
```bash
export OPENAI_API_KEY='sk-proj-...'
```

### 2. Configure Request
```python
request = MigrationRequest(
    operation_type=OperationType.MIGRATION_AND_TRANSFORMATION,  # Important!
    use_ai=True,
    ai_config={
        'provider': 'openai',
        'api_key': os.environ.get('OPENAI_API_KEY'),
        'model': 'gpt-3.5-turbo'
    }
)
```

### 3. Run Migration
```bash
python run_cli.py
# Select "Migration + Transformation" (default)
# Select "Enable AI-powered migration"
```

---

## 🎯 What Gets AI Treatment

| File Type | Detection | AI Features |
|-----------|-----------|-------------|
| **Step Definitions** | `*Steps.java`, `@Given/@When/@Then` | Cucumber→Robot, Playwright actions |
| **Page Objects** | `*Page.java`, `@FindBy` | Locator extraction, keyword conversion |
| **Locators** | `*Locator*.java`, `By.*` | Quality analysis, self-healing suggestions |

---

## 📊 Expected Output

### Step Definition
```robot
*** Settings ***
Documentation    AI-powered transformation
Library          Browser

*** Keywords ***
User Enters Credentials
    [Arguments]    ${username}    ${password}
    [Documentation]    When: user enters username and password
    Fill Text    id=username    ${username}
    Fill Text    id=password    ${password}
```

### Page Object
```robot
*** Settings ***
Documentation    AI-powered transformation
Library          Browser

*** Variables ***
${LOGIN_BUTTON}    data-testid=login-btn

*** Keywords ***
Click Login
    [Documentation]    Click the login button
    Click    ${LOGIN_BUTTON}
```

### Locators (Self-Healing)
```robot
*** Variables ***
# HIGH QUALITY: Stable locator
${USERNAME}    id=username

# POOR QUALITY: Brittle XPath
# ALTERNATIVES:
#   1. id=password
#   2. data-testid=pwd-field (ADD THIS!)
${PASSWORD}    xpath=//form/div[2]/input
```

---

## ✅ Verify AI is Working

Look for logs:
```
🤖 AI-POWERED transformation mode enabled
   Detected: Step Definition file
🤖 Using AI to transform...
Calling openai with model gpt-3.5-turbo...
✅ AI transformation successful! Tokens: 1234, Cost: $0.0025
```

---

## 💰 Cost Reference

| Model | Cost per 1K tokens | Typical file |
|-------|-------------------|--------------|
| GPT-3.5-turbo | $0.002 | $0.003 |
| GPT-4 | $0.03 | $0.045 |
| Claude 3 Sonnet | $0.003 | $0.0045 |

100 files ≈ $0.30-$4.50 depending on model

---

## 🧪 Test Commands

```bash
# Quick test
python test_ai_transform.py

# Comparison demo
python demo_ai_vs_pattern.py

# Full demo (all 3 file types)
python demo_comprehensive_ai.py
```

---

## 🔧 Troubleshooting

| Issue | Fix |
|-------|-----|
| AI not being used | Check `use_ai=True` and API key set |
| "Falling back to pattern-based" | API key invalid or quota exceeded |
| No self-healing comments | File not detected as locator file |

---

## 📚 Full Docs

- `docs/AI_TRANSFORMATION_USAGE.md` - Complete guide
- `AI_IMPLEMENTATION_COMPLETE.md` - Implementation details
- `README.md` - Project overview
