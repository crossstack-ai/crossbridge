# Coverage Intelligence - Quick Reference

## 🎯 What CrossBridge Coverage Does

CrossBridge is a **Coverage Intelligence Platform**, not a traditional "coverage %" tool.

### It Answers:
- ✅ What code/features are exercised
- ✅ What changes are risky  
- ✅ What tests matter
- ✅ Where gaps exist
- ✅ Which APIs are called
- ✅ Which UI components are used

### It Does NOT:
- ❌ Give fake "63% coverage" numbers for SaaS apps
- ❌ Pretend to know backend coverage without instrumentation
- ❌ Make up percentages

---

## 📊 Three Coverage Layers

### 1️⃣ **Test → Code** (Instrumented)
**What:** Which code is executed by tests  
**When:** You own/control the backend  
**Tools:** JaCoCo (Java), coverage.py (Python), Istanbul (JS)

### 2️⃣ **UI → Backend** (Behavioral)
**What:** Which features/APIs/UI are exercised  
**When:** Testing SaaS/vendor apps (no backend access)  
**Tools:** API endpoint tracking, UI component tracking, network capture

### 3️⃣ **Change → Impact** (Analysis)
**What:** Which tests are affected by code changes  
**When:** Planning test execution after code changes  
**Tools:** Impact analysis, change event tracking

---

## 🔧 Coverage Types

### Instrumented Coverage (Backend Access Required)

| Type | Tool | When to Use |
|------|------|-------------|
| **Java** | JaCoCo | Java backend (Spring, Selenium) |
| **Python** | coverage.py | Python backend (Flask, Django, pytest) |
| **JavaScript** | Istanbul/NYC | JS backend (Node.js, Jest) |
| **BDD** | Cucumber | Step → Code mapping |

**Usage:**
```python
# Java
from core.coverage.jacoco_parser import JaCoCoXMLParser

# Python
from core.coverage.coverage_py_parser import CoveragePyParser

# JavaScript
from core.coverage.istanbul_parser import IstanbulParser
```

---

### Behavioral Coverage (SaaS-Friendly)

| Type | What It Tracks | When to Use |
|------|----------------|-------------|
| **API Endpoint** | HTTP endpoints called | SaaS apps, cloud consoles |
| **UI Component** | UI elements interacted with | UI testing (Selenium, Playwright) |
| **Network** | Raw HTTP traffic | Detailed API analysis |
| **Contract** | API schema fields | API contract testing |

**Usage:**
```python
from core.coverage.behavioral_collectors import (
    ApiEndpointCollector,
    UiComponentCollector,
    NetworkCaptureCollector,
    ContractCoverageCollector
)

# During test execution
api_collector = ApiEndpointCollector()
api_collector.record_api_call(
    test_case_id=test_id,
    endpoint_path="/api/users",
    http_method="GET",
    status_code=200
)
```

---

## 📝 Quick Examples

### Example 1: Java Coverage (Instrumented)
```python
from core.coverage.jacoco_parser import JaCoCoXMLParser

parser = JaCoCoXMLParser()
mapping = parser.parse(
    xml_path="target/site/jacoco/jacoco.xml",
    test_name="test_login"
)

# Stores: test_login → LoginService.authenticate()
```

### Example 2: Python Coverage (Instrumented)
```python
from core.coverage.coverage_py_parser import extract_coverage_from_pytest

mapping = extract_coverage_from_pytest(
    working_dir=Path("."),
    test_name="test_user_creation"
)

# Stores: test_user_creation → user_service.create_user()
```

### Example 3: SaaS API Testing (Behavioral)
```python
from core.coverage.behavioral_collectors import ApiEndpointCollector

collector = ApiEndpointCollector()

# During test
collector.record_api_call(
    test_case_id=test_id,
    endpoint_path="/api/v1/users/123",
    http_method="GET",
    status_code=200,
    execution_time_ms=45.2
)

# Get summary
summary = collector.get_coverage_summary()
# {
#   'total_endpoints': 1,
#   'unique_paths': 1,
#   'http_methods': ['GET'],
#   'status_codes': [200]
# }
```

### Example 4: UI Component Testing (Behavioral)
```python
from core.coverage.behavioral_collectors import UiComponentCollector

collector = UiComponentCollector()

# During Selenium test
collector.record_interaction(
    test_case_id=test_id,
    component_name="login_button",
    component_type="button",
    interaction_type="click",
    selector="#login-btn",
    page_url="https://app.example.com/login"
)

summary = collector.get_coverage_summary()
```

---

## 🗄️ Database Tables

### Core Tables (Already Existed)
- `test_case` - Test definitions
- `feature` - Product features
- `code_unit` - Code classes/methods
- `test_feature_map` - Test ↔ Feature links
- `test_code_coverage_map` - Test ↔ Code coverage

### NEW Behavioral Tables
- `api_endpoint_coverage` - API calls during tests
- `ui_component_coverage` - UI interactions during tests
- `network_capture` - Raw HTTP traffic
- `contract_coverage` - API schema coverage

---

## 📊 Key Views

### Core Views (Already Existed)
- `functional_coverage_map` - Code units with test coverage
- `test_to_feature_coverage` - Test-to-feature relationships
- `change_impact_surface` - Change impact analysis
- `coverage_gaps` - Features without tests

### NEW Behavioral Views
- `api_endpoint_summary` - API endpoint coverage summary
- `ui_component_summary` - UI component coverage summary
- `functional_surface_coverage` - **UNIFIED** all coverage types

---

## 🎯 Decision Tree: Which Coverage to Use?

### Do you control the backend?
**YES** → Use **Instrumented Coverage** (JaCoCo, coverage.py, Istanbul)  
**NO** → Use **Behavioral Coverage** (API, UI, Network)

### Are you testing a SaaS/vendor app?
**YES** → Use **Behavioral Coverage**  
**NO** → Use **Instrumented Coverage**

### Do you need contract validation?
**YES** → Use **Contract Coverage**  
**NO** → Use API Endpoint or UI Component Coverage

### Do you need change impact analysis?
**YES** → Use **Change Impact Surface**  
**NO** → Use functional coverage only

---

## 📈 Reports You Get

### For Instrumented Coverage:
```
Functional Coverage Map
- LoginService.authenticate() → 3 tests
- UserController.getUser() → 2 tests
- OrderRepository.save() → 1 test
```

### For Behavioral Coverage (SaaS):
```
API Endpoint Coverage
- GET /api/users → 5 tests
- POST /api/orders → 3 tests
- PUT /api/users/{id} → 2 tests

UI Component Coverage
- Login button → 4 tests
- Search input → 3 tests
- Profile dropdown → 2 tests
```

### For Change Impact:
```
Change Impact Surface
File: user_service.py
Impacted Tests:
- test_user_creation
- test_user_update
- test_login_flow
```

---

## 🚀 Getting Started

### 1. For Java Projects:
```bash
# Enable JaCoCo in Maven/Gradle
# Run tests with coverage
mvn test jacoco:report

# CrossBridge parses jacoco.xml
crossbridge coverage map --project ./
```

### 2. For Python Projects:
```bash
# Install coverage.py
pip install coverage

# Run tests with coverage
coverage run -m pytest
coverage json

# CrossBridge parses coverage.json
crossbridge coverage map --project ./
```

### 3. For SaaS Testing:
```python
# In your test framework
from core.coverage.behavioral_collectors import ApiEndpointCollector

# Hook into HTTP requests
api_collector = ApiEndpointCollector()
# ... record API calls during tests

# Save to database
repository.save_api_coverage(api_collector.get_covered_endpoints())
```

---

## 📚 File Reference

| File | Purpose |
|------|---------|
| `functional_models.py` | Data models (extended with behavioral) |
| `jacoco_parser.py` | Java coverage parser |
| `coverage_py_parser.py` | **NEW** Python coverage parser |
| `istanbul_parser.py` | **NEW** JavaScript coverage parser |
| `behavioral_collectors.py` | **NEW** API/UI/Network collectors |
| `functional_coverage_schema.sql` | Database schema (extended) |
| `engine.py` | Coverage orchestration |
| `repository.py` | Database operations |

---

## 🎓 Key Concepts

### Coverage ≠ Percentage
CrossBridge stores **relationships**, not percentages:
- `test_login` → `LoginService.authenticate()`
- `test_checkout` → `POST /api/orders`
- `test_profile` → `#profile-button`

### Instrumented vs Behavioral
- **Instrumented:** Requires code access (backend)
- **Behavioral:** Works without code access (SaaS)

### Honest Reporting
❌ "63% backend code coverage" (when you can't instrument)  
✅ "85% of critical UI flows covered"  
✅ "12 API endpoints exercised"  
✅ "Login, checkout, profile tested"

---

## 💡 Pro Tips

1. **For internal apps:** Use instrumented coverage (JaCoCo, coverage.py)
2. **For vendor SaaS:** Use behavioral coverage (API, UI tracking)
3. **For hybrid systems:** Use both (instrumented backend + behavioral frontend)
4. **For change impact:** Always enable change tracking
5. **For CI/CD:** Integrate coverage collection into pipeline

---

## 📞 Support

See full documentation:
- `COVERAGE_INTELLIGENCE_IMPLEMENTATION.md` - Complete implementation details
- `FUNCTIONAL_COVERAGE_IMPLEMENTATION.md` - Functional coverage guide
- `FUNCTIONAL_COVERAGE_QUICKSTART.md` - Quick start guide
