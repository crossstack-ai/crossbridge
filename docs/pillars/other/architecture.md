# CrossBridge Architecture

> **System design, components, and technical architecture**

Coming soon - comprehensive architecture documentation.

For now, see:
- [Architecture Directory](architecture/)
- [Implementation Summaries](implementation/)
- [Component Documentation](../core/)

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CrossBridge AI                        │
├─────────────────────────────────────────────────────────────┤
│  CLI Layer  │  MCP Server  │  Web API (planned)            │
├─────────────────────────────────────────────────────────────┤
│  Orchestration  │  Intelligence  │  AI/ML  │  Observability │
├─────────────────────────────────────────────────────────────┤
│  Framework Adapters (13+)  │  BDD  │  Parsers  │  Memory   │
├─────────────────────────────────────────────────────────────┤
│  Storage: PostgreSQL  │  InfluxDB  │  Vector (pgvector)    │
└─────────────────────────────────────────────────────────────┘
```

## Core Modules

- **Execution**: Test execution orchestration and intelligence
- **AI**: Semantic engine, embeddings, LLM integration
- **Observability**: Sidecar runtime, profiling, monitoring
- **BDD**: BDD framework adapters (Cucumber, Robot, JBehave)
- **Migration**: Framework migration and transformation
- **Memory**: Semantic memory and vector storage

Full architecture documentation coming soon.
