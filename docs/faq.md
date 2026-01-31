# Frequently Asked Questions

> **Common questions about CrossBridge AI**

## General

**Q: What is CrossBridge AI?**
A: CrossBridge is an open-source, AI-powered platform for analyzing, modernizing, and optimizing test automation without forcing rewrites or migrations.

**Q: Who created CrossBridge?**
A: CrossBridge AI is developed by CrossStack AI and the open-source community.

**Q: What license is CrossBridge under?**
A: Apache License 2.0

---

## Framework Support

**Q: What frameworks does CrossBridge support?**
A: 13+ frameworks including pytest, Selenium (Java/Python/.NET), Cypress, Playwright, Robot Framework, Cucumber, JBehave, TestNG, JUnit, NUnit, SpecFlow, Behave, and RestAssured.

**Q: Can I use CrossBridge without migrating my tests?**
A: Yes! Observer mode lets you get intelligence without changing test code.

**Q: How do I add support for my custom framework?**
A: Implement the `FrameworkAdapter` interface. See [Custom Adapters Guide](frameworks/CUSTOM_ADAPTERS.md).

---

## AI Features

**Q: Does CrossBridge require AI/LLM API keys?**
A: No. Most features work without AI. AI enhancement is optional.

**Q: Which AI providers are supported?**
A: OpenAI, Anthropic (Voyage AI), Ollama (local), HuggingFace (local).

**Q: How accurate is failure classification?**
A: 85-95% for common failure patterns using deterministic rules. AI can enhance but never overrides.

**Q: Can CrossBridge work offline?**
A: Yes, when AI features are disabled or using local providers (Ollama, HuggingFace).

---

## Deployment

**Q: Can CrossBridge run on-premises?**
A: Yes, fully on-premises deployment is supported with PostgreSQL/InfluxDB.

**Q: Is Docker required?**
A: No, but Docker makes deployment easier. Native installation supported.

**Q: What databases are supported?**
A: PostgreSQL (recommended), InfluxDB, or local file storage.

---

## Migration

**Q: Do I have to migrate all tests at once?**
A: No, CrossBridge supports incremental, batch-based migration.

**Q: Can I rollback migrations?**
A: Yes, every transformation is reversible with full audit trails.

**Q: How long does migration take?**
A: 2-4 weeks for 200-300 tests with AI assistance, depending on complexity.

---

## Performance

**Q: What's the overhead of the sidecar runtime?**
A: <1% CPU average, <100MB memory, <1ms latency per event.

**Q: Can CrossBridge handle large test suites?**
A: Yes, designed for enterprise scale (tested with 10,000+ tests).

---

## Security

**Q: Does CrossBridge log sensitive data?**
A: No by default. PII masking is configurable.

**Q: Is data encrypted?**
A: Database-level encryption recommended. TLS for network traffic.

---

## Cost

**Q: Is CrossBridge free?**
A: Yes, CrossBridge is open-source (Apache 2.0). AI provider costs (OpenAI, etc.) are separate.

**Q: What are typical AI costs?**
A: Embeddings: $0.002-$0.013 per 1000 tests. LLM usage is optional and varies.

---

## Getting Help

**Q: Where can I get support?**
A: GitHub Issues, Discussions, or community channels.

**Q: How do I contribute?**
A: See [Contributing Guidelines](contributing/CONTRIBUTING.md).

**Q: Where's the documentation?**
A: [docs/README.md](README.md)

---

More questions? [Open an issue](https://github.com/crossstack-ai/crossbridge/issues) or check the [docs](README.md).
