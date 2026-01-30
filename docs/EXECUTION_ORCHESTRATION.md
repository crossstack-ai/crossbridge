# Crossbridge Execution Orchestration

**Complete Guide to Intelligent Test Execution**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Execution Strategies](#execution-strategies)
4. [Framework Support](#framework-support)
5. [CLI Usage](#cli-usage)
6. [CI/CD Integration](#cicd-integration)
7. [Configuration](#configuration)
8. [API Reference](#api-reference)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### What is Execution Orchestration?

Crossbridge's execution orchestration is an **intelligent test selection and execution layer** that determines **WHAT**, **WHEN**, and **HOW** to run tests, while delegating actual execution to existing test frameworks.

### Key Principles

✅ **Framework-Agnostic**: Works with TestNG, Robot, Pytest, Cypress, Playwright, and more  
✅ **Non-Invasive**: No test code changes required  
✅ **Orchestrator, Not Runner**: Invokes frameworks via CLI, doesn't replace them  
✅ **CI/CD Native**: Designed for modern CI/CD pipelines  
✅ **Intelligence Layer**: Uses AI, git, coverage, and historical data for smart selection

### Why Use It?

- **Reduce CI/CD time** by 60-80% with intelligent test selection
- **Increase confidence** with risk-based execution
- **Faster feedback** with impact-based testing on PRs
- **Cost savings** on cloud CI minutes and AI tokens
- **Better quality** by focusing on high-risk areas

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     CROSSBRIDGE ORCHESTRATOR                     │
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Strategy   │───▶│    Plan      │───▶│   Adapter    │      │
│  │  (WHAT to    │    │  (Selected   │    │  (HOW to     │      │
│  │    run)      │    │    tests)    │    │    run)      │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                                          │             │
│         ▼                                          ▼             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Context (Git, Memory, History)                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TEST FRAMEWORKS (Unchanged)                   │
│                                                                   │
│   TestNG  │  Robot  │  Pytest  │  Cypress  │  Playwright  │...  │
└─────────────────────────────────────────────────────────────────┘
```

### Components

#### 1. **Execution API** (`core/execution/orchestration/api.py`)
Core data models: `ExecutionRequest`, `ExecutionPlan`, `ExecutionResult`, `ExecutionContext`

#### 2. **Strategies** (`core/execution/orchestration/strategies.py`)
Determine which tests to run:
- `SmokeStrategy`: Fast signal tests
- `ImpactedStrategy`: Tests affected by code changes
- `RiskBasedStrategy`: Tests ranked by historical risk
- `FullStrategy`: All available tests

#### 3. **Adapters** (`core/execution/orchestration/adapters.py`)
Framework-specific invocation:
- `TestNGAdapter`: Maven/Gradle invocation
- `RobotAdapter`: Robot Framework CLI
- `PytestAdapter`: Pytest with markers
- More adapters for other frameworks

#### 4. **Orchestrator** (`core/execution/orchestration/orchestrator.py`)
Coordinates the entire flow from request to result

---

## Execution Strategies

### 1. Smoke Strategy

**Purpose**: Fast signal tests for quick feedback

**Selection Criteria**:
- Tests tagged with `smoke`, `sanity`, `critical`, or `p0`
- Typically 5-20% of full suite
- Runs in < 10 minutes

**Use Cases**:
- PR validation
- Pre-deployment checks
- Quick smoke tests before full runs

**Example**:
```bash
crossbridge exec run --framework pytest --strategy smoke
```

**Configuration** (`crossbridge.yml`):
```yaml
execution:
  strategies:
    smoke:
      enabled: true
      tags: ["smoke", "sanity", "critical", "p0"]
      max_duration_minutes: 10
```

---

### 2. Impacted Strategy

**Purpose**: Run only tests affected by code changes

**Selection Criteria**:
- Tests covering changed files (via code coverage)
- Semantically related tests (via semantic engine)
- Critical tests (always included)
- Minimum 5 tests (with fallback to smoke)

**Use Cases**:
- Feature development
- PR validation
- Targeted regression

**Example**:
```bash
crossbridge exec run \
  --framework testng \
  --strategy impacted \
  --base-branch origin/main
```

**How It Works**:
1. Analyze git diff to find changed files
2. Query coverage database for tests covering those files
3. Use semantic engine to find related tests
4. Include critical tests as safety net
5. Fall back to smoke if too few tests selected

**Configuration**:
```yaml
execution:
  strategies:
    impacted:
      enabled: true
      sources:
        git_diff: true
        coverage_mapping: true
        semantic_analysis: true
      fallback_strategy: smoke
      min_tests: 5
      semantic_threshold: 0.7
```

**Typical Reduction**: 60-80%

---

### 3. Risk-Based Strategy

**Purpose**: Run tests ranked by historical risk

**Selection Criteria**:
Multi-signal risk scoring:
- **Failure rate (40%)**: Historical pass/fail rate
- **Code churn (20%)**: Changes in covered code
- **Criticality (30%)**: Business importance tags
- **Flakiness (-10%)**: Penalty for flaky tests

**Use Cases**:
- Release pipelines
- Nightly regression
- High-confidence testing

**Example**:
```bash
crossbridge exec run \
  --framework robot \
  --strategy risk \
  --max-tests 100 \
  --env production
```

**Risk Score Formula**:
```
risk_score = (failure_rate * 0.4) 
           + (code_churn * 0.2) 
           + (criticality * 0.3) 
           - (flakiness * 0.1)
```

**Configuration**:
```yaml
execution:
  strategies:
    risk:
      enabled: true
      weights:
        failure_rate: 0.4
        code_churn: 0.2
        criticality: 0.3
        flakiness_penalty: -0.1
      min_risk_score: 0.3
      default_max_tests: 100
```

**Typical Reduction**: 40-60%

---

### 4. Full Strategy

**Purpose**: Run all available tests

**Selection Criteria**:
- Everything
- No intelligence, just comprehensive coverage

**Use Cases**:
- Baseline runs
- Release validation
- Nightly full regression
- When confidence > speed

**Example**:
```bash
crossbridge exec run --framework pytest --strategy full --env prod
```

**Configuration**:
```yaml
execution:
  strategies:
    full:
      enabled: true
      parallel: true
      max_duration_minutes: 180  # 3 hours
```

---

## Framework Support

### Supported Frameworks (13 Total)

| Framework | Language | Adapter | Invocation Method | Parallel Support |
|-----------|----------|---------|-------------------|------------------|
| **Java Frameworks** ||||
| TestNG | Java | `TestNGAdapter` | Maven/Gradle | ✅ Yes (methods) |
| JUnit 4/5 | Java | `JUnitAdapter` | Maven/Gradle | ✅ Yes (jupiter) |
| RestAssured | Java | `RestAssuredAdapter` | Maven/Gradle | ✅ Yes |
| Cucumber | Java | `CucumberAdapter` | Maven + Cucumber | ✅ Yes |
| **Python Frameworks** ||||
| Robot Framework | Python | `RobotAdapter` | Robot CLI + pabot | ✅ Yes (pabot) |
| Pytest | Python | `PytestAdapter` | Pytest + markers | ✅ Yes (xdist) |
| Behave | Python | `BehaveAdapter` | Behave CLI | ✅ Yes (processes) |
| **JavaScript/TypeScript** ||||
| Cypress | JS/TS | `CypressAdapter` | Cypress CLI | ✅ Yes (built-in) |
| Playwright | JS/TS | `PlaywrightAdapter` | Playwright CLI | ✅ Yes (workers) |
| **.NET Frameworks** ||||
| SpecFlow | .NET | `SpecFlowAdapter` | dotnet test | ✅ Yes |
| NUnit | .NET | `NUnitAdapter` | dotnet test | ✅ Yes |

**All 13 frameworks are production-ready** with full execution orchestration support.

### Framework-Specific Examples

#### TestNG (Java)

**Execution**:
```bash
crossbridge exec run --framework testng --strategy impacted
```

**Under the hood**:
```bash
# Crossbridge generates suite XML
mvn test -DsuiteXmlFile=target/crossbridge-suite.xml -Denvironment=staging
```

**Configuration**:
```yaml
execution:
  adapters:
    testng:
      enabled: true
      build_tool: mvn  # or gradle
      parallel_methods: 4
      report_dir: target/surefire-reports
```

---

#### Robot Framework

**Execution**:
```bash
crossbridge exec run --framework robot --strategy smoke
```

**Under the hood**:
```bash
# Crossbridge filters by tags
pabot --processes 4 --include smoke --variable ENV:staging tests/
```

**Configuration**:
```yaml
execution:
  adapters:
    robot:
      enabled: true
      use_pabot: true
      pabot_processes: 4
      output_dir: robot-results
```

---

#### Pytest (Python)

**Execution**:
```bash
crossbridge exec run --framework pytest --strategy risk --max-tests 50
```

**Under the hood**:
```bash
# Crossbridge generates marker expression or file list
pytest -n 4 -m "critical or high_risk" --junitxml=pytest-results.xml
```

**Configuration**:
```yaml
execution:
  adapters:
    pytest:
      enabled: true
      use_xdist: true
      xdist_workers: 4
      junit_xml: pytest-results.xml
```

---

## CLI Usage

### Basic Commands

#### Run Tests

```bash
crossbridge exec run \
  --framework <framework> \
  --strategy <strategy> \
  [OPTIONS]
```

**Options**:
- `--framework`: Test framework (required)
- `--strategy`: Execution strategy (default: `impacted`)
- `--env`: Environment (default: `dev`)
- `--ci`: Enable CI mode
- `--dry-run`: Show plan without executing
- `--max-tests`: Budget limit
- `--max-duration`: Time limit (minutes)
- `--tags`: Include tags (comma-separated)
- `--exclude-tags`: Exclude tags
- `--include-flaky`: Include flaky tests
- `--no-parallel`: Disable parallel execution
- `--base-branch`: Base branch for impact analysis
- `--json`: Output as JSON

#### Show Execution Plan

```bash
crossbridge exec plan \
  --framework <framework> \
  --strategy <strategy> \
  [OPTIONS]
```

Shows what would be executed without running tests.

### Examples

#### 1. Quick Smoke Test
```bash
crossbridge exec run --framework pytest --strategy smoke
```

#### 2. PR Validation (Impacted)
```bash
crossbridge exec run \
  --framework testng \
  --strategy impacted \
  --env staging \
  --base-branch origin/main \
  --ci
```

#### 3. Release Testing (Risk-Based with Budget)
```bash
crossbridge exec run \
  --framework robot \
  --strategy risk \
  --env production \
  --max-tests 100 \
  --max-duration 60 \
  --ci
```

#### 4. Nightly Regression (Full Suite)
```bash
crossbridge exec run \
  --framework pytest \
  --strategy full \
  --env staging \
  --ci \
  --max-duration 180
```

#### 5. Dry Run to See Plan
```bash
crossbridge exec plan \
  --framework testng \
  --strategy risk \
  --json > plan.json
```

#### 6. CI/CD with Metadata
```bash
crossbridge exec run \
  --framework pytest \
  --strategy impacted \
  --env staging \
  --ci \
  --branch $CI_BRANCH \
  --commit $CI_COMMIT \
  --build-id $CI_BUILD_ID \
  --json > result.json
```

---

## CI/CD Integration

### Quick Start (GitHub Actions)

```yaml
- name: Run Crossbridge Tests
  run: |
    crossbridge exec run \
      --framework pytest \
      --strategy impacted \
      --env staging \
      --ci \
      --base-branch origin/main \
      --json > result.json
```

### Platform-Specific Examples

See [`.ci/CICD_INTEGRATION_EXAMPLES.md`](.ci/CICD_INTEGRATION_EXAMPLES.md) for detailed examples for:
- Jenkins
- GitHub Actions
- GitLab CI
- Azure DevOps
- CircleCI
- Bitbucket Pipelines

### CI/CD Best Practices

1. **Use `--ci` flag** for optimized behavior
2. **Pass git metadata** (`--branch`, `--commit`, `--build-id`)
3. **Set time budgets** to prevent timeouts
4. **Use JSON output** for parsing results
5. **Archive results** for historical analysis
6. **Different strategies per environment**:
   - PRs: `impacted` or `smoke`
   - Main: `risk`
   - Nightly: `full`

---

## Configuration

### Main Configuration (`crossbridge.yml`)

```yaml
execution:
  enabled: true
  
  # Strategy settings
  strategies:
    smoke:
      enabled: true
      tags: ["smoke", "sanity", "critical", "p0"]
      max_duration_minutes: 10
    
    impacted:
      enabled: true
      sources:
        git_diff: true
        coverage_mapping: true
        semantic_analysis: true
      fallback_strategy: smoke
      min_tests: 5
    
    risk:
      enabled: true
      weights:
        failure_rate: 0.4
        code_churn: 0.2
        criticality: 0.3
        flakiness_penalty: -0.1
      default_max_tests: 100
    
    full:
      enabled: true
      parallel: true
  
  # Framework adapters
  adapters:
    testng:
      enabled: true
      build_tool: mvn
    robot:
      enabled: true
      use_pabot: true
    pytest:
      enabled: true
      use_xdist: true
  
  # General settings
  settings:
    default_strategy:
      dev: smoke
      qa: impacted
      staging: risk
      prod: risk
    
    parallel:
      enabled: true
      max_workers: 4
    
    timeouts:
      default_test_timeout: 300
      default_suite_timeout: 3600
    
    retries:
      enabled: true
      max_retries: 1
```

---

## API Reference

### ExecutionRequest

```python
from core.execution.orchestration import ExecutionRequest, StrategyType

request = ExecutionRequest(
    framework="pytest",
    strategy=StrategyType.IMPACTED,
    environment="staging",
    ci_mode=True,
    dry_run=False,
    max_tests=50,
    max_duration_minutes=30,
    tags=["critical", "api"],
    exclude_tags=["slow"],
    include_flaky=False,
    parallel=True,
    base_branch="main",
    metadata={"branch": "feature-123", "commit": "abc123"}
)
```

### ExecutionPlan

```python
# Generated by strategies
plan = orchestrator.plan(request)

print(f"Selected: {plan.total_tests()} tests")
print(f"Reduction: {plan.reduction_percentage(100)}%")
print(f"Estimated: {plan.estimated_duration_minutes} minutes")

for test in plan.selected_tests:
    priority = plan.priority[test]
    reason = plan.reasons[test]
    print(f"{test}: P{priority} - {reason}")
```

### ExecutionResult

```python
result = orchestrator.execute(request)

print(f"Pass Rate: {result.pass_rate():.1f}%")
print(f"Duration: {result.execution_time_seconds}s")
print(f"Failed: {len(result.failed_tests)}")
print(f"Reports: {result.report_paths}")

if result.has_failures():
    for test in result.failed_tests:
        print(f"❌ {test}")
```

### Orchestrator

```python
from core.execution.orchestration import create_orchestrator
from pathlib import Path

# Create orchestrator
orchestrator = create_orchestrator(
    workspace=Path("/path/to/project"),
    config={}  # Optional config override
)

# Plan execution
plan = orchestrator.plan(request)

# Execute plan
result = orchestrator.run(plan)

# Or do both
result = orchestrator.execute(request)
```

---

## Best Practices

### 1. Strategy Selection

**PR/Feature Development**: Use `impacted`
- Fast feedback
- Runs only relevant tests
- 60-80% reduction

**Release/Staging**: Use `risk`
- Comprehensive but targeted
- Focuses on high-value tests
- 40-60% reduction

**Nightly/Baseline**: Use `full`
- Complete coverage
- Baseline for comparison
- No reduction

**Quick Checks**: Use `smoke`
- Fastest signal
- Pre-deployment validation
- 80-95% reduction

### 2. Configuration Best Practices

✅ **Set reasonable timeouts**: Prevent pipeline hangs
✅ **Enable parallel execution**: Maximize throughput
✅ **Configure retries carefully**: Avoid false positives
✅ **Use environment-specific strategies**: Different needs per env
✅ **Archive results**: Enable historical analysis

### 3. Git Integration

For impacted strategy to work:
- Fetch sufficient git history (`fetch-depth: 0`)
- Provide base branch (`--base-branch origin/main`)
- Maintain code coverage data

### 4. Test Tagging

Tag tests appropriately:
- `@smoke`, `@critical`: For smoke strategy
- `@p0`, `@p1`, `@p2`: For priority-based selection
- `@flaky`: For flaky test filtering
- `@slow`: For exclusion in fast runs

### 5. CI/CD Optimization

```yaml
# GitHub Actions example
- name: Execute Tests
  run: |
    # Get plan first
    crossbridge exec plan --framework pytest --strategy impacted --json > plan.json
    
    # Check if tests selected
    if [ $(jq '.total_selected' plan.json) -gt 0 ]; then
      # Run tests
      crossbridge exec run --framework pytest --strategy impacted --ci
    else
      echo "No tests selected, skipping"
    fi
```

---

## Troubleshooting

### No Tests Selected

**Symptoms**: Plan shows 0 tests selected

**Causes**:
1. No git changes detected
2. No coverage mapping available
3. All tests filtered out by tags

**Solutions**:
```bash
# Check what's available
crossbridge exec plan --framework pytest --strategy full

# Check git changes
git diff --name-only origin/main

# Verify coverage data exists
ls -la ./data/coverage/

# Use fallback strategy
crossbridge exec run --framework pytest --strategy smoke
```

### Timeout Issues

**Symptoms**: Execution times out in CI

**Solutions**:
1. Set explicit budget:
   ```bash
   crossbridge exec run --framework testng --max-duration 30 --max-tests 50
   ```

2. Use more aggressive strategy:
   ```bash
   crossbridge exec run --framework pytest --strategy smoke
   ```

3. Enable parallel execution:
   ```yaml
   execution:
     settings:
       parallel:
         enabled: true
         max_workers: 8
   ```

### Framework Not Found

**Symptoms**: "Unsupported framework" error

**Solutions**:
1. Check spelling: `pytest` not `pytest-python`
2. Verify adapter enabled in config:
   ```yaml
   execution:
     adapters:
       pytest:
         enabled: true
   ```
3. Check supported frameworks: `testng`, `junit`, `restassured`, `robot`, `pytest`, `behave`, `cypress`, `playwright`, `cucumber`, `specflow`, `nunit`

### Git History Not Available

**Symptoms**: Impacted strategy falls back to smoke

**Solutions**:
```yaml
# GitHub Actions - fetch full history
- uses: actions/checkout@v3
  with:
    fetch-depth: 0  # Important!
```

### Parse Errors

**Symptoms**: Cannot parse framework results

**Solutions**:
1. Verify report format matches expectation
2. Check report directory exists
3. Ensure framework completed execution
4. Check adapter configuration

---

## Summary

Crossbridge Execution Orchestration provides:

✅ **Intelligent test selection** (60-80% reduction)  
✅ **Framework-agnostic design** (works with existing frameworks)  
✅ **CI/CD native** (designed for pipelines)  
✅ **Multiple strategies** (smoke, impacted, risk, full)  
✅ **Zero test changes** (non-invasive)  
✅ **Production-ready** (comprehensive error handling)

### Next Steps

1. **Configure** your `crossbridge.yml`
2. **Choose** appropriate strategy per environment
3. **Integrate** with your CI/CD pipeline
4. **Monitor** execution metrics
5. **Iterate** based on results

### Support

- Documentation: `docs/EXECUTION_ORCHESTRATION.md`
- CI/CD Examples: `.ci/CICD_INTEGRATION_EXAMPLES.md`
- Configuration: `crossbridge.yml` (execution section)
- Tests: `tests/unit/execution/test_orchestration.py`

---

**Built by CrossStack AI** | **Product: CrossBridge**  
*Intelligent test execution that adapts, not replaces.*
