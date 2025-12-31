# Playwright Multi-Language Adapter

**Status**: ✅ **PRODUCTION READY**

Unified adapter for Playwright tests across all officially supported language bindings.

---

## Supported Language Bindings

| Language | Framework | Test Pattern | Status |
|----------|-----------|--------------|--------|
| **JavaScript** | @playwright/test | `*.spec.js`, `*.test.js` | ✅ Full |
| **TypeScript** | @playwright/test | `*.spec.ts`, `*.test.ts` | ✅ Full |
| **Python** | pytest-playwright | `test_*.py`, `*_test.py` | ✅ Full |
| **Java** | JUnit 4/5 + playwright-java | `*Test.java` | ✅ Full |
| **Java** | TestNG + playwright-java | `*Test.java` | ✅ Full |
| **.NET** | NUnit + Microsoft.Playwright | `*Test.cs`, `*Tests.cs` | ✅ Full |
| **.NET** | MSTest + Microsoft.Playwright | `*Test.cs`, `*Tests.cs` | ✅ Full |
| **.NET** | xUnit + Microsoft.Playwright | `*Test.cs`, `*Tests.cs` | ✅ Full |

---

## Features

### 🎯 Auto-Detection
- Automatically detects project language and framework
- No manual configuration required
- Works with standard project structures

### 🔍 Test Discovery
- Language-specific test discovery
- Supports all test patterns and conventions
- Fast and reliable

### ▶️ Test Execution
- Native execution using framework tools
- Result parsing and normalization
- Timeout handling

### 📊 Metadata Extraction
- Static analysis without execution
- Extract test names, locations, tags
- Framework-agnostic representation

---

## Installation

No additional dependencies required beyond Playwright itself for each language.

### JavaScript/TypeScript
```bash
npm install -D @playwright/test
npx playwright install
```

### Python
```bash
pip install pytest-playwright
playwright install
```

### Java (Maven)
```xml
<dependency>
    <groupId>com.microsoft.playwright</groupId>
    <artifactId>playwright</artifactId>
    <version>1.40.0</version>
</dependency>
```

### .NET
```bash
dotnet add package Microsoft.Playwright
dotnet add package Microsoft.Playwright.NUnit
pwsh bin/Debug/net6.0/playwright.ps1 install
```

---

## Usage

### Basic Usage (Auto-detection)

```python
from adapters.playwright import PlaywrightAdapter

# Auto-detect project configuration
adapter = PlaywrightAdapter("/path/to/playwright/project")

# Discover tests
tests = adapter.discover_tests()
print(f"Found {len(tests)} tests")

# Run all tests
results = adapter.run_tests()

# Run specific tests
results = adapter.run_tests(tests=["login test", "checkout test"])

# Run with tag filtering
results = adapter.run_tests(tags=["smoke"])
```

### Check Configuration

```python
# Get detected configuration
config_info = adapter.get_config_info()
print(f"Language: {config_info['language']}")
print(f"Framework: {config_info['framework']}")
print(f"Test Directory: {config_info['test_dir']}")
print(f"Config File: {config_info['config_file']}")
```

### Manual Configuration

```python
from adapters.playwright import (
    PlaywrightAdapter,
    PlaywrightProjectConfig,
    PlaywrightLanguage,
    PlaywrightTestFramework
)
from pathlib import Path

# Create manual configuration
config = PlaywrightProjectConfig(
    language=PlaywrightLanguage.TYPESCRIPT,
    framework=PlaywrightTestFramework.PLAYWRIGHT_TEST,
    test_dir=Path("/path/to/tests"),
    config_file=Path("/path/to/playwright.config.ts"),
    project_root=Path("/path/to/project")
)

adapter = PlaywrightAdapter("/path/to/project", config=config)
```

### Metadata Extraction (Read-only)

```python
from adapters.playwright import PlaywrightExtractor

# Extract test metadata without execution
extractor = PlaywrightExtractor("/path/to/project")
tests = extractor.extract_tests()

for test in tests:
    print(f"Test: {test.name}")
    print(f"  File: {test.file_path}:{test.line_number}")
    print(f"  Framework: {test.framework}")
```

---

## Project Detection

The adapter auto-detects projects based on these indicators:

### JavaScript/TypeScript
- `package.json` with `@playwright/test` dependency
- `playwright.config.js` or `playwright.config.ts`
- Test files: `*.spec.{js,ts}` or `*.test.{js,ts}`

### Python
- `pytest.ini`, `pyproject.toml`, or `requirements.txt`
- `pytest-playwright` or `playwright` in pip list
- Test files: `test_*.py` or `*_test.py` with playwright imports

### Java
- `pom.xml` with `com.microsoft.playwright` dependency (Maven)
- `build.gradle` with playwright dependency (Gradle)
- Test files: `*Test.java` in `src/test/java/`

### .NET
- `*.csproj` with `Microsoft.Playwright` package
- NUnit/MSTest/xUnit test framework
- Test files: `*Test.cs` or `*Tests.cs`

---

## Architecture

```
PlaywrightAdapter (Unified API)
    ├── PlaywrightProjectDetector (Auto-detection)
    ├── PlaywrightTestExecutor (@playwright/test - JS/TS)
    ├── PytestPlaywrightExecutor (pytest-playwright - Python)
    ├── JavaPlaywrightExecutor (JUnit/TestNG - Java)
    └── DotNetPlaywrightExecutor (NUnit/MSTest/xUnit - .NET)
```

### Key Classes

**PlaywrightAdapter**: Main unified interface
- Auto-detects project configuration
- Routes to language-specific executor
- Provides unified discovery and execution

**PlaywrightProjectDetector**: Auto-detection engine
- Scans project for language indicators
- Detects test framework
- Identifies test directories and config files

**Language-Specific Executors**: Implementation for each binding
- Native command execution
- Result parsing
- Error handling

**PlaywrightExtractor**: Read-only metadata extraction
- Static analysis of test files
- Pattern matching for test definitions
- Framework-agnostic representation

---

## Test Result Format

All executors return results in unified format:

```python
@dataclass
class TestResult:
    name: str          # Test name/identifier
    status: str        # "pass" | "fail" | "skip"
    duration_ms: int   # Execution time in milliseconds
    message: str       # Error message if failed
```

---

## Examples by Language

### JavaScript Example

```javascript
// tests/login.spec.js
import { test, expect } from '@playwright/test';

test('user can login', async ({ page }) => {
  await page.goto('https://example.com');
  await page.fill('#username', 'testuser');
  await page.fill('#password', 'password');
  await page.click('#login');
  await expect(page).toHaveURL('/dashboard');
});
```

**Usage**:
```python
adapter = PlaywrightAdapter("/path/to/project")
tests = adapter.discover_tests()  # ['user can login']
results = adapter.run_tests()
```

### Python Example

```python
# tests/test_login.py
import pytest
from playwright.sync_api import Page

def test_user_can_login(page: Page):
    page.goto("https://example.com")
    page.fill("#username", "testuser")
    page.fill("#password", "password")
    page.click("#login")
    assert page.url == "https://example.com/dashboard"
```

**Usage**:
```python
adapter = PlaywrightAdapter("/path/to/project")
tests = adapter.discover_tests()  # ['test_user_can_login']
results = adapter.run_tests()
```

### Java Example

```java
// src/test/java/LoginTest.java
import com.microsoft.playwright.*;
import org.junit.jupiter.api.*;

public class LoginTest {
    private Browser browser;
    private Page page;
    
    @BeforeEach
    void setUp() {
        browser = Playwright.create().chromium().launch();
        page = browser.newPage();
    }
    
    @Test
    void userCanLogin() {
        page.navigate("https://example.com");
        page.fill("#username", "testuser");
        page.fill("#password", "password");
        page.click("#login");
        assertEquals("https://example.com/dashboard", page.url());
    }
    
    @AfterEach
    void tearDown() {
        browser.close();
    }
}
```

**Usage**:
```python
adapter = PlaywrightAdapter("/path/to/project")
tests = adapter.discover_tests()  # ['LoginTest']
results = adapter.run_tests()
```

### .NET Example

```csharp
// Tests/LoginTests.cs
using Microsoft.Playwright;
using Microsoft.Playwright.NUnit;
using NUnit.Framework;

[TestFixture]
public class LoginTests : PageTest
{
    [Test]
    public async Task UserCanLogin()
    {
        await Page.GotoAsync("https://example.com");
        await Page.FillAsync("#username", "testuser");
        await Page.FillAsync("#password", "password");
        await Page.ClickAsync("#login");
        Assert.AreEqual("https://example.com/dashboard", Page.Url);
    }
}
```

**Usage**:
```python
adapter = PlaywrightAdapter("/path/to/project")
tests = adapter.discover_tests()  # ['UserCanLogin']
results = adapter.run_tests()
```

---

## CLI Integration

The Playwright adapter integrates with CrossBridge CLI:

```bash
# Discover tests
crossbridge discover --framework playwright --project ./tests

# Run tests
crossbridge run --framework playwright --project ./tests

# Run with filtering
crossbridge run --framework playwright --project ./tests --tests "login,checkout"

# Get framework info
crossbridge info --framework playwright --project ./tests
```

---

## Error Handling

The adapter handles common errors gracefully:

- **Framework not installed**: Clear error message with installation instructions
- **No tests found**: Returns empty list with warning
- **Invalid project structure**: Detection fails with descriptive message
- **Execution timeout**: Configurable timeout with fallback
- **Parse errors**: Fallback to overall pass/fail status

---

## Testing

See `tests/unit/test_playwright_adapter.py` for comprehensive unit tests covering:
- Auto-detection for all languages
- Test discovery
- Test execution
- Result parsing
- Error scenarios
- Edge cases

---

## Limitations

1. **Java/Maven**: Full execution requires Maven/Gradle installed
2. **.NET**: Requires .NET SDK installed
3. **Result Parsing**: Some executors use simplified parsing (overall pass/fail)
4. **Tag Support**: Implementation varies by framework

---

## Future Enhancements

- [ ] Parallel execution support
- [ ] Enhanced result parsing (per-test metrics)
- [ ] Coverage collection integration
- [ ] Visual regression detection
- [ ] Cross-browser execution
- [ ] CI/CD pipeline templates

---

## Contributing

To add support for a new framework or improve existing support:

1. Add detection logic to `PlaywrightProjectDetector`
2. Create executor class (e.g., `NewFrameworkExecutor`)
3. Implement `discover_tests()` and `run_tests()`
4. Add tests to `tests/unit/test_playwright_adapter.py`
5. Update this README

---

## License

Same as CrossBridge main project.
