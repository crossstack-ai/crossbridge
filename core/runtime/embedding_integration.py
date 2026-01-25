"""
Runtime Integration for Embedding Providers

Wraps embedding provider calls with rate limiting, retry logic, and health checks.
"""

from typing import List, Optional

from core.logging import get_logger, LogCategory
from core.memory.embedding_provider import EmbeddingProvider, EmbeddingProviderError
from core.runtime import (
    retry_with_backoff,
    check_rate_limit,
    RateLimitExceeded,
    get_health_registry,
    VectorStoreHealthCheck,
    NetworkError,
    ServerError,
    load_runtime_config,
)

logger = get_logger(__name__, category=LogCategory.AI)


class HardenedEmbeddingProvider:
    """
    Wrapper around EmbeddingProvider with production hardening.
    
    Features:
    - Rate limiting per user/org
    - Exponential backoff retry
    - Health check registration
    - Automatic error conversion
    """
    
    def __init__(
        self,
        provider: EmbeddingProvider,
        rate_limit_key: Optional[str] = None,
        retry_policy_name: str = "expensive",
        enable_rate_limiting: bool = True,
        enable_retry: bool = True,
        enable_health_checks: bool = True,
    ):
        """
        Initialize hardened embedding provider.
        
        Args:
            provider: Underlying embedding provider
            rate_limit_key: Key for rate limiting (e.g., "user:123", "org:456")
            retry_policy_name: Retry policy (default, expensive, quick, conservative)
            enable_rate_limiting: Enable rate limiting (from YAML config)
            enable_retry: Enable retry logic (from YAML config)
            enable_health_checks: Enable health check registration (from YAML config)
        """
        self.provider = provider
        self.rate_limit_key = rate_limit_key or "default"
        self.retry_policy_name = retry_policy_name
        
        # Load runtime config
        config = load_runtime_config()
        
        self.enable_rate_limiting = enable_rate_limiting and config.rate_limiting.enabled
        self.enable_retry = enable_retry and config.retry.enabled
        self.enable_health_checks = enable_health_checks and config.health_checks.enabled
        
        # Register health check
        if self.enable_health_checks:
            registry = get_health_registry()
            health_check = VectorStoreHealthCheck(
                store=provider,
                name=f"embedding_provider_{provider.__class__.__name__}"
            )
            registry.register(health_check.name, health_check)
            logger.info(
                f"Registered health check for {provider.__class__.__name__}",
                extra={"provider": provider.__class__.__name__}
            )
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings with rate limiting and retry.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            RateLimitExceeded: If rate limit exceeded
            EmbeddingProviderError: If embedding fails after retries
        """
        # Check rate limit
        if self.enable_rate_limiting:
            operation = "embed"
            if not check_rate_limit(key=self.rate_limit_key, operation=operation):
                logger.warning(
                    f"Rate limit exceeded for {self.rate_limit_key}",
                    extra={
                        "rate_limit_key": self.rate_limit_key,
                        "operation": operation,
                        "text_count": len(texts),
                    }
                )
                raise RateLimitExceeded(f"Rate limit exceeded for {operation}")
        
        # Retry wrapper
        if self.enable_retry:
            def _call():
                try:
                    return self.provider.embed(texts)
                except EmbeddingProviderError as e:
                    # Convert to retryable error if appropriate
                    error_str = str(e).lower()
                    if "timeout" in error_str or "timed out" in error_str:
                        raise NetworkError(f"Embedding timeout: {e}")
                    elif "429" in error_str or "rate limit" in error_str:
                        raise ServerError(f"Rate limit: {e}")
                    elif "500" in error_str or "503" in error_str or "502" in error_str:
                        raise ServerError(f"Server error: {e}")
                    elif "connection" in error_str:
                        raise NetworkError(f"Connection error: {e}")
                    raise
                except Exception as e:
                    # Generic exception handling
                    error_str = str(e).lower()
                    if "timeout" in error_str:
                        raise NetworkError(f"Timeout: {e}")
                    elif "connection" in error_str:
                        raise NetworkError(f"Connection error: {e}")
                    raise
            
            try:
                result = retry_with_backoff(
                    _call,
                    policy_name=self.retry_policy_name,
                )
                logger.info(
                    "Embedding generation successful",
                    extra={
                        "text_count": len(texts),
                        "rate_limit_key": self.rate_limit_key,
                        "model": self.provider.model_name,
                    }
                )
                return result
            except Exception as e:
                logger.error(
                    f"Embedding failed after retries: {e}",
                    extra={
                        "text_count": len(texts),
                        "error": str(e),
                        "rate_limit_key": self.rate_limit_key,
                        "model": self.provider.model_name,
                    }
                )
                raise
        else:
            # No retry, direct call
            return self.provider.embed(texts)
    
    def get_dimension(self) -> int:
        """Return embedding dimension."""
        return self.provider.get_dimension()
    
    @property
    def model_name(self) -> str:
        """Return model name."""
        return self.provider.model_name


def harden_embedding_provider(
    provider: EmbeddingProvider,
    rate_limit_key: Optional[str] = None,
    retry_policy_name: str = "expensive",
) -> HardenedEmbeddingProvider:
    """
    Wrap an embedding provider with production hardening.
    
    Args:
        provider: Embedding provider to wrap
        rate_limit_key: Rate limit key (user:id, org:id)
        retry_policy_name: Retry policy name
        
    Returns:
        HardenedEmbeddingProvider instance
        
    Example:
        >>> from core.memory.embedding_provider import OpenAIEmbeddingProvider
        >>> provider = OpenAIEmbeddingProvider(model="text-embedding-3-large")
        >>> hardened = harden_embedding_provider(provider, rate_limit_key="user:123")
        >>> embeddings = hardened.embed(["test text"])
    """
    return HardenedEmbeddingProvider(
        provider=provider,
        rate_limit_key=rate_limit_key,
        retry_policy_name=retry_policy_name,
    )
