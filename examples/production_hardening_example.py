"""
Integration Example: Production Hardening

Demonstrates how to wire rate limiting, retries, and health checks together
for production-ready API calls and provider access.
"""

from core.runtime import (
    RateLimiter,
    retry_with_backoff,
    RetryPolicy,
    NetworkError,
    HealthRegistry,
    AIProviderHealthCheck,
    VectorStoreHealthCheck
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Example 1: Hardened Semantic Search
def hardened_semantic_search(query: str, user_id: str, embedding_provider, vector_store):
    """
    Production-grade semantic search with rate limiting, retries, and health checks.
    
    Args:
        query: Search query
        user_id: User identifier for rate limiting
        embedding_provider: Provider with embed() method
        vector_store: Vector store with search() method
        
    Returns:
        Search results
        
    Raises:
        RateLimitExceeded: If user exceeds rate limit
        Exception: If all retries exhausted
    """
    rate_limiter = RateLimiter()
    
    # 1. Check rate limit (30 requests per minute per user)
    if not rate_limiter.check(user_id, capacity=30, window_seconds=60):
        raise Exception(f"Rate limit exceeded for user {user_id}")
    
    # 2. Retry embedding generation with backoff
    embedding = retry_with_backoff(
        lambda: embedding_provider.embed([query]),
        RetryPolicy(max_attempts=3, base_delay=0.5)
    )
    
    # 3. Retry vector search with backoff
    results = retry_with_backoff(
        lambda: vector_store.search(embedding[0], limit=10),
        RetryPolicy(max_attempts=3, base_delay=0.5)
    )
    
    return results


# Example 2: AI Provider with All Hardening
class HardenedAIProvider:
    """
    AI provider wrapper with rate limiting, retries, and health checks.
    """
    
    def __init__(self, provider, user_id: str):
        self.provider = provider
        self.user_id = user_id
        self.rate_limiter = RateLimiter()
        self.retry_policy = RetryPolicy(
            max_attempts=4,
            base_delay=0.5,
            max_delay=5.0
        )
    
    def embed(self, texts: list) -> list:
        """
        Generate embeddings with rate limiting and retries.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings
        """
        # Rate limit: 60 requests per minute
        if not self.rate_limiter.check(
            self.user_id,
            capacity=60,
            window_seconds=60
        ):
            raise Exception(f"Rate limit exceeded for {self.user_id}")
        
        # Retry on transient failures
        return retry_with_backoff(
            lambda: self.provider.embed(texts),
            self.retry_policy
        )
    
    def transform(self, code: str, target: str) -> str:
        """
        Transform code with rate limiting and retries.
        
        Args:
            code: Source code
            target: Target framework
            
        Returns:
            Transformed code
        """
        # Different rate limit for expensive operations (10 per minute)
        if not self.rate_limiter.check(
            f"{self.user_id}_transform",
            capacity=10,
            window_seconds=60
        ):
            raise Exception(f"Transform rate limit exceeded for {self.user_id}")
        
        # More aggressive retry for transformations
        return retry_with_backoff(
            lambda: self.provider.transform(code, target),
            RetryPolicy(max_attempts=5, base_delay=1.0, max_delay=10.0)
        )
    
    def health_check(self) -> bool:
        """Check provider health."""
        try:
            self.provider.embed(["health_check"])
            return True
        except Exception:
            return False


# Example 3: Service Health Monitoring
def setup_health_monitoring(embedding_provider, vector_store, ai_provider):
    """
    Set up comprehensive health monitoring.
    
    Args:
        embedding_provider: Embedding provider
        vector_store: Vector store
        ai_provider: AI transformation provider
        
    Returns:
        HealthRegistry configured with all checks
    """
    registry = HealthRegistry()
    
    # Register health checks
    registry.register(
        "embedding_provider",
        AIProviderHealthCheck("embeddings", embedding_provider)
    )
    
    registry.register(
        "vector_store",
        VectorStoreHealthCheck("vectors", vector_store)
    )
    
    registry.register(
        "ai_provider",
        AIProviderHealthCheck("ai", ai_provider)
    )
    
    return registry


# Example 4: Request Handler with Full Stack
def handle_user_request(
    request_type: str,
    user_id: str,
    data: dict,
    providers: dict
):
    """
    Handle user request with full production hardening.
    
    Execution flow:
    1. Health checks
    2. Rate limiting
    3. Retries with backoff
    4. Error handling
    
    Args:
        request_type: Type of request (search, transform, etc.)
        user_id: User identifier
        data: Request data
        providers: Dict of service providers
        
    Returns:
        Response data
    """
    # 1. Health checks
    health_registry = providers.get('health_registry')
    if health_registry:
        health = health_registry.run_all()
        if not health['healthy']:
            logger.warning(f"Degraded health: {health['failed']} checks failed")
            # In production, might use fallback providers here
    
    # 2. Rate limiting
    rate_limiter = RateLimiter()
    
    # Different limits based on request type
    rate_limits = {
        'search': (30, 60),      # 30 per minute
        'transform': (10, 60),   # 10 per minute
        'embed': (60, 60)        # 60 per minute
    }
    
    capacity, window = rate_limits.get(request_type, (30, 60))
    
    if not rate_limiter.check(f"{user_id}_{request_type}", capacity, window):
        raise Exception(
            f"Rate limit exceeded for {user_id}: "
            f"{capacity} {request_type} requests per {window}s"
        )
    
    # 3. Execute with retries
    retry_policy = RetryPolicy(max_attempts=3, base_delay=0.5)
    
    def execute_request():
        if request_type == 'search':
            query = data['query']
            provider = providers['search']
            return provider.search(query)
        
        elif request_type == 'transform':
            code = data['code']
            target = data['target']
            provider = providers['ai']
            return provider.transform(code, target)
        
        elif request_type == 'embed':
            texts = data['texts']
            provider = providers['embedding']
            return provider.embed(texts)
        
        else:
            raise ValueError(f"Unknown request type: {request_type}")
    
    try:
        result = retry_with_backoff(execute_request, retry_policy)
        return {
            'success': True,
            'data': result,
            'user_id': user_id
        }
    
    except Exception as e:
        logger.error(f"Request failed for {user_id}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id
        }


# Example 5: Production Defaults
PRODUCTION_RATE_LIMITS = {
    'search': (30, 60),           # 30 searches per minute
    'transform': (10, 60),        # 10 transforms per minute
    'embed': (60, 60),            # 60 embeds per minute
    'health_check': (10, 60),     # 10 health checks per minute
}

PRODUCTION_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=0.5,
    max_delay=5.0,
    jitter=True
)

EXPENSIVE_OPERATION_RETRY = RetryPolicy(
    max_attempts=5,
    base_delay=1.0,
    max_delay=10.0,
    jitter=True
)


if __name__ == '__main__':
    print("Production Hardening Integration Examples")
    print("=" * 60)
    print()
    print("✅ Rate Limiting: Token bucket per user/org")
    print("✅ Retries: Exponential backoff with jitter")
    print("✅ Health Checks: Provider monitoring")
    print()
    print("See source code for usage examples:")
    print("  - hardened_semantic_search()")
    print("  - HardenedAIProvider class")
    print("  - setup_health_monitoring()")
    print("  - handle_user_request()")
