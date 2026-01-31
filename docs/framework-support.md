# Framework Support

> **Multi-framework, multi-language test automation platform**

CrossBridge AI supports **13+ test automation frameworks** across multiple languages and testing types.

---

## 🎯 Supported Frameworks

| Framework | Language | Type | Status | Completeness |
|-----------|----------|------|--------|--------------|
| **pytest** | Python | Unit/Integration | ✅ Production | 98% |
| **Selenium Python** | Python | UI Automation | ✅ Production | 95% |
| **Selenium Java** | Java | UI Automation | ✅ Beta | 92% |
| **Cucumber/JBehave (Java BDD)** | Java | BDD | ✅ Production | 95% |
| **Selenium .NET** | C# | UI Automation | ✅ Production | 95% |
| **Cypress** | JavaScript/TS | E2E | ✅ Production | 98% |
| **Robot Framework** | Robot | Keyword-Driven | ✅ Production | 95% |
| **JUnit/TestNG** | Java | Unit/Enterprise | ✅ Production | 95% |
| **NUnit/SpecFlow** | C# / .NET | Unit/BDD | ✅ Production | 96% |
| **Playwright** | JavaScript/TS/Python | E2E | ✅ Production | 96% |
| **RestAssured** | Java | API | ✅ Production | 95% |
| **Cucumber/Behave** | Gherkin | BDD | ✅ Production | 96% |

**Average Completeness: 95%**

---

## 🔑 Key Capabilities

### Framework-Agnostic Architecture
- **Pluggable adapters** for each framework
- **Unified interface** across all frameworks
- **No framework lock-in** - use multiple frameworks simultaneously

### Two Operating Modes

#### 1. **Observer Mode** (No Code Changes)
Works with existing tests as-is:
```yaml
# crossbridge.yml
runtime:
  sidecar:
    enabled: true  # Zero-impact observability
```

#### 2. **Migration Mode** (Incremental Transformation)
Convert tests gradually:
```bash
crossbridge migrate --from selenium-java --to playwright
```

### Language Support
- **Python**: pytest, Robot Framework, Selenium, Behave
- **Java**: Selenium, TestNG, JUnit, RestAssured, Cucumber, JBehave
- **JavaScript/TypeScript**: Cypress, Playwright
- **.NET/C#**: Selenium, NUnit, SpecFlow

---

## 🧪 Framework-Specific Features

### BDD Framework Support
CrossBridge includes comprehensive BDD adapters:

**Cucumber Java**:
- Feature file parsing with Gherkin syntax
- Step definition mapping (Java annotations)
- Scenario outline expansion
- Execution report analysis (cucumber.json)
- [Full details →](bdd/BDD_IMPLEMENTATION_SUMMARY.md)

**Robot Framework BDD**:
- Keyword-driven test support
- Resource file parsing
- Test suite discovery
- Output.xml analysis
- [Full details →](bdd/BDD_IMPLEMENTATION_SUMMARY.md)

**JBehave**:
- Story file parsing
- Step mapping with Java methods
- JUnit XML report parsing
- [Full details →](bdd/BDD_IMPLEMENTATION_SUMMARY.md)

### Web Automation Features
**Selenium** (Java, Python, .NET):
- WebDriver command tracking
- Page Object Model support
- Locator extraction and analysis
- Browser log analysis

**Cypress**:
- Component testing support (React, Vue)
- Multi-config handling
- TypeScript type generation
- Custom command detection

**Playwright**:
- Multi-browser support
- Trace file analysis
- Auto-waiting intelligence
- Network request profiling

### API Testing Support
**RestAssured**:
- Request filter chain extraction
- POJO mapping (Jackson/Gson annotations)
- Fluent API chain analysis
- Response validation tracking

**Behave/SpecFlow** (API scenarios):
- Gherkin API scenario parsing
- HTTP method detection
- Response assertion analysis

---

## 🚀 How Framework Detection Works

CrossBridge automatically detects your framework:

```python
from core.repo.discovery import discover_tests

# Auto-detects framework from file patterns
results = discover_tests(path="./tests")
print(f"Detected framework: {results.framework}")
```

**Detection signals**:
- File extensions (`.py`, `.java`, `.feature`, `.robot`)
- Import statements (`import pytest`, `import org.junit`)
- Configuration files (`pytest.ini`, `pom.xml`, `cypress.config.js`)
- Directory structure patterns

---

## 📊 Framework Adapter API

All framework adapters implement a unified interface:

```python
class FrameworkAdapter(ABC):
    @abstractmethod
    def discover_tests(self, path: Path) -> List[TestEntity]:
        """Discover tests in directory"""
        
    @abstractmethod
    def parse_results(self, results_path: Path) -> List[TestResult]:
        """Parse execution results"""
        
    @abstractmethod
    def extract_metadata(self, test_file: Path) -> TestMetadata:
        """Extract test metadata (tags, priority, etc.)"""
```

**Available adapters**: See [adapters/](../adapters/) directory

---

## 🔌 Adding Custom Framework Support

1. **Implement adapter interface**:
   ```python
   from adapters.common.base import FrameworkAdapter
   
   class MyFrameworkAdapter(FrameworkAdapter):
       def discover_tests(self, path):
           # Implementation
   ```

2. **Register adapter**:
   ```python
   from core.repo.registry import register_adapter
   register_adapter("my-framework", MyFrameworkAdapter)
   ```

3. **Configure in crossbridge.yml**:
   ```yaml
   frameworks:
     my-framework:
       enabled: true
   ```

**Full guide**: [Custom Framework Adapters](frameworks/CUSTOM_ADAPTERS.md)

---

## 📈 Framework Roadmap

### ✅ Available Now
- All 13 frameworks listed above
- Observer mode for all frameworks
- Migration support (Selenium → Playwright)

### 🚧 In Progress
- Karate framework support
- Postman collection support
- Enhanced .NET support (xUnit, MSTest)

### 📋 Planned
- K6 performance testing
- JMeter support
- Appium mobile testing
- WebdriverIO support

---

## 📚 Framework-Specific Guides

- [Selenium Guide](../selenium-java/README.md)
- [Pytest Integration](../quick-start/pytest-quickstart.md)
- [Cypress Setup](../quick-start/cypress-quickstart.md)
- [Robot Framework](../quick-start/robot-quickstart.md)
- [BDD Frameworks](../bdd/README.md)

---

## 🆚 Framework Comparison Matrix

| Feature | Selenium | Cypress | Playwright | Pytest | Robot |
|---------|----------|---------|------------|--------|-------|
| **UI Automation** | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| **API Testing** | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| **BDD Support** | ✅ | ⚠️ | ⚠️ | ✅ | ✅ |
| **Multi-Browser** | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| **Parallel Execution** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **CrossBridge Support** | ✅ | ✅ | ✅ | ✅ | ✅ |

---

**Need help choosing a framework?** Check the [framework migration guide](framework-migration.md) for recommendations.
