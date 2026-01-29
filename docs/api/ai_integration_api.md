# AI Integration API Documentation

## Overview

CrossBridge provides a flexible AI integration framework that supports multiple LLM providers (OpenAI, Anthropic, Azure, self-hosted models) for test enhancement, code generation, and intelligent analysis.

## Core Architecture

### Provider Interface

All AI providers implement the `LLMProvider` interface:

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from core.ai.models import AIMessage, AIResponse, ModelConfig, AIExecutionContext

class LLMProvider(ABC):
    """Base interface for LLM providers."""
    
    @abstractmethod
    def complete(
        self,
        *,
        messages: List[AIMessage],
        model_config: ModelConfig,
        context: AIExecutionContext
    ) -> AIResponse:
        """
        Generate completion from messages.
        
        Args:
            messages: List of conversation messages
            model_config: Model configuration (temperature, max_tokens, etc.)
            context: Execution context with metadata
            
        Returns:
            AIResponse: Generated response with usage metrics
            
        Raises:
            AuthenticationError: Invalid API credentials
            RateLimitError: Rate limit exceeded
            ProviderError: Other provider-specific errors
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        pass
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost for token usage."""
        pass
```

## Supported Providers

### OpenAI Provider

```python
from core.ai.providers import OpenAIProvider
from core.ai.models import ModelConfig

# Initialize provider
provider = OpenAIProvider(config={
    "api_key": "your-api-key",  # Or set OPENAI_API_KEY env var
    "base_url": "https://api.openai.com/v1",  # Optional
    "organization": "org-id"  # Optional
})

# Configure model
model_config = ModelConfig(
    model_name="gpt-4",
    temperature=0.3,
    max_tokens=2000,
    top_p=1.0
)
```

### Anthropic Provider

```python
from core.ai.providers import AnthropicProvider

provider = AnthropicProvider(config={
    "api_key": "your-api-key",  # Or set ANTHROPIC_API_KEY env var
    "base_url": "https://api.anthropic.com"  # Optional
})

model_config = ModelConfig(
    model_name="claude-3-5-sonnet-20241022",
    temperature=0.3,
    max_tokens=4000
)
```

### Azure OpenAI Provider

```python
from core.ai.providers import AzureOpenAIProvider

provider = AzureOpenAIProvider(config={
    "api_key": "your-azure-key",
    "azure_endpoint": "https://your-resource.openai.azure.com",
    "api_version": "2024-02-15-preview",
    "deployment_name": "gpt-4-deployment"
})
```

### Self-Hosted Models

```python
from core.ai.providers import SelfHostedProvider

# For Ollama or other OpenAI-compatible endpoints
provider = SelfHostedProvider(config={
    "base_url": "http://localhost:11434/v1",
    "model_name": "llama2"
})
```

## AI Execution Context

The execution context provides metadata and constraints for AI operations:

```python
from core.ai.models import AIExecutionContext, ExecutionStatus

context = AIExecutionContext(
    task_id="enhance_test_001",
    framework="pytest",
    source_file="tests/test_login.py",
    user_id="developer@example.com",
    metadata={
        "test_count": 15,
        "complexity": "medium"
    },
    max_retries=3,
    timeout_seconds=30
)
```

## Message Format

Messages follow a standardized format:

```python
from core.ai.models import AIMessage, MessageRole

messages = [
    AIMessage(
        role=MessageRole.SYSTEM,
        content="You are a test automation expert..."
    ),
    AIMessage(
        role=MessageRole.USER,
        content="Transform this Selenium test to Playwright:\n\n" + test_code
    )
]
```

## Model Configuration

Configure model behavior:

```python
from core.ai.models import ModelConfig

config = ModelConfig(
    model_name="gpt-4",
    temperature=0.3,        # Lower = more deterministic
    max_tokens=2000,        # Maximum response length
    top_p=1.0,              # Nucleus sampling parameter
    frequency_penalty=0.0,  # Reduce repetition
    presence_penalty=0.0,   # Encourage diversity
    stop_sequences=["END"]  # Custom stop sequences
)
```

## Making AI Requests

### Basic Completion

```python
from core.ai.providers import get_provider
from core.ai.models import ProviderType

# Get configured provider
provider = get_provider(ProviderType.OPENAI)

# Prepare messages
messages = [
    AIMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
    AIMessage(role=MessageRole.USER, content="Explain test automation.")
]

# Generate completion
response = provider.complete(
    messages=messages,
    model_config=model_config,
    context=context
)

# Access response
print(response.content)
print(f"Tokens used: {response.usage.total_tokens}")
print(f"Cost: ${response.cost:.4f}")
```

### With Retries and Error Handling

```python
from core.ai.exceptions import RateLimitError, AuthenticationError

max_retries = 3
for attempt in range(max_retries):
    try:
        response = provider.complete(
            messages=messages,
            model_config=model_config,
            context=context
        )
        break
    except RateLimitError as e:
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # Exponential backoff
            time.sleep(wait_time)
        else:
            raise
    except AuthenticationError:
        # Don't retry authentication errors
        raise
```

## AI-Powered Features

### Test Enhancement

```python
from core.ai.enhancer import AITestEnhancer

enhancer = AITestEnhancer(provider=provider)

# Enhance a test with AI
enhanced_code = enhancer.enhance_test(
    source_code=original_test,
    framework="pytest",
    enhancements=[
        "add_docstrings",
        "improve_assertions",
        "add_error_handling",
        "modernize_locators"
    ]
)
```

### Code Transformation with AI

```python
from core.ai.transformer import AITransformer

transformer = AITransformer(provider=provider)

# Transform between frameworks
transformed = transformer.transform(
    source_code=selenium_test,
    source_framework="selenium",
    target_framework="playwright",
    preserve_structure=True
)
```

### Test Generation

```python
from core.ai.generator import AITestGenerator

generator = AITestGenerator(provider=provider)

# Generate tests from requirements
tests = generator.generate_from_requirements(
    requirements="""
    User Story: As a user, I want to login with email and password
    
    Acceptance Criteria:
    - Valid credentials should login successfully
    - Invalid credentials should show error message
    - Empty fields should be validated
    """,
    framework="pytest",
    page_objects=["LoginPage", "DashboardPage"]
)
```

### Intelligent Analysis

```python
from core.ai.analyzer import AITestAnalyzer

analyzer = AITestAnalyzer(provider=provider)

# Analyze test quality
analysis = analyzer.analyze_test_quality(
    test_code=test_content,
    metrics=["maintainability", "reliability", "performance"]
)

print(f"Quality score: {analysis.overall_score}/10")
for issue in analysis.issues:
    print(f"- {issue.severity}: {issue.description}")
```

## Prompt Engineering

### Custom Prompts

```python
from core.ai.prompts import PromptTemplate

# Define custom prompt template
template = PromptTemplate(
    system="You are a Playwright expert specializing in {specialty}.",
    user="Convert this {source_framework} test to Playwright:\n\n{code}"
)

# Render with variables
messages = template.render(
    specialty="accessibility testing",
    source_framework="Selenium",
    code=selenium_code
)
```

### Prompt Best Practices

1. **Be Specific**: Clearly state the desired output format
2. **Provide Context**: Include framework versions, constraints
3. **Use Examples**: Few-shot learning improves accuracy
4. **Set Boundaries**: Specify what NOT to do
5. **Request Explanations**: Ask for reasoning when needed

Example:

```python
system_prompt = """
You are an expert in test automation framework migration.

Your task: Convert Selenium WebDriver tests to Playwright.

Requirements:
- Use Playwright's modern locator strategies (getByRole, getByLabel, etc.)
- Replace explicit waits with Playwright's auto-waiting
- Convert assertions to Playwright expect() style
- Maintain test structure and readability
- Add TypeScript type hints if applicable

Do NOT:
- Change test logic or behavior
- Remove important assertions
- Simplify tests unnecessarily
- Add features not in the original test

Output: Only the converted test code, no explanations unless requested.
"""
```

## Cost Management

### Token Estimation

```python
from core.ai.utils import estimate_tokens

# Estimate tokens before making request
prompt_tokens = estimate_tokens(messages, model="gpt-4")
estimated_cost = provider.estimate_cost(
    prompt_tokens=prompt_tokens,
    completion_tokens=1000  # Estimated
)

print(f"Estimated cost: ${estimated_cost:.4f}")
```

### Cost Tracking

```python
from core.ai.governance import CostTracker

tracker = CostTracker()

# Track AI usage
tracker.record_usage(
    provider="openai",
    model="gpt-4",
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
    cost=response.cost,
    task="test_transformation"
)

# Get usage summary
summary = tracker.get_summary(period="today")
print(f"Total cost today: ${summary.total_cost:.2f}")
print(f"Total requests: {summary.request_count}")
```

## Model Selection

### Automatic Model Selection

```python
from core.ai.model_selector import SmartModelSelector

selector = SmartModelSelector()

# Select optimal model based on task
model = selector.select_model(
    task="test_transformation",
    complexity="medium",
    max_cost=0.10,
    preferred_provider="openai"
)

print(f"Selected: {model.model_name} (estimated cost: ${model.estimated_cost:.4f})")
```

### Task-Based Configuration

```yaml
# ai_config.yaml
model_selection:
  simple_tasks:
    models: ["gpt-3.5-turbo", "claude-3-haiku"]
    max_tokens: 1000
    temperature: 0.3
  
  medium_tasks:
    models: ["gpt-4-turbo", "claude-3-sonnet"]
    max_tokens: 2000
    temperature: 0.3
  
  complex_tasks:
    models: ["gpt-4", "claude-3-5-sonnet"]
    max_tokens: 4000
    temperature: 0.2
```

## Error Handling

### Exception Hierarchy

```python
from core.ai.exceptions import (
    AIError,              # Base exception
    AuthenticationError,  # Invalid credentials
    RateLimitError,       # Rate limit exceeded
    ProviderError,        # Provider-specific error
    TimeoutError,         # Request timeout
    InvalidResponseError  # Malformed response
)
```

### Graceful Fallback

```python
from core.ai.fallback import AIFallbackHandler

handler = AIFallbackHandler(
    primary_provider=openai_provider,
    fallback_providers=[anthropic_provider, azure_provider]
)

# Automatically try fallbacks on failure
response = handler.complete_with_fallback(
    messages=messages,
    model_config=config,
    context=context
)
```

## Caching

### Response Caching

```python
from core.ai.cache import AIResponseCache

cache = AIResponseCache(backend="file", ttl=86400)  # 24 hours

# Check cache before making request
cache_key = cache.generate_key(messages, model_config)
cached_response = cache.get(cache_key)

if cached_response:
    response = cached_response
else:
    response = provider.complete(messages, model_config, context)
    cache.set(cache_key, response)
```

## Configuration

### Environment Variables

```bash
# Provider API Keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export AZURE_OPENAI_KEY="..."

# Provider Configuration
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="gpt-4-deployment"

# Self-Hosted Models
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="llama2"
```

### Configuration File

```yaml
# crossbridge.yaml
ai:
  providers:
    openai:
      enabled: true
      default_model: "gpt-4"
      max_tokens: 2000
      temperature: 0.3
    
    anthropic:
      enabled: true
      default_model: "claude-3-5-sonnet-20241022"
      max_tokens: 4000
      temperature: 0.3
  
  features:
    test_enhancement: true
    code_generation: true
    intelligent_analysis: true
  
  cost_limits:
    daily_limit: 10.00
    monthly_limit: 200.00
    per_request_limit: 0.50
```

## Best Practices

1. **Use Specific Models for Tasks**: Don't use GPT-4 for simple tasks
2. **Implement Caching**: Cache responses to reduce costs
3. **Monitor Usage**: Track costs and usage patterns
4. **Handle Errors Gracefully**: Implement fallbacks and retries
5. **Optimize Prompts**: Shorter, clearer prompts = lower costs
6. **Validate Responses**: Always validate AI-generated code
7. **Use Async When Possible**: Improve throughput with async operations

## API Reference

### Core Modules

- `core.ai.base` - Base provider interface
- `core.ai.providers` - Provider implementations
- `core.ai.models` - Data models (AIMessage, AIResponse, etc.)
- `core.ai.enhancer` - Test enhancement utilities
- `core.ai.transformer` - AI-powered transformations
- `core.ai.analyzer` - Test analysis utilities
- `core.ai.governance` - Cost tracking and governance
- `core.ai.cache` - Response caching
- `core.ai.prompts` - Prompt templates and utilities

## Examples

See [examples/ai_integration/](../examples/ai_integration/) for complete examples of:

- Custom AI provider integration
- Advanced prompt engineering
- Batch AI processing
- Cost optimization strategies
- Error handling patterns

## Further Reading

- [AI Provider Integration Guide](../guides/ai_providers.md)
- [Prompt Engineering Best Practices](../guides/prompt_engineering.md)
- [Cost Optimization Strategies](../guides/cost_optimization.md)
