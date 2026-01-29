# CrossBridge Troubleshooting Guide

## Table of Contents

1. [Environment Setup Issues](#environment-setup-issues)
2. [Database Connection Problems](#database-connection-problems)
3. [AI Provider Issues](#ai-provider-issues)
4. [Test Collection and Parsing Errors](#test-collection-and-parsing-errors)
5. [Transformation and Migration Issues](#transformation-and-migration-issues)
6. [Performance Issues](#performance-issues)
7. [Framework-Specific Problems](#framework-specific-problems)
8. [Common Error Messages](#common-error-messages)

---

## Environment Setup Issues

### Python Version Compatibility

**Problem**: `SyntaxError` or `ImportError` when running CrossBridge

**Solution**:
```bash
# Check Python version (requires 3.9+)
python --version

# If using older version, install Python 3.11
# Ubuntu/Debian
sudo apt install python3.11

# macOS with Homebrew
brew install python@3.11

# Create virtual environment with correct version
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

### Missing Dependencies

**Problem**: `ModuleNotFoundError` for required packages

**Solution**:
```bash
# Install all dependencies
pip install -r requirements.txt

# If specific package fails, install individually
pip install --upgrade pip
pip install <package-name>

# For development dependencies
pip install -e ".[dev]"
```

### Permission Issues

**Problem**: `PermissionError` when accessing files or directories

**Solution**:
```bash
# Fix .env file permissions
chmod 600 .env

# Fix cache directory permissions
chmod 755 ~/.crossbridge/cache

# On Windows, right-click → Properties → Security → Edit permissions
```

---

## Database Connection Problems

### Connection Refused

**Problem**: `psycopg2.OperationalError: could not connect to server`

**Troubleshooting**:
```bash
# 1. Check if PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list | grep postgres  # macOS

# 2. Start PostgreSQL if not running
sudo systemctl start postgresql  # Linux
brew services start postgresql  # macOS

# 3. Test connection manually
psql -h localhost -U crossbridge_user -d crossbridge

# 4. Check environment variables
echo $DB_HOST
echo $DB_PORT
echo $DB_NAME
echo $DB_USER
```

**Solution**:
- Verify `DB_HOST` is correct (usually `localhost` or `127.0.0.1`)
- Check `DB_PORT` (default is `5432`)
- Ensure PostgreSQL service is running
- Verify firewall isn't blocking port 5432

### Authentication Failed

**Problem**: `psycopg2.OperationalError: FATAL: password authentication failed`

**Solution**:
```bash
# 1. Verify credentials
echo $DB_USER
echo $DB_PASSWORD

# 2. Reset password in PostgreSQL
sudo -u postgres psql
postgres=# ALTER USER crossbridge_user WITH PASSWORD 'new_password';
postgres=# \q

# 3. Update .env file
DB_PASSWORD=new_password

# 4. Test connection
python scripts/validate_environment.py
```

### Database Does Not Exist

**Problem**: `psycopg2.OperationalError: FATAL: database "crossbridge" does not exist`

**Solution**:
```bash
# Create database
sudo -u postgres psql
postgres=# CREATE DATABASE crossbridge;
postgres=# GRANT ALL PRIVILEGES ON DATABASE crossbridge TO crossbridge_user;
postgres=# \q

# Or use setup script
./scripts/setup_database.sh
```

### SSL Connection Issues

**Problem**: SSL-related connection errors

**Solution**:
```bash
# Disable SSL for local development
DB_SSL_MODE=disable

# For production with SSL
DB_SSL_MODE=require
# Provide SSL certificate if needed
DB_SSL_CERT=/path/to/client-cert.pem
DB_SSL_KEY=/path/to/client-key.pem
DB_SSL_ROOT_CERT=/path/to/root-cert.pem
```

---

## AI Provider Issues

### Invalid API Key

**Problem**: `AuthenticationError: Invalid API key`

**Troubleshooting**:
```bash
# 1. Verify API key format
# OpenAI: starts with 'sk-proj-' or 'sk-'
# Anthropic: starts with 'sk-ant-'
# Azure: no specific prefix

# 2. Check if key is set correctly
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# 3. Test API key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Solution**:
- Generate new API key from provider's dashboard
- Update `.env` file with new key
- Ensure no extra spaces or quotes in key value
- Reload environment variables: `source .env`

### Rate Limit Exceeded

**Problem**: `RateLimitError: Rate limit exceeded`

**Solution**:
```python
# Implement exponential backoff
import time

max_retries = 3
for attempt in range(max_retries):
    try:
        response = provider.complete(messages, config, context)
        break
    except RateLimitError:
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(wait_time)
        else:
            raise
```

Or configure rate limits:
```yaml
# crossbridge.yaml
ai:
  rate_limits:
    requests_per_minute: 10
    tokens_per_minute: 50000
```

### Timeout Errors

**Problem**: Requests timing out

**Solution**:
```bash
# Increase timeout in environment
REQUEST_TIMEOUT=60  # seconds

# Or in code
context = AIExecutionContext(
    task_id="task",
    timeout_seconds=60
)
```

### Provider Not Available

**Problem**: `ProviderError: Provider is not available`

**Troubleshooting**:
```bash
# 1. Check network connectivity
ping api.openai.com
ping api.anthropic.com

# 2. Check for proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY

# 3. Test endpoint directly
curl https://api.openai.com/v1/models

# 4. Verify firewall isn't blocking
```

**Solution**:
- Check internet connection
- Configure proxy if needed:
  ```bash
  export HTTPS_PROXY=http://proxy.company.com:8080
  ```
- Use alternative provider as fallback
- For self-hosted models, verify server is running

---

## Test Collection and Parsing Errors

### Tests Not Found

**Problem**: CrossBridge doesn't find any tests

**Solution**:
```bash
# 1. Verify test path
ls -la tests/

# 2. Check framework detection
crossbridge analyze --path tests/ --debug

# 3. Ensure test files follow naming conventions
# pytest: test_*.py or *_test.py
# Robot: *.robot
# Selenium Java: *Test.java or *Tests.java
```

### Parse Errors

**Problem**: `ParseError: Failed to parse test file`

**Troubleshooting**:
```bash
# 1. Check syntax of test file
python -m py_compile tests/test_file.py  # Python
robot --dryrun tests/test_file.robot  # Robot Framework

# 2. Enable debug logging
LOG_LEVEL=DEBUG crossbridge analyze --path tests/

# 3. Check for encoding issues
file tests/test_file.py  # Should show UTF-8
```

**Solution**:
- Fix syntax errors in test files
- Ensure files are UTF-8 encoded
- Check for unsupported framework features
- Update CrossBridge to latest version

### Import Errors During Collection

**Problem**: `ImportError` when collecting tests

**Solution**:
```bash
# 1. Install missing test dependencies
pip install pytest selenium playwright robotframework

# 2. Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 3. Check for circular imports
python -c "import tests.test_file"

# 4. Use isolated environment
crossbridge analyze --path tests/ --isolated
```

---

## Transformation and Migration Issues

### Transformation Fails

**Problem**: Code transformation produces invalid output

**Solution**:
```bash
# 1. Enable validation
crossbridge transform \
  --source selenium \
  --target playwright \
  --validate

# 2. Use AI enhancement for complex cases
crossbridge transform \
  --source selenium \
  --target playwright \
  --ai-enhance

# 3. Check transformation report
cat transformation_report.json
```

### Generated Code Has Syntax Errors

**Problem**: Generated code doesn't compile/run

**Troubleshooting**:
```bash
# 1. Validate generated code
python -m py_compile generated_test.py
pylint generated_test.py

# 2. Compare with original
diff original_test.py generated_test.py

# 3. Run with verbose output
crossbridge transform --verbose
```

**Solution**:
- Report issue with sample code
- Use manual review mode:
  ```bash
  crossbridge transform --review-mode
  ```
- Apply post-transformation fixes:
  ```python
  from core.translation.post_processor import PostProcessor
  processor = PostProcessor()
  fixed_code = processor.fix_common_issues(generated_code)
  ```

### Locators Not Converted Properly

**Problem**: Locators don't work in target framework

**Solution**:
```bash
# 1. Use modern locator strategy
crossbridge transform \
  --modernize-locators \
  --prefer-accessible-name

# 2. Manually review locators
crossbridge transform --export-locator-map

# 3. Use AI to improve locators
crossbridge transform --ai-enhance-locators
```

---

## Performance Issues

### Slow Test Analysis

**Problem**: Analysis takes too long for large repositories

**Solution**:
```bash
# 1. Increase worker threads
MAX_WORKERS=8 crossbridge analyze --path tests/

# 2. Use file filtering
crossbridge analyze --path tests/ --pattern "test_critical_*.py"

# 3. Enable caching
crossbridge analyze --path tests/ --cache

# 4. Skip AI features for initial analysis
ENABLE_AI_FEATURES=false crossbridge analyze --path tests/
```

### High Memory Usage

**Problem**: Out of memory errors

**Solution**:
```bash
# 1. Process in batches
crossbridge analyze --path tests/ --batch-size 100

# 2. Increase available memory
# Docker
docker run -m 4g crossbridge ...

# 3. Use streaming mode for large files
crossbridge analyze --stream

# 4. Clear cache
rm -rf ~/.crossbridge/cache/*
```

### Database Operations Slow

**Problem**: Database queries are slow

**Solution**:
```sql
-- 1. Add indexes
CREATE INDEX idx_test_executions_test_id ON test_executions(test_id);
CREATE INDEX idx_test_executions_executed_at ON test_executions(executed_at);

-- 2. Vacuum database
VACUUM ANALYZE;

-- 3. Check query performance
EXPLAIN ANALYZE SELECT * FROM test_executions WHERE test_id = 'test123';
```

---

## Framework-Specific Problems

### Selenium Issues

**Problem**: ChromeDriver version mismatch

**Solution**:
```bash
# Install webdriver-manager
pip install webdriver-manager

# Use in tests
from webdriver_manager.chrome import ChromeDriverManager
driver = webdriver.Chrome(ChromeDriverManager().install())
```

### Playwright Issues

**Problem**: Browsers not installed

**Solution**:
```bash
# Install browsers
playwright install

# Install specific browser
playwright install chromium

# Install with dependencies
playwright install --with-deps
```

### Robot Framework Issues

**Problem**: Keywords not found

**Solution**:
```bash
# 1. Check library installation
pip list | grep -i robot

# 2. Verify import in test
*** Settings ***
Library    SeleniumLibrary

# 3. Check PYTHONPATH
robot --pythonpath . tests/
```

### pytest Issues

**Problem**: Fixtures not discovered

**Solution**:
```bash
# 1. Check conftest.py location
# Should be in test directory or parent

# 2. Verify fixture scope
@pytest.fixture(scope="function")  # or "class", "module", "session"

# 3. Check for name conflicts
pytest --fixtures
```

---

## Common Error Messages

### `ModuleNotFoundError: No module named 'core'`

**Cause**: CrossBridge not installed or PYTHONPATH issue

**Solution**:
```bash
# Install in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### `FileNotFoundError: .env file not found`

**Cause**: Missing configuration file

**Solution**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### `ValueError: No AI providers configured`

**Cause**: Missing AI provider API keys

**Solution**:
```bash
# Add at least one provider to .env
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

### `RuntimeError: Event loop is closed`

**Cause**: Async operation issue in Playwright

**Solution**:
```python
# Use sync API
from playwright.sync_api import sync_playwright

# Or properly manage event loop
import asyncio
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
```

---

## Getting Help

### Debug Mode

Enable verbose logging:
```bash
LOG_LEVEL=DEBUG crossbridge <command>
```

### Generate Diagnostic Report

```bash
crossbridge diagnose --output diagnostic_report.json
```

### Check System Information

```bash
python scripts/system_info.py
```

### Report Issues

When reporting issues, include:
1. CrossBridge version: `crossbridge --version`
2. Python version: `python --version`
3. Operating system and version
4. Full error message and stack trace
5. Steps to reproduce
6. Relevant configuration (with secrets removed)

**GitHub Issues**: https://github.com/crossstack-ai/crossbridge/issues

### Community Support

- Documentation: `docs/`
- Examples: `examples/`
- FAQ: `docs/FAQ.md`

---

## Preventive Measures

### Regular Maintenance

```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Clean cache
rm -rf ~/.crossbridge/cache/*

# Vacuum database
psql -d crossbridge -c "VACUUM ANALYZE;"

# Update CrossBridge
pip install --upgrade crossbridge
```

### Best Practices

1. **Use Virtual Environments**: Isolate dependencies
2. **Keep Dependencies Updated**: Regular updates prevent issues
3. **Validate Configuration**: Run `scripts/validate_environment.py`
4. **Monitor Logs**: Check logs regularly for warnings
5. **Backup Database**: Regular backups of test data
6. **Test Changes**: Validate in staging before production

---

For additional help, see:
- [Configuration Guide](guides/configuration.md)
- [Environment Variables](ENVIRONMENT_VARIABLES.md)
- [API Documentation](api/)
- [Examples](../examples/)
