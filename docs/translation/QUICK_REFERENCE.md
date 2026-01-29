# Framework Translation Quick Reference

## Quick Start

```bash
# Translate a single file
crossbridge translate -s selenium-java -t playwright-python -i LoginTest.java -o test_login.py

# Translate a directory
crossbridge translate -s selenium-java -t playwright-python -i src/test/java -o tests/

# With AI refinement (Enterprise)
crossbridge translate -s selenium-java -t playwright-python -i tests/ -o new-tests/ --use-ai
```

## Common Commands

### Single File

```bash
crossbridge translate \
  --source selenium-java \
  --target playwright-python \
  --input tests/LoginTest.java \
  --output tests/test_login.py
```

### Directory (Batch)

```bash
crossbridge translate \
  --source selenium-java \
  --target playwright-python \
  --input src/test/java \
  --output tests/ \
  --mode batch
```

### Dry Run (Preview Only)

```bash
crossbridge translate \
  --source selenium-java \
  --target playwright-python \
  --input LoginTest.java \
  --output test_login.py \
  --dry-run \
  --verbose
```

## Programmatic API

### Basic Translation

```python
from core.translation.pipeline import TranslationPipeline

pipeline = TranslationPipeline()
result = pipeline.translate(
    source_code=selenium_code,
    source_framework="selenium-java",
    target_framework="playwright-python",
)

if result.success:
    print(result.target_code)
```

### With Configuration

```python
from core.translation.pipeline import (
    TranslationPipeline,
    TranslationConfig,
    TranslationMode,
    ValidationLevel,
)

config = TranslationConfig(
    source_framework="selenium-java",
    target_framework="playwright-python",
    mode=TranslationMode.AUTOMATED,
    use_ai=True,
    max_credits=100,
    confidence_threshold=0.7,
    validation_level=ValidationLevel.STRICT,
)

pipeline = TranslationPipeline()
result = pipeline.translate(source_code, "selenium-java", "playwright-python")
```

### Check Results

```python
if result.success:
    print(f"✅ Confidence: {result.confidence:.1%}")
    print(f"📊 Actions: {result.statistics['actions']}")
    print(f"✓ Assertions: {result.statistics['assertions']}")
    
    if result.warnings:
        print("⚠️ Warnings:")
        for warning in result.warnings:
            print(f"  • {warning}")
    
    if result.todos:
        print("📝 TODOs:")
        for todo in result.todos:
            print(f"  • {todo}")
else:
    print("❌ Errors:")
    for error in result.errors:
        print(f"  • {error}")
```

## Supported Paths

| Source | Target | Status |
|--------|--------|--------|
| selenium-java | playwright-python | ✅ Release Stage |
| selenium-python | playwright-python | 🔄 Planned |
| restassured | pytest | 🔄 Planned |
| robot | pytest | 🔄 Planned |

## Translation Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `assistive` | Preview each, require confirmation | Learning, initial migration |
| `automated` | Auto-apply high confidence only | Production use |
| `batch` | Translate all, generate report | Large codebases |

## Validation Levels

| Level | Behavior | Use Case |
|-------|----------|----------|
| `strict` | Fail on any errors | Production (default) |
| `lenient` | Warn but continue | Exploration |
| `skip` | No validation | Speed over safety |

## Confidence Scores

| Score | Meaning | Action |
|-------|---------|--------|
| 0.9-1.0 | Very high confidence | Direct mapping |
| 0.7-0.9 | Good translation | Minor review |
| 0.5-0.7 | Uncertain | Review required |
| 0.0-0.5 | Low confidence | Manual work needed |

## Common Patterns

### Selenium → Playwright

| Selenium | Playwright |
|----------|-----------|
| `driver.get(url)` | `page.goto(url)` |
| `element.click()` | `locator.click()` |
| `element.sendKeys(text)` | `locator.fill(text)` |
| `element.getText()` | `locator.text_content()` |
| `element.isDisplayed()` | `locator.is_visible()` |
| `WebDriverWait(...)` | *removed (auto-wait)* |
| `Thread.sleep(...)` | *removed* |
| `By.id("btn")` | `page.get_by_role("button")` |

## Idiom Transformations

| Idiom | Description | Result |
|-------|-------------|--------|
| `explicit_wait_removal` | Remove WebDriverWait | Playwright auto-waits |
| `sleep_removal` | Remove Thread.sleep | Not needed |
| `prefer_role_based_selectors` | Use accessibility selectors | Better maintainability |
| `given_when_then_to_aaa` | BDD to AAA pattern | Pytest convention |

## File Naming

| Source | Target |
|--------|--------|
| `LoginTest.java` | `test_login.py` |
| `UserManagementTest.java` | `test_user_management.py` |
| `ApiTest.java` | `test_api.py` |

## Error Handling

### Translation Failed

```python
result = pipeline.translate(...)
if not result.success:
    for error in result.errors:
        print(f"Error: {error}")
```

### Low Confidence

```python
if result.confidence < 0.7:
    print("⚠️ Low confidence - manual review needed")
    for todo in result.todos:
        print(f"TODO: {todo}")
```

## CLI Options Reference

| Option | Short | Values | Default | Description |
|--------|-------|--------|---------|-------------|
| `--source` | `-s` | framework | required | Source framework |
| `--target` | `-t` | framework | required | Target framework |
| `--input` | `-i` | path | required | Input file/dir |
| `--output` | `-o` | path | required | Output file/dir |
| `--mode` | `-m` | assistive\|automated\|batch | assistive | Translation mode |
| `--use-ai` | | flag | false | Use AI refinement |
| `--max-credits` | | number | 100 | Max AI credits |
| `--confidence-threshold` | | 0.0-1.0 | 0.7 | Min confidence |
| `--validation` | | strict\|lenient\|skip | strict | Validation level |
| `--dry-run` | | flag | false | Preview only |
| `--verbose` | `-v` | flag | false | Verbose output |

## Extension API

### Custom Parser

```python
from core.translation.pipeline import SourceParser
from core.translation.intent_model import TestIntent, ActionIntent, ActionType

class MyParser(SourceParser):
    def __init__(self):
        super().__init__(framework="my-framework")
    
    def can_parse(self, source_code: str) -> bool:
        return "my_marker" in source_code
    
    def parse(self, source_code: str, source_file: str = "") -> TestIntent:
        intent = TestIntent(...)
        # Parse and add actions
        intent.add_step(ActionIntent(action_type=ActionType.CLICK, ...))
        return intent
```

### Custom Generator

```python
from core.translation.pipeline import TargetGenerator
from core.translation.intent_model import TestIntent, IntentType

class MyGenerator(TargetGenerator):
    def __init__(self):
        super().__init__(framework="my-framework")
    
    def can_generate(self, intent: TestIntent) -> bool:
        return intent.test_type == IntentType.UI
    
    def generate(self, intent: TestIntent) -> str:
        # Generate code from intent
        code = "def test_...():\n"
        for step in intent.steps:
            code += f"    # {step.description}\n"
        return code
```

### Custom Idiom

```python
from core.translation.registry import IdiomPattern, idiom_registry

idiom_registry.add_idiom(IdiomPattern(
    name="my_idiom",
    description="Transform X to Y",
    source_pattern="old_pattern",
    target_pattern="new_pattern",
    applies_to=["source-framework"],
))
```

## Troubleshooting

### Issue: Translation fails

**Check:**
- Is source framework correct?
- Is input file valid?
- Run with `--verbose` for details

### Issue: Low confidence

**Solutions:**
- Use `--use-ai` (Enterprise)
- Review source tests
- Add custom idioms

### Issue: Generated code doesn't run

**Solutions:**
- Check `--validation strict`
- Review TODO comments
- Verify framework versions

### Issue: Wrong selectors

**Solutions:**
- Add data-testid attributes
- Use role-based selectors
- Custom selector mapping

## Best Practices

1. **Start small** - Translate one file first
2. **Use dry-run** - Preview before writing
3. **Review TODOs** - Check all TODO comments
4. **Run tests** - Verify generated code
5. **Version control** - Commit before translation
6. **Incremental** - Don't translate everything at once

## Examples Directory

```
examples/translation/
├── quick_demo.py                    # Simple demo
├── selenium_to_playwright_example.py # Complete example
└── custom_parser_example.py          # Extension example
```

## Documentation Links

- **Full Guide**: [docs/translation/README.md](README.md)
- **Implementation**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **API Docs**: Auto-generated from code
- **Contributing**: [CONTRIBUTING.md](../../CONTRIBUTING.md)

## Support

- 📖 **Docs**: https://crossbridge.dev/docs/translation
- 💬 **Discord**: https://discord.gg/crossbridge
- 🐛 **Issues**: https://github.com/crossbridge/crossbridge/issues
- 📧 **Email**: support@crossbridge.dev
