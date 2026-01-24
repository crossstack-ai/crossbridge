# Functional Coverage Quick Start

## 🚀 Quick Commands

```bash
# Show functional coverage map
crossbridge coverage map

# Show test-to-feature coverage
crossbridge coverage features

# Show coverage gaps
crossbridge coverage gaps

# Analyze change impact
crossbridge coverage impact --file LoginService.java

# Get summary statistics
crossbridge coverage summary

# Export to CSV
crossbridge coverage map --output report.csv --format csv

# Export to JSON
crossbridge coverage features --output report.json --format json
```

## 📊 Console Output Examples

### Functional Coverage Map
```
| Code Unit           | Tests | TestRail TCs     |
|---------------------|-------|------------------|
| LoginService.java   | 14    | C12345, C12401   |
| AuthController.java | 9     | C12011           |
```

### Test-to-Feature Coverage
```
| Feature | Test Case                | TestRail TC |
|---------|--------------------------|-------------|
| Login   | LoginTest.testValid      | C12345      |
| Login   | LoginBDD.ValidLogin      | C12401      |
```

### Change Impact Surface
```
+---------------------------+-----------+-------------+
| Impacted Test             | Feature   | TestRail TC |
+---------------------------+-----------+-------------+
| LoginTest.testValidLogin  | Login     | C12345      |
+---------------------------+-----------+-------------+
```

## 🔧 Setup Steps

### 1. Install Dependencies
```bash
pip install tabulate rich
```

### 2. Apply Database Schema
```sql
psql -U crossbridge -d crossbridge_db -f core/coverage/functional_coverage_schema.sql
```

### 3. Test CLI
```bash
crossbridge coverage --help
crossbridge coverage summary
```

## 🏷️ External Test Case Patterns

### Java (JUnit/TestNG)
```java
@TestRail(id = "C12345")
@Test
public void testLogin() { }

@ExternalTestCase("C12345")
@Test
public void testLogin() { }
```

### Python (pytest)
```python
@pytest.mark.testrail("C12345")
def test_login():
    pass
```

### Robot Framework
```robot
*** Test Cases ***
Valid Login
    [Tags]    testrail:C12345
    Login With Valid Credentials
```

### Cucumber
```gherkin
@testrail:C12345
Scenario: Valid login
    Given I am on the login page
```

## 📈 Grafana Queries

### Coverage Map
```sql
SELECT * FROM functional_coverage_map
ORDER BY test_count DESC LIMIT 50;
```

### Impact Analysis
```sql
SELECT * FROM change_impact_surface
WHERE changed_file = '$file_path';
```

### Coverage Gaps
```sql
SELECT * FROM coverage_gaps;
```

## 🔗 Integration Points

### During Test Discovery
```python
from core.coverage.external_extractors import extract_external_refs_from_file
from core.coverage.functional_repository import FunctionalCoverageRepository

# Extract external TC refs
refs = extract_external_refs_from_file(test_file, framework="java")

# Store in database
repo = FunctionalCoverageRepository(session)
for ref in refs:
    external_tc = ExternalTestCase(
        system=ref.system,
        external_id=ref.external_id
    )
    repo.upsert_external_test_case(external_tc)
```

### Map Test to Feature
```python
feature = Feature(
    name="Login",
    type=FeatureType.BDD,
    source=FeatureSource.CUCUMBER
)
repo.upsert_feature(feature)

mapping = TestFeatureMap(
    test_case_id=test.id,
    feature_id=feature.id,
    source=MappingSource.COVERAGE
)
repo.create_test_feature_mapping(mapping)
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `core/coverage/functional_coverage_schema.sql` | Database schema |
| `core/coverage/functional_models.py` | Data models |
| `core/coverage/functional_repository.py` | Database operations |
| `core/coverage/console_formatter.py` | Console output |
| `core/coverage/external_extractors.py` | External TC extraction |
| `cli/commands/coverage_commands.py` | CLI commands |

## 🎯 Design Principles

✅ No fake coverage percentages  
✅ Shows honest relationships  
✅ Grafana-ready views  
✅ Console-first UX  
✅ External TC integration  
✅ Framework-agnostic  

## 💡 Tips

1. **Start Small**: Test with `--limit 10` first
2. **Export Reports**: Use `--output` for sharing
3. **Filter Features**: Use `--feature login` for focused view
4. **Check Gaps**: Run `coverage gaps` regularly
5. **CI Integration**: Add impact analysis to PR checks

## 📚 Learn More

See [`FUNCTIONAL_COVERAGE_IMPLEMENTATION.md`](FUNCTIONAL_COVERAGE_IMPLEMENTATION.md) for full documentation.
