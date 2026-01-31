# Framework Migration

> **Incremental, AI-assisted test modernization without big-bang rewrites**

CrossBridge AI enables gradual, safe migration from legacy test frameworks to modern alternatives.

---

## 🎯 Migration Philosophy

### No Big-Bang Rewrites
- **Incremental**: Migrate tests gradually, not all at once
- **Safe**: Validate each transformation before applying
- **Reversible**: Rollback capability for every change
- **Non-disruptive**: Keep existing tests running during migration

### Two Migration Paths

#### Path 1: Observer Mode (No Migration)
Work with existing tests as-is:
```yaml
runtime:
  sidecar:
    enabled: true  # Get insights without changing tests
```

#### Path 2: Incremental Transformation
Migrate tests selectively:
```bash
crossbridge migrate --from selenium-java --to playwright --batch-size 10
```

---

## 🔄 Supported Migrations

### Currently Available

| From | To | Status | Completeness |
|------|-----|--------|--------------|
| Selenium Java | Playwright | ✅ Production | 92% |
| Selenium Python | Playwright | ✅ Production | 90% |
| Cucumber Java | Robot Framework BDD | ✅ Production | 88% |
| Selenium Java BDD | Modern BDD | ✅ Production | 95% |

### Planned Migrations

| From | To | Status | ETA |
|------|-----|--------|-----|
| Selenium .NET | Playwright .NET | 🚧 In Progress | Q2 2026 |
| Protractor | Cypress | 📋 Planned | Q3 2026 |
| WebdriverIO | Playwright | 📋 Planned | Q3 2026 |

---

## 🚀 Migration Process

### 1. Discovery & Analysis

Analyze existing test suite:

```bash
# Discover all tests
crossbridge discover --framework selenium-java --output analysis.json

# Analyze migration readiness
crossbridge migrate analyze --source analysis.json

# Output:
# Total tests: 245
# Page Objects: 23
# Simple tests: 189 (easy to migrate)
# Complex tests: 56 (need review)
# Estimated effort: 2-3 weeks with AI assistance
```

### 2. Strategy Selection

Choose migration approach:

**Quick Refresh** (Tier 1):
- Syntax updates only
- Minimal changes
- Fast, automated

**Content Validation** (Tier 2):
- Parse and validate structure
- Moderate changes
- Semi-automated

**Deep Regeneration** (Tier 3):
- Full AI-powered rewrite
- Significant improvements
- AI-assisted with human review

### 3. Batch Migration

Migrate in small, manageable batches:

```bash
# Migrate 10 tests at a time
crossbridge migrate run \
  --from selenium-java \
  --to playwright \
  --source src/test/java \
  --output tests/playwright \
  --batch-size 10 \
  --tier 2

# Review changes
git diff tests/playwright/

# Run tests to validate
npx playwright test

# Commit batch if successful
git commit -m "Migrate batch 1 (10 tests)"
```

### 4. Validation

Validate each batch before proceeding:

```bash
# Run migrated tests
crossbridge exec run --framework playwright --strategy full

# Compare results
crossbridge compare-results \
  --original results/selenium.json \
  --migrated results/playwright.json

# Confidence score: 0.94
# Pass rate: 100% (original: 100%)
# Duration: 45s (original: 120s) - 2.7x faster!
```

### 5. Incremental Rollout

Deploy gradually:

```
Week 1: Smoke tests (20 tests)  → Validate in staging
Week 2: Login flow (35 tests)   → Validate in staging
Week 3: Checkout (28 tests)     → Validate in staging
Week 4: Admin panel (42 tests)  → Validate in staging
Week 5: Full suite (245 tests)  → Production rollout
```

---

## 🤖 AI-Powered Transformation

### Automatic Enhancements

**Selenium → Playwright example**:

**Before (Selenium)**:
```java
driver.findElement(By.id("login-button")).click();
WebDriverWait wait = new WebDriverWait(driver, 10);
wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("dashboard")));
```

**After (Playwright, AI-enhanced)**:
```typescript
await page.locator('[data-testid="login-button"]').click();
await page.waitForSelector('[data-testid="dashboard"]');
```

**AI improvements**:
- ✅ Modern locator strategy (data-testid preferred)
- ✅ Auto-waiting (no explicit waits needed)
- ✅ Async/await syntax
- ✅ Type-safe selectors

### Step Definition Transformation

**Cucumber → Robot Framework**:

**Before (Cucumber)**:
```java
@Given("user is on login page")
public void userOnLoginPage() {
    driver.get("https://app.com/login");
}

@When("user enters {string} and {string}")
public void userEnters(String username, String password) {
    driver.findElement(By.id("username")).sendKeys(username);
    driver.findElement(By.id("password")).sendKeys(password);
}
```

**After (Robot Framework)**:
```robot
*** Keywords ***
User Is On Login Page
    Open Browser    https://app.com/login    Chrome

User Enters Username And Password
    [Arguments]    ${username}    ${password}
    Input Text    id:username    ${username}
    Input Text    id:password    ${password}
```

### Locator Modernization

**Self-Healing Locator Strategy**:
1. **data-testid** (most stable)
2. **id** (good stability)
3. **CSS class** (moderate stability)
4. **XPath** (avoid when possible)

**AI extracts locators** from page objects:
```
Extracted 243 locators from 15 page objects
Strategy applied:
  data-testid: 87 (36%)
  id: 145 (60%)
  CSS: 11 (4%)
  XPath: 0 (avoided)
```

---

## 📊 Migration Metrics

### Success Tracking

**Key metrics**:
- Tests migrated: `245 / 245 (100%)`
- Pass rate: `245 / 245 (100%)`
- Confidence: `0.94 (High)`
- Duration improvement: `2.7x faster`
- Maintenance reduction: `40% fewer LOC`

### Cost Analysis

**Before (Selenium Java)**:
- 245 tests
- ~120 minutes execution
- ~8,500 LOC
- Maintenance: 2 hours/week

**After (Playwright)**:
- 245 tests
- ~45 minutes execution
- ~5,100 LOC (40% reduction)
- Maintenance: 1.2 hours/week (40% reduction)

**ROI**: 3-month payback period

---

## 🛡️ Safety & Validation

### Transformation Validation

Every transformation includes:

**Confidence Scoring**:
```json
{
  "transformation_id": "ai-abc123",
  "confidence": 0.87,
  "signals": {
    "model_confidence": 0.92,
    "syntax_valid": true,
    "diff_size_penalty": -0.05,
    "similarity_score": 0.65
  },
  "requires_review": false
}
```

**Validation Checks**:
- ✅ Syntax validation (code parses)
- ✅ Linting rules (no violations)
- ✅ Similarity check (not too different from original)
- ✅ Test execution (runs successfully)

### Rollback Capability

**Before/After Snapshots**:
```bash
# View transformation
crossbridge ai-transform show ai-abc123 --show-diff

# Rollback if needed
crossbridge ai-transform rollback ai-abc123

# Audit trail
crossbridge ai-transform audit ai-abc123
```

### Human Review

**Low confidence transformations** (<0.8) require human approval:

```bash
# Review pending transformations
crossbridge ai-transform list --needs-review

# Approve with comments
crossbridge ai-transform approve ai-abc123 \
  --reviewer john@example.com \
  --comments "Looks good, applied to staging"
```

---

## 🎓 Migration Guides

### By Framework

- [Selenium Java → Playwright](../../migration/selenium-java-to-playwright.md)
- [Selenium Python → Playwright](../../migration/selenium-python-to-playwright.md)
- [Cucumber Java → Robot BDD](../../migration/cucumber-to-robot.md)
- [Legacy BDD → Modern BDD](../../migration/legacy-bdd-modernization.md)

### By Use Case

- [E2E UI Tests](../../migration/e2e-ui-migration.md)
- [API Tests](../../migration/api-test-migration.md)
- [BDD Scenarios](../../migration/bdd-migration.md)
- [Integration Tests](../../migration/integration-test-migration.md)

---

## 📚 Best Practices

### Do's ✅
- Start with smoke tests (low risk)
- Migrate in small batches (10-20 tests)
- Validate each batch thoroughly
- Keep original tests running during migration
- Use AI assistance with human review
- Track metrics and confidence scores

### Don'ts ❌
- Migrate entire suite at once
- Skip validation steps
- Auto-merge low-confidence transformations
- Delete original tests immediately
- Ignore linting/style guidelines
- Rush the process

---

## 🔧 Configuration

```yaml
# crossbridge.yml
migration:
  enabled: true
  
  # Source framework
  source:
    framework: selenium-java
    path: src/test/java
    
  # Target framework
  target:
    framework: playwright
    path: tests/playwright
    language: typescript
  
  # AI configuration
  ai:
    enabled: true
    provider: openai
    model: gpt-4
    confidence_threshold: 0.8  # Require review below this
  
  # Batch settings
  batch_size: 10
  parallel: false  # Migrate sequentially for safety
  
  # Validation
  validation:
    syntax_check: true
    lint_check: true
    test_execution: true
```

---

## 📊 Migration Dashboard

Track migration progress:

**Grafana Dashboard**:
- Tests migrated (cumulative)
- Pass rate comparison
- Performance improvement
- Confidence distribution
- Review queue size

---

## ❓ Common Challenges

### Challenge 1: Complex Page Objects
**Solution**: Migrate page objects first, then tests

### Challenge 2: Custom Utilities
**Solution**: Create equivalent utilities in target framework before migration

### Challenge 3: Database Dependencies
**Solution**: Abstract DB access, migrate separately

### Challenge 4: Dynamic Locators
**Solution**: Use AI to suggest stable locators

---

## 🚀 Getting Started

```bash
# 1. Analyze existing tests
crossbridge migrate analyze --framework selenium-java

# 2. Plan migration
crossbridge migrate plan --batch-size 10

# 3. Run first batch
crossbridge migrate run --batch 1

# 4. Validate
npx playwright test

# 5. Continue
crossbridge migrate run --batch 2
```

**Estimated time**: 2-4 weeks for 200-300 tests with AI assistance

---

**Ready to start migrating?** Check the [getting started guide](../../getting-started.md) or framework-specific [migration guides](migration/).
