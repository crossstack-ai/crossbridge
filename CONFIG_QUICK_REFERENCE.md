# CrossBridge Configuration - Quick Reference

## 🚀 Quick Start (30 seconds)

### 1. Create Config File
```bash
cp crossbridge.yml my-project/crossbridge.yml
```

### 2. Edit Essential Settings
```yaml
crossbridge:
  application:
    product_name: MyApp
    application_version: v1.0.0
  
  database:
    host: localhost
    password: mypassword
  
  ai:
    api_key: ${OPENAI_API_KEY}
```

### 3. Use in Code
```python
from core.config import get_config

config = get_config()
db_url = config.database.connection_string
```

## 📝 Common Tasks

### Access Configuration
```python
from core.config import get_config

config = get_config()
```

### Database Connection
```python
conn_str = config.database.connection_string
# postgresql://user:pass@host:port/database
```

### Check AI Settings
```python
if config.ai.enabled:
    print(f"Using {config.ai.provider} with {config.ai.model}")
```

### Check Translation Mode
```python
if config.translation.mode == "automated":
    print("Running in automated mode")
```

## 🔧 Environment Variables

### CI/CD
```bash
export APP_VERSION=$(git describe --tags)
export CROSSBRIDGE_DB_HOST=prod-db.internal
export OPENAI_API_KEY=sk-...
```

### In Config File
```yaml
application:
  application_version: ${APP_VERSION:-v1.0.0}
database:
  host: ${CROSSBRIDGE_DB_HOST:-localhost}
ai:
  api_key: ${OPENAI_API_KEY}
```

## ⚙️ Essential Settings

### Application
```yaml
application:
  product_name: string        # Your app name
  application_version: string # Version being tested
  environment: string         # dev/staging/production
```

### Database
```yaml
database:
  host: string     # Database host
  port: int        # Default: 5432
  database: string # Database name
  user: string     # DB username
  password: string # DB password
```

### Translation
```yaml
translation:
  mode: assistive | automated | batch
  use_ai: true | false
  validation_level: strict | lenient | skip
```

### AI
```yaml
ai:
  enabled: true | false
  provider: openai | anthropic | custom
  api_key: string
  model: string  # gpt-3.5-turbo, gpt-4, claude-3-sonnet
```

## 🎯 Use Cases

### Local Development
```yaml
crossbridge:
  database:
    host: localhost
  ai:
    enabled: false  # Save credits
  flaky_detection:
    min_executions_reliable: 5  # Faster
```

### CI/CD Pipeline
```yaml
crossbridge:
  application:
    application_version: ${CI_COMMIT_TAG}
  translation:
    mode: automated
    validation_level: lenient
```

### Production
```yaml
crossbridge:
  application:
    environment: production
  observer:
    flaky_threshold: 0.05  # Stricter
  flaky_detection:
    min_executions_confident: 50
```

## 🐛 Troubleshooting

### Config Not Loading?
1. Check file name: `crossbridge.yml` or `crossbridge.yaml`
2. Check location: project root or parent directory
3. Verify YAML syntax (use linter)

### Environment Variables Not Working?
```yaml
# ✅ Correct
variable: ${VAR_NAME:-default}

# ❌ Wrong
variable: $VAR_NAME
variable: ${VAR_NAME-default}  # Missing colon
```

### Values Wrong Type?
```yaml
# ✅ Correct
enabled: true      # Boolean
port: 5432         # Number
name: "MyApp"      # String

# ❌ Wrong
enabled: "true"    # String not boolean
port: "5432"       # String not number
```

## 📚 Full Documentation

- **Complete Guide**: [docs/CONFIG.md](docs/CONFIG.md)
- **Full Config**: [crossbridge.yml](crossbridge.yml)
- **Implementation**: [UNIFIED_CONFIG_IMPLEMENTATION.md](UNIFIED_CONFIG_IMPLEMENTATION.md)

## 🔗 Python API

```python
# Import
from core.config import get_config, reset_config

# Load config
config = get_config()

# Access settings
config.database.host
config.translation.mode
config.ai.provider

# Reset (testing only)
reset_config()
```

## ✨ Default Values

| Setting | Default |
|---------|---------|
| mode | observer |
| database.host | 10.55.12.99 |
| database.port | 5432 |
| translation.mode | assistive |
| ai.provider | openai |
| ai.model | gpt-3.5-turbo |
| flaky_detection.n_estimators | 200 |
| observer.flaky_threshold | 0.15 |

---

**Need Help?** Check [docs/CONFIG.md](docs/CONFIG.md) for detailed documentation.
