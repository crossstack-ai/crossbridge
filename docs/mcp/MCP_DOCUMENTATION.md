# Model Context Protocol (MCP) Integration

Copyright (c) 2025 Vikas Verma  
Licensed under the Apache License, Version 2.0

---

## Overview

CrossBridge AI integrates with the **Model Context Protocol (MCP)** to provide AI-powered test intelligence capabilities. MCP enables seamless communication between CrossBridge and various AI language models (LLMs) for enhanced test analysis, generation, and transformation.

---

## What is MCP?

The Model Context Protocol is a standardized interface for AI model integration that provides:

- **Unified AI Access** - Single interface for multiple AI providers (OpenAI, Anthropic, local models)
- **Context Management** - Efficient handling of test context for AI prompts
- **Streaming Support** - Real-time AI responses during transformations
- **Error Handling** - Graceful fallbacks when AI is unavailable
- **Cost Optimization** - Token usage tracking and cost management

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CrossBridge AI                          │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │  MCP Client  │────────▶│  MCP Server  │                │
│  └──────────────┘         └──────┬───────┘                │
│         │                         │                         │
│         │                         │                         │
│  ┌──────▼──────────────────────────▼─────┐                │
│  │        MCP Protocol Layer              │                │
│  │  - Request/Response handling           │                │
│  │  - Context serialization               │                │
│  │  - Token management                    │                │
│  └────────────────┬───────────────────────┘                │
│                   │                                         │
└───────────────────┼─────────────────────────────────────────┘
                    │
      ┌─────────────┴──────────────┐
      │                            │
┌─────▼──────┐            ┌───────▼───────┐
│  OpenAI    │            │  Anthropic    │
│  GPT-4     │            │  Claude 3.5   │
└────────────┘            └───────────────┘
```

---

## MCP Client

The **MCP Client** is embedded in CrossBridge and handles:

- Sending test transformation requests to AI models
- Managing conversation context for multi-turn interactions
- Token usage tracking and cost calculation
- Streaming responses during long transformations

### Client Configuration

Configure the MCP client in `crossbridge.yml`:

```yaml
mcp:
  client:
    enabled: true
    timeout: 30  # seconds
    retry_attempts: 3
    retry_delay: 2  # seconds
```

### Programmatic Usage

```python
from core.ai.mcp.client import MCPClient
from core.ai.providers import create_provider

# Initialize provider
provider = create_provider('openai', model='gpt-4', api_key='sk-...')

# Create MCP client
client = MCPClient(provider=provider)

# Send transformation request
response = client.transform_test(
    source_code="@Test\npublic void testLogin() { ... }",
    source_framework="junit",
    target_framework="pytest",
    context={
        "page_objects": ["LoginPage"],
        "dependencies": ["selenium"]
    }
)

print(response.transformed_code)
print(f"Tokens used: {response.token_count}")
print(f"Cost: ${response.cost:.4f}")
```

---

## MCP Server

The **MCP Server** can be run as a standalone service to handle AI requests for multiple CrossBridge instances.

### Why Use MCP Server?

- **Centralized AI** - Share AI quota across multiple teams/projects
- **Cost Control** - Monitor and limit AI spending
- **Caching** - Cache common transformations to reduce API calls
- **Audit Trail** - Log all AI requests for compliance

### Server Installation

```bash
# Install MCP server dependencies
pip install -r requirements-mcp.txt

# Start MCP server
python -m core.ai.mcp.server \
  --host 0.0.0.0 \
  --port 8080 \
  --provider openai \
  --api-key sk-...
```

### Server Configuration

Create `mcp_server.yml`:

```yaml
server:
  host: 0.0.0.0
  port: 8080
  workers: 4
  
providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    model: gpt-4
    max_tokens: 4000
    temperature: 0.3
  
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model: claude-3-5-sonnet-20240620
    max_tokens: 4000
    temperature: 0.3
  
cache:
  enabled: true
  backend: redis
  redis_url: redis://localhost:6379/0
  ttl: 86400  # 24 hours
  
rate_limiting:
  enabled: true
  requests_per_minute: 60
  requests_per_hour: 1000
  
logging:
  level: INFO
  file: /var/log/mcp-server.log
  audit_enabled: true
```

### Client Configuration for Server

Configure CrossBridge clients to use MCP server:

```yaml
mcp:
  client:
    mode: server  # Use MCP server instead of direct AI calls
    server_url: http://mcp-server:8080
    api_key: ${MCP_SERVER_API_KEY}
    timeout: 60
```

---

## AI Providers

CrossBridge MCP supports multiple AI providers:

### OpenAI

```yaml
mcp:
  provider:
    type: openai
    api_key: ${OPENAI_API_KEY}
    model: gpt-4  # or gpt-3.5-turbo, gpt-4-turbo
    max_tokens: 4000
    temperature: 0.3
    organization: ${OPENAI_ORG}  # optional
```

**Supported Models:**
- `gpt-4` - Highest quality (expensive)
- `gpt-4-turbo` - Fast and affordable
- `gpt-3.5-turbo` - Budget-friendly

### Anthropic Claude

```yaml
mcp:
  provider:
    type: anthropic
    api_key: ${ANTHROPIC_API_KEY}
    model: claude-3-5-sonnet-20240620
    max_tokens: 4000
    temperature: 0.3
```

**Supported Models:**
- `claude-3-5-sonnet-20240620` - Best for code (recommended)
- `claude-3-opus-20240229` - Highest quality
- `claude-3-haiku-20240307` - Fastest and cheapest

### Local Models (Ollama)

```yaml
mcp:
  provider:
    type: ollama
    base_url: http://localhost:11434
    model: codellama:7b
    temperature: 0.3
```

**Supported Models:**
- `codellama:7b` - Code-focused, 7B parameters
- `codellama:13b` - Higher quality
- `deepseek-coder:6.7b` - Excellent for code

---

## Context Management

MCP efficiently manages test context for AI prompts:

### Context Types

1. **File Context** - Source file being transformed
2. **Framework Context** - Source/target framework information
3. **Dependency Context** - Related page objects, utilities
4. **Historical Context** - Previous transformations for learning

### Context Example

```python
context = {
    "source_file": {
        "path": "tests/LoginTest.java",
        "content": "...",
        "language": "java",
        "framework": "junit"
    },
    "dependencies": [
        {
            "type": "page_object",
            "name": "LoginPage",
            "content": "..."
        }
    ],
    "target": {
        "framework": "pytest",
        "language": "python"
    },
    "preferences": {
        "locator_strategy": "data-testid",
        "assertion_style": "pytest",
        "async_preferred": True
    }
}
```

---

## Token Usage & Cost Tracking

MCP tracks token usage and costs for all AI operations:

### Per-Request Tracking

```python
response = client.transform_test(source_code, ...)

print(f"Prompt tokens: {response.prompt_tokens}")
print(f"Completion tokens: {response.completion_tokens}")
print(f"Total tokens: {response.total_tokens}")
print(f"Cost: ${response.cost:.4f}")
```

### Aggregate Statistics

```bash
# View MCP usage statistics
python -m cli.app mcp stats

# Output:
Total Requests: 142
Total Tokens: 1,245,320
Total Cost: $2.49

By Provider:
  OpenAI (GPT-4): 98 requests, $1.96
  Anthropic (Claude): 44 requests, $0.53

By Operation:
  Test Transformation: 120 requests, $2.20
  Code Analysis: 15 requests, $0.21
  Documentation: 7 requests, $0.08
```

---

## Streaming Responses

For long transformations, MCP supports streaming:

```python
for chunk in client.transform_test_streaming(source_code, ...):
    if chunk.type == 'code':
        print(chunk.content, end='', flush=True)
    elif chunk.type == 'metadata':
        print(f"\n[Tokens: {chunk.tokens}]")
```

---

## Error Handling & Fallbacks

MCP provides graceful fallbacks when AI is unavailable:

```yaml
mcp:
  fallback:
    enabled: true
    strategy: pattern_based  # Use pattern-based transformation
    cache_responses: true    # Cache AI responses for reuse
```

**Fallback Hierarchy:**

1. **AI Response** - Primary method
2. **Cached Response** - If identical request seen before
3. **Pattern-Based** - Rule-based transformation
4. **Manual Placeholder** - Generate TODO markers

---

## Security & Privacy

### API Key Management

**Never commit API keys!** Use environment variables:

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

Or use secrets management:

```bash
# AWS Secrets Manager
export OPENAI_API_KEY=$(aws secretsmanager get-secret-value --secret-id openai-key --query SecretString --output text)

# HashiCorp Vault
export OPENAI_API_KEY=$(vault kv get -field=api_key secret/openai)
```

### Data Privacy

By default, MCP:

- ✅ Does NOT store code on AI provider servers (ephemeral)
- ✅ Does NOT share code between organizations
- ✅ Respects data retention policies

For sensitive code, use **local models** (Ollama):

```yaml
mcp:
  provider:
    type: ollama  # Runs entirely on your infrastructure
    base_url: http://localhost:11434
```

---

## Monitoring & Observability

### Prometheus Metrics

MCP exports metrics for monitoring:

```
# HELP mcp_requests_total Total MCP requests
# TYPE mcp_requests_total counter
mcp_requests_total{provider="openai",operation="transform"} 142

# HELP mcp_tokens_total Total tokens consumed
# TYPE mcp_tokens_total counter
mcp_tokens_total{provider="openai",type="prompt"} 850000
mcp_tokens_total{provider="openai",type="completion"} 395320

# HELP mcp_cost_total Total cost in USD
# TYPE mcp_cost_total counter
mcp_cost_total{provider="openai"} 2.49
```

### Grafana Dashboard

Import `grafana/mcp_dashboard.json` for:

- Request rate and success rate
- Token usage over time
- Cost tracking and budget alerts
- Provider comparison

---

## Best Practices

### 1. Choose the Right Model

| Use Case | Recommended Model | Reason |
|----------|-------------------|--------|
| Production transformations | Claude 3.5 Sonnet | Best code quality |
| Development/testing | GPT-3.5 Turbo | Fast and cheap |
| Sensitive code | Ollama CodeLlama | Private, no API |
| High volume | GPT-4 Turbo | Good balance |

### 2. Optimize Token Usage

- **Minimize context** - Only include necessary files
- **Cache responses** - Enable caching for repeated requests
- **Batch operations** - Transform multiple files in one request

### 3. Set Cost Limits

```yaml
mcp:
  cost_limits:
    per_request: 0.10   # Max $0.10 per request
    per_hour: 5.00      # Max $5/hour
    per_day: 50.00      # Max $50/day
```

### 4. Monitor Quality

Regularly review AI-generated code:

```bash
# Compare AI vs pattern-based quality
python -m cli.app analyze quality \
  --ai-output transformed_ai/ \
  --pattern-output transformed_pattern/
```

---

## Examples

### Example 1: Transform JUnit → pytest

```python
from core.ai.mcp import MCPClient, create_provider

provider = create_provider('openai', model='gpt-4', api_key='sk-...')
client = MCPClient(provider)

junit_test = """
@Test
public void testUserLogin() {
    LoginPage page = new LoginPage(driver);
    page.login("admin", "pass123");
    assertTrue(page.isLoggedIn());
}
"""

result = client.transform_test(
    source_code=junit_test,
    source_framework="junit",
    target_framework="pytest",
    context={"page_objects": ["LoginPage"]}
)

print(result.transformed_code)
# Output:
# def test_user_login(login_page):
#     login_page.login("admin", "pass123")
#     assert login_page.is_logged_in()
```

### Example 2: Analyze Flaky Test

```python
result = client.analyze_code(
    code=failing_test_code,
    analysis_type="flaky_detection",
    context={
        "failure_history": [
            {"date": "2026-01-20", "error": "TimeoutException"},
            {"date": "2026-01-21", "error": "StaleElementException"}
        ]
    }
)

print(result.insights)
# Output:
# - Likely flaky due to timing issues
# - Recommendation: Add explicit waits
# - Confidence: 0.87
```

---

## Troubleshooting

### MCP Client Not Connecting

```bash
# Test connectivity
python -m core.ai.mcp.test_connection \
  --provider openai \
  --api-key sk-...

# Expected output:
✓ Connection successful
✓ Model accessible: gpt-4
✓ Token count: 15
```

### High Token Usage

```bash
# Analyze token usage
python -m cli.app mcp analyze-usage --last-24h

# Output shows top consumers:
1. LongTestFile.java: 45,000 tokens ($0.90)
   Recommendation: Split into smaller files

2. PageObjectWithComments.java: 38,000 tokens ($0.76)
   Recommendation: Remove verbose comments
```

### Rate Limiting

If hitting rate limits:

```yaml
mcp:
  rate_limiting:
    requests_per_minute: 10  # Reduce from default
    exponential_backoff: true
    max_retries: 5
```

---

## API Reference

### MCPClient

```python
class MCPClient:
    def __init__(self, provider: AIProvider, config: MCPConfig = None):
        """Initialize MCP client with AI provider"""
    
    def transform_test(
        self,
        source_code: str,
        source_framework: str,
        target_framework: str,
        context: dict = None
    ) -> TransformationResponse:
        """Transform test code from one framework to another"""
    
    def analyze_code(
        self,
        code: str,
        analysis_type: str,
        context: dict = None
    ) -> AnalysisResponse:
        """Analyze code for issues, patterns, or improvements"""
    
    def generate_tests(
        self,
        specification: str,
        framework: str,
        context: dict = None
    ) -> GenerationResponse:
        """Generate new tests from specification"""
```

---

## Further Reading

- **[AI Setup Guide](../ai/AI_SETUP.md)** - Configure AI providers
- **[AI Transformation Usage](../ai/AI_TRANSFORMATION_USAGE.md)** - Use AI for migrations
- **[API Documentation](../api/API.md)** - Complete API reference

---

## Support

For MCP-specific issues:

- **📧 Email**: vikas.sdet@gmail.com
- ** Issues**: [GitHub Issues](https://github.com/crossstack-ai/crossbridge/issues)

---

**Powered by CrossBridge AI - Intelligent Test Modernization**
