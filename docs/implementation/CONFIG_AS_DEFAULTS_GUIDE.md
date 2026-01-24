# CrossBridge AI: Config as Default Inputs - Integration Guide

## ✅ Yes! Config File Values Act as Default Inputs

When you run the CrossBridge AI application, **all values from `crossbridge.yml` act as default inputs** to the main program.

### Priority Order (High to Low)
1. **CLI Arguments** - Explicitly passed command-line flags
2. **Config File** - Values from `crossbridge.yml`
3. **Hardcoded Defaults** - Built-in fallback values

## 🎯 How It Works

### Configuration Loading Flow
```
Application Startup
    ↓
Load crossbridge.yml → Apply environment variables → Create config object
    ↓                         ↓                              ↓
Parse YAML file      ${VAR:-default}              Typed dataclasses
    ↓
Make available to entire application via get_config()
    ↓
CLI commands use config values as defaults
    ↓
CLI arguments override config values when provided
```

## 📝 Logging Configuration (NEW!)

### Complete Logging Settings

```yaml
logging:
  # Global log level
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  
  # Output format
  format: detailed  # simple, detailed, json
  
  # File logging
  log_to_file: true
  log_file_path: logs/crossbridge.log
  
  # Console logging
  log_to_console: true
  
  # Rotation
  max_file_size_mb: 10
  backup_count: 5
  
  # Component-specific overrides
  translation_level: null  # Override for translation module
  ai_level: DEBUG          # Debug AI interactions
  database_level: null     # Debug SQL queries
  observer_level: null     # Debug observer events
```

### Log Levels Explained

| Level | Description | Use Case |
|-------|-------------|----------|
| **DEBUG** | Detailed diagnostic info | Development, troubleshooting |
| **INFO** | General informational | Normal operation (default) |
| **WARNING** | Potential issues | Production monitoring |
| **ERROR** | Error conditions | Production, failure tracking |
| **CRITICAL** | Critical failures | System-level issues |

### Log Formats

#### Simple
```
2026-01-18 10:30:45 - INFO - Translation started
```

#### Detailed (Default)
```
2026-01-18 10:30:45 - crossbridge.translation - INFO - [pipeline.py:123] - Translation started
```

#### JSON (For Log Aggregation)
```json
{"timestamp": "2026-01-18 10:30:45", "level": "INFO", "module": "translation", "message": "Translation started"}
```

## 🔧 CLI Integration Pattern

### Example: Translation Command

**Before (Only CLI Flags)**:
```bash
crossbridge translate \
  --source selenium \
  --target playwright \
  --mode automated \
  --use-ai \
  --max-credits 500 \
  --validation strict
```

**After (Config + CLI)**:

**crossbridge.yml**:
```yaml
crossbridge:
  translation:
    mode: automated
    use_ai: true
    max_credits: 500
    validation_level: strict
```

**Command** (Much shorter!):
```bash
crossbridge translate --source selenium --target playwright
```

**Override when needed**:
```bash
crossbridge translate --source selenium --target playwright --mode assistive
# Uses mode=assistive from CLI, all other values from config
```

## 💻 Python Integration Code

### 1. Basic Pattern

```python
import click
from core.config import get_config

@click.command()
@click.option('--mode', default=None)
@click.option('--use-ai/--no-ai', default=None)
def translate(mode, use_ai):
    config = get_config()
    
    # CLI args override config
    final_mode = mode if mode is not None else config.translation.mode
    final_use_ai = use_ai if use_ai is not None else config.translation.use_ai
    
    print(f"Mode: {final_mode}")
    print(f"AI: {final_use_ai}")
```

### 2. Helper Function Pattern

```python
def get_effective_value(cli_value, config_value, default=None):
    """Priority: CLI > Config > Default"""
    return cli_value if cli_value is not None else (config_value or default)

@click.command()
@click.option('--db-host', default=None)
def command(db_host):
    config = get_config()
    host = get_effective_value(db_host, config.database.host, 'localhost')
```

### 3. Context-Based Pattern (Recommended)

```python
@click.group()
@click.pass_context
def main(ctx):
    """Load config once for all commands"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = get_config()

@main.command()
@click.pass_context
@click.option('--mode', default=None)
def translate(ctx, mode):
    config = ctx.obj['config']
    effective_mode = mode or config.translation.mode
```

## 🚀 Application Startup Integration

### Complete Startup Flow

```python
from core.config import get_config
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configure logging from config file"""
    config = get_config()
    log_config = config.logging
    
    # Setup based on config
    level = getattr(logging, log_config.level)
    
    # Format
    if log_config.format == 'simple':
        fmt = '%(asctime)s - %(levelname)s - %(message)s'
    elif log_config.format == 'json':
        fmt = '{"time": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s"}'
    else:  # detailed
        fmt = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    
    # Configure root logger
    logging.basicConfig(level=level, format=fmt)
    
    # File handler
    if log_config.log_to_file:
        handler = RotatingFileHandler(
            log_config.log_file_path,
            maxBytes=log_config.max_file_size_mb * 1024 * 1024,
            backupCount=log_config.backup_count
        )
        handler.setFormatter(logging.Formatter(fmt))
        logging.getLogger().addHandler(handler)

def main():
    # 1. Load config
    config = get_config()
    
    # 2. Setup logging
    setup_logging()
    
    # 3. Log startup
    logging.info("=" * 60)
    logging.info(f"CrossBridge {config.application.application_version}")
    logging.info(f"Mode: {config.mode}")
    logging.info(f"Config: {config._config_file or 'defaults'}")
    logging.info("=" * 60)
    
    # 4. Run application
    run_cli()
```

## 📊 Real-World Examples

### Example 1: Development Environment

**crossbridge.dev.yml**:
```yaml
crossbridge:
  application:
    environment: development
  
  database:
    host: localhost
    password: dev_password
  
  ai:
    enabled: false  # Save credits
  
  translation:
    mode: assistive
    validation_level: strict
  
  logging:
    level: DEBUG  # Verbose logging
    log_to_file: true
    log_to_console: true
```

**Usage**:
```bash
export CROSSBRIDGE_CONFIG=crossbridge.dev.yml
python -m crossbridge translate --source selenium --target playwright
# All settings from config, just specify source/target
```

### Example 2: CI/CD Pipeline

**crossbridge.ci.yml**:
```yaml
crossbridge:
  application:
    application_version: ${CI_COMMIT_TAG}
    environment: ${CI_ENVIRONMENT_NAME}
  
  database:
    host: ${CI_DB_HOST}
  
  translation:
    mode: automated  # No human intervention
    validation_level: lenient
  
  logging:
    level: INFO
    format: json  # For log aggregation
    log_to_file: true
    log_file_path: ${CI_PROJECT_DIR}/logs/crossbridge.log
```

**CI Script**:
```bash
export CI_COMMIT_TAG=$(git describe --tags)
export CI_ENVIRONMENT_NAME=staging
export CI_DB_HOST=staging-db.internal

python -m crossbridge translate --source selenium --target playwright
# Uses config with environment variables substituted
```

### Example 3: Production with Component-Specific Logging

**crossbridge.prod.yml**:
```yaml
crossbridge:
  application:
    environment: production
  
  database:
    host: prod-db-01.internal
  
  logging:
    level: WARNING  # Only warnings and errors
    format: json
    log_to_file: true
    log_to_console: false
    
    # Debug specific components
    ai_level: DEBUG  # Troubleshoot AI issues
    database_level: INFO  # Track DB queries
```

**Result**: Most of application logs at WARNING level, but AI module logs at DEBUG level.

## 🎯 Benefits Summary

### Before Unified Config
- ❌ Long CLI commands with 10+ flags
- ❌ Configuration scattered across files
- ❌ No central defaults
- ❌ Hard to maintain consistency
- ❌ Difficult CI/CD integration

### After Unified Config
- ✅ **Short CLI commands** - only specify what's different
- ✅ **Config as defaults** - YAML values automatically used
- ✅ **CLI overrides config** - flexibility when needed
- ✅ **Environment variables** - dynamic configuration
- ✅ **Single source of truth** - one place to configure
- ✅ **Logging included** - comprehensive log control
- ✅ **Type-safe** - validated configuration
- ✅ **CI/CD friendly** - environment-based configs

## 📚 Complete Integration Example

See [examples/cli_config_integration.py](../examples/cli_config_integration.py) for:

- ✅ CLI commands using config as defaults
- ✅ Helper functions for config priority
- ✅ Context-based config sharing
- ✅ Logging setup from config
- ✅ Complete application startup flow
- ✅ Real-world command examples

## 🔍 Verification

### Check Current Config
```python
from core.config import get_config

config = get_config()
print(f"Config file: {config._config_file}")
print(f"Log level: {config.logging.level}")
print(f"Translation mode: {config.translation.mode}")
print(f"AI enabled: {config.ai.enabled}")
```

### Show All Settings
```bash
python examples/cli_config_integration.py main show-config
```

### Test CLI Override
```bash
# Uses config defaults
python examples/cli_config_integration.py main translate --source selenium --target playwright

# Overrides mode from CLI
python examples/cli_config_integration.py main translate --source selenium --target playwright --mode automated
```

## 🎉 Summary

**Question 1: Will it cover log levels?**
- ✅ **YES!** Complete logging configuration added:
  - Global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Output format (simple, detailed, json)
  - File and console logging
  - Log rotation settings
  - Component-specific log level overrides

**Question 2: Will config values act as default inputs?**
- ✅ **YES!** Config values automatically become defaults:
  - Application loads `crossbridge.yml` at startup
  - All commands use config values as defaults
  - CLI arguments override config when provided
  - Environment variables can override YAML values
  - Priority: CLI args > Config file > Hardcoded defaults

---

**Implementation Status**: ✅ Complete and tested
**Files Updated**: `core/config/loader.py`, `crossbridge.yml`, `core/config/__init__.py`
**Example Code**: `examples/cli_config_integration.py`
