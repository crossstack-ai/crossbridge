# CI/CD Integration Examples

Examples for integrating Crossbridge execution orchestration into CI/CD pipelines.

## Table of Contents

1. [Jenkins](#jenkins)
2. [GitHub Actions](#github-actions)
3. [GitLab CI](#gitlab-ci)
4. [Azure DevOps](#azure-devops)
5. [CircleCI](#circleci)
6. [Bitbucket Pipelines](#bitbucket-pipelines)

---

## Jenkins

### Declarative Pipeline

```groovy
pipeline {
    agent any
    
    environment {
        CROSSBRIDGE_ENV = 'staging'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Test Plan') {
            steps {
                script {
                    // Show execution plan
                    sh '''
                        crossbridge exec plan \
                          --framework testng \
                          --strategy impacted \
                          --env ${CROSSBRIDGE_ENV} \
                          --base-branch origin/main \
                          --json > plan.json
                    '''
                    
                    // Parse and display
                    def plan = readJSON file: 'plan.json'
                    echo "Will execute ${plan.total_selected} tests"
                }
            }
        }
        
        stage('Execute Tests') {
            steps {
                sh '''
                    crossbridge exec run \
                      --framework testng \
                      --strategy impacted \
                      --env ${CROSSBRIDGE_ENV} \
                      --ci \
                      --base-branch origin/main \
                      --branch ${GIT_BRANCH} \
                      --commit ${GIT_COMMIT} \
                      --build-id ${BUILD_ID} \
                      --json > result.json
                '''
            }
        }
        
        stage('Report') {
            steps {
                script {
                    def result = readJSON file: 'result.json'
                    
                    echo "Test Results:"
                    echo "  Passed: ${result.passed}"
                    echo "  Failed: ${result.failed}"
                    echo "  Pass Rate: ${result.pass_rate}%"
                    
                    if (result.has_failures) {
                        currentBuild.result = 'UNSTABLE'
                    }
                }
                
                // Publish reports
                publishHTML([
                    reportName: 'Test Report',
                    reportDir: 'target/surefire-reports',
                    reportFiles: '*.html'
                ])
            }
        }
    }
    
    post {
        always {
            // Archive results
            archiveArtifacts artifacts: 'result.json,plan.json', allowEmptyArchive: true
        }
    }
}
```

### Scripted Pipeline (with retry)

```groovy
node {
    stage('Test Execution') {
        retry(2) {
            sh '''
                crossbridge exec run \
                  --framework robot \
                  --strategy risk \
                  --env prod \
                  --ci \
                  --max-tests 100 \
                  --max-duration 30
            '''
        }
    }
}
```

---

## GitHub Actions

### Basic Workflow

```yaml
name: Crossbridge Test Execution

on:
  pull_request:
    branches: [ main, develop ]
  push:
    branches: [ main ]

env:
  PYTHON_VERSION: '3.10'

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history for impact analysis
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install Crossbridge
        run: |
          pip install crossbridge
          crossbridge --version
      
      - name: Generate execution plan
        id: plan
        run: |
          crossbridge exec plan \
            --framework pytest \
            --strategy impacted \
            --env staging \
            --base-branch origin/main \
            --json > plan.json
          
          # Extract metrics
          echo "tests=$(jq -r '.total_selected' plan.json)" >> $GITHUB_OUTPUT
          echo "duration=$(jq -r '.estimated_duration_minutes' plan.json)" >> $GITHUB_OUTPUT
      
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `🚀 **Crossbridge Execution Plan**\n\n` +
                    `Tests to run: ${{ steps.plan.outputs.tests }}\n` +
                    `Estimated time: ${{ steps.plan.outputs.duration }} minutes`
            })
      
      - name: Execute tests
        run: |
          crossbridge exec run \
            --framework pytest \
            --strategy impacted \
            --env staging \
            --ci \
            --base-branch origin/main \
            --branch ${{ github.head_ref || github.ref_name }} \
            --commit ${{ github.sha }} \
            --build-id ${{ github.run_id }} \
            --json > result.json
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: |
            result.json
            plan.json
            pytest-results.xml
      
      - name: Publish test results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: always()
        with:
          files: pytest-results.xml
```

### Multi-strategy workflow

```yaml
name: Multi-Strategy Testing

on:
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM

jobs:
  smoke:
    name: Smoke Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run smoke tests
        run: |
          crossbridge exec run \
            --framework cypress \
            --strategy smoke \
            --env production \
            --ci
  
  risk:
    name: Risk-Based Tests
    runs-on: ubuntu-latest
    needs: smoke
    steps:
      - uses: actions/checkout@v3
      - name: Run risk-based tests
        run: |
          crossbridge exec run \
            --framework playwright \
            --strategy risk \
            --env production \
            --ci \
            --max-tests 50
  
  full:
    name: Full Regression
    runs-on: ubuntu-latest
    needs: risk
    if: github.event_name == 'schedule'
    steps:
      - uses: actions/checkout@v3
      - name: Run full suite
        run: |
          crossbridge exec run \
            --framework testng \
            --strategy full \
            --env production \
            --ci \
            --max-duration 120
```

---

## GitLab CI

### Basic Configuration

```yaml
# .gitlab-ci.yml

stages:
  - plan
  - test
  - report

variables:
  CROSSBRIDGE_ENV: staging
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip

before_script:
  - pip install crossbridge

plan_tests:
  stage: plan
  script:
    - |
      crossbridge exec plan \
        --framework robot \
        --strategy impacted \
        --env $CROSSBRIDGE_ENV \
        --base-branch origin/main \
        --json > plan.json
    - cat plan.json
  artifacts:
    reports:
      dotenv: plan.env
    paths:
      - plan.json

execute_tests:
  stage: test
  script:
    - |
      crossbridge exec run \
        --framework robot \
        --strategy impacted \
        --env $CROSSBRIDGE_ENV \
        --ci \
        --base-branch origin/main \
        --branch $CI_COMMIT_REF_NAME \
        --commit $CI_COMMIT_SHA \
        --build-id $CI_PIPELINE_ID \
        --json > result.json
  artifacts:
    when: always
    reports:
      junit: robot-results/*.xml
    paths:
      - result.json
      - robot-results/
  dependencies:
    - plan_tests

report_results:
  stage: report
  script:
    - |
      pass_rate=$(jq -r '.pass_rate' result.json)
      echo "Pass Rate: $pass_rate%"
      
      if [ "$pass_rate" -lt "80" ]; then
        echo "⚠️ Pass rate below threshold (80%)"
        exit 1
      fi
  dependencies:
    - execute_tests
```

### Merge Request Pipeline

```yaml
test_mr:
  stage: test
  only:
    - merge_requests
  script:
    - |
      crossbridge exec run \
        --framework pytest \
        --strategy impacted \
        --env dev \
        --ci \
        --base-branch origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME \
        --branch $CI_COMMIT_REF_NAME \
        --commit $CI_COMMIT_SHA \
        --max-duration 15  # Quick feedback for MRs
```

---

## Azure DevOps

### YAML Pipeline

```yaml
# azure-pipelines.yml

trigger:
  branches:
    include:
      - main
      - develop
      - feature/*

pr:
  branches:
    include:
      - main
      - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  pythonVersion: '3.10'
  crossbridgeEnv: 'staging'

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '$(pythonVersion)'
    displayName: 'Use Python $(pythonVersion)'

  - script: |
      pip install crossbridge
      crossbridge --version
    displayName: 'Install Crossbridge'

  - script: |
      crossbridge exec plan \
        --framework testng \
        --strategy impacted \
        --env $(crossbridgeEnv) \
        --base-branch origin/main \
        --json > $(Build.ArtifactStagingDirectory)/plan.json
    displayName: 'Generate execution plan'

  - script: |
      crossbridge exec run \
        --framework testng \
        --strategy impacted \
        --env $(crossbridgeEnv) \
        --ci \
        --base-branch origin/main \
        --branch $(Build.SourceBranchName) \
        --commit $(Build.SourceVersion) \
        --build-id $(Build.BuildId) \
        --json > $(Build.ArtifactStagingDirectory)/result.json
    displayName: 'Execute tests'

  - task: PublishTestResults@2
    inputs:
      testResultsFormat: 'JUnit'
      testResultsFiles: '**/TEST-*.xml'
      mergeTestResults: true
      failTaskOnFailedTests: true
    condition: always()
    displayName: 'Publish test results'

  - task: PublishBuildArtifacts@1
    inputs:
      pathToPublish: '$(Build.ArtifactStagingDirectory)'
      artifactName: 'crossbridge-results'
    condition: always()
    displayName: 'Publish artifacts'
```

---

## CircleCI

### Configuration

```yaml
# .circleci/config.yml

version: 2.1

orbs:
  python: circleci/python@2.1.1

jobs:
  test:
    docker:
      - image: cimg/python:3.10
    
    steps:
      - checkout
      
      - python/install-packages:
          pkg-manager: pip
          pip-dependency-file: requirements.txt
      
      - run:
          name: Install Crossbridge
          command: pip install crossbridge
      
      - run:
          name: Plan execution
          command: |
            crossbridge exec plan \
              --framework pytest \
              --strategy impacted \
              --env staging \
              --base-branch origin/main \
              --json > plan.json
      
      - run:
          name: Execute tests
          command: |
            crossbridge exec run \
              --framework pytest \
              --strategy impacted \
              --env staging \
              --ci \
              --base-branch origin/main \
              --branch $CIRCLE_BRANCH \
              --commit $CIRCLE_SHA1 \
              --build-id $CIRCLE_BUILD_NUM \
              --json > result.json
      
      - store_test_results:
          path: pytest-results.xml
      
      - store_artifacts:
          path: result.json
          destination: crossbridge-results

workflows:
  test-workflow:
    jobs:
      - test:
          filters:
            branches:
              only:
                - main
                - develop
```

---

## Bitbucket Pipelines

### Configuration

```yaml
# bitbucket-pipelines.yml

image: python:3.10

definitions:
  steps:
    - step: &test
        name: Execute Tests
        caches:
          - pip
        script:
          - pip install crossbridge
          - |
            crossbridge exec run \
              --framework robot \
              --strategy impacted \
              --env staging \
              --ci \
              --base-branch origin/main \
              --branch $BITBUCKET_BRANCH \
              --commit $BITBUCKET_COMMIT \
              --build-id $BITBUCKET_BUILD_NUMBER \
              --json > result.json
        artifacts:
          - result.json
          - robot-results/**

pipelines:
  default:
    - step: *test
  
  branches:
    main:
      - step:
          <<: *test
          name: Production Tests
          script:
            - pip install crossbridge
            - |
              crossbridge exec run \
                --framework robot \
                --strategy risk \
                --env production \
                --ci \
                --max-tests 100
  
  pull-requests:
    '**':
      - step:
          <<: *test
          name: PR Tests (Impacted)
```

---

## Common Patterns

### 1. Conditional Execution

```bash
# Only run if there are test changes
if crossbridge exec plan --framework pytest --strategy impacted --json | jq -e '.total_selected > 0'; then
    crossbridge exec run --framework pytest --strategy impacted --ci
else
    echo "No impacted tests, skipping execution"
fi
```

### 2. Parallel Execution

```yaml
# GitHub Actions - matrix strategy
strategy:
  matrix:
    strategy: [smoke, impacted, risk]

steps:
  - name: Execute ${{ matrix.strategy }} tests
    run: |
      crossbridge exec run \
        --framework pytest \
        --strategy ${{ matrix.strategy }} \
        --ci
```

### 3. Environment-specific strategies

```bash
# Different strategies per environment
case "$ENV" in
  dev)
    STRATEGY="smoke"
    ;;
  staging)
    STRATEGY="impacted"
    ;;
  production)
    STRATEGY="risk"
    MAX_TESTS="--max-tests 100"
    ;;
esac

crossbridge exec run \
  --framework testng \
  --strategy $STRATEGY \
  --env $ENV \
  --ci \
  $MAX_TESTS
```

### 4. Retry on failure

```bash
# Retry failed tests with full strategy
if ! crossbridge exec run --framework pytest --strategy impacted --ci; then
    echo "Impacted tests failed, running full suite..."
    crossbridge exec run --framework pytest --strategy full --ci
fi
```

---

## Best Practices

1. **Use `--ci` flag** in CI/CD for optimized logging and behavior
2. **Enable dry-run for PRs** to show execution plan before running
3. **Set time budgets** (`--max-duration`) to prevent pipeline timeouts
4. **Use JSON output** (`--json`) for programmatic result parsing
5. **Pass git metadata** (`--branch`, `--commit`, `--build-id`) for traceability
6. **Cache Crossbridge** installation to speed up pipelines
7. **Use appropriate strategies**:
   - **PRs**: `impacted` or `smoke`
   - **Main branch**: `risk` or `full`
   - **Nightly**: `full`
8. **Archive results** for historical analysis

---

## Troubleshooting

### Issue: No tests selected

```bash
# Check what would be selected
crossbridge exec plan --framework pytest --strategy impacted --base-branch origin/main

# Fall back to smoke if no impacted tests
crossbridge exec run --framework pytest --strategy smoke --ci
```

### Issue: Timeout in CI

```bash
# Set explicit budget
crossbridge exec run \
  --framework testng \
  --strategy risk \
  --max-duration 30 \
  --max-tests 50 \
  --ci
```

### Issue: Git history not available

```yaml
# GitHub Actions - fetch full history
- uses: actions/checkout@v3
  with:
    fetch-depth: 0  # Important for impact analysis
```

---

## Next Steps

1. Customize examples for your CI/CD platform
2. Configure `crossbridge.yml` with execution settings
3. Set up proper authentication/credentials
4. Monitor execution metrics
5. Iterate on strategies based on results
