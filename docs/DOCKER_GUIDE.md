# CrossBridge Docker Guide

**Containerized Execution Orchestration**

Complete guide to running CrossBridge as a Docker container for local development and CI/CD pipelines.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Philosophy](#philosophy)
3. [Docker Image](#docker-image)
4. [Volumes](#volumes)
5. [Environment Variables](#environment-variables)
6. [Usage Examples](#usage-examples)
7. [docker-compose](#docker-compose)
8. [CI/CD Integration](#cicd-integration)
9. [Exit Codes](#exit-codes)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Pull Image

```bash
docker pull crossbridge/crossbridge:1.0.0
```

### 2. Run with docker-compose

```bash
# Copy example environment file
cp .env.docker.example .env

# Edit .env to customize

# Run
docker-compose up
```

### 3. Run Directly

```bash
docker run --rm \
  -v $(pwd)/test-repo:/workspace:ro \
  -v $(pwd)/crossbridge-data/logs:/data/logs \
  -v $(pwd)/crossbridge-data/reports:/data/reports \
  crossbridge/crossbridge:1.0.0 exec run \
  --framework pytest \
  --strategy smoke
```

---

## Philosophy

CrossBridge Docker follows these principles:

### ✅ **DO: Tool Container**
- CrossBridge runs like `terraform` or `kubectl`
- Stateless execution
- Exit after task completion
- Behaves like CLI tool

### ✅ **DO: Externalized State**
- Logs → volume
- Reports → volume
- Cache → volume
- Config → mounted file or env vars

### ✅ **DO: Framework-Agnostic**
- No test frameworks baked in
- No browser binaries
- No language runtimes (except Python for CrossBridge itself)
- Invokes external frameworks via CLI

### ❌ **DON'T: Application Server**
- Not a long-running service
- Not a web server
- Not a persistent daemon

### ❌ **DON'T: Include Everything**
- No Java/Node/browsers in image
- No test code in image
- No framework executables

**Think:** `terraform apply` not `jenkins run`

---

## Docker Image

### Image Structure

```
crossbridge/crossbridge:1.0.0
├── Python 3.11 (slim)
├── CrossBridge CLI
├── Execution orchestration
├── Adapters (11 frameworks)
└── Volume mount points
```

### Image Tags

| Tag | Description | Use Case |
|-----|-------------|----------|
| `1.0.0` | Specific version | Production (locked) |
| `1.0` | Minor version | Production (patch updates) |
| `1` | Major version | Development |
| `latest` | Latest release | Quick testing |

**Recommendation:** Use specific versions (e.g., `1.0.0`) in CI/CD for reproducibility.

### Image Size

- Base image: ~150MB (Python 3.11-slim)
- CrossBridge: ~200MB (with dependencies)
- **Total**: ~350MB

---

## Volumes

### Required Volumes

| Volume | Path | Purpose | Access |
|--------|------|---------|--------|
| **Workspace** | `/workspace` | Test repository | Read-only recommended |
| **Logs** | `/data/logs` | Execution logs | Read-write |
| **Reports** | `/data/reports` | Test reports, artifacts | Read-write |
| **Cache** | `/data/cache` | Git diff, memory cache | Read-write |

### Volume Setup

```bash
# Create host directories
mkdir -p crossbridge-data/{logs,reports,cache}

# Set permissions (if needed)
chmod 777 crossbridge-data/{logs,reports,cache}
```

### Volume Examples

**Local Development:**
```bash
docker run --rm \
  -v $(pwd)/my-tests:/workspace:ro \
  -v $(pwd)/crossbridge-data/logs:/data/logs \
  -v $(pwd)/crossbridge-data/reports:/data/reports \
  -v $(pwd)/crossbridge-data/cache:/data/cache \
  crossbridge/crossbridge:1.0.0 exec run --framework pytest --strategy smoke
```

**Named Volumes:**
```bash
docker run --rm \
  -v $(pwd)/my-tests:/workspace:ro \
  -v crossbridge-logs:/data/logs \
  -v crossbridge-reports:/data/reports \
  -v crossbridge-cache:/data/cache \
  crossbridge/crossbridge:1.0.0 exec run --framework testng --strategy impacted
```

---

## Environment Variables

### Core Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CROSSBRIDGE_HOME` | `/data` | Base directory for volumes |
| `CROSSBRIDGE_LOG_DIR` | `/data/logs` | Log directory |
| `CROSSBRIDGE_REPORT_DIR` | `/data/reports` | Report directory |
| `CROSSBRIDGE_CACHE_DIR` | `/data/cache` | Cache directory |
| `CROSSBRIDGE_WORKSPACE` | `/workspace` | Test repository path |

### Execution Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CROSSBRIDGE_MODE` | `observer` | Execution mode |
| `CROSSBRIDGE_ENV` | `local` | Environment name |
| `CROSSBRIDGE_LOG_LEVEL` | `INFO` | Log level |

### Database Variables

| Variable | Description |
|----------|-------------|
| `CROSSBRIDGE_DB_HOST` | PostgreSQL host |
| `CROSSBRIDGE_DB_PORT` | PostgreSQL port |
| `CROSSBRIDGE_DB_NAME` | Database name |
| `CROSSBRIDGE_DB_USER` | Database user |
| `CROSSBRIDGE_DB_PASSWORD` | Database password |

### Application Tracking

| Variable | Description |
|----------|-------------|
| `PRODUCT_NAME` | Product/application name |
| `APP_VERSION` | Application version |
| `ENVIRONMENT` | Environment (dev, qa, staging, prod) |

### Example

```bash
docker run --rm \
  -e CROSSBRIDGE_LOG_LEVEL=DEBUG \
  -e CROSSBRIDGE_ENV=staging \
  -e PRODUCT_NAME=MyApp \
  -e APP_VERSION=v2.0.0 \
  -v $(pwd)/tests:/workspace:ro \
  crossbridge/crossbridge:1.0.0 exec run --framework pytest --strategy impacted
```

---

## Usage Examples

### 1. Smoke Tests

```bash
docker run --rm \
  -v $(pwd)/test-repo:/workspace:ro \
  -v $(pwd)/crossbridge-data/logs:/data/logs \
  -v $(pwd)/crossbridge-data/reports:/data/reports \
  crossbridge/crossbridge:1.0.0 exec run \
  --framework pytest \
  --strategy smoke
```

### 2. Impacted Tests (PR Validation)

```bash
docker run --rm \
  -v $(pwd)/test-repo:/workspace:ro \
  -v $(pwd)/crossbridge-data/logs:/data/logs \
  -v $(pwd)/crossbridge-data/reports:/data/reports \
  -v $(pwd)/crossbridge-data/cache:/data/cache \
  -e GIT_BASE_BRANCH=main \
  crossbridge/crossbridge:1.0.0 exec run \
  --framework testng \
  --strategy impacted \
  --base-branch origin/main \
  --ci
```

### 3. Risk-Based Tests (Release)

```bash
docker run --rm \
  -v $(pwd)/test-repo:/workspace:ro \
  -v $(pwd)/crossbridge-data/logs:/data/logs \
  -v $(pwd)/crossbridge-data/reports:/data/reports \
  crossbridge/crossbridge:1.0.0 exec run \
  --framework robot \
  --strategy risk \
  --max-tests 100 \
  --env prod
```

### 4. Dry Run (Plan Only)

```bash
docker run --rm \
  -v $(pwd)/test-repo:/workspace:ro \
  crossbridge/crossbridge:1.0.0 exec plan \
  --framework pytest \
  --strategy impacted \
  --json
```

### 5. With Configuration File

```bash
docker run --rm \
  -v $(pwd)/test-repo:/workspace:ro \
  -v $(pwd)/crossbridge.yml:/opt/crossbridge/crossbridge.yml:ro \
  -v $(pwd)/crossbridge-data/logs:/data/logs \
  -v $(pwd)/crossbridge-data/reports:/data/reports \
  crossbridge/crossbridge:1.0.0 exec run \
  --framework cypress \
  --strategy smoke
```

### 6. Interactive Shell (Debugging)

```bash
docker run --rm -it \
  -v $(pwd)/test-repo:/workspace:ro \
  --entrypoint /bin/bash \
  crossbridge/crossbridge:1.0.0
```

---

## docker-compose

### Basic Setup

```yaml
version: "3.9"

services:
  crossbridge:
    image: crossbridge/crossbridge:1.0.0
    working_dir: /workspace
    volumes:
      - ./test-repo:/workspace:ro
      - ./crossbridge-data/logs:/data/logs
      - ./crossbridge-data/reports:/data/reports
      - ./crossbridge-data/cache:/data/cache
    environment:
      - CROSSBRIDGE_ENV=local
      - CROSSBRIDGE_LOG_LEVEL=INFO
    command: exec run --framework pytest --strategy smoke
```

### Run

```bash
# Default command
docker-compose up

# Custom command
docker-compose run --rm crossbridge exec run --framework testng --strategy impacted

# Dry run
docker-compose run --rm crossbridge exec plan --framework pytest --strategy risk

# Interactive shell
docker-compose run --rm --entrypoint /bin/bash crossbridge
```

### With Database

```yaml
services:
  crossbridge:
    image: crossbridge/crossbridge:1.0.0
    depends_on:
      - postgres
    environment:
      - CROSSBRIDGE_DB_HOST=postgres

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=crossbridge
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=admin
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  postgres-data:
```

Run with database:

```bash
docker-compose --profile database up
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: CrossBridge Execution

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Create volume directories
        run: mkdir -p crossbridge-data/{logs,reports,cache}
      
      - name: Run CrossBridge
        run: |
          docker run --rm \
            -v $(pwd):/workspace:ro \
            -v $(pwd)/crossbridge-data/logs:/data/logs \
            -v $(pwd)/crossbridge-data/reports:/data/reports \
            -v $(pwd)/crossbridge-data/cache:/data/cache \
            -e CROSSBRIDGE_ENV=ci \
            crossbridge/crossbridge:1.0.0 exec run \
            --framework pytest \
            --strategy impacted \
            --base-branch origin/${{ github.base_ref || 'main' }} \
            --ci \
            --json > result.json
      
      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: crossbridge-data/reports/
      
      - name: Check exit code
        run: exit ${{ steps.crossbridge.outcome == 'success' && 0 || 1 }}
```

### GitLab CI

```yaml
crossbridge:execution:
  stage: test
  image: docker:latest
  services:
    - docker:dind
  script:
    - mkdir -p crossbridge-data/{logs,reports,cache}
    - |
      docker run --rm \
        -v $(pwd):/workspace:ro \
        -v $(pwd)/crossbridge-data/logs:/data/logs \
        -v $(pwd)/crossbridge-data/reports:/data/reports \
        -v $(pwd)/crossbridge-data/cache:/data/cache \
        -e CROSSBRIDGE_ENV=ci \
        crossbridge/crossbridge:1.0.0 exec run \
        --framework testng \
        --strategy impacted \
        --ci
  artifacts:
    when: always
    paths:
      - crossbridge-data/reports/
    reports:
      junit: crossbridge-data/reports/**/*.xml
```

### Jenkins

```groovy
pipeline {
    agent any
    
    environment {
        CROSSBRIDGE_VERSION = '1.0.0'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'mkdir -p crossbridge-data/{logs,reports,cache}'
            }
        }
        
        stage('Execute Tests') {
            steps {
                script {
                    def exitCode = sh(
                        script: """
                            docker run --rm \
                              -v ${WORKSPACE}:/workspace:ro \
                              -v ${WORKSPACE}/crossbridge-data/logs:/data/logs \
                              -v ${WORKSPACE}/crossbridge-data/reports:/data/reports \
                              -v ${WORKSPACE}/crossbridge-data/cache:/data/cache \
                              -e CROSSBRIDGE_ENV=ci \
                              crossbridge/crossbridge:${CROSSBRIDGE_VERSION} exec run \
                              --framework pytest \
                              --strategy impacted \
                              --ci
                        """,
                        returnStatus: true
                    )
                    
                    if (exitCode != 0) {
                        error("CrossBridge execution failed with exit code ${exitCode}")
                    }
                }
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'crossbridge-data/reports/**/*', allowEmptyArchive: true
            junit 'crossbridge-data/reports/**/*.xml'
        }
    }
}
```

---

## Exit Codes

CrossBridge uses standard exit codes for CI/CD integration:

| Exit Code | Meaning | CI/CD Action |
|-----------|---------|--------------|
| **0** | All tests passed | ✅ Build succeeds |
| **1** | Test failures | ❌ Build fails |
| **2** | Execution error | ❌ Build fails |
| **3** | Configuration error | ❌ Build fails |

### Handling Exit Codes

```bash
# Run and capture exit code
docker run --rm \
  -v $(pwd)/tests:/workspace:ro \
  crossbridge/crossbridge:1.0.0 exec run \
  --framework pytest \
  --strategy smoke

EXIT_CODE=$?

case $EXIT_CODE in
  0)
    echo "✅ All tests passed"
    ;;
  1)
    echo "❌ Test failures"
    ;;
  2)
    echo "⚠️  Execution error"
    ;;
  3)
    echo "🔧 Configuration error"
    ;;
esac

exit $EXIT_CODE
```

---

## Troubleshooting

### Issue: Permission Denied on Volumes

**Problem:** Can't write to log/report directories

**Solution:**
```bash
# Option 1: Fix permissions
chmod -R 777 crossbridge-data/

# Option 2: Run as root (not recommended)
docker run --rm --user root ...

# Option 3: Match container user ID
docker run --rm --user $(id -u):$(id -g) ...
```

### Issue: Test Repository Not Found

**Problem:** CrossBridge can't find tests

**Solution:**
```bash
# Ensure workspace is mounted
docker run --rm \
  -v $(pwd)/test-repo:/workspace:ro \  # ← Check this path
  crossbridge/crossbridge:1.0.0 exec run --framework pytest --strategy smoke

# Verify mount inside container
docker run --rm -it \
  -v $(pwd)/test-repo:/workspace:ro \
  --entrypoint /bin/bash \
  crossbridge/crossbridge:1.0.0 -c "ls -la /workspace"
```

### Issue: Framework Not Found

**Problem:** CrossBridge can't invoke test framework

**Cause:** Test frameworks run on **host**, not in container

**Solution:**
```bash
# v1: Framework must be installed on host
# CrossBridge generates CLI commands, host executes them

# Ensure framework is available
pytest --version  # For pytest
mvn --version     # For TestNG
```

### Issue: No Reports Generated

**Problem:** Report directory is empty

**Solution:**
```bash
# 1. Check volume mount
docker run --rm \
  -v $(pwd)/crossbridge-data/reports:/data/reports \  # ← Verify path
  ...

# 2. Check execution completed
docker logs crossbridge  # If using docker-compose

# 3. Check framework report location matches adapter config
```

### Issue: Out of Memory

**Problem:** Container runs out of memory

**Solution:**
```bash
# Increase Docker memory limit
docker run --rm \
  --memory="4g" \
  --memory-swap="4g" \
  ...

# Or in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
```

---

## Best Practices

### 1. Version Pinning

✅ **DO:**
```yaml
image: crossbridge/crossbridge:1.0.0
```

❌ **DON'T:**
```yaml
image: crossbridge/crossbridge:latest
```

### 2. Read-Only Workspace

✅ **DO:**
```bash
-v $(pwd)/tests:/workspace:ro
```

### 3. Named Volumes for Persistence

✅ **DO:**
```yaml
volumes:
  - crossbridge-logs:/data/logs
  - crossbridge-reports:/data/reports
```

### 4. Environment-Specific Configs

✅ **DO:**
```bash
# .env.dev
CROSSBRIDGE_ENV=dev
STRATEGY=smoke

# .env.prod
CROSSBRIDGE_ENV=prod
STRATEGY=risk
```

### 5. CI/CD Exit Code Handling

✅ **DO:**
```bash
docker run ... || exit $?
```

---

## Summary

CrossBridge Docker provides:

✅ **Stateless execution** - No persistent state in container  
✅ **Volume-based persistence** - Logs, reports externalized  
✅ **Framework-agnostic** - Works with 13+ frameworks  
✅ **CI/CD friendly** - Standard exit codes, JSON output  
✅ **Reproducible** - Semantic versioning, locked versions  

**Next Steps:**
- Try [Quick Start](#quick-start)
- Read [CI/CD Integration](#cicd-integration)
- Customize [docker-compose.yml](#docker-compose)

---

**Prepared by:** CrossStack AI Team  
**Product:** CrossBridge  
**Module:** Docker Packaging  
**Date:** January 31, 2026
