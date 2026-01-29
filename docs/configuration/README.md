# Configuration & Environment

Configuration guides, environment setup, and troubleshooting documentation.

## Configuration Files

- **[ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)** - Complete reference for all environment variables used by CrossBridge including database, AI, Grafana, and framework-specific settings

## Troubleshooting

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Comprehensive troubleshooting guide covering common issues, error messages, and their solutions

## Quick Reference

### Environment Setup
The [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) guide covers:
- Database configuration (PostgreSQL/SQLite)
- AI service configuration (OpenAI, Anthropic, Gemini)
- Grafana integration settings
- Framework adapter settings
- Memory and caching configuration
- Logging and debug options

### Common Issues
The [TROUBLESHOOTING.md](TROUBLESHOOTING.md) guide provides solutions for:
- Database connection issues
- AI service integration problems
- Parser and transformation errors
- Performance and memory issues
- Framework-specific problems

## Configuration Best Practices

1. **Use Environment Files**: Store configuration in `.env` files (never commit sensitive data)
2. **Validate Settings**: Use the built-in configuration validation tools
3. **Document Changes**: Keep track of custom configuration changes
4. **Test Configurations**: Verify settings in development before deploying to production
5. **Secure Secrets**: Use secret management tools for API keys and credentials

## Related Documentation

- **Guides**: See [../guides/](../guides/) for technical implementation guides
- **Testing**: See [../testing/](../testing/) for test configuration options
- **Project**: See [../project/](../project/) for project-level documentation

---

*For the complete documentation index, see [../project/INDEX.md](../project/INDEX.md)*
