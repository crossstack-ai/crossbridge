# API Change Intelligence - Complete Feature Documentation

## 🎯 Overview

**API Change Intelligence** is a comprehensive system for detecting, analyzing, and responding to OpenAPI/Swagger specification changes. It provides intelligent test selection, automated alerting, and seamless CI/CD integration.

## ✨ Key Features

### 1. **Multi-Source Spec Collection**
- File-based specs
- URL-based specs (with authentication)
- Git repository integration
- Version detection and comparison

### 2. **Change Detection & Analysis**
- **oasdiff Integration**: Industry-standard OpenAPI comparison
- **Breaking Change Detection**: Automatic identification of breaking changes
- **Change Categorization**: Added, Modified, Removed entities
- **Risk Assessment**: Critical, High, Medium, Low risk levels

### 3. **Rule-Based Intelligence (Always Active)**
- Deterministic test recommendations
- Endpoint-to-test mapping
- Parameter impact analysis
- Response structure analysis
- No external dependencies required

### 4. **AI Enhancement (Optional)**
- GPT-4.1-mini integration
- Claude 3.5 Sonnet support
- Token tracking and budgets
- Cost control mechanisms
- **Note**: System works fully without AI

### 5. **Impact Analysis** ⭐
- **Multi-Strategy Test Detection**:
  - Custom mappings (user-defined)
  - Static code analysis (string literals, patterns)
  - Coverage data analysis (when available)
  - Convention-based matching (naming patterns)
  
- **Confidence Scoring**:
  - High (>80%): Direct references found
  - Medium (40-80%): Pattern matches
  - Low (<40%): Weak correlations
  
- **Framework Support**:
  - pytest (Python)
  - Robot Framework
  - Selenium
  - Playwright
  - Cypress
  - Jest/Mocha

### 6. **Alert System** ⭐
- **Email Notifications**:
  - SMTP integration
  - HTML and plain text formats
  - Severity-based filtering
  - Beautiful templating
  
- **Slack Integration**:
  - Webhook support
  - Rich block formatting
  - @mention support for critical alerts
  - Severity-based routing
  
- **Alert Features**:
  - Individual or summary mode
  - Automatic deduplication
  - Database history tracking
  - Configurable thresholds

### 7. **CI/CD Integration** ⭐
- **Smart Test Selection**:
  - Confidence-based filtering
  - Configurable thresholds
  - Maximum test limits
  - Framework-specific grouping
  
- **Output Formats**:
  - **pytest**: `pytest test1.py::test_func test2.py::test_another`
  - **Robot**: `robot --test 'Test Name' test1.robot`
  - **JSON**: Structured test metadata
  - **Text**: One test per line
  - **GitHub Actions**: `::set-output name=tests::...`
  - **Jenkins**: Comma-separated list
  
- **CI Configuration Generation**:
  - GitHub Actions workflows
  - Jenkins pipelines
  - GitLab CI templates

### 8. **Documentation Generation**
- **Markdown Output**:
  - Incremental mode (append to existing)
  - Full mode (complete rewrite)
  - Risk badges and icons
  - Test recommendations
  - Breaking change highlights
  
- **Future Support** (planned):
  - Confluence export
  - HTML reports
  - PDF generation

### 9. **Observability**
- **Grafana Dashboard** (8 panels):
  - API Changes Over Time
  - Breaking vs Non-Breaking Changes
  - Risk Level Distribution
  - High-Risk APIs Heatmap
  - AI Usage Tracking
  - Token Usage Monitoring
  - Change Type Breakdown
  - Recent Breaking Changes Table
  
- **Database Storage**:
  - Full change history
  - Alert tracking
  - AI token usage
  - Test coverage mapping

## 🚀 Quick Start

### Installation

1. **Install oasdiff** (required):
```bash
# Option 1: Using Go
go install github.com/tufin/oasdiff@latest

# Option 2: Download binary
# Windows: https://github.com/tufin/oasdiff/releases/download/v1.10.0/oasdiff_1.10.0_windows_amd64.tar.gz
# Linux: https://github.com/tufin/oasdiff/releases/download/v1.10.0/oasdiff_1.10.0_linux_amd64.tar.gz
# macOS: https://github.com/tufin/oasdiff/releases/download/v1.10.0/oasdiff_1.10.0_darwin_amd64.tar.gz
```

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Verify installation**:
```bash
crossbridge api-diff check-deps
```

### Basic Configuration

Create or update `crossbridge.yml`:

```yaml
crossbridge:
  api_change:
    enabled: true
    
    # Spec source configuration
    spec_source:
      type: file  # or 'url' or 'git'
      current: specs/openapi-v2.yaml
      previous: specs/openapi-v1.yaml
    
    # Intelligence configuration
    intelligence:
      mode: hybrid  # 'rules', 'hybrid', or 'ai-only'
      rules:
        enabled: true
      ai:
        enabled: false  # Set to true when API keys configured
        provider: openai
        model: gpt-4.1-mini
        max_tokens_per_month: 100000
    
    # Impact analysis (NEW)
    impact_analysis:
      enabled: true
      test_directories:
        - tests/
        - test/
      framework: pytest  # or 'robot', 'selenium', etc.
      custom_mappings:
        "GET /api/users":
          - test_file: tests/api/test_users.py
            test_name: test_get_users
    
    # CI integration (NEW)
    ci_integration:
      enabled: true
      min_confidence: 0.5  # Only run tests with >50% confidence
      max_tests: 100       # Limit number of tests (0 = unlimited)
    
    # Alerting (NEW)
    alerts:
      enabled: true
      email:
        enabled: true
        smtp_host: smtp.gmail.com
        smtp_port: 587
        smtp_user: alerts@example.com
        smtp_password: ${SMTP_PASSWORD}  # Use environment variable
        from_email: crossbridge@example.com
        to_emails:
          - qa-team@example.com
          - engineering@example.com
        min_severity: high  # Only send high/critical alerts
      slack:
        enabled: true
        webhook_url: ${SLACK_WEBHOOK_URL}
        channel: "#api-alerts"
        username: "CrossBridge AI"
        mention_users:
          - U12345678  # Slack user IDs for critical alerts
        min_severity: critical
    
    # Documentation
    documentation:
      enabled: true
      output_dir: docs/api-changes
      formats:
        markdown:
          enabled: true
          mode: incremental  # or 'full'
```

### Usage Examples

#### 1. Run API Diff Analysis
```bash
# Basic analysis
crossbridge api-diff run

# With AI enhancement
crossbridge api-diff run --ai

# Verbose output
crossbridge api-diff run --verbose

# Custom config file
crossbridge api-diff run --config my-config.yml
```

**Output**:
```
============================================================
CrossBridge AI - API Change Intelligence
============================================================

[1/6] Collecting OpenAPI specifications...
  Previous version: 1.0.0
  Current version: 2.0.0

[2/6] Running oasdiff comparison...
  Found 3 breaking changes

[3/6] Normalizing changes...
  Normalized 12 changes

[4/6] Applying rule-based intelligence...

[5/6] Applying AI intelligence...
  AI intelligence disabled

[5.5/6] Analyzing test impact...
  Found 24 potentially affected tests
  Must run: 8 tests
  Should run: 12 tests

[5.6/6] Sending alerts...
  Sent alerts for 3 critical changes

[6/6] Generating documentation...
  Markdown documentation generated

============================================================
Analysis Complete!
============================================================
Total Changes: 12
Breaking Changes: 3
High Risk Changes: 5
Duration: 2341ms
============================================================

📝 Documentation: docs/api-changes/api-changes.md

🧪 Test Recommendations:
  • Must run: 8 tests
  • Should run: 12 tests

Run: crossbridge api-diff export-tests tests.txt --format pytest
```

#### 2. Export Test List for CI
```bash
# Export as pytest command
crossbridge api-diff export-tests tests.txt --format pytest

# Export as JSON
crossbridge api-diff export-tests tests.json --format json

# Export with custom confidence threshold
crossbridge api-diff export-tests tests.txt --format pytest --min-confidence 0.7

# Export for Robot Framework
crossbridge api-diff export-tests tests.txt --format robot
```

**Example pytest output** (tests.txt):
```
pytest tests/api/test_users.py::test_get_users tests/api/test_users.py::test_create_user tests/integration/test_user_workflow.py
```

**Example JSON output** (tests.json):
```json
{
  "total": 8,
  "tests": [
    {
      "file": "tests/api/test_users.py",
      "name": "test_get_users",
      "confidence": 0.85,
      "endpoint": "/api/v1/users",
      "method": "GET",
      "reason": "Direct endpoint reference found"
    },
    ...
  ]
}
```

#### 3. GitHub Actions Integration

Create `.github/workflows/api-change-tests.yml`:

```yaml
name: API Change Tests

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  api-change-detection:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install oasdiff
        run: |
          go install github.com/tufin/oasdiff@latest
          echo "$HOME/go/bin" >> $GITHUB_PATH
      
      - name: Install CrossBridge
        run: pip install -r requirements.txt
      
      - name: Run API Change Analysis
        run: crossbridge api-diff run
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
      
      - name: Export Test List
        run: crossbridge api-diff export-tests affected-tests.txt --format pytest
      
      - name: Run Affected Tests
        run: $(cat affected-tests.txt)
```

#### 4. Jenkins Integration

```groovy
pipeline {
    agent any
    
    stages {
        stage('API Change Detection') {
            steps {
                sh 'crossbridge api-diff run'
            }
        }
        
        stage('Export Tests') {
            steps {
                sh 'crossbridge api-diff export-tests tests.txt --format pytest'
            }
        }
        
        stage('Run Tests') {
            steps {
                sh '$(cat tests.txt)'
            }
        }
    }
}
```

## 📊 Real-World Use Cases

### Use Case 1: Breaking Change Alert
**Scenario**: Backend team removes a required field from `/api/users` endpoint.

**What Happens**:
1. ✅ oasdiff detects breaking change
2. ✅ Change normalized with HIGH risk level
3. ✅ Impact analyzer finds 12 affected tests
4. ✅ Alert sent to Slack with @mention
5. ✅ Email sent to QA team
6. ✅ Documentation updated with breaking change badge
7. ✅ Test list exported for CI

**Result**: QA team notified within seconds, can run targeted tests immediately.

### Use Case 2: New Endpoint Added
**Scenario**: New `/api/v2/products` endpoint added.

**What Happens**:
1. ✅ Change detected as ADDED entity
2. ✅ Rule engine recommends creating new tests
3. ✅ Impact analyzer finds no existing tests (expected)
4. ✅ Documentation updated with new endpoint details
5. ✅ Low-severity alert sent (informational)

**Result**: Team aware of new endpoint, can plan test coverage.

### Use Case 3: Non-Breaking Parameter Change
**Scenario**: Optional query parameter added to `/api/search`.

**What Happens**:
1. ✅ Change detected as MODIFIED parameter
2. ✅ Risk level: LOW (non-breaking)
3. ✅ Impact analyzer finds 4 related tests with MEDIUM confidence
4. ✅ Documentation updated
5. ✅ No alerts sent (below threshold)

**Result**: Change documented, tests identified but not critical to run immediately.

## 🎓 Advanced Features

### Custom Test Mappings

For complex scenarios, define explicit test-to-endpoint mappings:

```yaml
impact_analysis:
  custom_mappings:
    "GET /api/users":
      - test_file: tests/api/test_users.py
        test_name: test_get_all_users
      - test_file: tests/integration/test_user_listing.py
        test_name: test_user_pagination
    
    "POST /api/orders":
      - test_file: tests/api/test_orders.py
      - test_file: tests/e2e/test_checkout_flow.py
```

### Alert Severity Customization

```yaml
alerts:
  email:
    min_severity: high  # Only high/critical
  slack:
    min_severity: medium  # Medium and above
```

### Multi-Environment Configuration

```yaml
# Production spec tracking
spec_source:
  type: url
  current: https://api.prod.example.com/openapi.yaml
  previous: https://api.staging.example.com/openapi.yaml
  auth:
    type: bearer
    token: ${API_TOKEN}
```

### Git-Based Spec Comparison

```yaml
spec_source:
  type: git
  repository: https://github.com/example/api-specs.git
  current_branch: main
  previous_branch: release-1.0
  spec_path: specs/openapi.yaml
```

## 📈 Monitoring & Analytics

### Grafana Dashboard

Import the dashboard: `grafana/dashboards/api_change_intelligence.json`

**Panels**:
1. **API Changes Over Time**: Line chart showing change frequency
2. **Breaking vs Non-Breaking**: Stacked area chart
3. **Risk Distribution**: Pie chart of risk levels
4. **High-Risk APIs**: Table of critical changes
5. **AI Usage**: Toggle between AI and manual detection
6. **Token Usage**: Gauge showing monthly token consumption
7. **Change Types**: Bar chart of entity changes
8. **Recent Breaking**: Table of latest breaking changes

### Database Queries

Query change history:
```sql
-- Recent breaking changes
SELECT * FROM api_changes 
WHERE breaking = true 
ORDER BY detected_at DESC 
LIMIT 10;

-- Changes by risk level
SELECT risk_level, COUNT(*) 
FROM api_changes 
GROUP BY risk_level;

-- Alert history
SELECT * FROM api_change_alerts 
ORDER BY sent_at DESC;
```

## 🔧 Troubleshooting

### Common Issues

**1. "oasdiff not found"**
```bash
# Solution: Install oasdiff
go install github.com/tufin/oasdiff@latest
# Or download binary from releases
```

**2. "No test impacts found"**
- Check test_directories paths
- Verify framework setting matches your tests
- Add custom_mappings for complex scenarios
- Ensure test files follow naming conventions

**3. "Email alerts not sending"**
- Verify SMTP credentials
- Check firewall/network settings
- Test with telnet: `telnet smtp.gmail.com 587`
- Enable "less secure apps" for Gmail

**4. "Slack webhook failed"**
- Verify webhook URL is correct
- Check workspace permissions
- Test webhook with curl:
  ```bash
  curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"Test"}' \
    YOUR_WEBHOOK_URL
  ```

## 🎯 Best Practices

### 1. Start Simple
- Begin with file-based specs
- Enable rule-based intelligence only
- Add alerts after validating detection
- Enable AI last (optional)

### 2. Tune Confidence Thresholds
- Start with 0.5 minimum confidence
- Monitor false positives/negatives
- Adjust based on your codebase
- Use custom mappings for critical endpoints

### 3. Alert Fatigue Prevention
- Set appropriate severity thresholds
- Use summary mode for bulk changes
- Limit alert frequency
- Route different severities to different channels

### 4. CI Integration
- Export tests to file for reproducibility
- Set max_tests limit for long suites
- Use confidence thresholds to balance speed/coverage
- Cache test results between runs

### 5. Documentation
- Use incremental mode for git-friendly diffs
- Review generated docs regularly
- Link to test coverage in docs
- Archive old change logs

## 📞 Support

- **Email**: vikas.sdet@gmail.com
- **GitHub**: https://github.com/crossstack-ai/crossbridge
- **Documentation**: docs/api-change/
- **Spec**: docs/implementation/API_CHANGE_INTELLIGENCE_SPEC.md

## 🗺️ Roadmap

### Completed (v2.0)
- ✅ Multi-source spec collection
- ✅ oasdiff integration
- ✅ Rule-based intelligence
- ✅ Impact analysis with multiple strategies
- ✅ Email and Slack alerts
- ✅ CI integration with 6 formats
- ✅ Test selection and confidence scoring
- ✅ Grafana dashboard
- ✅ Complete documentation

### Future (v2.1+)
- 🔜 Runtime coverage collection
- 🔜 Machine learning for confidence scoring
- 🔜 Confluence integration
- 🔜 Microsoft Teams alerts
- 🔜 Custom webhook support
- 🔜 Historical trend analysis
- 🔜 Test gap detection
- 🔜 Performance impact prediction

---

**Built with ❤️ by CrossStack AI**  
**Version 2.0 - Production Ready**  
**Last Updated: January 29, 2026**
