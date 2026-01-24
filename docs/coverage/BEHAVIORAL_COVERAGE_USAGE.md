# Behavioral Coverage Implementation - Usage Guide

## Overview
CrossBridge now supports **behavioral coverage** for SaaS applications where backend instrumentation is not available. This enables coverage tracking through observable behaviors: API calls, UI interactions, network traffic, and contract validation.

## Quick Start

### 1. Database Setup

Apply the schema to your PostgreSQL database:

```bash
python scripts/apply_coverage_schema_only.py
```

This creates 13 tables and 6 views for behavioral coverage tracking.

### 2. Collect API Endpoint Coverage

```python
from core.coverage.behavioral_collectors import ApiEndpointCollector
import uuid

# Initialize collector
collector = ApiEndpointCollector()

# Record API calls during test execution
test_id = uuid.uuid4()  # Your test case ID

coverage = collector.record_api_call(
    test_case_id=test_id,
    endpoint_path="/api/v1/users/12345",
    http_method="GET",
    status_code=200,
    request_body='{"filter": "active"}',
    response_body='{"id": 12345, "name": "John"}'
)

# Path is automatically normalized: /api/v1/users/{id}
print(f"Normalized: {coverage.endpoint_path}")

# Get summary
summary = collector.get_coverage_summary()
print(f"Covered {summary['unique_paths']} unique endpoints")
```

### 3. Collect UI Component Coverage

```python
from core.coverage.behavioral_collectors import UiComponentCollector

collector = UiComponentCollector()

# Record UI interactions
coverage = collector.record_interaction(
    test_case_id=test_id,
    component_name="login_button",
    component_type="button",
    interaction_type="click",
    selector="#submit-btn",
    page_url="https://app.example.com/login"
)

# Get summary
summary = collector.get_coverage_summary()
print(f"Interacted with {summary['unique_components']} components")
```

### 4. Collect Network Traffic

```python
from core.coverage.behavioral_collectors import NetworkCaptureCollector

collector = NetworkCaptureCollector()

# Record network requests
capture = collector.record_request(
    test_case_id=test_id,
    request_url="https://api.example.com/users",
    request_method="GET",
    response_status=200,
    duration_ms=125.5
)

# Convert to API coverage
api_coverage = collector.to_api_endpoint_coverage(test_id)
print(f"Captured {len(api_coverage)} unique API endpoints")
```

### 5. Track Contract Coverage

```python
from core.coverage.behavioral_collectors import ContractCoverageCollector

collector = ContractCoverageCollector()

# Record contract usage
coverage = collector.record_contract_usage(
    test_case_id=test_id,
    contract_name="UserAPI.getUser",
    contract_version="v1",
    request_fields={"userId", "includeInactive"},
    response_fields={"id", "name", "email", "status"}
)

# Report validation failure
collector.record_contract_usage(
    test_case_id=test_id,
    contract_name="OrderAPI.createOrder",
    contract_version="v2",
    request_fields={"customerId", "items"},
    response_fields={"orderId"},
    validation_passed=False,
    validation_errors=["Missing required field: paymentMethod"]
)
```

## Integration with Test Frameworks

### Pytest Integration

```python
import pytest
from core.coverage.behavioral_collectors import ApiEndpointCollector

@pytest.fixture
def api_collector():
    """API coverage collector fixture."""
    return ApiEndpointCollector()

def test_user_login(api_collector, db_session):
    test_id = get_test_id()  # Your test ID resolver
    
    # Test code...
    response = requests.post("/api/auth/login", json={"username": "test"})
    
    # Record coverage
    api_collector.record_api_call(
        test_case_id=test_id,
        endpoint_path="/api/auth/login",
        http_method="POST",
        status_code=response.status_code
    )
    
    # Store in database
    save_coverage_to_db(api_collector, db_session)
```

### Selenium Integration

```python
from selenium import webdriver
from core.coverage.behavioral_collectors import UiComponentCollector

class CoverageTrackingTest:
    def setup_method(self):
        self.driver = webdriver.Chrome()
        self.ui_collector = UiComponentCollector()
        self.test_id = uuid.uuid4()
    
    def test_login_flow(self):
        # Navigate and interact
        self.driver.get("https://app.example.com/login")
        
        username_field = self.driver.find_element(By.ID, "username")
        username_field.send_keys("test@example.com")
        
        # Record coverage
        self.ui_collector.record_interaction(
            test_case_id=self.test_id,
            component_name="username_input",
            component_type="input",
            interaction_type="type",
            selector="#username",
            page_url=self.driver.current_url
        )
        
        # Continue test...
```

## Database Queries

### Query API Coverage

```sql
-- Get all endpoints tested
SELECT endpoint_path, http_method, COUNT(DISTINCT test_case_id) as test_count
FROM api_endpoint_coverage
GROUP BY endpoint_path, http_method
ORDER BY test_count DESC;

-- Get endpoints by test
SELECT tc.method_name, aec.endpoint_path, aec.http_method, aec.status_code
FROM api_endpoint_coverage aec
JOIN test_case tc ON aec.test_case_id = tc.id
WHERE tc.framework = 'pytest';
```

### Query UI Coverage

```sql
-- Get most interacted components
SELECT component_name, component_type, SUM(interaction_count) as total_interactions
FROM ui_component_coverage
GROUP BY component_name, component_type
ORDER BY total_interactions DESC;

-- Get components by page
SELECT page_url, COUNT(DISTINCT component_name) as component_count
FROM ui_component_coverage
WHERE page_url IS NOT NULL
GROUP BY page_url;
```

### Use Views

```sql
-- API Endpoint Summary
SELECT * FROM api_endpoint_summary
ORDER BY test_count DESC
LIMIT 10;

-- UI Component Summary  
SELECT * FROM ui_component_summary
ORDER BY total_interactions DESC;

-- Functional Surface Coverage (Unified View)
SELECT * FROM functional_surface_coverage
WHERE coverage_type = 'api';
```

## Testing

### Unit Tests
```bash
# Run coverage parser tests
pytest tests/core/coverage/test_coverage_py_parser.py -v
pytest tests/core/coverage/test_istanbul_parser.py -v
pytest tests/core/coverage/test_behavioral_collectors.py -v
```

### Integration Tests
```bash
# Run database integration tests
pytest tests/integration/test_coverage_integration.py -v
```

## Architecture

### Components

1. **Parsers**
   - `coverage_py_parser.py` - Parse coverage.py JSON reports
   - `istanbul_parser.py` - Parse Istanbul/NYC coverage reports

2. **Behavioral Collectors**
   - `ApiEndpointCollector` - Track API endpoint coverage
   - `UiComponentCollector` - Track UI component interactions
   - `NetworkCaptureCollector` - Capture raw network traffic
   - `ContractCoverageCollector` - Track API contract coverage

3. **Database Schema**
   - 13 tables for coverage storage
   - 6 views for reporting and analysis
   - Full support for PostgreSQL

### Data Flow

```
Test Execution
     │
     ├─> API Calls ──────> ApiEndpointCollector ─┐
     ├─> UI Interactions ─> UiComponentCollector ─┤
     ├─> Network Traffic ─> NetworkCaptureCollector
     └─> Contract Checks ─> ContractCoverageCollector
                                                   │
                                                   ▼
                                            PostgreSQL DB
                                                   │
                                                   ▼
                                         Views & Reports
```

## Best Practices

1. **Endpoint Normalization**: IDs are automatically replaced with `{id}` placeholders
   - `/api/users/12345` → `/api/users/{id}`
   - `/api/orders/550e8400-e29b-41d4-a716-446655440000` → `/api/orders/{id}`

2. **Test ID Management**: Ensure consistent test_case_id across collectors and database

3. **Performance**: Use batch inserts for high-volume coverage data

4. **Schema Updates**: Apply schema changes via `apply_coverage_schema_only.py`

## Troubleshooting

### Import Errors
Ensure you run tests from project root:
```bash
cd /path/to/crossbridge
python -m pytest tests/...
```

### Database Connection
Verify PostgreSQL connection string in scripts:
```python
DB_CONN = "postgresql://user:password@host:port/database"
```

### UUID Adapter
For psycopg2, register UUID adapter:
```python
import psycopg2.extras
psycopg2.extras.register_uuid()
```

## Files Reference

- Implementation:
  - `core/coverage/coverage_py_parser.py`
  - `core/coverage/istanbul_parser.py`
  - `core/coverage/behavioral_collectors.py`
  - `core/coverage/functional_models.py` (extended)
  - `core/coverage/functional_coverage_schema.sql` (extended)

- Scripts:
  - `scripts/apply_coverage_schema_only.py`
  - `scripts/check_db_schema.py`

- Tests:
  - `tests/core/coverage/test_coverage_py_parser.py` (11 tests)
  - `tests/core/coverage/test_istanbul_parser.py` (14 tests)
  - `tests/core/coverage/test_behavioral_collectors.py` (14 tests)
  - `tests/integration/test_coverage_integration.py` (4 tests)

- Documentation:
  - `COVERAGE_INTELLIGENCE_IMPLEMENTATION.md`
  - `COVERAGE_QUICK_REFERENCE.md`
  - `BEHAVIORAL_COVERAGE_USAGE.md` (this file)

## Summary

✅ **39 unit tests** (100% passing)  
✅ **4 integration tests** (100% passing)  
✅ **PostgreSQL schema** applied  
✅ **SaaS-friendly** behavioral coverage  
✅ **Production ready**  

For detailed implementation guide, see `COVERAGE_INTELLIGENCE_IMPLEMENTATION.md`
