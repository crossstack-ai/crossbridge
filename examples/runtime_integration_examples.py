"""
Production Runtime Integration Examples

Real-world examples of integrating production hardening with CrossBridge features.
"""

# ============================================================================
# Example 1: Hardened AI Provider
# ============================================================================

from core.ai.providers import OpenAIProvider
from core.runtime import harden_ai_provider
from core.ai.models import AIMessage, ModelConfig, AIExecutionContext

# Create base provider
base_provider = OpenAIProvider(config={"api_key": "sk-..."})

# Wrap with production hardening
hardened_provider = harden_ai_provider(
    provider=base_provider,
    rate_limit_key="user:12345",  # Per-user rate limiting
    retry_policy_name="expensive",  # 5 retries for expensive AI calls
)

# Use normally - rate limiting and retries are automatic
messages = [AIMessage(role="user", content="Explain pytest")]
config = ModelConfig(model="gpt-4", temperature=0.7)
context = AIExecutionContext(user_id="12345", operation="test_generation")

try:
    response = hardened_provider.complete(
        messages=messages,
        model_config=config,
        context=context,
    )
    print(f"Success: {response.content}")
except Exception as e:
    print(f"Failed after retries: {e}")


# ============================================================================
# Example 2: Hardened Embedding Provider
# ============================================================================

from core.memory.embedding_provider import OpenAIEmbeddingProvider
from core.runtime import harden_embedding_provider

# Create base embedding provider
base_embedder = OpenAIEmbeddingProvider(
    model="text-embedding-3-large",
    api_key="sk-...",
)

# Wrap with production hardening
hardened_embedder = harden_embedding_provider(
    provider=base_embedder,
    rate_limit_key="org:premium_org",  # Per-org rate limiting
    retry_policy_name="expensive",  # Retry on transient failures
)

# Use normally - rate limiting and retries are automatic
texts = [
    "Test case for login functionality",
    "Test case for checkout process",
]

try:
    embeddings = hardened_embedder.embed(texts)
    print(f"Generated {len(embeddings)} embeddings")
except Exception as e:
    print(f"Embedding failed: {e}")


# ============================================================================
# Example 3: Database Operations with Retry
# ============================================================================

import psycopg2
from core.runtime import with_database_retry, harden_database_connection

# Option A: Decorator approach
@with_database_retry(retry_policy_name="quick", operation_name="get_test_results")
def get_test_results(conn, test_id: str):
    """Query with automatic retry on connection errors."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM test_results WHERE test_id = %s", (test_id,))
    return cursor.fetchall()

# Option B: Wrapper approach
conn = psycopg2.connect("postgresql://localhost/crossbridge")
hardened_conn = harden_database_connection(conn, retry_policy_name="quick")

# Queries automatically retry on transient failures
cursor = hardened_conn.execute("SELECT * FROM flaky_tests")
results = cursor.fetchall()


# ============================================================================
# Example 4: Health Check Monitoring
# ============================================================================

from core.runtime import get_health_registry

# Get global health registry
registry = get_health_registry()

# Check overall health
if registry.is_healthy():
    print("✓ All systems operational")
else:
    # Get failed checks
    failed = registry.get_failed_checks()
    print(f"⚠ {len(failed)} systems degraded:")
    for name, result in failed.items():
        print(f"  - {name}: {result.message}")

# Run all health checks and get detailed status
status = registry.run_all()
print(f"Status: {status}")
print(f"Checked: {len(registry.get_all())} providers")


# ============================================================================
# Example 5: Full Stack Integration
# ============================================================================

from core.runtime import (
    harden_ai_provider,
    harden_embedding_provider,
    register_database_health_check,
    get_health_registry,
    load_runtime_config,
)
from core.ai.providers import OpenAIProvider
from core.memory.embedding_provider import OpenAIEmbeddingProvider
import psycopg2

def setup_production_hardening(user_id: str):
    """
    Complete production hardening setup for CrossBridge.
    
    This sets up:
    - AI provider with rate limiting and retry
    - Embedding provider with rate limiting and retry
    - Database health checks
    - All configured via crossbridge.yml
    """
    # Load configuration
    config = load_runtime_config()
    
    # 1. Setup AI Provider
    ai_provider = OpenAIProvider(config={"api_key": "sk-..."})
    hardened_ai = harden_ai_provider(
        provider=ai_provider,
        rate_limit_key=f"user:{user_id}",
        retry_policy_name="expensive",  # From YAML config
    )
    
    # 2. Setup Embedding Provider
    embedding_provider = OpenAIEmbeddingProvider(model="text-embedding-3-large")
    hardened_embeddings = harden_embedding_provider(
        provider=embedding_provider,
        rate_limit_key=f"user:{user_id}",
        retry_policy_name="expensive",  # From YAML config
    )
    
    # 3. Setup Database Health Check
    def check_db():
        try:
            conn = psycopg2.connect("postgresql://localhost/crossbridge")
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.debug(f"Database health check failed: {e}")
            return False
    
    register_database_health_check(check_db, "postgresql")
    
    # 4. Verify health
    registry = get_health_registry()
    if registry.is_healthy():
        print("✓ Production hardening initialized successfully")
    else:
        print("⚠ Some health checks failed")
        for name, result in registry.get_failed_checks().items():
            print(f"  - {name}: {result.message}")
    
    return {
        "ai_provider": hardened_ai,
        "embedding_provider": hardened_embeddings,
        "health_registry": registry,
    }


# ============================================================================
# Example 6: Using with Semantic Search
# ============================================================================

from core.runtime import retry_with_backoff, check_rate_limit, RateLimitExceeded

def hardened_semantic_search(query: str, user_id: str):
    """
    Semantic search with production hardening.
    
    Features:
    - Rate limiting per user
    - Retry on transient failures
    - Structured logging
    """
    # Check rate limit
    if not check_rate_limit(key=f"user:{user_id}", operation="search"):
        raise RateLimitExceeded("Search rate limit exceeded")
    
    # Retry wrapper
    def _search():
        # Your semantic search logic here
        embeddings = hardened_embedder.embed([query])
        results = vector_store.search(embeddings[0], top_k=10)
        return results
    
    # Automatically retries on transient failures
    results = retry_with_backoff(
        _search,
        policy_name="default",  # From YAML config
    )
    
    return results


# ============================================================================
# Example 7: Configuration-Driven Setup
# ============================================================================

from core.runtime import load_runtime_config, get_rate_limit_for_operation

# Load configuration from crossbridge.yml
config = load_runtime_config()

# Check if features are enabled
if config.rate_limiting.enabled:
    print("✓ Rate limiting enabled")
    
    # Get operation-specific limits
    search_limits = get_rate_limit_for_operation("search")
    print(f"  Search: {search_limits['capacity']} per {search_limits['window_seconds']}s")
    
    embed_limits = get_rate_limit_for_operation("embed")
    print(f"  Embed: {embed_limits['capacity']} per {embed_limits['window_seconds']}s")

if config.retry.enabled:
    print("✓ Retry logic enabled")
    print(f"  Default policy: {config.retry.default_policy['max_attempts']} attempts")
    print(f"  Expensive policy: {config.retry.expensive_policy['max_attempts']} attempts")

if config.health_checks.enabled:
    print("✓ Health checks enabled")
    print(f"  Interval: {config.health_checks.interval}s")
    print(f"  Timeout: {config.health_checks.timeout}s")
    
    # Check provider status
    for provider_name, provider_config in config.health_checks.providers.items():
        if provider_config.get("enabled"):
            print(f"  - {provider_name}: {provider_config.get('check_type')}")


# ============================================================================
# Example 8: Testing with Mock Providers
# ============================================================================

from core.runtime import HardenedAIProvider

class MockAIProvider:
    """Mock AI provider for testing."""
    
    def complete(self, *, messages, model_config, context):
        return {"content": "Mock response", "tokens": 100}
    
    def embed(self, texts):
        return [[0.1] * 1536 for _ in texts]

# Wrap mock with production hardening for integration tests
mock_provider = MockAIProvider()
hardened_mock = HardenedAIProvider(
    provider=mock_provider,
    rate_limit_key="test:123",
    retry_policy_name="quick",
)

# Test rate limiting
for i in range(100):
    try:
        response = hardened_mock.complete(
            messages=[],
            model_config=None,
            context=None,
        )
    except RateLimitExceeded:
        print(f"Rate limit exceeded after {i} calls")
        break


if __name__ == "__main__":
    print("Production Runtime Integration Examples")
    print("=" * 70)
    
    # Run Example 5: Full stack setup
    print("\nExample 5: Full Stack Integration")
    print("-" * 70)
    services = setup_production_hardening(user_id="demo_user")
    
    print("\nExample 7: Configuration-Driven Setup")
    print("-" * 70)
    config = load_runtime_config()
    print(f"Rate limiting: {config.rate_limiting.enabled}")
    print(f"Retry logic: {config.retry.enabled}")
    print(f"Health checks: {config.health_checks.enabled}")
    
    print("\n✓ All examples completed")
