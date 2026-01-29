# Testing Documentation

Documentation related to testing features, credentials management, and test impact analysis.

## Testing Features

- **[TEST_CREDENTIALS_CACHING.md](TEST_CREDENTIALS_CACHING.md)** - Guide to credential caching for secure test execution including encryption, storage, and retrieval patterns
- **[TEST_CREDS_CLI_COMMAND.md](TEST_CREDS_CLI_COMMAND.md)** - CLI commands for managing test credentials including setup, configuration, and usage examples
- **[testing-impact-mapping.md](testing-impact-mapping.md)** - Test impact mapping and analysis documentation for understanding test coverage and dependencies

## Feature Overview

### Credentials Management
CrossBridge provides secure credential management for test execution:
- Encrypted credential storage
- Automatic credential caching
- CLI-based credential management
- Environment-specific credential isolation

See:
- [TEST_CREDENTIALS_CACHING.md](TEST_CREDENTIALS_CACHING.md) for implementation details
- [TEST_CREDS_CLI_COMMAND.md](TEST_CREDS_CLI_COMMAND.md) for command reference

### Test Impact Analysis
Understand how code changes affect your test suite:
- Test-to-code mapping
- Impact analysis and coverage
- Test prioritization strategies
- Change risk assessment

See [testing-impact-mapping.md](testing-impact-mapping.md) for details.

## Quick Start

### Setting Up Test Credentials
```bash
# Configure credentials via CLI
crossbridge test-creds setup

# Cache credentials for a test run
crossbridge test-creds cache --env production

# View cached credentials
crossbridge test-creds list
```

### Running Impact Analysis
```bash
# Analyze test impact for recent changes
crossbridge analyze impact --since HEAD~5

# Generate impact report
crossbridge analyze impact --report
```

## Testing Best Practices

1. **Secure Credentials**: Always use encrypted credential storage
2. **Environment Isolation**: Separate credentials by environment (dev/staging/prod)
3. **Impact Analysis**: Run impact analysis before large test suite executions
4. **Credential Rotation**: Regularly rotate cached credentials
5. **Coverage Monitoring**: Track test coverage and impact metrics

## Related Documentation

- **Guides**: See [../guides/](../guides/) for technical testing guides
- **Configuration**: See [../configuration/](../configuration/) for test environment setup
- **Reports**: See [../reports/](../reports/) for test execution reports

---

*For the complete documentation index, see [../project/INDEX.md](../project/INDEX.md)*
