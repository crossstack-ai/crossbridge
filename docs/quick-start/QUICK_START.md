# CrossBridge AI - Quick Start Guide

Copyright (c) 2025 Vikas Verma  
Licensed under the Apache License, Version 2.0

---

## 🚀 Quick Start

Get started with CrossBridge AI in minutes - choose your mode based on your needs.

---

## Prerequisites

Before starting, ensure you have:

- **Python 3.8+** installed
- **Git** for cloning the repository
- **PostgreSQL** (optional, for persistence features)
- **Grafana** (optional, for dashboards)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/crossstack-ai/crossbridge.git
cd crossbridge
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Verify Installation

```bash
python -m cli.app --version
```

---

## Choose Your Mode

CrossBridge AI offers two primary modes of operation:

### Mode 1: NO MIGRATION (Sidecar Observer) ⭐ Recommended

**Best for:** Teams wanting intelligence on existing tests without any code changes.

**What you get:**
- Coverage tracking
- Flaky test detection
- Risk scores
- Test optimization insights
- Zero code changes required

[→ Jump to No-Migration Setup](#no-migration-mode-setup)

### Mode 2: FULL MIGRATION (Transformation)

**Best for:** Teams ready to modernize their test framework.

**What you get:**
- Legacy → Modern framework transformation
- Selenium → Playwright/Robot Framework
- BDD transformation
- AI-enhanced code quality

[→ Jump to Migration Setup](#migration-mode-setup)

---

## No-Migration Mode Setup

### Step 1: Configure Environment

```bash
export CROSSBRIDGE_ENABLED=true
export CROSSBRIDGE_DB_HOST=localhost
export CROSSBRIDGE_DB_PORT=5432
export CROSSBRIDGE_DB_NAME=crossbridge
export CROSSBRIDGE_DB_USER=postgres
export CROSSBRIDGE_DB_PASSWORD=admin
export CROSSBRIDGE_APPLICATION_VERSION=v2.0.0
```

Or create a `.env` file:

```env
CROSSBRIDGE_ENABLED=true
CROSSBRIDGE_DB_HOST=localhost
CROSSBRIDGE_DB_PORT=5432
CROSSBRIDGE_DB_NAME=crossbridge
CROSSBRIDGE_DB_USER=postgres
CROSSBRIDGE_DB_PASSWORD=admin
CROSSBRIDGE_APPLICATION_VERSION=v2.0.0
```

### Step 2: Add Framework Listener/Plugin

Choose your framework and add the appropriate hook:

#### Selenium Java (TestNG)

Add to `testng.xml`:

```xml
<listeners>
  <listener class-name="com.crossbridge.CrossBridgeListener"/>
</listeners>
```

#### Selenium Java (JUnit)

Add to your test class:

```java
@RunWith(CrossBridgeRunner.class)
public class MyTest {
    // your tests
}
```

#### Python pytest

Add to `conftest.py`:

```python
pytest_plugins = ["crossbridge.pytest_plugin"]
```

#### Robot Framework

Add to your robot file or command line:

```robot
*** Settings ***
Library    CrossBridgeListener
```

Or via command line:

```bash
robot --listener CrossBridgeListener tests/
```

#### Cypress

Update `cypress.config.js`:

```javascript
const { defineConfig } = require('cypress');
const crossbridge = require('crossbridge-cypress');

module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      crossbridge.register(on, { enabled: true });
      return config;
    },
  },
});
```

#### Playwright

Update `playwright.config.ts`:

```typescript
import { defineConfig } from '@playwright/test';
import { CrossBridgeReporter } from 'crossbridge-playwright';

export default defineConfig({
  reporter: [['list'], [CrossBridgeReporter]],
});
```

### Step 3: Run Your Tests

Run your tests normally:

```bash
# For TestNG
mvn test

# For pytest
pytest tests/

# For Robot Framework
robot tests/

# For Cypress
npx cypress run

# For Playwright
npx playwright test
```

### Step 4: View Intelligence

#### Via Grafana Dashboards

1. Import dashboard: `grafana/flaky_dashboard_fixed.json`
2. Configure PostgreSQL datasource
3. View real-time analytics

#### Via CLI

```bash
# List flaky tests
python -m cli.app flaky list

# Coverage report
python -m cli.app coverage report

# Memory search
python -m cli.app search query "login tests"
```

📖 **Learn More**: [No-Migration Framework Support](../sidecar/NO_MIGRATION_IMPLEMENTATION_COMPLETE.md)

---

## Migration Mode Setup

### Step 1: Start Interactive CLI

```bash
python -m cli.app
```

### Step 2: Select Migration Mode

Choose "Migration + Transformation" from the menu.

### Step 3: Configure Source Framework

Select your source framework:

- Selenium Java + Cucumber
- Selenium Python + pytest
- .NET SpecFlow
- RestAssured (API tests)
- Other supported frameworks

### Step 4: Connect Repository

Choose your repository type:

- **Bitbucket** - Cloud or Server
- **GitHub** - Public or Enterprise
- **Azure DevOps** - Azure Repos
- **Local** - Local filesystem

Provide credentials if needed (tokens, passwords).

### Step 5: Configure Paths

Specify:

- **Step definitions path** - Location of your step definitions
- **Page objects path** - Location of your page objects
- **Feature files path** - Location of Gherkin features
- **Output path** - Where to generate transformed tests

### Step 6: Select Transformation Mode

Choose transformation quality:

- **Manual** - Fast, creates TODOs for manual review
- **Enhanced** - Smart extraction with pattern matching (recommended)
- **Hybrid** - AI-enhanced with human review markers (best quality)

### Step 7: Enable AI (Optional)

If you want AI-powered transformation:

```bash
export OPENAI_API_KEY=sk-your-key-here
# or
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Configure in CLI when prompted.

### Step 8: Run Migration

Review configuration and start migration:

```
✓ Source: Selenium Java + Cucumber
✓ Target: Robot Framework + Playwright
✓ Repository: GitHub (crossstack-ai/my-tests)
✓ Mode: Enhanced
✓ AI: Enabled (OpenAI GPT-4)

Proceed? [Y/n]: Y

🚀 Starting migration...
```

### Step 9: Review Output

After migration completes:

1. **Check generated branch** - `crossbridge-migration-<timestamp>`
2. **Review transformation report** - `migration_report.html`
3. **Validate tests** - Run validation checks
4. **Merge when ready** - Create PR for review

📖 **Learn More**: [AI Transformation Usage](../ai/AI_TRANSFORMATION_USAGE.md)

---

## Next Steps

### For No-Migration Users

1. **Set up Grafana** - [Grafana Setup Guide](../observability/CONTINUOUS_INTELLIGENCE_README.md)
2. **Configure CI/CD** - [CI/CD Integration](../ci-cd/CI_CD_FLAKY_INTEGRATION.md)
3. **Explore Memory** - [Memory & Embeddings](../memory/MEMORY_EMBEDDINGS_SYSTEM.md)

### For Migration Users

1. **Validate tests** - [Post-Migration Testing](../POST_MIGRATION_TESTING.md)
2. **Customize adapters** - [Adapter Development](../frameworks/FRAMEWORK_ADAPTERS_REFERENCE.md)
3. **Enhance with AI** - [AI Setup](../ai/AI_SETUP.md)

---

## Common Issues & Troubleshooting

### Database Connection Issues

```bash
# Test connection
psql -h localhost -U postgres -d crossbridge

# Create database if missing
createdb -h localhost -U postgres crossbridge
```

### Listener Not Working

Ensure classpath includes CrossBridge JAR:

```bash
# For Java/TestNG
-classpath /path/to/crossbridge-listener.jar

# Or add to pom.xml dependency
```

### API Keys Not Working

```bash
# Verify OpenAI key
python -c "import openai; openai.api_key='sk-...'; print(openai.Model.list())"

# Verify Anthropic key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "content-type: application/json"
```

### Grafana Dashboards Empty

1. Check PostgreSQL datasource connection
2. Verify data exists: `SELECT COUNT(*) FROM test_execution;`
3. Check dashboard time range settings
4. Review [Grafana Comprehensive Troubleshooting](../observability/GRAFANA_COMPREHENSIVE_TROUBLESHOOTING.md)

---

## Configuration Files

### crossbridge.yml

Create `crossbridge.yml` in your project root:

```yaml
crossbridge:
  enabled: true
  
  database:
    enabled: true
    host: ${CROSSBRIDGE_DB_HOST:-localhost}
    port: ${CROSSBRIDGE_DB_PORT:-5432}
    database: ${CROSSBRIDGE_DB_NAME:-crossbridge}
    user: ${CROSSBRIDGE_DB_USER:-postgres}
    password: ${CROSSBRIDGE_DB_PASSWORD}
  
  memory:
    enabled: true
    embedding_provider:
      type: openai
      model: text-embedding-3-large
      api_key: ${OPENAI_API_KEY}
    vector_store:
      type: pgvector
      dimension: 3072
  
  flaky_detection:
    enabled: true
    ml_algorithm: isolation_forest
    threshold: 0.7
  
  coverage:
    enabled: true
    track_behavioral: true
    track_functional: true
```

📖 **Complete reference**: [Configuration Guide](../config/CONFIG.md)

---

## Video Tutorials

Coming soon! We're working on video tutorials for:

- ✅ 5-minute No-Migration setup
- ✅ Complete migration walkthrough
- ✅ Grafana dashboard setup
- ✅ AI-powered transformation

---

## Support & Help

Need help getting started?

- **📖 Documentation**: [Complete Index](../INDEX.md)
- ** Issues**: [Report Problems](https://github.com/crossstack-ai/crossbridge/issues)
- **📧 Email**: vikas.sdet@gmail.com

---

**Ready to modernize your test automation? Let's get started!** 🚀
