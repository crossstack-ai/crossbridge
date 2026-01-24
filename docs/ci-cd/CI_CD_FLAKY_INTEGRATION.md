# CI/CD Integration for Flaky Test Detection

This guide shows how to integrate CrossBridge flaky test detection into your CI/CD pipeline.

## Table of Contents

- [GitHub Actions](#github-actions)
- [GitLab CI](#gitlab-ci)
- [Jenkins](#jenkins)
- [Azure DevOps](#azure-devops)
- [CircleCI](#circleci)
- [Database Setup](#database-setup)
- [Grafana Setup](#grafana-setup)

---

## Prerequisites

### 1. PostgreSQL Database

Flaky detection requires a PostgreSQL database to store test execution history and detection results.

```bash
# Set environment variable
export CROSSBRIDGE_DB_URL="postgresql://user:password@host:5432/crossbridge"
```

### 2. Create Database Tables

```bash
# Initialize database schema
python -c "from core.flaky_detection.persistence import FlakyDetectionRepository; FlakyDetectionRepository('$CROSSBRIDGE_DB_URL').create_tables()"
```

---

## GitHub Actions

### Basic Integration

```yaml
name: Test Suite with Flaky Detection

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: crossbridge
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install crossbridge
      
      - name: Run tests and capture results
        id: tests
        run: |
          pytest --json-report --json-report-file=test_results.json
        continue-on-error: true
      
      - name: Store test execution in database
        env:
          CROSSBRIDGE_DB_URL: postgresql://postgres:postgres@localhost:5432/crossbridge
        run: |
          python scripts/store_test_results.py test_results.json
      
      - name: Run flaky detection
        env:
          CROSSBRIDGE_DB_URL: postgresql://postgres:postgres@localhost:5432/crossbridge
        run: |
          crossbridge flaky detect --days 30 --output flaky_report.json
      
      - name: Upload flaky test report
        uses: actions/upload-artifact@v3
        with:
          name: flaky-test-report
          path: flaky_report.json
      
      - name: Comment PR with flaky tests
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('flaky_report.json', 'utf8'));
            
            if (report.summary.flaky_tests > 0) {
              const body = `## ⚠️ Flaky Tests Detected\n\n` +
                `Found ${report.summary.flaky_tests} flaky tests:\n\n` +
                report.flaky_tests.map(t => 
                  `- **${t.test_name}** (${t.severity}) - ${t.flaky_score.toFixed(3)}`
                ).join('\n');
              
              github.rest.issues.createComment({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                body: body
              });
            }
```

### Advanced: Fail on Critical Flaky Tests

```yaml
      - name: Check for critical flaky tests
        env:
          CROSSBRIDGE_DB_URL: postgresql://postgres:postgres@localhost:5432/crossbridge
        run: |
          python -c "
          import json, sys
          with open('flaky_report.json') as f:
              report = json.load(f)
          critical = sum(1 for t in report.get('flaky_tests', []) if t['severity'] == 'critical')
          if critical > 0:
              print(f'❌ Found {critical} critical flaky tests!')
              sys.exit(1)
          "
```

---

## GitLab CI

```yaml
stages:
  - test
  - analyze
  - report

variables:
  POSTGRES_DB: crossbridge
  POSTGRES_USER: crossbridge
  POSTGRES_PASSWORD: crossbridge
  CROSSBRIDGE_DB_URL: postgresql://crossbridge:crossbridge@postgres:5432/crossbridge

services:
  - postgres:15

test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pytest --json-report --json-report-file=test_results.json
    - python scripts/store_test_results.py test_results.json
  artifacts:
    paths:
      - test_results.json
    when: always

flaky_detection:
  stage: analyze
  image: python:3.11
  dependencies:
    - test
  script:
    - pip install crossbridge
    - crossbridge flaky detect --days 30 --output flaky_report.json --verbose
  artifacts:
    reports:
      junit: flaky_report.json
    paths:
      - flaky_report.json
  allow_failure: true

flaky_report:
  stage: report
  image: python:3.11
  dependencies:
    - flaky_detection
  script:
    - |
      if [ -f flaky_report.json ]; then
        echo "📊 Flaky Test Report"
        crossbridge flaky list --severity critical
      fi
  only:
    - merge_requests
```

---

## Jenkins

```groovy
pipeline {
    agent any
    
    environment {
        CROSSBRIDGE_DB_URL = credentials('crossbridge-db-url')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'pip install crossbridge'
            }
        }
        
        stage('Test') {
            steps {
                sh 'pytest --json-report --json-report-file=test_results.json'
                sh 'python scripts/store_test_results.py test_results.json'
            }
        }
        
        stage('Flaky Detection') {
            steps {
                script {
                    def flakyReport = sh(
                        script: 'crossbridge flaky detect --days 30 --output flaky_report.json',
                        returnStatus: true
                    )
                    
                    archiveArtifacts artifacts: 'flaky_report.json', allowEmptyArchive: true
                    
                    // Parse and display results
                    def report = readJSON file: 'flaky_report.json'
                    if (report.summary.flaky_tests > 0) {
                        echo "⚠️ Found ${report.summary.flaky_tests} flaky tests"
                        
                        def criticalTests = report.flaky_tests.findAll { it.severity == 'critical' }
                        if (criticalTests.size() > 0) {
                            unstable(message: "Found ${criticalTests.size()} critical flaky tests")
                        }
                    }
                }
            }
        }
        
        stage('Report') {
            steps {
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: '.',
                    reportFiles: 'flaky_report.json',
                    reportName: 'Flaky Test Report'
                ])
            }
        }
    }
    
    post {
        always {
            // Send Slack notification for critical flaky tests
            script {
                def report = readJSON file: 'flaky_report.json'
                def criticalCount = report.flaky_tests.count { it.severity == 'critical' }
                
                if (criticalCount > 0) {
                    slackSend(
                        color: 'danger',
                        message: "🔴 ${criticalCount} critical flaky tests detected in ${env.JOB_NAME} #${env.BUILD_NUMBER}"
                    )
                }
            }
        }
    }
}
```

---

## Azure DevOps

```yaml
trigger:
  branches:
    include:
      - main
      - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  CROSSBRIDGE_DB_URL: $(crossbridge-db-connection-string)

stages:
- stage: Test
  jobs:
  - job: RunTests
    steps:
    - task: UsePythonVersion@0
      inputs:
        versionSpec: '3.11'
    
    - script: |
        pip install -r requirements.txt
        pytest --json-report --json-report-file=test_results.json
      displayName: 'Run Tests'
      continueOnError: true
    
    - script: |
        python scripts/store_test_results.py test_results.json
      displayName: 'Store Test Results'
      env:
        CROSSBRIDGE_DB_URL: $(CROSSBRIDGE_DB_URL)

- stage: FlakyDetection
  dependsOn: Test
  jobs:
  - job: DetectFlaky
    steps:
    - script: |
        pip install crossbridge
        crossbridge flaky detect --days 30 --output $(Build.ArtifactStagingDirectory)/flaky_report.json
      displayName: 'Detect Flaky Tests'
      env:
        CROSSBRIDGE_DB_URL: $(CROSSBRIDGE_DB_URL)
    
    - task: PublishBuildArtifacts@1
      inputs:
        pathToPublish: '$(Build.ArtifactStagingDirectory)/flaky_report.json'
        artifactName: 'FlakyTestReport'
    
    - script: |
        crossbridge flaky list --severity critical
      displayName: 'List Critical Flaky Tests'
      env:
        CROSSBRIDGE_DB_URL: $(CROSSBRIDGE_DB_URL)
```

---

## CircleCI

```yaml
version: 2.1

orbs:
  python: circleci/python@2.1.1

executors:
  python-postgres:
    docker:
      - image: cimg/python:3.11
      - image: cimg/postgres:15.0
        environment:
          POSTGRES_DB: crossbridge
          POSTGRES_USER: crossbridge
          POSTGRES_PASSWORD: crossbridge

jobs:
  test:
    executor: python-postgres
    steps:
      - checkout
      
      - run:
          name: Install dependencies
          command: |
            pip install -r requirements.txt
      
      - run:
          name: Wait for Postgres
          command: |
            dockerize -wait tcp://localhost:5432 -timeout 1m
      
      - run:
          name: Run tests
          command: |
            pytest --json-report --json-report-file=test_results.json
      
      - run:
          name: Store test results
          command: |
            python scripts/store_test_results.py test_results.json
          environment:
            CROSSBRIDGE_DB_URL: postgresql://crossbridge:crossbridge@localhost:5432/crossbridge
      
      - store_test_results:
          path: test_results.json
  
  flaky_detection:
    executor: python-postgres
    steps:
      - checkout
      
      - run:
          name: Install CrossBridge
          command: pip install crossbridge
      
      - run:
          name: Detect flaky tests
          command: |
            crossbridge flaky detect --days 30 --output flaky_report.json
          environment:
            CROSSBRIDGE_DB_URL: postgresql://crossbridge:crossbridge@localhost:5432/crossbridge
      
      - run:
          name: Display flaky tests
          command: |
            crossbridge flaky list --severity critical
          environment:
            CROSSBRIDGE_DB_URL: postgresql://crossbridge:crossbridge@localhost:5432/crossbridge
      
      - store_artifacts:
          path: flaky_report.json

workflows:
  test_and_analyze:
    jobs:
      - test
      - flaky_detection:
          requires:
            - test
```

---

## Database Setup

### PostgreSQL Setup (Docker)

```bash
# Start PostgreSQL container
docker run -d \
  --name crossbridge-postgres \
  -e POSTGRES_DB=crossbridge \
  -e POSTGRES_USER=crossbridge \
  -e POSTGRES_PASSWORD=crossbridge \
  -p 5432:5432 \
  postgres:15

# Set environment variable
export CROSSBRIDGE_DB_URL="postgresql://crossbridge:crossbridge@localhost:5432/crossbridge"

# Initialize database schema
python -c "
from core.flaky_detection.persistence import FlakyDetectionRepository
repo = FlakyDetectionRepository('$CROSSBRIDGE_DB_URL')
repo.create_tables()
print('✅ Database tables created')
"
```

### Database Schema

The flaky detection system creates three tables:

1. **test_execution** - Stores all test execution records
   - test_id, test_name, framework, status, duration_ms
   - executed_at, error_type, retry_count
   - git_commit, environment, build_id

2. **flaky_test** - Current flaky test detection results
   - test_id, framework, is_flaky, flaky_score
   - confidence, severity, features
   - primary_indicators, detected_at

3. **flaky_test_history** - Historical detection results for trend analysis
   - test_id, flaky_score, is_flaky, confidence
   - detected_at, model_version

---

## Grafana Setup

### Import Dashboard

1. Copy the dashboard JSON from `grafana/flaky_test_dashboard.json`
2. In Grafana: **Dashboards** → **Import** → Paste JSON
3. Select your PostgreSQL datasource
4. Click **Import**

### Configure PostgreSQL Datasource

```yaml
apiVersion: 1
datasources:
  - name: CrossBridge PostgreSQL
    type: postgres
    url: postgres-host:5432
    database: crossbridge
    user: crossbridge
    secureJsonData:
      password: crossbridge
    jsonData:
      sslmode: disable
      postgresVersion: 1500
      timescaledb: false
```

### Dashboard Features

- **Flaky Test Summary** - Total count of flaky tests
- **Severity Distribution** - Pie chart of flaky tests by severity
- **Trend Analysis** - 30-day trend of flaky test detection
- **Top Flaky Tests** - Table of most problematic tests
- **Framework Breakdown** - Flaky tests grouped by framework
- **Execution Status** - Real-time test pass/fail distribution
- **Confidence Distribution** - Histogram of confidence scores

---

## Storing Test Results

Create a script to parse test results and store in database:

```python
# scripts/store_test_results.py
import json
import sys
import os
from datetime import datetime
from core.flaky_detection.models import TestExecutionRecord, TestFramework, TestStatus
from core.flaky_detection.persistence import FlakyDetectionRepository

def store_pytest_results(results_file: str):
    """Store pytest JSON results in database."""
    
    db_url = os.environ.get('CROSSBRIDGE_DB_URL')
    if not db_url:
        print("❌ CROSSBRIDGE_DB_URL not set")
        sys.exit(1)
    
    repo = FlakyDetectionRepository(db_url)
    
    with open(results_file) as f:
        data = json.load(f)
    
    git_commit = os.environ.get('GITHUB_SHA') or os.environ.get('CI_COMMIT_SHA')
    build_id = os.environ.get('GITHUB_RUN_ID') or os.environ.get('CI_JOB_ID')
    
    records = []
    for test in data.get('tests', []):
        status_map = {
            'passed': TestStatus.PASSED,
            'failed': TestStatus.FAILED,
            'skipped': TestStatus.SKIPPED
        }
        
        record = TestExecutionRecord(
            test_id=test['nodeid'],
            test_name=test['nodeid'],
            framework=TestFramework.PYTEST,
            status=status_map.get(test['outcome'], TestStatus.FAILED),
            duration_ms=int(test['duration'] * 1000),
            executed_at=datetime.now(),
            git_commit=git_commit,
            build_id=build_id,
            error_signature=test.get('call', {}).get('crash', {}).get('message'),
            error_full=test.get('call', {}).get('longrepr')
        )
        records.append(record)
    
    repo.save_executions_batch(records)
    print(f"✅ Stored {len(records)} test execution records")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python store_test_results.py <results_file.json>")
        sys.exit(1)
    
    store_pytest_results(sys.argv[1])
```

---

## Notifications

### Slack Integration

```python
# scripts/notify_flaky_tests.py
import json
import os
import requests

def send_slack_notification(webhook_url: str, report_file: str):
    """Send Slack notification for flaky tests."""
    
    with open(report_file) as f:
        report = json.load(f)
    
    if report['summary']['flaky_tests'] == 0:
        return
    
    critical = sum(1 for t in report['flaky_tests'] if t['severity'] == 'critical')
    high = sum(1 for t in report['flaky_tests'] if t['severity'] == 'high')
    
    message = {
        "text": f"🔬 Flaky Test Detection Results",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔬 Flaky Test Detection"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Flaky:*\n{report['summary']['flaky_tests']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Critical:*\n🔴 {critical}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*High:*\n🟠 {high}"
                    }
                ]
            }
        ]
    }
    
    if critical > 0:
        message["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Critical Flaky Tests:*\n" + "\n".join(
                    f"• {t['test_name']}" 
                    for t in report['flaky_tests'] 
                    if t['severity'] == 'critical'
                )[:10]  # First 10
            }
        })
    
    requests.post(webhook_url, json=message)
    print("✅ Slack notification sent")

if __name__ == '__main__':
    webhook = os.environ.get('SLACK_WEBHOOK_URL')
    if webhook:
        send_slack_notification(webhook, 'flaky_report.json')
```

---

## Best Practices

### 1. Run Flaky Detection Regularly
- Daily scheduled CI jobs
- After every merge to main branch
- Weekly comprehensive analysis

### 2. Set Quality Gates
```bash
# Fail build if critical flaky tests found
crossbridge flaky list --severity critical | grep -c "🔴" && exit 1
```

### 3. Track Trends
- Monitor flaky test count over time
- Set up alerts for increasing flakiness
- Review Grafana dashboards weekly

### 4. Prioritize Fixes
- Fix critical severity first
- Focus on high-failure-rate tests
- Address tests with external test IDs (TestRail/Zephyr)

### 5. Database Maintenance
```bash
# Clean up old execution records (keep last 90 days)
python -c "
from core.flaky_detection.persistence import FlakyDetectionRepository
repo = FlakyDetectionRepository('$CROSSBRIDGE_DB_URL')
deleted = repo.cleanup_old_executions(days_to_keep=90)
print(f'Deleted {deleted} old records')
"
```

---

## Troubleshooting

### Database Connection Issues
```bash
# Test database connection
psql "$CROSSBRIDGE_DB_URL" -c "SELECT 1"
```

### Missing Test Results
```bash
# Verify test executions are being stored
crossbridge flaky detect --days 7 --verbose
```

### Insufficient Training Data
```bash
# Check execution history
psql "$CROSSBRIDGE_DB_URL" -c "
SELECT test_id, COUNT(*) as executions 
FROM test_execution 
WHERE executed_at >= NOW() - INTERVAL '30 days'
GROUP BY test_id 
ORDER BY executions DESC 
LIMIT 10;
"
```

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/crossstack-ai/crossbridge/issues
- Documentation: https://docs.crossstack.ai/crossbridge
- Email: support@crossstack.ai
