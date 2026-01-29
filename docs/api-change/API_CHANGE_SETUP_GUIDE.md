# API Change Intelligence - Setup Guide

## Overview

API Change Intelligence is a CrossBridge feature that automatically detects changes in OpenAPI/Swagger specifications and provides:

- **Incremental Documentation**: Automatic change logs in Markdown
- **Risk Analysis**: Rule-based + AI-powered risk assessment  
- **Test Recommendations**: Suggested tests for each change
- **Grafana Dashboards**: Visual monitoring of API changes over time
- **CI Integration**: Selective test execution based on impacts (coming soon)

## Prerequisites

### Required
- Python 3.9+ 
- PostgreSQL database (for storage)
- **oasdiff** tool (see installation below)

### Optional
- OpenAI API key (for AI-enhanced analysis)
- Grafana (for dashboards)

## Installation

### 1. Install oasdiff

oasdiff is a Go tool for comparing OpenAPI specs.

**Option A: Using Go**
```bash
go install github.com/tufin/oasdiff@latest
```

**Option B: Download Binary**
Download from: https://github.com/tufin/oasdiff/releases

**Verify Installation:**
```bash
oasdiff --version
```

Or use CrossBridge to check:
```bash
crossbridge api-diff check-deps
```

### 2. Database Setup

Add tables to your CrossBridge database:

```bash
# Run database migration (if you have migrations setup)
alembic upgrade head

# Or manually create tables using SQL from:
# core/intelligence/api_change/storage/schema.py
```

## Configuration

Add to your `crossbridge.yml`:

```yaml
crossbridge:
  # API Change Intelligence Configuration
  api_change:
    enabled: true  # Set to false to disable
    
    # Spec Sources
    spec_source:
      type: file  # file | url | git | auto
      current: specs/openapi.yaml
      previous: specs/openapi_prev.yaml
    
    # Intelligence Configuration
    intelligence:
      mode: hybrid  # none | rules | hybrid | ai-only
      
      # Rule-based (always enabled)
      rules:
        enabled: true
        detect_breaking: true
        calculate_risk: true
        recommend_tests: true
      
      # AI Enhancement (optional, requires API key)
      ai:
        enabled: false  # Set true to enable AI
        provider: openai
        model: gpt-4.1-mini
        max_tokens_per_run: 2000
        temperature: 0.2
        
        budgeting:
          monthly_token_limit: 5000000
          warn_at_percent: 80
    
    # Documentation Generation
    documentation:
      enabled: true
      output_dir: docs/api-changes
      
      formats:
        markdown:
          enabled: true
          file: api-changes.md
          append_mode: true
    
    # Grafana Observability
    observability:
      enabled: true
      grafana:
        dashboard_uid: api-change-intel
        auto_import: false
```

### Configuration Options

#### Spec Sources

**File-based:**
```yaml
spec_source:
  type: file
  current: specs/openapi-v2.yaml
  previous: specs/openapi-v1.yaml
```

**URL-based:**
```yaml
spec_source:
  type: url
  url:
    current: https://api.example.com/swagger.json
    previous: https://api.example.com/swagger-v1.json
    headers:
      Authorization: Bearer ${API_TOKEN}
```

**Git-based:**
```yaml
spec_source:
  type: git
  git:
    repo: .
    spec_path: docs/api/openapi.yaml
    current_commit: HEAD
    previous_commit: HEAD~1
```

## Usage

### Basic Usage

```bash
# Run API diff analysis
crossbridge api-diff run

# With verbose output
crossbridge api-diff run --verbose

# Enable AI (if configured)
crossbridge api-diff run --ai

# Custom output directory
crossbridge api-diff run --output-dir docs/my-api-changes
```

### CI/CD Integration

**GitHub Actions:**

```yaml
name: API Change Detection

on:
  pull_request:
    paths:
      - 'docs/api/openapi.yaml'

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 2  # Need previous commit
      
      - name: Install oasdiff
        run: |
          wget https://github.com/tufin/oasdiff/releases/download/v1.10.0/oasdiff_1.10.0_linux_amd64.tar.gz
          tar -xzf oasdiff_1.10.0_linux_amd64.tar.gz
          sudo mv oasdiff /usr/local/bin/
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install CrossBridge
        run: pip install -r requirements.txt
      
      - name: Run API Change Detection
        run: crossbridge api-diff run --verbose
      
      - name: Upload Change Documentation
        uses: actions/upload-artifact@v3
        with:
          name: api-changes
          path: docs/api-changes/
```

## Output

### Markdown Documentation

Generated at: `docs/api-changes/api-changes.md`

Example:
```markdown
## API Changes – 2026-01-29 10:45 UTC

**Summary:**
- ✅ Total Changes: 5
- ⚠️ Breaking Changes: 1
- 🔥 High Risk Changes: 2

### ➕ Added

#### `POST /api/v1/backup/jobs`
- **Risk:** 🟡 MEDIUM
- **Recommended Tests:**
  - Create positive test for POST /api/v1/backup/jobs
  - Verify authentication/authorization
  - Test error responses (400, 401, 403, 500)
```

### Console Output

```
============================================================
CrossBridge AI - API Change Intelligence
============================================================

[1/6] Collecting OpenAPI specifications...
  Previous version: 1.0.0
  Current version: 2.0.0

[2/6] Running oasdiff comparison...
  Found 1 breaking changes

[3/6] Normalizing changes...
  Normalized 5 changes

[4/6] Applying rule-based intelligence...

[5/6] Applying AI intelligence...
  AI intelligence disabled

[6/6] Generating documentation...
  Markdown documentation generated

============================================================
Analysis Complete!
============================================================
Total Changes: 5
Breaking Changes: 1
High Risk Changes: 2
Duration: 1234ms
============================================================

📝 Documentation: docs/api-changes/api-changes.md
```

## Grafana Dashboard

### Import Dashboard

1. Open Grafana
2. Go to Dashboards → Import
3. Upload `grafana/dashboards/api_change_intelligence.json`
4. Select your PostgreSQL datasource
5. Click Import

### Dashboard Panels

The dashboard includes:

- **API Changes Over Time**: Trend of all changes
- **Breaking vs Non-Breaking**: Safety monitoring
- **Risk Level Distribution**: Risk breakdown (Low/Medium/High/Critical)
- **High-Risk APIs Heatmap**: Which APIs change most
- **AI Usage**: AI vs rule-based detection
- **AI Token Usage**: Monthly token consumption
- **Change Type Breakdown**: Added/Modified/Removed
- **Recent Breaking Changes**: Latest breaking changes table

## Troubleshooting

### oasdiff not found

```
❌ oasdiff not found. Install it:
  go install github.com/tufin/oasdiff@latest
```

**Solution:** Install oasdiff (see Installation section)

### API Change Intelligence is disabled

```
⚠️ API Change Intelligence is disabled in config
```

**Solution:** Set `api_change.enabled: true` in `crossbridge.yml`

### Configuration not found

```
❌ api_change configuration not found in config file
```

**Solution:** Add `api_change:` section to `crossbridge.yml` (see Configuration section)

### Database connection errors

Make sure your PostgreSQL database is running and `CROSSBRIDGE_DB_URL` is set:

```bash
export CROSSBRIDGE_DB_URL="postgresql://user:pass@localhost:5432/crossbridge"
```

## Advanced Features (Coming Soon)

### Alert System
- Email notifications for breaking changes
- Slack integration
- Custom webhooks

### CI Trigger
- Selective test execution
- Automatic test impact analysis
- Test prioritization based on risk

### AI Enhancements
- Advanced risk prediction
- Historical correlation
- Semantic change understanding

## Support

For issues or questions:
- Email: vikas.sdet@gmail.com
- GitHub: https://github.com/crossstack-ai/crossbridge
- Website: https://crossstack.ai

---

**Built with ❤️ by CrossStack AI**
