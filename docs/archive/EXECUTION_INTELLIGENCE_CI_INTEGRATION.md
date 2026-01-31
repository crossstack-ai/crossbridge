# Execution Intelligence Engine - CI/CD Integration

Comprehensive guide for integrating Crossbridge's execution intelligence engine into CI/CD pipelines.

## Overview

The execution intelligence engine provides:
- **Framework-agnostic** failure analysis
- **Deterministic classification** (works without AI)
- **Code path resolution** for automation failures
- **CI-friendly** structured output
- **Smart failure routing** (fail only on product defects)

## Quick Start

### GitHub Actions

```yaml
name: Test with Intelligent Failure Analysis

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        continue-on-error: true
        run: |
          pytest tests/ --log-file=test-output.log
      
      - name: Analyze test failures
        if: failure()
        run: |
          crossbridge analyze logs \
            --log-file test-output.log \
            --test-name ${{ github.job }} \
            --framework pytest \
            --format json \
            --fail-on product > analysis.json
      
      - name: Upload analysis results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: failure-analysis
          path: analysis.json
      
      - name: Comment on PR
        if: failure() && github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const analysis = JSON.parse(fs.readFileSync('analysis.json'));
            
            if (analysis.classification) {
              const body = `## Test Failure Analysis
              
**Failure Type**: ${analysis.classification.failure_type}
**Confidence**: ${(analysis.classification.confidence * 100).toFixed(0)}%
**Reason**: ${analysis.classification.reason}

${analysis.classification.code_reference ? 
`**Code Location**: ${analysis.classification.code_reference.file}:${analysis.classification.code_reference.line}

\`\`\`
${analysis.classification.code_reference.snippet}
\`\`\`` : ''}
              `;
              
              github.rest.issues.createComment({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                body: body
              });
            }
```

### GitLab CI

```yaml
test:
  stage: test
  script:
    - pytest tests/ --log-file=test-output.log || true
    - |
      crossbridge analyze logs \
        --log-file test-output.log \
        --test-name ${CI_JOB_NAME} \
        --framework pytest \
        --format json \
        --fail-on product > analysis.json
  artifacts:
    when: always
    paths:
      - test-output.log
      - analysis.json
    reports:
      junit: analysis.json
  allow_failure:
    exit_codes: [0, 1]  # Allow specific failures
```

### Jenkins

```groovy
pipeline {
    agent any
    
    stages {
        stage('Test') {
            steps {
                script {
                    // Run tests (allow failure)
                    sh 'pytest tests/ --log-file=test-output.log || true'
                    
                    // Analyze failures
                    def exitCode = sh(
                        script: '''
                            crossbridge analyze logs \
                                --log-file test-output.log \
                                --test-name ${JOB_NAME} \
                                --framework pytest \
                                --format json \
                                --fail-on product > analysis.json
                        ''',
                        returnStatus: true
                    )
                    
                    // Read analysis
                    def analysis = readJSON file: 'analysis.json'
                    
                    // Determine action
                    if (analysis.classification) {
                        def failureType = analysis.classification.failure_type
                        def confidence = analysis.classification.confidence
                        
                        echo "Failure Type: ${failureType} (confidence: ${confidence})"
                        
                        // Only fail for product defects
                        if (failureType == 'PRODUCT_DEFECT') {
                            error("Test failed due to product defect")
                        } else {
                            unstable("Test failed due to ${failureType}")
                        }
                    }
                }
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'analysis.json', allowEmptyArchive: true
        }
    }
}
```

### Azure Pipelines

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.10'

- script: |
    pip install -r requirements.txt
  displayName: 'Install dependencies'

- script: |
    pytest tests/ --log-file=test-output.log || true
  displayName: 'Run tests'
  continueOnError: true

- script: |
    crossbridge analyze logs \
      --log-file test-output.log \
      --test-name $(Build.DefinitionName) \
      --framework pytest \
      --format json \
      --fail-on product > analysis.json
  displayName: 'Analyze failures'
  condition: failed()

- task: PublishBuildArtifacts@1
  inputs:
    pathToPublish: 'analysis.json'
    artifactName: 'failure-analysis'
  condition: always()
```

## Command Reference

### Analyze Single Log File

```bash
crossbridge analyze logs \
  --log-file test-output.log \
  --test-name test_login \
  --framework pytest \
  --workspace . \
  --format json \
  --fail-on product
```

**Options:**
- `--log-file`: Path to test log file (required)
- `--test-name`: Name of the test (required)
- `--framework`: Test framework (selenium/pytest/robot/playwright/generic)
- `--workspace`: Workspace root directory (default: current directory)
- `--format`: Output format (json/text/summary)
- `--enable-ai`: Enable AI enhancement (optional)
- `--fail-on`: Exit with error code if failure type matches (product/automation/all/none)

### Analyze Directory of Logs

```bash
crossbridge analyze directory \
  --log-dir ./test-output \
  --pattern "*.log" \
  --framework pytest \
  --output results.json \
  --fail-on product
```

**Options:**
- `--log-dir`: Directory containing test logs (required)
- `--pattern`: File pattern to match (default: *.log)
- `--framework`: Test framework
- `--workspace`: Workspace root directory
- `--output`: Output file for detailed results (JSON format)
- `--fail-on`: Exit with error code if any failure type matches

## Failure Types

The engine classifies failures into these categories:

| Failure Type | Description | CI Action |
|-------------|-------------|-----------|
| `PRODUCT_DEFECT` | Application bug | **Fail build** |
| `AUTOMATION_DEFECT` | Test code issue | Warning only |
| `ENVIRONMENT_ISSUE` | Infrastructure/network | Warning only |
| `CONFIGURATION_ISSUE` | Config problem | Warning only |
| `UNKNOWN` | Unable to classify | Configurable |

## Output Formats

### JSON Format

```json
{
  "test_name": "test_login",
  "status": "FAILED",
  "classification": {
    "failure_type": "PRODUCT_DEFECT",
    "confidence": 0.88,
    "reason": "Assertion failed - expected 'Welcome' but got 'Error'",
    "evidence": [
      "AssertionError: assert 'Welcome' == 'Error'",
      "Expected: Welcome",
      "Actual: Error"
    ],
    "code_reference": {
      "file": "tests/test_login.py",
      "line": 42,
      "snippet": ">>> 42 | assert welcome_msg == 'Welcome'",
      "function": "test_login_success"
    },
    "rule_matched": "assertion_failure",
    "ai_enhanced": false
  },
  "signals": [
    {
      "signal_type": "assertion",
      "message": "AssertionError: assert 'Welcome' == 'Error'",
      "confidence": 0.95
    }
  ],
  "framework": "pytest"
}
```

### Text Format

```
============================================================
TEST: test_login
============================================================
Failure Type: PRODUCT_DEFECT
Confidence: 0.88
Reason: Assertion failed - expected 'Welcome' but got 'Error'

Evidence:
  1. AssertionError: assert 'Welcome' == 'Error'...
  2. Expected: Welcome...
  3. Actual: Error...

Code Reference:
  File: tests/test_login.py
  Line: 42
  Function: test_login_success

Code Snippet:
    40 | def test_login_success(client):
    41 |     response = client.login('user', 'pass')
>>> 42 |     assert response.message == 'Welcome'
    43 |     assert response.status == 200
============================================================
```

### Summary Format

```
test_login: PRODUCT_DEFECT (confidence: 0.88)
```

## Advanced Use Cases

### 1. Fail Only on Product Defects

```bash
# Run tests and only fail CI for product bugs
pytest tests/ --log-file=output.log || true
crossbridge analyze logs \
  --log-file output.log \
  --test-name $TEST_NAME \
  --fail-on product
```

**Result**: CI passes for automation/environment issues, fails only for product defects.

### 2. Batch Analysis with Reporting

```bash
# Analyze all test logs and generate report
crossbridge analyze directory \
  --log-dir ./test-results \
  --pattern "test_*.log" \
  --output analysis-report.json

# Use jq to extract summary
cat analysis-report.json | jq '.summary'
```

### 3. Automated PR Comments

```bash
# Analyze and format for PR comment
ANALYSIS=$(crossbridge analyze logs \
  --log-file test.log \
  --test-name test_api \
  --format json)

# Extract key details
FAILURE_TYPE=$(echo $ANALYSIS | jq -r '.classification.failure_type')
CONFIDENCE=$(echo $ANALYSIS | jq -r '.classification.confidence')
REASON=$(echo $ANALYSIS | jq -r '.classification.reason')

# Post to PR (using GitHub CLI)
gh pr comment $PR_NUMBER --body "**Failure**: $FAILURE_TYPE (${CONFIDENCE}% confidence)\n$REASON"
```

### 4. Custom Failure Routing

```bash
# Different actions based on failure type
RESULT=$(crossbridge analyze logs --log-file test.log --format json)
FAILURE_TYPE=$(echo $RESULT | jq -r '.classification.failure_type')

case $FAILURE_TYPE in
  "PRODUCT_DEFECT")
    echo "Product bug detected - notifying dev team"
    slack-notify --channel dev --message "Product bug in $TEST_NAME"
    exit 1
    ;;
  "AUTOMATION_DEFECT")
    echo "Test code issue - notifying QA team"
    slack-notify --channel qa --message "Test issue in $TEST_NAME"
    exit 0
    ;;
  "ENVIRONMENT_ISSUE")
    echo "Environment issue - retrying in 5 minutes"
    sleep 300
    retry-test
    ;;
esac
```

### 5. Historical Tracking

```bash
# Store analysis results in database
crossbridge analyze directory \
  --log-dir ./test-results \
  --output analysis.json

# Upload to data warehouse
cat analysis.json | \
  jq '.results[] | {test: .test_name, type: .classification.failure_type, timestamp: now}' | \
  psql -d metrics -c "COPY failures FROM STDIN WITH (FORMAT json)"
```

## Integration Patterns

### Pattern 1: Post-Test Analysis (Recommended)

```yaml
- run: pytest tests/ || true
- run: crossbridge analyze logs --fail-on product
- if: failure()
  run: notify-team
```

**Benefits:**
- Tests always run to completion
- Smart failure classification
- Only fails CI for real product bugs

### Pattern 2: Real-Time Streaming

```bash
# Stream test output to analyzer
pytest tests/ 2>&1 | tee test-output.log
crossbridge analyze logs --log-file test-output.log
```

### Pattern 3: Multi-Framework Analysis

```bash
# Analyze different frameworks separately
crossbridge analyze logs --log-file selenium.log --framework selenium
crossbridge analyze logs --log-file robot.log --framework robot
crossbridge analyze logs --log-file api.log --framework pytest
```

## Best Practices

### 1. Use `--fail-on product` for PR checks

```yaml
- run: crossbridge analyze logs --fail-on product
```

This ensures:
- PRs don't get blocked by flaky tests
- Automation issues can be fixed separately
- Only real product bugs block merges

### 2. Store analysis results as artifacts

```yaml
- uses: actions/upload-artifact@v3
  with:
    name: failure-analysis
    path: |
      test-output.log
      analysis.json
```

### 3. Add PR comments for transparency

Show developers:
- What failed
- Why it failed
- Exact code location
- Suggested fix (if AI-enhanced)

### 4. Track trends over time

- Store analysis results in a database
- Build dashboards (Grafana, Tableau)
- Identify patterns (flaky tests, recurring issues)

### 5. Customize rules for your project

```python
from core.execution.intelligence.classifier import ClassificationRule, FailureType

# Add custom rule
rule = ClassificationRule(
    name="custom_database_timeout",
    conditions=["database", "timeout", "connection pool"],
    failure_type=FailureType.ENVIRONMENT_ISSUE,
    confidence=0.90,
    priority=95
)

classifier.add_rule(rule)
```

## Troubleshooting

### Issue: "No log files found"

**Solution**: Ensure log file path is correct and file exists.

```bash
# Check file exists
ls -la test-output.log

# Try with absolute path
crossbridge analyze logs --log-file $(pwd)/test-output.log
```

### Issue: "Unable to classify failure"

**Causes:**
- Log format not recognized
- Insufficient error details in logs

**Solution:**
1. Use `--framework generic` for unknown formats
2. Increase log verbosity in tests
3. Add custom adapter for your framework

### Issue: "Code reference not resolved"

**Causes:**
- Stacktrace doesn't contain file paths
- Files not in workspace

**Solution:**
```bash
# Specify correct workspace root
crossbridge analyze logs \
  --workspace /path/to/project/root \
  --log-file test.log
```

## Performance

- **Parsing**: ~100ms per log file
- **Classification**: ~50ms per failure
- **Code resolution**: ~20ms per stacktrace
- **AI enhancement**: ~500ms per failure (if enabled)

**Recommended**: Use batch analysis for >10 log files.

## Security

- Logs are processed locally (not sent to external servers)
- AI enhancement is optional and configurable
- No sensitive data leaves your infrastructure
- Code snippets are extracted from local workspace only

## Next Steps

- [ ] Set up GitHub Actions workflow
- [ ] Configure failure routing rules
- [ ] Add PR comment automation
- [ ] Set up historical tracking
- [ ] Customize classification rules
- [ ] Enable AI enhancement (optional)

## Support

For issues or questions:
- GitHub: https://github.com/crossstack-ai/crossbridge/issues
- Docs: https://docs.crossbridge.dev
- Email: support@crossbridge.dev
