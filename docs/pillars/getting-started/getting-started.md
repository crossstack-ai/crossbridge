# Getting Started with CrossBridge AI

> **5-minute quickstart guide**

CrossBridge AI helps you analyze, modernize, and optimize test automation without forcing rewrites or migrations.

---

## 📋 Prerequisites

- **Python 3.9+**
- **Git**
- **Database** (PostgreSQL recommended, optional for basic usage)
- **OpenAI API key** (optional, for AI features)

---

## ⚡ Quick Setup

### 1. Clone and Install

```bash
# Clone repository
git clone https://github.com/crossstack-ai/crossbridge.git
cd crossbridge

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy example configuration
cp crossbridge.yml.example crossbridge.yml

# Edit configuration (optional for basic usage)
nano crossbridge.yml
```

### 3. Choose Your Mode

CrossBridge offers **two modes**:

#### **Option A: Observer Mode** (No Code Changes)
Works with existing tests as-is:

```bash
# Enable observer mode
export CROSSBRIDGE_ENABLED=true

# Run your tests normally
pytest tests/  # or mvn test, npm test, etc.

# CrossBridge observes and provides intelligence automatically
```

#### **Option B: Migration Mode** (Transform Tests)
Convert tests to modern frameworks:

```bash
# Start interactive CLI
python -m cli.app

# Follow prompts to:
# 1. Select source framework (e.g., Selenium Java)
# 2. Choose target framework (e.g., Playwright)
# 3. Configure paths
# 4. Run migration
```

---

## 🎯 Common Workflows

### Analyze Existing Tests

```bash
# Discover tests
crossbridge discover --framework pytest --output discovery.json

# Run semantic analysis
crossbridge semantic index -f pytest -p ./tests
crossbridge semantic search "login timeout tests"
```

### Detect Flaky Tests

```bash
# Analyze test history
crossbridge flaky detect --db-url postgresql://user:pass@host/db

# List flaky tests
crossbridge flaky list --severity critical
```

### Intelligent Test Execution

```bash
# Run smoke tests only
crossbridge exec run --framework pytest --strategy smoke

# Run impacted tests (PR validation)
crossbridge exec run --framework pytest --strategy impacted --base-branch main
```

### Classify Test Failures

```bash
# Analyze failure logs
crossbridge analyze logs --log-file test_output.log --framework pytest

# Classify as: PRODUCT_DEFECT | LOCATOR_ISSUE | ENVIRONMENT | FLAKY
```

---

## 📊 View Results

### Grafana Dashboards (Optional)

```bash
# Import dashboard
grafana/import_dashboard.sh

# View at http://localhost:3000
```

### CLI Output

Most commands provide JSON output for automation:

```bash
crossbridge analyze logs --format json > analysis.json
```

---

## 🆘 Troubleshooting

### Database Connection Issues

```bash
# Test database connection
crossbridge config validate

# Use environment variables
export DATABASE_URL="postgresql://user:pass@host:5432/db"
```

### AI Provider Errors

```bash
# Check API key
export OPENAI_API_KEY="sk-..."

# Test AI connection
crossbridge ai test-connection
```

### Framework Detection Issues

```bash
# Manually specify framework
crossbridge discover --framework pytest --path ./tests
```

---

## 📚 Next Steps

- **Framework-specific guides**: [quick-start/](quick-start/)
- **Configuration deep-dive**: [configuration/](configuration/)
- **Architecture overview**: [architecture.md](../../architecture.md)
- **All features**: [README.md](../../README.md)

---

## 🤝 Getting Help

- **GitHub Issues**: [Report bugs](https://github.com/crossstack-ai/crossbridge/issues)
- **Documentation**: [Full docs](../../README.md)
- **Community**: [Discussions](https://github.com/crossstack-ai/crossbridge/discussions)

---

**⚡ Ready to explore?** Check out the [framework support guide](../../framework-support.md) to see all supported frameworks.
