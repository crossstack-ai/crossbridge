# API Change Intelligence - Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Auto-Enable Feature (Automatic During Migration)

The API Change Intelligence feature is **automatically enabled** when you run CrossBridge migrations:

```bash
# Option 1: Automatic (runs during first migration)
crossbridge migrate

# Option 2: Manual enable
python scripts/enable_api_change_intelligence.py
```

### Step 2: Verify Dependencies

```bash
crossbridge api-diff check-deps
```

**Expected Output:**
```
✅ oasdiff: v1.10.0
✅ All dependencies installed
```

**If oasdiff is missing:**
```bash
# Option 1: Using Go
go install github.com/tufin/oasdiff@latest

# Option 2: Download binary
# https://github.com/tufin/oasdiff/releases
```

### Step 3: Configure Spec Sources

Edit `crossbridge.yml`:

```yaml
crossbridge:
  api_change:
    enabled: true
    spec_source:
      type: file  # Start with local files
      current: specs/openapi.yaml
      previous: specs/openapi_prev.yaml
```

### Step 4: Run Analysis

```bash
crossbridge api-diff run
```

**Output:**
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
  No alerts configured (skipped)

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
```

## 🎯 Common Configurations

### Configuration 1: Basic (File-Based)

```yaml
crossbridge:
  api_change:
    enabled: true
    spec_source:
      type: file
      current: specs/openapi.yaml
      previous: specs/openapi_prev.yaml
    
    impact_analysis:
      enabled: true
      test_directories:
        - tests/
      framework: pytest
```

### Configuration 2: URL-Based with Authentication

```yaml
crossbridge:
  api_change:
    enabled: true
    spec_source:
      type: url
      current: https://api.example.com/v2/openapi.yaml
      previous: https://api.example.com/v1/openapi.yaml
      auth:
        type: bearer
        token: ${API_TOKEN}
```

### Configuration 3: Git-Based Comparison

```yaml
crossbridge:
  api_change:
    enabled: true
    spec_source:
      type: git
      repository: https://github.com/example/api-specs.git
      current_branch: main
      previous_branch: release-1.0
      spec_path: openapi.yaml
```

### Configuration 4: With Alerts (Production)

```yaml
crossbridge:
  api_change:
    enabled: true
    
    alerts:
      enabled: true
      
      email:
        enabled: true
        smtp_host: smtp.gmail.com
        smtp_port: 587
        smtp_user: ${SMTP_USER}
        smtp_password: ${SMTP_PASSWORD}
        from_email: crossbridge@example.com
        to_emails:
          - qa-team@example.com
        min_severity: high
      
      slack:
        enabled: true
        webhook_url: ${SLACK_WEBHOOK_URL}
        mention_users:
          - U12345678  # Critical alerts only
      
      confluence:
        enabled: true
        url: https://your-domain.atlassian.net
        username: ${CONFLUENCE_USER}
        auth_token: ${CONFLUENCE_TOKEN}
        space_key: API
        parent_page_id: 123456  # Optional
        page_title_prefix: "API Change Alert"
        update_mode: create  # or 'update' to append
        min_severity: high
        min_severity: critical
```

## 🛡️ Resilience & Error Handling

### Automatic Retry Logic

All external calls include **automatic retry with exponential backoff**:

- **oasdiff**: 3 retries, 2s → 4s → 8s
- **Email (SMTP)**: 3 retries, 2s → 4s → 8s
- **Slack webhooks**: 3 retries, 2s → 4s → 8s, honors rate limits
- **AI API calls**: 3 retries, 2s → 4s → 8s

### Graceful Degradation

The system continues working even if optional components fail:

| Component | Fails | Result |
|-----------|-------|--------|
| AI Engine | ❌ | ✅ Uses rule-based intelligence |
| Email Alerts | ❌ | ✅ Continues with Slack/Confluence/other channels |
| Slack Alerts | ❌ | ✅ Continues with Email/Confluence/other channels |
| Confluence Alerts | ❌ | ✅ Continues with Email/Slack/other channels |
| Impact Analyzer | ❌ | ✅ Analysis completes without test recommendations |
| Documentation | ❌ | ✅ Results still available in database/console |

### Error Handling Examples

**Example 1: SMTP Connection Failure**
```
⚠️  Email send attempt 1 failed: Connection refused. Retrying in 2s...
⚠️  Email send attempt 2 failed: Connection refused. Retrying in 4s...
⚠️  Email send attempt 3 failed: Connection refused. Retrying in 8s...
❌ Failed to send email after 3 attempts
✅ Continuing with analysis...
```

**Example 2: Slack Rate Limit**
```
⚠️  Slack rate limited, waiting 5s...
✅ Slack alert sent successfully after rate limit
```

**Example 3: oasdiff Timeout**
```
⚠️  oasdiff attempt 1 failed: Command timeout. Retrying in 2s...
✅ oasdiff completed successfully on attempt 2
```

## 📊 Logging

### Log Levels

Configure in `crossbridge.yml`:

```yaml
crossbridge:
  logging:
    level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    file:
      enabled: true
      path: logs/crossbridge.log
    
    console:
      enabled: true
      color: true
```

### Log Output Examples

**INFO Level (Default):**
```
2026-01-29 10:15:23 - INFO - Collecting OpenAPI specifications...
2026-01-29 10:15:24 - INFO - Running oasdiff comparison...
2026-01-29 10:15:25 - INFO - Found 12 changes
```

**DEBUG Level:**
```
2026-01-29 10:15:23 - DEBUG - Loading spec from: specs/openapi.yaml
2026-01-29 10:15:23 - DEBUG - Spec version detected: 1.0.0
2026-01-29 10:15:24 - DEBUG - Running: oasdiff diff --format json specs/old.yaml specs/new.yaml
2026-01-29 10:15:24 - DEBUG - oasdiff output: {...}
```

**ERROR Level:**
```
2026-01-29 10:15:23 - ERROR - Failed to load spec: File not found
2026-01-29 10:15:23 - ERROR - Stack trace:
  File "spec_collector.py", line 45, in collect_specs
    with open(spec_path) as f:
FileNotFoundError: specs/openapi.yaml
```

## 🔧 Troubleshooting

### Issue 1: "oasdiff not found"

**Solution:**
```bash
# Check if installed
which oasdiff

# Install
go install github.com/tufin/oasdiff@latest

# Verify
oasdiff --version
```

### Issue 2: "No test impacts found"

**Solutions:**
1. Check test directories in config:
   ```yaml
   impact_analysis:
     test_directories:
       - tests/        # ✓
       - src/test/     # ✓
   ```

2. Verify framework setting:
   ```yaml
   impact_analysis:
     framework: pytest  # Must match your tests
   ```

3. Add custom mappings:
   ```yaml
   impact_analysis:
     custom_mappings:
       "GET /api/users":
         - test_file: tests/test_users.py
   ```

### Issue 3: "Email alerts not sending"

**Solutions:**
1. Test SMTP connection:
   ```bash
   telnet smtp.gmail.com 587
   ```

2. Check credentials:
   ```bash
   echo $SMTP_PASSWORD  # Should be set
   ```

3. Enable debug logging:
   ```yaml
   logging:
     level: DEBUG
   ```

4. For Gmail, enable "App Passwords":
   - https://myaccount.google.com/apppasswords

### Issue 4: "Slack webhook failed"

**Solutions:**
1. Test webhook manually:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test message"}' \
     $SLACK_WEBHOOK_URL
   ```

2. Verify webhook URL format:
   ```
   https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
   ```

3. Check workspace permissions

## 🎓 Next Steps

### 1. Enable CI Integration

Add to `.github/workflows/api-changes.yml`:

```yaml
name: API Change Detection

on: [push, pull_request]

jobs:
  api-changes:
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
      
      - name: Export Affected Tests
        run: crossbridge api-diff export-tests tests.txt --format pytest
      
      - name: Run Affected Tests
        run: $(cat tests.txt)
```

### 2. Set Up Grafana Dashboard

1. Import dashboard: `grafana/dashboards/api_change_intelligence.json`
2. Configure PostgreSQL datasource
3. Set refresh interval to 30s

### 3. Configure AI Enhancement (Optional)

```yaml
crossbridge:
  api_change:
    intelligence:
      ai:
        enabled: true
        provider: openai
        model: gpt-4.1-mini
        api_key: ${OPENAI_API_KEY}
        max_tokens_per_month: 100000
```

### 4. Add Custom Test Mappings

For complex API-to-test relationships:

```yaml
impact_analysis:
  custom_mappings:
    "GET /api/users":
      - test_file: tests/api/test_users.py
        test_name: test_get_all_users
      - test_file: tests/integration/test_user_flow.py
    
    "POST /api/orders":
      - test_file: tests/api/test_orders.py
      - test_file: tests/e2e/test_checkout.py
```

## 📚 Documentation

- **Complete Guide**: [COMPLETE_FEATURE_GUIDE.md](COMPLETE_FEATURE_GUIDE.md)
- **Implementation Details**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **API Specification**: [docs/implementation/API_CHANGE_INTELLIGENCE_SPEC.md](../implementation/API_CHANGE_INTELLIGENCE_SPEC.md)
- **Setup Guide**: [API_CHANGE_SETUP_GUIDE.md](API_CHANGE_SETUP_GUIDE.md)

## 📞 Support

- **Email**: vikas.sdet@gmail.com
- **GitHub**: https://github.com/crossstack-ai/crossbridge
- **Issues**: https://github.com/crossstack-ai/crossbridge/issues

---

**Built with ❤️ by CrossStack AI**  
**Last Updated: January 29, 2026**
