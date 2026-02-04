# CrossBridge Log Parser CLI

**Universal log parsing utility with automatic intelligence analysis**

## Overview

`crossbridge-log` is a command-line utility that provides intelligent log parsing and analysis for all test automation frameworks. It automatically applies execution intelligence to classify failures, extract signals, and provide actionable recommendations.

## Key Features

### 🎯 **Automatic Intelligence** (NEW!)
- ✅ **Failure Classification** - Automatically categorizes failures into:
  - `PRODUCT_DEFECT` - Application bugs
  - `AUTOMATION_DEFECT` - Test code issues  
  - `ENVIRONMENT_ISSUE` - Infrastructure problems
  - `CONFIGURATION_ISSUE` - Setup/config problems
  - `UNKNOWN` - Unable to classify

- ✅ **Signal Extraction** - Detects:
  - Timeout errors
  - Assertion failures
  - Locator/element issues
  - Network/connection errors
  - Configuration problems

- ✅ **Code Reference Resolution** - Pinpoints exact test code location for automation defects

- ✅ **Works Without AI** - Fully deterministic, rule-based analysis (no AI required)

### 🔍 **Universal Parsing**
Supports all major frameworks:
- Robot Framework (`output.xml`)
- Cypress (`cypress-results.json`)
- Playwright (`playwright-trace.json`)
- Behave BDD (`behave-results.json`)
- Java Cucumber (`*Steps.java`)

### 🎛️ **Powerful Filtering**
- Filter by test name (with wildcards)
- Filter by test ID
- Filter by status (PASS/FAIL/SKIP)
- Filter by error code
- Filter by text pattern (case-insensitive)
- Filter by time range

### 💾 **Flexible Output**
- Console display (formatted, color-coded)
- JSON file export
- API upload (for remote access)

---

## Installation

```bash
# Clone repository
git clone https://github.com/crossstack-ai/crossbridge.git
cd crossbridge

# Make executable
chmod +x bin/crossbridge-log

# Add to PATH (optional)
export PATH=$PATH:$(pwd)/bin
```

---

## Quick Start

### Basic Usage (with automatic intelligence)

```bash
# Parse Robot Framework log
./bin/crossbridge-log output.xml

# Parse Cypress results
./bin/crossbridge-log cypress-results.json

# Parse with custom sidecar
SIDECAR_HOST=remote-server ./bin/crossbridge-log output.xml
```

**Output includes:**
- Parsed test results
- **Intelligence Analysis Summary** (NEW!)
  - Failure classifications breakdown
  - Detected signals
  - Actionable recommendations
- Framework-specific statistics

---

## Usage Examples

### 1. Basic Parsing with Intelligence

```bash
./bin/crossbridge-log output.xml
```

**Output:**
```
Checking sidecar API...
✓ Detected framework: robot
Parsing log file: output.xml
Running intelligence analysis...
✓ Intelligence analysis complete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Intelligence Analysis Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Failure Classifications:
  • PRODUCT_DEFECT: 2
  • AUTOMATION_DEFECT: 1

Detected Signals:
  • assertion_failure: 2
  • locator_error: 1

Recommendations:
  ✓ Review application code for bugs
  ✓ Update test automation code/locators

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           Robot Framework Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
...
```

### 2. Filter Failed Tests Only

```bash
./bin/crossbridge-log output.xml --status FAIL
```

Shows only failed tests with intelligence analysis.

### 3. Filter by Test Name (Wildcards Supported)

```bash
# All login tests
./bin/crossbridge-log output.xml --test-name 'Login*'

# Tests containing "API"
./bin/crossbridge-log output.xml --test-name '*API*'
```

### 4. Filter by Error Code/Pattern

```bash
# Find all "Connection refused" errors
./bin/crossbridge-log output.xml --pattern "Connection refused"

# Find all timeout errors
./bin/crossbridge-log output.xml --error-code "TimeoutException"
```

### 5. Save to File

```bash
# Save to specific file
./bin/crossbridge-log output.xml --output results.json

# Auto-generated timestamped file
./bin/crossbridge-log output.xml
# Creates: output.xml.parsed.20260205_143022.json
```

### 6. Time-Based Filtering

```bash
# Tests after specific time
./bin/crossbridge-log output.xml --time-from '2026-02-05T10:00:00'

# Tests in time range
./bin/crossbridge-log output.xml \
  --time-from '2026-02-05T10:00:00' \
  --time-to '2026-02-05T12:00:00'
```

### 7. Combined Filters

```bash
# Failed login tests with assertion errors
./bin/crossbridge-log output.xml \
  --status FAIL \
  --test-name 'Login*' \
  --pattern 'AssertionError'
```

### 8. Disable Intelligence Analysis

```bash
# Use basic parsing only (faster for large logs)
./bin/crossbridge-log output.xml --no-analyze
```

---

## Command-Line Options

```
Usage: crossbridge-log <log-file> [OPTIONS]

Options:
  -o, --output FILE          Save parsed results to FILE (JSON format)
  -t, --test-name PATTERN    Filter tests by name (supports wildcards)
  -i, --test-id ID           Filter by specific test ID
  -s, --status STATUS        Filter by status (PASS, FAIL, SKIP)
  -e, --error-code CODE      Filter by error code in messages
  -p, --pattern PATTERN      Filter by text pattern (case-insensitive)
  --time-from DATETIME       Filter tests starting after DATETIME
  --time-to DATETIME         Filter tests ending before DATETIME
  --no-analyze               Disable automatic intelligence analysis
  -h, --help                 Show this help message

Environment Variables:
  SIDECAR_HOST   - Sidecar API host (default: localhost)
  SIDECAR_PORT   - Sidecar API port (default: 8765)
```

---

## Intelligence Analysis Details

### How It Works

1. **Automatic Framework Detection**
   - Analyzes filename and content
   - Selects appropriate parser

2. **Log Parsing**
   - Uses framework-specific parser (Robot, Cypress, etc.)
   - Normalizes to standard format

3. **Intelligence Analysis** (Automatic, unless `--no-analyze`)
   - Calls sidecar `/analyze` endpoint
   - Uses `ExecutionAnalyzer` (deterministic, no AI)
   - Extracts failure signals
   - Classifies each failure
   - Resolves code references (for automation defects)
   - Generates recommendations

4. **Filtering**
   - Applies user-specified filters
   - Works on enriched data

5. **Display**
   - Shows intelligence summary
   - Shows filtered results
   - Saves to file/API

### Classification Logic

**PRODUCT_DEFECT:**
- Assertion failures
- Unexpected values
- API errors (4xx/5xx)
- Business logic failures

**AUTOMATION_DEFECT:**
- Element not found
- Stale element references
- Incorrect locators
- Test syntax errors

**ENVIRONMENT_ISSUE:**
- Connection timeouts
- Network errors
- DNS failures
- Out of memory

**CONFIGURATION_ISSUE:**
- Missing files
- Wrong credentials
- Import errors
- Dependency issues

### Signal Types

- `assertion_failure` - Assert/expect statements failed
- `timeout` - Operation exceeded time limit
- `locator_error` - Element locator not found
- `network_error` - Connection/network issues
- `http_error` - HTTP status errors
- `configuration_error` - Config/setup problems

---

## API Access

### Upload to Sidecar (Automatic)

Results are automatically uploaded to sidecar (if < 10MB):

```bash
./bin/crossbridge-log output.xml

# Output:
✓ Results uploaded successfully
Access via API:
  GET  http://localhost:8765/logs/abc123
  GET  http://localhost:8765/logs/abc123/summary
  GET  http://localhost:8765/logs/abc123/failures
```

### API Endpoints

```bash
# Get full log
curl http://localhost:8765/logs/abc123

# Get summary only
curl http://localhost:8765/logs/abc123/summary

# Get failures only
curl http://localhost:8765/logs/abc123/failures

# List all logs
curl http://localhost:8765/logs

# Delete log
curl -X DELETE http://localhost:8765/logs/abc123
```

---

## Integration with Existing Components

### 1. Execution Intelligence Engine
**Location:** `core/execution/intelligence/`

- **ExecutionAnalyzer** - Main analysis engine
- **Signal Extractors** - Pattern-based signal detection
- **Rule-Based Classifier** - 30+ classification rules
- **Code Reference Resolver** - Stack trace parsing

**Usage:**
```python
from core.execution.intelligence.analyzer import ExecutionAnalyzer

analyzer = ExecutionAnalyzer(enable_ai=False)  # Works without AI
result = analyzer.analyze(raw_log, test_name, framework)
print(result.classification.failure_type)  # PRODUCT_DEFECT, etc.
```

### 2. JSON Log Adapter
**Location:** `core/execution/intelligence/log_adapters/`

- Parses application logs (JSON/ELK/Fluentd)
- Correlates with test execution logs
- Normalizes to canonical schema

**Complementary Use:**
- `crossbridge-log` → Test execution logs
- `JSON Log Adapter` → Application logs
- Correlate both for full-stack analysis

### 3. Framework Parsers
**Location:** `core/intelligence/`

- `RobotLogParser` - Robot Framework
- `CypressResultsParser` - Cypress
- `PlaywrightTraceParser` - Playwright
- `BehaveJSONParser` - Behave BDD
- `JavaStepDefinitionParser` - Java Cucumber

**Reuse:**
`crossbridge-log` uses same parsers as runtime execution.

---

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Parse logs | ~100ms | Per log file |
| Extract signals | ~50ms | Per failure |
| Classify | ~50ms | Per failure |
| Resolve code | ~20ms | Per stack trace |
| **Total (with intelligence)** | ~220ms | Per test failure |
| Total (without intelligence) | ~100ms | Basic parsing only |

**Recommendations:**
- Use `--no-analyze` for very large logs (>1000 tests)
- Use filtering to reduce dataset before analysis
- Enable intelligence for failure analysis (worth the 120ms overhead)

---

## Troubleshooting

### Issue: Sidecar not reachable

```
Error: Sidecar API not reachable at http://localhost:8765
```

**Solution:**
1. Start sidecar: `python -m services.sidecar_api`
2. Check `SIDECAR_HOST` and `SIDECAR_PORT`
3. Verify firewall allows connection

### Issue: Intelligence analysis not available

```
Note: Intelligence analysis not available (using basic parsing)
```

**Solution:**
1. Update sidecar to latest version (includes `/analyze` endpoint)
2. Restart sidecar
3. Intelligence analysis requires sidecar with ExecutionAnalyzer

### Issue: No failures to analyze

```
Recommendations:
  ✓ All tests passed - no analysis needed
```

**Solution:**
This is normal - intelligence only runs on failed tests.

---

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run tests and analyze
  run: |
    pytest tests/ --html=report.html
    ./bin/crossbridge-log pytest-output.log --status FAIL --output failures.json
    
- name: Check for product defects
  run: |
    if grep -q "PRODUCT_DEFECT" failures.json; then
      echo "Product defects found!"
      exit 1
    fi
```

### GitLab CI

```yaml
test:
  script:
    - robot tests/
    - ./bin/crossbridge-log output.xml --status FAIL --output failures.json
  artifacts:
    when: always
    paths:
      - failures.json
    reports:
      junit: failures.json
```

### Jenkins

```groovy
stage('Test Analysis') {
    steps {
        sh '''
            ./bin/crossbridge-log output.xml --status FAIL --output failures.json
            
            if grep -q "PRODUCT_DEFECT" failures.json; then
                currentBuild.result = 'FAILURE'
            fi
        '''
    }
}
```

---

## Advanced Usage

### Batch Processing

```bash
# Process all logs in directory
for log in logs/*.xml; do
  ./bin/crossbridge-log "$log" --status FAIL --output "analyzed_$(basename $log).json"
done
```

### Remote Sidecar

```bash
# Use remote sidecar server
export SIDECAR_HOST=10.60.75.145
export SIDECAR_PORT=8765

./bin/crossbridge-log output.xml
```

### Programmatic Access (Python)

```python
import subprocess
import json

# Run crossbridge-log
result = subprocess.run(
    ['./bin/crossbridge-log', 'output.xml', '--output', 'results.json'],
    capture_output=True
)

# Load results
with open('results.json') as f:
    data = json.load(f)
    
# Access intelligence summary
summary = data.get('intelligence_summary', {})
product_defects = summary.get('classifications', {}).get('PRODUCT_DEFECT', 0)

print(f"Found {product_defects} product defects")
```

---

## Related Documentation

- [Execution Intelligence](../EXECUTION_INTELLIGENCE.md) - Deep dive into analysis engine
- [JSON Log Adapter](../log_analysis/JSON_LOG_ADAPTER.md) - Application log correlation
- [Intelligence Features](../releases/historical/intelligence_features.md) - Parser details
- [Sidecar API](../sidecar/SIDECAR_API.md) - API reference

---

## Contributing

To add support for a new framework:

1. Implement parser in `core/intelligence/`
2. Register in sidecar API (`services/sidecar_api.py`)
3. Add detection logic in `crossbridge-log` (`detect_framework()`)
4. Add tests in `tests/unit/test_crossbridge_log.py`
5. Update this documentation

---

## License

Apache 2.0

---

## Support

- Issues: https://github.com/crossstack-ai/crossbridge/issues
- Docs: https://docs.crossbridge.dev
- Email: support@crossbridge.dev
