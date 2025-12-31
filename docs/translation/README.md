# Framework-to-Framework Translation

## Overview

CrossBridge's Framework Translation feature enables **semantic translation** of test code between different testing frameworks. Unlike simple syntax converters, CrossBridge translates the **intent** and **behavior** of tests using a Neutral Intent Model (NIM).

## Key Principles

### ✅ What CrossBridge Does

- **Translates test intent and behavior** - not just syntax
- **Uses Neutral Intent Model** - framework-agnostic representation
- **Applies framework-specific idioms** - generates idiomatic code
- **Provides explicit confidence scores** - so you know what to review
- **Injects TODOs** for uncertain translations
- **Maintains traceability** - links to source code

### ❌ What CrossBridge Does NOT Do

- **Regex / line-by-line translation** - we understand semantics
- **"LLM, rewrite this file" prompts** - we have structured process
- **100% automated without review** - human verification is important
- **Syntax-only conversion** - we translate behavior

## Architecture

```
┌─────────────────┐
│  Source Code    │  (Selenium Java)
│  LoginTest.java │
└────────┬────────┘
         │
         │ Parser extracts actions, assertions, locators
         ▼
┌─────────────────────────────────────┐
│   Neutral Intent Model (NIM)        │
│                                     │
│   TestIntent {                      │
│     test_type: UI                   │
│     steps: [                        │
│       ActionIntent(NAVIGATE, ...)   │
│       ActionIntent(FILL, ...)       │
│       ActionIntent(CLICK, ...)      │
│     ]                               │
│     assertions: [                   │
│       AssertionIntent(VISIBLE, ...) │
│       AssertionIntent(TEXT, ...)    │
│     ]                               │
│   }                                 │
└────────┬────────────────────────────┘
         │
         │ Apply idioms, map APIs
         ▼
┌─────────────────┐
│  Target Code    │  (Playwright Python)
│  test_login.py  │
└─────────────────┘
```

## Translation Pipeline

The translation process follows 7 steps:

1. **Parse** - Extract TestIntent from source code
2. **Normalize** - Standardize actions and assertions
3. **Apply Idioms** - Transform framework-specific patterns
4. **Generate** - Create target code from intent
5. **AI Refine** *(optional, paid tier)* - Improve quality with AI
6. **Validate** - Check syntax and imports
7. **Inject TODOs** - Mark low-confidence items for review

## Supported Translation Paths

### Phase 1 (MVP)

| Source | Target | Status |
|--------|--------|--------|
| Selenium Java | Playwright Python | ✅ Implemented |
| Selenium Python | Playwright Python | 🔄 In Progress |
| RestAssured | Pytest | 🔄 Planned |
| Robot Framework | Pytest | 🔄 Planned |

### Phase 2 (Future)

- Cypress → Playwright
- Selenium → Cypress
- JUnit → Pytest
- TestNG → Pytest

## Usage

### CLI

```bash
# Basic translation
crossbridge translate \
  --source selenium-java \
  --target playwright-python \
  --input tests/LoginTest.java \
  --output tests/test_login.py

# With AI refinement (paid tier)
crossbridge translate \
  --source selenium-java \
  --target playwright-python \
  --input src/test/java \
  --output tests/ \
  --use-ai \
  --max-credits 500

# Batch mode
crossbridge translate \
  --source selenium-java \
  --target playwright-python \
  --input test-suite/ \
  --output playwright-tests/ \
  --mode batch \
  --validation lenient
```

### Programmatic API

```python
from core.translation.pipeline import TranslationPipeline

# Create pipeline
pipeline = TranslationPipeline()

# Translate single file
result = pipeline.translate(
    source_code=selenium_code,
    source_framework="selenium-java",
    target_framework="playwright-python",
)

if result.success:
    print(f"Confidence: {result.confidence:.1%}")
    print(result.target_code)
    
    # Review TODOs
    for todo in result.todos:
        print(f"TODO: {todo}")
```

## Translation Modes

### Assistive (Default)

- Shows preview of each translation
- Requires user confirmation
- Best for learning and initial migrations

### Automated

- Auto-applies high-confidence translations
- Prompts for low-confidence items
- Best for production use

### Batch

- Translates all files without prompts
- Generates review report
- Best for large codebases

## Confidence Scoring

Each translation receives a confidence score (0.0 to 1.0):

- **0.9-1.0**: Direct mapping, very high confidence
- **0.7-0.9**: Good translation, minor review recommended
- **0.5-0.7**: Uncertain translation, review required
- **0.0-0.5**: Low confidence, likely needs manual work

Low confidence items are marked with:
- ⚠️ Warning comments in code
- TODO comments for manual review
- Entry in `result.todos` list

## Idiom Transformations

CrossBridge automatically applies framework-specific idioms:

### Selenium → Playwright

| Selenium Pattern | Playwright Idiom | Reason |
|-----------------|------------------|--------|
| `WebDriverWait(...).until(...)` | *Removed* | Playwright auto-waits |
| `Thread.sleep(...)` | *Removed* | Not needed |
| `By.id("btn")` | `page.get_by_role("button")` | Accessibility-first |
| `findElement(...).getText()` | `expect(locator).to_have_text(...)` | Cleaner assertions |
| `driver.quit()` | *Handled by fixture* | Automatic cleanup |

### RestAssured → Pytest

| RestAssured Pattern | Pytest Idiom | Reason |
|--------------------|--------------|--------|
| `given().auth().get()` | `requests.get(auth=...)` | Native Python |
| `given().when().then()` | AAA pattern | Pytest convention |
| `assertThat(...).isEqualTo()` | `assert ... == ...` | Python native |

## Examples

### Example 1: Simple Login Test

**Input (Selenium Java):**

```java
@Test
public void testLogin() {
    driver.get("https://example.com/login");
    driver.findElement(By.id("username")).sendKeys("admin");
    driver.findElement(By.id("password")).sendKeys("pass123");
    driver.findElement(By.id("login-btn")).click();
    
    assertTrue(driver.findElement(By.id("welcome")).isDisplayed());
}
```

**Output (Playwright Python):**

```python
def test_login(page: Page):
    page.goto("https://example.com/login")
    page.locator("#username").fill("admin")
    page.locator("#password").fill("pass123")
    page.get_by_role("button", name="login").click()
    
    expect(page.locator("#welcome")).to_be_visible()
```

### Example 2: Test with Explicit Waits

**Input (Selenium Java):**

```java
@Test
public void testDynamicContent() {
    driver.get("https://example.com");
    
    WebDriverWait wait = new WebDriverWait(driver, 10);
    wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("content")));
    
    Thread.sleep(2000);
    
    driver.findElement(By.id("button")).click();
}
```

**Output (Playwright Python):**

```python
def test_dynamic_content(page: Page):
    page.goto("https://example.com")
    
    # Explicit wait removed - Playwright auto-waits
    
    # Sleep removed - Playwright auto-waits
    # TODO: If this sleep was intentional, use page.wait_for_timeout()
    
    page.locator("#button").click()
```

## Validation

CrossBridge validates generated code at three levels:

### Strict (Default)

- Fails on syntax errors
- Fails on missing imports
- Fails on undefined variables
- Best for production

### Lenient

- Warns on issues but generates code
- Useful for exploration
- Good for iterative refinement

### Skip

- No validation
- Fastest mode
- Use only if you have external validation

## AI Refinement (Enterprise)

The OSS version provides rule-based translation. The Enterprise version adds AI refinement:

```python
# Enterprise only
result = pipeline.translate(
    source_code=code,
    source_framework="selenium-java",
    target_framework="playwright-python",
    use_ai=True,  # Requires Enterprise license
    max_credits=100,
)
```

AI refinement provides:
- Better selector suggestions
- More idiomatic code patterns
- Smarter variable naming
- Enhanced comments and documentation

## Best Practices

### 1. Start with Assistive Mode

```bash
crossbridge translate \
  --source selenium-java \
  --target playwright-python \
  --input LoginTest.java \
  --output test_login.py \
  --mode assistive
```

Review the output, learn the patterns, then use automated mode.

### 2. Review TODOs

Always check `result.todos` or TODO comments in generated code:

```python
if result.todos:
    print("Review needed:")
    for todo in result.todos:
        print(f"  - {todo}")
```

### 3. Run Tests After Translation

Generated tests may need adjustments:

```bash
# After translation
pytest tests/test_login.py -v

# Fix any failures
# Re-run
```

### 4. Use Version Control

Commit before translation:

```bash
git add .
git commit -m "Pre-translation checkpoint"

crossbridge translate ...

# Review changes
git diff

# If good
git commit -m "Translated tests to Playwright"

# If not
git reset --hard HEAD
```

### 5. Incremental Migration

Don't translate everything at once:

1. Start with simple tests
2. Build confidence
3. Tackle complex tests
4. Run both frameworks in parallel
5. Gradually retire old framework

## Troubleshooting

### Issue: Low Confidence Scores

**Problem:** Many translations have confidence < 0.7

**Solutions:**
- Use AI refinement (Enterprise)
- Review and improve source tests
- Add custom idiom patterns
- Extend API mapping registry

### Issue: Generated Code Doesn't Run

**Problem:** Syntax errors or missing imports

**Solutions:**
- Use `--validation strict`
- Check framework versions
- Review TODO comments
- File issue with example code

### Issue: Incorrect Selector Translation

**Problem:** Locators don't work in target framework

**Solutions:**
- Prefer role-based selectors in source
- Add data-testid attributes
- Manually review selector mappings
- Use AI refinement

## Contributing

Want to add support for more frameworks? See [CONTRIBUTING.md](../CONTRIBUTING.md) for:

- Adding new parsers
- Adding new generators
- Extending idiom registry
- Improving confidence scoring

## Limitations

Current limitations (to be improved):

- ❌ Dynamic selectors (e.g., generated at runtime)
- ❌ Custom wait conditions
- ❌ Complex page object patterns
- ❌ Framework-specific plugins
- ❌ Non-standard test annotations

## Roadmap

### Q1 2024
- ✅ Selenium Java → Playwright Python
- 🔄 Selenium Python → Playwright Python
- 🔄 RestAssured → Pytest

### Q2 2024
- Robot Framework → Pytest
- Cypress → Playwright
- Enhanced AI refinement

### Q3 2024
- Selenium → Cypress
- JUnit → Pytest
- Custom framework support

## FAQ

**Q: Is this just a syntax converter?**

A: No! CrossBridge translates *test intent and behavior*, not just syntax. It understands what your test does and generates idiomatic code in the target framework.

**Q: Can I trust automated translations?**

A: Always review generated code, especially low-confidence items marked with TODOs. Use assistive mode first to build confidence.

**Q: Do I need AI refinement?**

A: No, the OSS version provides excellent rule-based translation. AI refinement (Enterprise) improves quality but isn't required.

**Q: Will translations be 100% accurate?**

A: High-confidence translations (>0.9) are typically accurate. Lower confidence translations need review. Always test after translation.

**Q: Can I customize translation rules?**

A: Yes! Extend `ApiMappingRegistry` and `IdiomRegistry` with custom patterns for your specific needs.

## Support

- 📖 Docs: https://crossbridge.dev/docs/translation
- 💬 Discord: https://discord.gg/crossbridge
- 🐛 Issues: https://github.com/crossbridge/crossbridge/issues
- 📧 Email: support@crossbridge.dev
