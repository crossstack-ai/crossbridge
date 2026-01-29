# AI Documentation

**Consolidated AI documentation for CrossBridge's AI-powered transformation capabilities.**

## 📘 Main Documentation

### [AI_GUIDE.md](AI_GUIDE.md) - **Complete AI Reference**

**The single comprehensive guide for all AI features in CrossBridge.**

This guide consolidates all AI documentation into one authoritative source covering:

- ✅ **Quick Start** - Get AI working in 3 steps
- ✅ **Setup & Configuration** - API keys, environment variables, verification
- ✅ **Operation Types** - When and how AI is used
- ✅ **AI Features** - Step definitions, page objects, locator analysis, self-healing
- ✅ **Model Selection** - OpenAI, Anthropic, Gemini comparison with costs
- ✅ **Transformation Modes** - AI-powered vs. pattern-based
- ✅ **Usage Examples** - CLI, programmatic, repo-native
- ✅ **Test Generation** - AI-powered test creation from natural language
- ✅ **Cost Management** - Estimation, optimization, budget control
- ✅ **Troubleshooting** - Common issues and solutions

## Quick Links

| Topic | Section | Description |
|-------|---------|-------------|
| **Getting Started** | [Quick Start](AI_GUIDE.md#quick-start) | Enable AI in 3 steps |
| **Setup** | [AI Setup](AI_GUIDE.md#ai-setup--configuration) | API keys, environment vars |
| **When to Use AI** | [Operation Types](AI_GUIDE.md#operation-types--ai-support) | MIGRATION_AND_TRANSFORMATION vs TRANSFORMATION |
| **Features** | [AI Features](AI_GUIDE.md#ai-features) | Step definitions, page objects, locators |
| **Models** | [Model Selection](AI_GUIDE.md#model-selection) | Compare OpenAI, Anthropic, Gemini |
| **Costs** | [Cost Management](AI_GUIDE.md#cost-management) | Estimate and optimize costs |
| **Problems** | [Troubleshooting](AI_GUIDE.md#troubleshooting) | Common issues and fixes |

## Key Concepts

### Operation Types

```
MIGRATION_AND_TRANSFORMATION → ✅ Full AI Support (Java → Robot)
TRANSFORMATION              → 🟡 Limited AI (locator modernization only)
MIGRATION                   → ❌ No AI (copy-only)
```

### Supported File Types

- **Step Definitions** (`*Steps.java`) - Cucumber → Robot Framework
- **Page Objects** (`*Page.java`) - Selenium → Playwright
- **Locators** (`*Locator*.java`) - Quality analysis + self-healing

### AI Providers

| Provider | Default Model | Cost/1K tokens | Best For |
|----------|---------------|----------------|----------|
| **OpenAI** | gpt-3.5-turbo | $0.002 | Most migrations |
| **Anthropic** | claude-3-sonnet | $0.003 | Balanced quality |
| **Google** | gemini-pro | $0.0005 | Budget-friendly |

## Common Use Cases

### 1. Enable AI for New Migration

```bash
python run_cli.py
# Select: Migration + Transformation
# Enable AI: Yes
# Provider: OpenAI
# Model: gpt-3.5-turbo
```

### 2. Configure AI Programmatically

```python
request = MigrationRequest(
    operation_type=OperationType.MIGRATION_AND_TRANSFORMATION,
    use_ai=True,
    ai_config={
        'provider': 'openai',
        'model': 'gpt-3.5-turbo',
        'api_key': os.environ.get('OPENAI_API_KEY')
    }
)
```

### 3. Generate Tests from Natural Language

```python
generator = AITestGenerator(provider='openai', model='gpt-4o')
test_code = generator.generate_test(
    description="Test user login flow",
    framework='robot-framework'
)
```

## What Changed?

**Previously:** 10 separate documentation files covering different aspects of AI
**Now:** 1 comprehensive guide ([AI_GUIDE.md](AI_GUIDE.md)) with all information organized logically

**Benefits:**
- ✅ Single source of truth
- ✅ No duplicate information
- ✅ Easy to navigate with table of contents
- ✅ Up-to-date with January 2026 features
- ✅ Consistent examples and terminology

## Migration from Old Docs

If you were using the old documentation:

| Old File | New Location |
|----------|--------------|
| `AI_QUICK_REFERENCE.md` | [Quick Start](AI_GUIDE.md#quick-start) |
| `AI_SETUP.md` | [AI Setup & Configuration](AI_GUIDE.md#ai-setup--configuration) |
| `AI_IMPLEMENTATION_COMPLETE.md` | [AI Features](AI_GUIDE.md#ai-features) |
| `AI_TRANSFORMATION_USAGE.md` | [Transformation Modes](AI_GUIDE.md#transformation-modes) + [Usage Examples](AI_GUIDE.md#usage-examples) |
| `AI_MODEL_SELECTION_ENHANCEMENT.md` | [Model Selection](AI_GUIDE.md#model-selection) |
| `AI_POWERED_TEST_GENERATION.md` | [AI-Powered Test Generation](AI_GUIDE.md#ai-powered-test-generation) |
| `AI_SUMMARY_IMPLEMENTATION.md` | [Cost Management](AI_GUIDE.md#cost-management) |
| `AI_TRANSFORMATION_SUMMARY.md` | [AI Features](AI_GUIDE.md#ai-features) |
| `AI_TRANSFORMATION_TEST_RESULTS.md` | Integrated throughout guide |
| `AI_SUMMARY_QUICK_REFERENCE.md` | [Cost Management](AI_GUIDE.md#cost-management) |

## Related Documentation

- **[Configuration](../configuration/)** - Environment variables, troubleshooting
- **[Guides](../guides/)** - Technical implementation guides
- **[Implementation](../implementation/)** - Framework status and progress

---

**Version:** 0.2.0 | **Last Updated:** January 2026 | **Status:** ✅ Production Ready
