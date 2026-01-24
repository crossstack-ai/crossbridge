# CrossBridge Unified Configuration Guide

## Overview

The unified configuration system provides a **single source of truth** for all CrossBridge settings. Instead of passing configuration through CLI flags, environment variables, or scattered config files, you can now manage everything through one `crossbridge.yml` file.

## Quick Start

### 1. Create Configuration File

Create `crossbridge.yml` in your project root:

```yaml
crossbridge:
  mode: observer
  
  application:
    product_name: MyApp
    application_version: v1.0.0
  
  database:
    host: localhost
    port: 5432
    database: mydb
    user: postgres
    password: mypassword
```

### 2. Use in Python Code

```python
from core.config import get_config

# Load configuration (singleton pattern)
config = get_config()

# Access settings
print(f"Database: {config.database.host}:{config.database.port}")
print(f"Mode: {config.mode}")
print(f"AI Provider: {config.ai.provider}")

# Get connection string
conn_str = config.database.connection_string
# postgresql://postgres:mypassword@localhost:5432/mydb
```

### 3. CLI Integration (Coming Soon)

```bash
# Configuration file takes precedence over CLI flags
crossbridge translate --source selenium --target playwright

# CLI flags override config file values
crossbridge translate --mode automated  # Overrides config.translation.mode
```

## Configuration Structure

### Core Settings

```yaml
crossbridge:
  # Operational mode: 'observer' (monitoring) or 'migration' (active translation)
  mode: observer
```

### Application Tracking

```yaml
application:
  # Application name for test tracking
  product_name: PaymentAPI
  
  # Version being tested (use with CI/CD: ${CI_COMMIT_TAG})
  application_version: v2.1.0
  
  # Environment: dev, staging, production
  environment: production
```

### Database Configuration

```yaml
database:
  enabled: true
  host: db.example.com
  port: 5432
  database: crossbridge_db
  user: postgres
  password: secure_password
```

**Generated connection string**: `postgresql://user:password@host:port/database`

### Test Translation/Migration

```yaml
translation:
  # Mode: assistive (human review), automated, batch
  mode: assistive
  
  # AI enhancement
  use_ai: true
  max_credits: 500
  confidence_threshold: 0.8  # 0.0-1.0
  
  # Validation: strict, lenient, skip
  validation_level: strict
  
  # Code preservation
  preserve_comments: true
  inject_todos: true
  
  # Performance
  max_workers: 10
  commit_batch_size: 10
```

### AI/LLM Configuration

```yaml
ai:
  enabled: true
  
  # Provider: openai, anthropic, custom
  provider: openai
  
  # API credentials (use environment variables!)
  api_key: ${OPENAI_API_KEY}
  
  # Model selection
  # OpenAI: gpt-3.5-turbo, gpt-4
  # Anthropic: claude-3-sonnet, claude-3-opus
  model: gpt-4
  
  # Model parameters
  temperature: 0.7  # 0.0 (deterministic) to 1.0 (creative)
  max_tokens: 2048
  timeout: 60
  
  # Enterprise settings
  endpoint: null  # Custom endpoint
  region: US      # Data residency
```

### Flaky Test Detection

```yaml
flaky_detection:
  enabled: true
  
  # Machine learning parameters
  n_estimators: 200         # Isolation forest trees
  contamination: 0.1        # Expected flaky ratio (10%)
  random_state: 42          # Reproducibility
  
  # Confidence thresholds
  min_executions_reliable: 15   # Minimum runs for detection
  min_executions_confident: 30  # Runs for full confidence
  min_confidence_threshold: 0.5
  
  # Model management
  auto_retrain: true
  retrain_threshold: 100
```

### Observer Mode

```yaml
observer:
  auto_detect_new_tests: true
  update_coverage_graph: true
  detect_drift: true
  flaky_threshold: 0.15  # Flag tests with >15% failure rate
```

### Intelligence Features

```yaml
intelligence:
  ai_enabled: true
  detect_coverage_gaps: true
  detect_redundant_tests: true
  risk_based_recommendations: true
```

### Framework-Specific Settings

```yaml
frameworks:
  pytest:
    enabled: true
    auto_instrument_api_calls: true
    auto_instrument_ui_interactions: false
    capture_network_traffic: true
    track_keywords: true
    track_api_calls: true
  
  playwright:
    enabled: true
    auto_instrument_api_calls: true
    auto_instrument_ui_interactions: true
    capture_network_traffic: true
  
  robot:
    enabled: true
    auto_instrument_api_calls: true
    auto_instrument_ui_interactions: true
    track_keywords: true
  
  cypress:
    enabled: true
    auto_instrument_api_calls: true
    capture_network_traffic: true
```

## Environment Variable Substitution

Use `${VAR_NAME:-default_value}` syntax for dynamic configuration:

```yaml
crossbridge:
  application:
    product_name: ${PRODUCT_NAME:-MyApp}
    application_version: ${APP_VERSION:-v1.0.0}
  
  database:
    host: ${CROSSBRIDGE_DB_HOST:-localhost}
    password: ${CROSSBRIDGE_DB_PASSWORD:-admin}
  
  ai:
    api_key: ${OPENAI_API_KEY}  # No default - must be set
```

**Common patterns**:

```bash
# CI/CD - GitLab
export APP_VERSION=$(git describe --tags)
export CI_ENVIRONMENT_NAME=production

# CI/CD - GitHub Actions
export APP_VERSION=${{ github.ref_name }}
export PRODUCT_NAME=${{ github.repository }}

# Local development
export OPENAI_API_KEY=sk-your-key-here
export CROSSBRIDGE_DB_HOST=localhost
```

## Configuration File Discovery

CrossBridge automatically searches for configuration files in this order:

1. `crossbridge.yml` (current directory)
2. `crossbridge.yaml` (current directory)
3. `.crossbridge.yml` (hidden file)
4. Parent directories (searches up the tree)
5. Falls back to defaults if no file found

**Priority**: `current dir → parent dirs → defaults`

## Usage Examples

### Local Development

```yaml
crossbridge:
  mode: observer
  
  database:
    host: localhost
    password: dev_password
  
  ai:
    enabled: false  # Save credits
  
  translation:
    mode: assistive
    validation_level: strict
  
  flaky_detection:
    min_executions_reliable: 5  # Faster feedback
```

### CI/CD Pipeline

```yaml
crossbridge:
  mode: observer
  
  application:
    application_version: ${CI_COMMIT_TAG}
    environment: ${CI_ENVIRONMENT_NAME}
  
  translation:
    mode: automated      # Faster for CI
    validation_level: lenient
  
  sidecar_hooks:
    auto_integrate: true
```

### Production Monitoring

```yaml
crossbridge:
  mode: observer
  
  application:
    environment: production
  
  observer:
    flaky_threshold: 0.05  # Stricter
  
  intelligence:
    risk_based_recommendations: true
  
  flaky_detection:
    min_executions_confident: 50  # More data
```

### Multi-Environment Setup

Create separate configs:

- `crossbridge.dev.yml`
- `crossbridge.staging.yml`
- `crossbridge.production.yml`

Load with environment variable:

```bash
export CROSSBRIDGE_CONFIG=crossbridge.staging.yml
python your_script.py
```

## Migration from CLI Flags

### Before (CLI flags)

```bash
crossbridge translate \
  --source selenium \
  --target playwright \
  --mode automated \
  --use-ai \
  --max-credits 500 \
  --confidence-threshold 0.8 \
  --validation strict \
  --enable-sidecar \
  --sidecar-db-host 10.55.12.99
```

### After (Config file)

**crossbridge.yml**:
```yaml
crossbridge:
  translation:
    mode: automated
    use_ai: true
    max_credits: 500
    confidence_threshold: 0.8
    validation_level: strict
  
  sidecar_hooks:
    enabled: true
  
  database:
    host: 10.55.12.99
```

**Command**:
```bash
crossbridge translate --source selenium --target playwright
```

## Python API Reference

### Loading Configuration

```python
from core.config import get_config, reset_config, ConfigLoader

# Singleton access (recommended)
config = get_config()

# Explicit loading from path
config = ConfigLoader.load(Path("/path/to/config.yml"))

# Reset singleton (useful for testing)
reset_config()
```

### Accessing Settings

```python
config = get_config()

# Database
print(config.database.host)
print(config.database.connection_string)

# Translation
if config.translation.use_ai:
    print(f"AI enabled with {config.translation.max_credits} credits")

# Flaky Detection
if config.flaky_detection.enabled:
    print(f"Flaky threshold: {config.observer.flaky_threshold}")

# Frameworks
if config.frameworks.pytest.enabled:
    print("pytest instrumentation enabled")
```

### Saving Configuration

```python
from core.config import CrossBridgeConfig, ConfigLoader
from pathlib import Path

config = CrossBridgeConfig(
    mode="migration",
    # ... other settings
)

ConfigLoader.save(config, Path("crossbridge.yml"))
```

## Configuration Schema

### Complete YAML Structure

```yaml
crossbridge:
  mode: observer | migration
  
  application:
    product_name: string
    application_version: string
    environment: string
  
  database:
    enabled: bool
    host: string
    port: int
    database: string
    user: string
    password: string
  
  sidecar_hooks:
    enabled: bool
    auto_integrate: bool
  
  translation:
    mode: assistive | automated | batch
    use_ai: bool
    max_credits: int
    confidence_threshold: float (0.0-1.0)
    validation_level: strict | lenient | skip
    preserve_comments: bool
    inject_todos: bool
    max_workers: int (1-20)
    commit_batch_size: int (5-20)
  
  ai:
    enabled: bool
    provider: openai | anthropic | custom
    api_key: string
    endpoint: string | null
    model: string
    region: string
    temperature: float (0.0-1.0)
    max_tokens: int
    timeout: int
  
  flaky_detection:
    enabled: bool
    n_estimators: int
    contamination: float (0.0-1.0)
    random_state: int
    min_executions_reliable: int
    min_executions_confident: int
    min_confidence_threshold: float (0.0-1.0)
    execution_window_size: int
    recent_window_size: int
    auto_retrain: bool
    retrain_threshold: int
    model_version: string
  
  observer:
    auto_detect_new_tests: bool
    update_coverage_graph: bool
    detect_drift: bool
    flaky_threshold: float (0.0-1.0)
  
  intelligence:
    ai_enabled: bool
    detect_coverage_gaps: bool
    detect_redundant_tests: bool
    risk_based_recommendations: bool
  
  frameworks:
    pytest:
      enabled: bool
      auto_instrument_api_calls: bool
      auto_instrument_ui_interactions: bool
      capture_network_traffic: bool
      track_keywords: bool
      track_api_calls: bool
    # ... similar for playwright, robot, cypress
```

## Default Values

Complete list available in [crossbridge.yml](../crossbridge.yml)

**Key defaults**:
- `mode`: `observer`
- `database.host`: `10.55.12.99`
- `database.port`: `5432`
- `translation.mode`: `assistive`
- `translation.confidence_threshold`: `0.7`
- `ai.provider`: `openai`
- `ai.model`: `gpt-3.5-turbo`
- `ai.temperature`: `0.7`
- `flaky_detection.n_estimators`: `200`
- `flaky_detection.contamination`: `0.1`
- `observer.flaky_threshold`: `0.15`

## Troubleshooting

### Configuration Not Found

**Issue**: Config file not being discovered

**Solutions**:
1. Check file name: `crossbridge.yml` or `crossbridge.yaml`
2. Check location: project root or parent directories
3. Check permissions: file must be readable
4. Use explicit path: `ConfigLoader.load(Path("path/to/config.yml"))`

### Environment Variables Not Substituted

**Issue**: `${VAR_NAME}` appearing as literal text

**Solutions**:
1. Ensure syntax: `${VAR_NAME:-default}` (colon before dash)
2. Export variable: `export VAR_NAME=value`
3. Check spelling of variable name
4. Verify variable is set: `echo $VAR_NAME`

### Type Errors

**Issue**: Configuration values have wrong type

**Solutions**:
1. YAML booleans: `true`/`false` (lowercase, no quotes)
2. Numbers: No quotes around integers/floats
3. Strings: Use quotes for special characters
4. Check indentation (YAML is whitespace-sensitive)

### Values Not Updating

**Issue**: Configuration changes not taking effect

**Solutions**:
1. Singleton cache: Call `reset_config()` for testing
2. Check file location: ensure editing the right file
3. Syntax errors: validate YAML with linter
4. Restart application to reload config

## Best Practices

1. **Security**: Never commit API keys or passwords
   - Use environment variables: `${OPENAI_API_KEY}`
   - Use `.gitignore` for local config files
   
2. **Documentation**: Add comments to complex settings
   ```yaml
   # Flaky threshold: 15% = flag tests with >15% failure rate
   flaky_threshold: 0.15
   ```

3. **Validation**: Test configuration before deployment
   ```python
   config = get_config()
   assert config.database.connection_string
   assert config.ai.api_key != "sk-default"
   ```

4. **Environment-specific**: Use separate config files
   - Development: loose validation, local database
   - Production: strict validation, secure credentials

5. **Version Control**: Track config structure but not secrets
   ```bash
   # Commit structure
   git add crossbridge.example.yml
   
   # Never commit secrets
   echo "crossbridge.local.yml" >> .gitignore
   ```

## Support

- **Documentation**: [docs/CONFIG.md](CONFIG.md)
- **Issues**: File bugs on GitHub
- **Examples**: See [crossbridge.yml](../crossbridge.yml) for complete reference
- **Tests**: [tests/unit/core/test_config_loader.py](../tests/unit/core/test_config_loader.py)
