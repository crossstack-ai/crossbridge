# Environment Variables Configuration

## Overview

CrossBridge uses environment variables for sensitive configuration like API keys, database credentials, and service endpoints. This document provides a complete reference of all supported environment variables.

## Quick Start

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your configuration:
   ```bash
   # Open in your preferred editor
   nano .env
   ```

3. Never commit `.env` to version control (already in `.gitignore`)

## Database Configuration

### PostgreSQL (Required for persistence features)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_HOST` | Yes* | `localhost` | PostgreSQL server hostname or IP |
| `DB_PORT` | No | `5432` | PostgreSQL server port |
| `DB_NAME` | Yes* | `crossbridge` | Database name to use |
| `DB_USER` | Yes* | - | Database username |
| `DB_PASSWORD` | Yes* | - | Database password |
| `DB_SSL_MODE` | No | `prefer` | SSL mode: `disable`, `allow`, `prefer`, `require` |

*Required only if using database persistence features (Grafana dashboards, historical analysis, etc.)

**Example:**
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crossbridge
DB_USER=crossbridge_user
DB_PASSWORD=secure_password_here
DB_SSL_MODE=require
```

### Connection Pool Settings (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_POOL_SIZE` | No | `10` | Maximum number of database connections |
| `DB_POOL_TIMEOUT` | No | `30` | Connection timeout in seconds |
| `DB_MAX_OVERFLOW` | No | `20` | Max connections beyond pool_size |

## AI Provider Configuration

### OpenAI (Conditional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Conditional** | - | OpenAI API key (starts with `sk-`) |
| `OPENAI_BASE_URL` | No | `https://api.openai.com/v1` | Custom OpenAI-compatible endpoint |
| `OPENAI_ORGANIZATION` | No | - | OpenAI organization ID |
| `OPENAI_DEFAULT_MODEL` | No | `gpt-4` | Default model to use |
| `OPENAI_MAX_TOKENS` | No | `2000` | Default max tokens per request |
| `OPENAI_TEMPERATURE` | No | `0.3` | Default temperature (0.0-2.0) |

**Example:**
```bash
OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz1234567890
OPENAI_DEFAULT_MODEL=gpt-4-turbo
OPENAI_TEMPERATURE=0.3
```

### Anthropic (Conditional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Conditional** | - | Anthropic API key (starts with `sk-ant-`) |
| `ANTHROPIC_BASE_URL` | No | `https://api.anthropic.com` | Anthropic API endpoint |
| `ANTHROPIC_DEFAULT_MODEL` | No | `claude-3-5-sonnet-20241022` | Default Claude model |
| `ANTHROPIC_MAX_TOKENS` | No | `4000` | Default max tokens per request |

**Example:**
```bash
ANTHROPIC_API_KEY=sk-ant-api03-abcdefghijklmnopqrstuvwxyz
ANTHROPIC_DEFAULT_MODEL=claude-3-5-sonnet-20241022
```

### Azure OpenAI (Conditional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_OPENAI_KEY` | Conditional** | - | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Conditional** | - | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | Conditional** | - | Deployment name in Azure |
| `AZURE_OPENAI_API_VERSION` | No | `2024-02-15-preview` | Azure OpenAI API version |

**Example:**
```bash
AZURE_OPENAI_KEY=your_azure_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4-deployment
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### Self-Hosted Models (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `llama2` | Default Ollama model |
| `SELF_HOSTED_BASE_URL` | No | - | Custom OpenAI-compatible endpoint |
| `SELF_HOSTED_MODEL` | No | - | Model name for self-hosted endpoint |

**Example:**
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

**At least one AI provider (OpenAI, Anthropic, or Azure) must be configured to use AI-powered features.

## Repository Integration

### Bitbucket (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BITBUCKET_USERNAME` | No | - | Bitbucket username |
| `BITBUCKET_PASSWORD` | No | - | Bitbucket app password |
| `BITBUCKET_PROJECT` | No | - | Default project key |
| `BITBUCKET_REPOSITORY` | No | - | Default repository slug |
| `BITBUCKET_URL` | No | `https://bitbucket.org` | Bitbucket server URL (for self-hosted) |

**Example:**
```bash
BITBUCKET_USERNAME=john.doe
BITBUCKET_PASSWORD=app_password_here
BITBUCKET_PROJECT=TEST
BITBUCKET_REPOSITORY=automation-tests
```

### GitHub (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | No | - | GitHub personal access token |
| `GITHUB_OWNER` | No | - | Default repository owner |
| `GITHUB_REPO` | No | - | Default repository name |

**Example:**
```bash
GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz1234567890
GITHUB_OWNER=my-org
GITHUB_REPO=test-automation
```

## Grafana Integration (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GRAFANA_URL` | No | `http://localhost:3000` | Grafana server URL |
| `GRAFANA_API_KEY` | No | - | Grafana API key for dashboard creation |
| `GRAFANA_ORG_ID` | No | `1` | Grafana organization ID |

**Example:**
```bash
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=eyJrIjoiYWJjZGVmZ2hpamts...
GRAFANA_ORG_ID=1
```

## Application Configuration (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_VERSION` | No | `0.1.1` | Override application version |
| `LOG_LEVEL` | No | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FILE` | No | - | Path to log file (if not set, logs to console only) |
| `CACHE_DIR` | No | `~/.crossbridge/cache` | Directory for cached data |
| `CONFIG_FILE` | No | `crossbridge.yaml` | Path to configuration file |

**Example:**
```bash
LOG_LEVEL=DEBUG
LOG_FILE=logs/crossbridge.log
CACHE_DIR=/var/cache/crossbridge
```

## Feature Flags (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENABLE_AI_FEATURES` | No | `true` | Enable AI-powered features |
| `ENABLE_FLAKY_DETECTION` | No | `true` | Enable flaky test detection |
| `ENABLE_PROFILING` | No | `true` | Enable performance profiling |
| `ENABLE_COVERAGE_ANALYSIS` | No | `true` | Enable coverage analysis |
| `ENABLE_CONTINUOUS_INTELLIGENCE` | No | `true` | Enable continuous intelligence features |

**Example:**
```bash
ENABLE_AI_FEATURES=true
ENABLE_FLAKY_DETECTION=true
ENABLE_PROFILING=false
```

## Performance Tuning (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MAX_WORKERS` | No | `4` | Maximum parallel workers for test processing |
| `BATCH_SIZE` | No | `100` | Batch size for database operations |
| `AI_CACHE_TTL` | No | `86400` | AI response cache TTL in seconds (24 hours) |
| `REQUEST_TIMEOUT` | No | `30` | Default request timeout in seconds |

**Example:**
```bash
MAX_WORKERS=8
BATCH_SIZE=200
AI_CACHE_TTL=43200  # 12 hours
REQUEST_TIMEOUT=60
```

## Cost Management (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_DAILY_COST_LIMIT` | No | - | Maximum daily AI cost in USD |
| `AI_MONTHLY_COST_LIMIT` | No | - | Maximum monthly AI cost in USD |
| `AI_PER_REQUEST_LIMIT` | No | - | Maximum cost per AI request in USD |

**Example:**
```bash
AI_DAILY_COST_LIMIT=10.00
AI_MONTHLY_COST_LIMIT=200.00
AI_PER_REQUEST_LIMIT=0.50
```

## Validation

Use the validation script to check your environment configuration:

```bash
python scripts/validate_environment.py
```

This will check:
- ✅ All required variables are set
- ✅ At least one AI provider is configured
- ✅ Database connection is working (if configured)
- ✅ API keys are valid format
- ⚠️  Optional features availability

## Security Best Practices

### Local Development

1. **Use `.env` file**: Store secrets in `.env` (never commit to git)
2. **Restrict file permissions**: 
   ```bash
   chmod 600 .env
   ```
3. **Rotate keys regularly**: Update API keys periodically

### CI/CD Environments

1. **Use CI Secrets**: Store in GitHub Secrets, GitLab CI Variables, etc.
2. **Mask sensitive output**: Ensure logs don't expose secrets
3. **Separate environments**: Use different keys for dev/staging/prod

**GitHub Actions Example:**
```yaml
env:
  DB_HOST: ${{ secrets.DB_HOST }}
  DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

**GitLab CI Example:**
```yaml
variables:
  DB_HOST: $DB_HOST
  DB_PASSWORD: $DB_PASSWORD
  OPENAI_API_KEY: $OPENAI_API_KEY
```

### Production Deployments

Use enterprise secret management:

1. **AWS Secrets Manager**: For AWS deployments
2. **Azure Key Vault**: For Azure deployments
3. **HashiCorp Vault**: For multi-cloud or on-premise
4. **Docker Secrets**: For Docker Swarm deployments
5. **Kubernetes Secrets**: For Kubernetes deployments

**Example with AWS Secrets Manager:**
```python
import boto3
import json

def get_secrets():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='crossbridge/production')
    return json.loads(response['SecretString'])

secrets = get_secrets()
os.environ['DB_PASSWORD'] = secrets['db_password']
os.environ['OPENAI_API_KEY'] = secrets['openai_api_key']
```

## Troubleshooting

### Database Connection Issues

```bash
# Test database connection
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME

# Check environment variables
echo $DB_HOST
echo $DB_USER
```

### AI Provider Issues

```bash
# Test OpenAI connection
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test Anthropic connection
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

### Permission Issues

```bash
# Check file permissions
ls -la .env

# Fix permissions if needed
chmod 600 .env
```

## Example Complete Configuration

```bash
# Database (Required for persistence)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crossbridge
DB_USER=crossbridge_user
DB_PASSWORD=secure_password_here

# AI Provider (At least one required for AI features)
OPENAI_API_KEY=sk-proj-your_key_here
OPENAI_DEFAULT_MODEL=gpt-4-turbo

# Optional: Anthropic for fallback
ANTHROPIC_API_KEY=sk-ant-your_key_here

# Application Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/crossbridge.log

# Feature Flags
ENABLE_AI_FEATURES=true
ENABLE_FLAKY_DETECTION=true
ENABLE_PROFILING=true

# Cost Management
AI_DAILY_COST_LIMIT=10.00
AI_MONTHLY_COST_LIMIT=200.00
```

## Related Documentation

- [Configuration Guide](../guides/configuration.md)
- [Security Best Practices](../guides/security.md)
- [Deployment Guide](../guides/deployment.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
