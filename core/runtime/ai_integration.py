"""
Runtime Integration for AI Providers

Wraps AI provider calls with rate limiting, retry logic, and health checks.
"""

from typing import List, Dict, Any, Optional
from functools import wraps
import time

from core.logging import get_logger, LogCategory
from core.ai.base import LLMProvider, ProviderError, RateLimitError as AIRateLimitError
from core.ai.models import AIMessage, ModelConfig, AIExecutionContext, AIResponse
from core.runtime import (
    retry_with_backoff,
    RetryPolicy,
    check_rate_limit,
    RateLimitExceeded,
    get_health_registry,
    AIProviderHealthCheck,
    NetworkError,
    ServerError,
    convert_http_error_to_retry,
    load_runtime_config,
)

logger = get_logger(__name__, category=LogCategory.AI)


class HardenedAIProvider:
    """
    Wrapper around LLMProvider with production hardening.
    
    Features:
    - Rate limiting per user/org
    - Exponential backoff retry
    - Health check registration
    - Automatic error conversion
    """
    
    def __init__(
        self,
        provider: LLMProvider,
        rate_limit_key: Optional[str] = None,
        retry_policy_name: str = "expensive",
        enable_rate_limiting: bool = True,
        enable_retry: bool = True,
        enable_health_checks: bool = True,
    ):
        """
        Initialize hardened AI provider.
        
        Args:
            provider: Underlying LLM provider
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
            health_check = AIProviderHealthCheck(
                provider=provider,
                name=f"ai_provider_{provider.__class__.__name__}"
            )
            registry.register(health_check.name, health_check)
            logger.info(
                f"Registered health check for {provider.__class__.__name__}",
                extra={"provider": provider.__class__.__name__}
            )
    
    def complete(
        self,
        *,
        messages: List[AIMessage],
        model_config: ModelConfig,
        context: AIExecutionContext,
    ) -> AIResponse:
        """
        Generate completion with rate limiting and retry.
        
        Args:
            messages: Input messages
            model_config: Model configuration
            context: Execution context
            
        Returns:
            AIResponse with generated content
            
        Raises:
            RateLimitExceeded: If rate limit exceeded
            ProviderError: If generation fails after retries
        """
        # Check rate limit
        if self.enable_rate_limiting:
            operation = "ai_generate"
            if not check_rate_limit(key=self.rate_limit_key, operation=operation):
                logger.warning(
                    f"Rate limit exceeded for {self.rate_limit_key}",
                    extra={
                        "rate_limit_key": self.rate_limit_key,
                        "operation": operation,
                    }
                )
                raise RateLimitExceeded(f"Rate limit exceeded for {operation}")
        
        # Retry wrapper
        if self.enable_retry:
            def _call():
                try:
                    return self.provider.complete(
                        messages=messages,
                        model_config=model_config,
                        context=context,
                    )
                except AIRateLimitError as e:
                    # Convert to runtime RateLimitError for retry
                    raise ServerError(f"AI provider rate limit: {e}")
                except Exception as e:
                    # Convert to retryable error if appropriate
                    if "timeout" in str(e).lower():
                        raise NetworkError(f"Timeout: {e}")
                    elif "connection" in str(e).lower():
                        raise NetworkError(f"Connection error: {e}")
                    elif "500" in str(e) or "503" in str(e):
                        raise ServerError(f"Server error: {e}")
                    raise
            
            try:
                result = retry_with_backoff(
                    _call,
                    policy_name=self.retry_policy_name,
                )
                logger.info(
                    "AI generation successful",
                    extra={
                        "model": model_config.model,
                        "messages": len(messages),
                        "rate_limit_key": self.rate_limit_key,
                    }
                )
                return result
            except Exception as e:
                logger.error(
                    f"AI generation failed after retries: {e}",
                    extra={
                        "model": model_config.model,
                        "error": str(e),
                        "rate_limit_key": self.rate_limit_key,
                    }
                )
                raise
        else:
            # No retry, direct call
            return self.provider.complete(
                messages=messages,
                model_config=model_config,
                context=context,
            )
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings with rate limiting and retry.
        
        Args:
            texts: Texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            RateLimitExceeded: If rate limit exceeded
            ProviderError: If embedding fails after retries
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
        if self.enable_retry and hasattr(self.provider, 'embed'):
            def _call():
                try:
                    return self.provider.embed(texts)
                except Exception as e:
                    # Convert to retryable error if appropriate
                    if "timeout" in str(e).lower():
                        raise NetworkError(f"Timeout: {e}")
                    elif "429" in str(e):
                        raise ServerError(f"Rate limit: {e}")
                    elif "500" in str(e) or "503" in str(e):
                        raise ServerError(f"Server error: {e}")
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
                    }
                )
                raise
        else:
            # No retry or no embed method
            if hasattr(self.provider, 'embed'):
                return self.provider.embed(texts)
            else:
                raise NotImplementedError("Provider does not support embeddings")


def harden_ai_provider(
    provider: LLMProvider,
    rate_limit_key: Optional[str] = None,
    retry_policy_name: str = "expensive",
) -> HardenedAIProvider:
    """
    Wrap an AI provider with production hardening.
    
    Args:
        provider: LLM provider to wrap
        rate_limit_key: Rate limit key (user:id, org:id)
        retry_policy_name: Retry policy name
        
    Returns:
        HardenedAIProvider instance
        
    Example:
        >>> from core.ai.providers import OpenAIProvider
        >>> provider = OpenAIProvider(config={"api_key": "sk-..."})
        >>> hardened = harden_ai_provider(provider, rate_limit_key="user:123")
        >>> response = hardened.complete(messages=messages, model_config=config, context=ctx)
    """
    return HardenedAIProvider(
        provider=provider,
        rate_limit_key=rate_limit_key,
        retry_policy_name=retry_policy_name,
    )
