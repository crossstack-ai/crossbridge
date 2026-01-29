# Environment Configuration Guide

## Overview

CrossBridge uses environment variables for configuration, following the **12-factor app** methodology. This allows:
- ✅ Separation of configuration from code
- ✅ Different settings per environment (dev, test, production)
- ✅ Secure credential management
- ✅ Easy CI/CD integration

---

## File Structure

```
crossbridge/
├── .env                          # YOUR LOCAL CONFIG (gitignored, DO NOT COMMIT)
├── .env.example                  # Template with all variables
├── .env.local.example            # Local development template
├── .env.production.example       # Production deployment template
└── crossbridge.yml               # YAML config (alternative/supplement to .env)
```

---

## 📁 Environment Files Explained

### `.env` (Local - **GITIGNORED**)
**Your personal environment file** - Contains actual credentials and local settings.
- ❌ **NEVER commit this file**
- ✅ Copy from `.env.example` and customize
- ✅ Contains real passwords, API keys, local paths

### `.env.example` (Template - **COMMITTED**)
**Template showing all available variables** - Safe to commit.
- ✅ Shows all configuration options
- ✅ Contains placeholder/default values
- ✅ Comprehensive documentation
- ✅ Updated with new features

### `.env.local.example` (Local Dev Template - **COMMITTED**)
**Quick start for local development** - Common local settings.
- ✅ Localhost database settings
- ✅ Disabled expensive features
- ✅ DEBUG logging enabled
- ✅ Fast iteration setup

### `.env.production.example` (Production Template - **COMMITTED**)
**Production deployment template** - Production-ready settings.
- ✅ Performance tuning
- ✅ Security hardening
- ✅ Monitoring enabled
- ✅ Resilience features

---

## 🚀 Quick Start

### For Local Development

```bash
# 1. Copy the local development template
cp .env.local.example .env

# 2. Edit with your local settings
nano .env

# 3. Update database credentials
CROSSBRIDGE_DB_HOST=localhost
CROSSBRIDGE_DB_PASSWORD=your_local_password

# 4. Verify configuration
python -c "from core.config.loader import load_config; config = load_config(); print(config)"
```

### For Production Deployment

```bash
# 1. Copy the production template
cp .env.production.example .env.production

# 2. Edit with production settings (CHANGE ALL "CHANGE_ME" values!)
nano .env.production

# 3. Use secrets manager (recommended)
export $(cat .env.production | xargs)

# OR use .env file (less secure)
python run_cli.py --env-file .env.production
```

---

## 📋 Required vs Optional Variables

### ✅ **Required** (Must Set)

| Variable | Purpose | Example |
|----------|---------|---------|
| `CROSSBRIDGE_DB_HOST` | Database server | `localhost` |
| `CROSSBRIDGE_DB_NAME` | Database name | `crossbridge_db` |
| `CROSSBRIDGE_DB_USER` | Database user | `postgres` |
| `CROSSBRIDGE_DB_PASSWORD` | Database password | `secure_password` |

### 🔧 **Important** (Recommended)

| Variable | Purpose | Default |
|----------|---------|---------|
| `GRAFANA_URL` | Dashboard URL | `http://localhost:3000` |
| `GRAFANA_API_KEY` | API access | (none - manual setup needed) |
| `CROSSBRIDGE_LOG_LEVEL` | Logging detail | `INFO` |
| `CROSSBRIDGE_ENVIRONMENT` | Env name | `development` |

### ⚙️ **Optional** (Feature-Specific)

| Variable | Purpose | When Needed |
|----------|---------|-------------|
| `OPENAI_API_KEY` | AI features | If using AI transformation |
| `ANTHROPIC_API_KEY` | Claude models | Alternative to OpenAI |
| `INFLUXDB_URL` | Time-series DB | If using InfluxDB profiling |
| `SLACK_WEBHOOK_URL` | Notifications | If using Slack alerts |

---

## 🔍 Configuration Priority

CrossBridge loads configuration in this order (later overrides earlier):

1. **Default values** (hardcoded in `core/config/loader.py`)
2. **crossbridge.yml** (YAML configuration file)
3. **Environment variables** (`.env` file or system env vars)
4. **Command-line arguments** (highest priority)

### Example Priority Flow

```python
# 1. Default (in code)
CROSSBRIDGE_LOG_LEVEL = "INFO"

# 2. crossbridge.yml (overrides default)
logging:
  level: WARNING

# 3. .env file (overrides YAML)
CROSSBRIDGE_LOG_LEVEL=DEBUG

# 4. System environment (overrides .env)
export CROSSBRIDGE_LOG_LEVEL=ERROR

# Result: ERROR (system env wins)
```

---

## 🛠️ Best Practices

### ✅ DO

1. **Use `.env.example` as template** - Always copy and customize
2. **Never commit `.env`** - Contains secrets (already gitignored)
3. **Use environment-specific files** - `.env.local`, `.env.production`
4. **Document all variables** - Add comments explaining purpose
5. **Use secrets managers** - AWS Secrets Manager, Vault for production
6. **Rotate credentials regularly** - Every 90 days minimum
7. **Validate on startup** - Check required variables exist
8. **Use strong passwords** - Min 32 characters, random

### ❌ DON'T

1. **Don't commit `.env`** - Use `.env.example` instead
2. **Don't hardcode secrets** - Always use environment variables
3. **Don't share `.env`** - Each developer has their own
4. **Don't use weak passwords** - Especially in production
5. **Don't skip validation** - Fail fast on missing config
6. **Don't mix environments** - Keep dev/test/prod separate

---

## 🔐 Security Considerations

### Sensitive Variables (Never Log or Display)

```bash
# Database passwords
CROSSBRIDGE_DB_PASSWORD=***

# API keys
OPENAI_API_KEY=sk-***
GRAFANA_API_KEY=***
GITHUB_TOKEN=ghp_***

# JWT secrets
CROSSBRIDGE_JWT_SECRET=***

# Integration tokens
JIRA_API_TOKEN=***
SLACK_WEBHOOK_URL=https://hooks.slack.com/***
```

### Secrets Management (Production)

**Recommended approaches:**

1. **AWS Secrets Manager**
```bash
# Store secret
aws secretsmanager create-secret --name crossbridge/db-password --secret-string "password"

# Retrieve in app
import boto3
secret = boto3.client('secretsmanager').get_secret_value(SecretId='crossbridge/db-password')
```

2. **HashiCorp Vault**
```bash
# Store secret
vault kv put secret/crossbridge db_password="password"

# Retrieve in app
import hvac
client = hvac.Client(url='http://vault:8200')
secret = client.secrets.kv.v2.read_secret_version(path='crossbridge')
```

3. **Environment Variables (CI/CD)**
```yaml
# GitHub Actions
env:
  CROSSBRIDGE_DB_PASSWORD: ${{ secrets.DB_PASSWORD }}

# GitLab CI
variables:
  CROSSBRIDGE_DB_PASSWORD: $DB_PASSWORD
```

---

## 🧪 Testing Configuration

### Running Tests with Different Configs

```bash
# Use test database
export CROSSBRIDGE_DB_NAME=crossbridge_test_db
pytest tests/

# Or use .env.test
cp .env.example .env.test
# Edit .env.test with test settings
pytest --env-file .env.test

# Or inline
CROSSBRIDGE_DB_NAME=test_db pytest tests/
```

---

## 🐳 Docker & Containerization

### Docker Compose

```yaml
# docker-compose.yml
services:
  crossbridge:
    build: .
    env_file:
      - .env.local  # Load from file
    environment:
      - CROSSBRIDGE_DB_HOST=postgres  # Override specific vars
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ${CROSSBRIDGE_DB_NAME}
      POSTGRES_USER: ${CROSSBRIDGE_DB_USER}
      POSTGRES_PASSWORD: ${CROSSBRIDGE_DB_PASSWORD}
```

### Kubernetes Secrets

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: crossbridge-secrets
type: Opaque
stringData:
  db-password: your_password_here
  openai-key: sk-your_key_here

---
# deployment.yaml
spec:
  containers:
  - name: crossbridge
    env:
    - name: CROSSBRIDGE_DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: crossbridge-secrets
          key: db-password
```

---

## 📚 Variable Reference

For complete list of all available environment variables, see:
- **[.env.example](.env.example)** - Full template with descriptions
- **[docs/config/CONFIG.md](docs/config/CONFIG.md)** - Detailed configuration guide
- **[README.md](README.md#-quick-start)** - Quick start examples

---

## 🔍 Troubleshooting

### Common Issues

**1. "Database connection failed"**
```bash
# Check variables are set
echo $CROSSBRIDGE_DB_HOST
echo $CROSSBRIDGE_DB_PASSWORD

# Test connection
psql -h $CROSSBRIDGE_DB_HOST -U $CROSSBRIDGE_DB_USER -d $CROSSBRIDGE_DB_NAME
```

**2. ".env not loaded"**
```bash
# Ensure python-dotenv is installed
pip install python-dotenv

# Check .env location (must be in project root)
ls -la .env

# Load explicitly in code
from dotenv import load_dotenv
load_dotenv()
```

**3. "Variables not taking effect"**
```bash
# Check priority order
# System env > .env > crossbridge.yml > defaults

# Unset system env if needed
unset CROSSBRIDGE_LOG_LEVEL

# Restart application after changes
```

---

## 📖 Related Documentation

- [Configuration Guide](docs/config/CONFIG.md) - Complete config documentation
- [Quick Start Guide](README.md#-quick-start) - Getting started
- [Production Hardening](docs/hardening/PRODUCTION_HARDENING.md) - Production deployment
- [Security Best Practices](docs/security/SECURITY.md) - Security guidelines

---

**Last Updated**: January 29, 2026  
**Maintainer**: CrossStack AI
