"""
AI Analyzer Integration for Test Intelligence.

This module provides the actual AI integration layer that:
- Connects to OpenAI/Azure OpenAI APIs
- Manages prompts and responses
- Handles rate limiting and retries
- Caches results for efficiency
"""

from typing import Optional, Dict, Any, List
import logging
import hashlib
import json
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Try to import OpenAI (optional dependency)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not installed. AI enrichment will be disabled.")


@dataclass
class AIAnalyzerConfig:
    """Configuration for AI analyzer."""
    api_key: Optional[str] = None
    api_base: Optional[str] = None  # For Azure OpenAI
    api_type: str = "openai"  # "openai" or "azure"
    api_version: Optional[str] = None  # For Azure
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 500
    timeout: int = 30
    max_retries: int = 2
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour


@dataclass
class CachedResponse:
    """Cached AI response."""
    response: str
    timestamp: datetime
    model: str
    confidence: float


class ResponseCache:
    """Simple in-memory cache for AI responses."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, CachedResponse] = {}
        self.ttl_seconds = ttl_seconds
    
    def _get_key(self, prompt: str, model: str) -> str:
        """Generate cache key from prompt and model."""
        content = f"{prompt}:{model}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, prompt: str, model: str) -> Optional[str]:
        """Get cached response if available and not expired."""
        key = self._get_key(prompt, model)
        
        if key not in self.cache:
            return None
        
        cached = self.cache[key]
        age = datetime.now(timezone.utc) - cached.timestamp
        
        if age.total_seconds() > self.ttl_seconds:
            # Expired, remove from cache
            del self.cache[key]
            return None
        
        logger.debug("Cache hit for prompt (age: %.1fs)", age.total_seconds())
        return cached.response
    
    def set(self, prompt: str, model: str, response: str, confidence: float = 1.0):
        """Cache a response."""
        key = self._get_key(prompt, model)
        self.cache[key] = CachedResponse(
            response=response,
            timestamp=datetime.now(timezone.utc),
            model=model,
            confidence=confidence
        )
    
    def clear(self):
        """Clear all cached responses."""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now(timezone.utc)
        valid_count = sum(
            1 for cached in self.cache.values()
            if (now - cached.timestamp).total_seconds() <= self.ttl_seconds
        )
        
        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_count,
            "ttl_seconds": self.ttl_seconds
        }


class AIAnalyzer:
    """
    AI Analyzer for test intelligence enrichment.
    
    This class provides the actual AI integration, handling:
    - API calls to OpenAI/Azure OpenAI
    - Response caching
    - Rate limiting
    - Retry logic
    - Error handling
    """
    
    def __init__(self, config: Optional[AIAnalyzerConfig] = None):
        """
        Initialize AI analyzer.
        
        Args:
            config: Optional configuration
        """
        self.config = config or AIAnalyzerConfig()
        self.cache = ResponseCache(ttl_seconds=self.config.cache_ttl_seconds)
        
        # Initialize OpenAI client if available
        if OPENAI_AVAILABLE and self.config.api_key:
            self._initialize_client()
        else:
            logger.warning("AI Analyzer not fully configured - API key missing or OpenAI not installed")
            self.client = None
    
    def _initialize_client(self):
        """Initialize OpenAI client."""
        if self.config.api_type == "azure":
            openai.api_type = "azure"
            openai.api_base = self.config.api_base
            openai.api_version = self.config.api_version
            openai.api_key = self.config.api_key
        else:
            openai.api_key = self.config.api_key
            if self.config.api_base:
                openai.api_base = self.config.api_base
        
        self.client = openai
        logger.info("AI Analyzer initialized (type=%s, model=%s)", 
                   self.config.api_type, self.config.model)
    
    def analyze(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout_ms: Optional[int] = None
    ) -> Optional[str]:
        """
        Analyze a prompt using AI.
        
        Args:
            prompt: The prompt to analyze
            max_tokens: Maximum tokens in response (overrides config)
            temperature: Temperature for generation (overrides config)
            timeout_ms: Timeout in milliseconds (overrides config)
            
        Returns:
            AI response string or None on failure
        """
        if not self.client:
            logger.debug("AI client not configured, skipping analysis")
            return None
        
        # Check cache first
        if self.config.cache_enabled:
            cached = self.cache.get(prompt, self.config.model)
            if cached:
                return cached
        
        # Prepare parameters
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature
        timeout = (timeout_ms / 1000) if timeout_ms else self.config.timeout
        
        # Call API with retries
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self._call_api(prompt, max_tokens, temperature, timeout)
                
                # Cache successful response
                if response and self.config.cache_enabled:
                    self.cache.set(prompt, self.config.model, response)
                
                return response
                
            except Exception as e:
                logger.warning(
                    "AI analysis attempt %d/%d failed: %s",
                    attempt + 1,
                    self.config.max_retries + 1,
                    str(e)
                )
                
                if attempt == self.config.max_retries:
                    logger.error("AI analysis failed after %d attempts", attempt + 1)
                    return None
        
        return None
    
    def _call_api(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        timeout: float
    ) -> Optional[str]:
        """
        Make actual API call to OpenAI.
        
        Args:
            prompt: The prompt
            max_tokens: Max tokens
            temperature: Temperature
            timeout: Timeout in seconds
            
        Returns:
            Response text or None
        """
        try:
            if self.config.api_type == "azure":
                response = self.client.ChatCompletion.create(
                    engine=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    request_timeout=timeout
                )
            else:
                response = self.client.ChatCompletion.create(
                    model=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    request_timeout=timeout
                )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error("OpenAI API call failed: %s", str(e))
            raise
    
    def batch_analyze(
        self,
        prompts: List[str],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> List[Optional[str]]:
        """
        Analyze multiple prompts (sequential for now).
        
        Args:
            prompts: List of prompts
            max_tokens: Max tokens per response
            temperature: Temperature
            
        Returns:
            List of responses (None for failures)
        """
        results = []
        for prompt in prompts:
            result = self.analyze(prompt, max_tokens, temperature)
            results.append(result)
        
        return results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()
    
    def clear_cache(self):
        """Clear response cache."""
        self.cache.clear()
        logger.info("AI response cache cleared")


def create_analyzer_from_env() -> Optional[AIAnalyzer]:
    """
    Create AI analyzer from environment variables.
    
    Environment variables:
    - OPENAI_API_KEY: OpenAI API key
    - OPENAI_API_BASE: Optional API base URL
    - OPENAI_API_TYPE: "openai" or "azure"
    - AZURE_OPENAI_ENDPOINT: Azure endpoint (if using Azure)
    - AZURE_OPENAI_API_VERSION: Azure API version
    - OPENAI_MODEL: Model to use
    
    Returns:
        AIAnalyzer instance or None if not configured
    """
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.info("OPENAI_API_KEY not set, AI analyzer disabled")
        return None
    
    api_type = os.getenv("OPENAI_API_TYPE", "openai")
    
    config = AIAnalyzerConfig(
        api_key=api_key,
        api_type=api_type,
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
        max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "500"))
    )
    
    if api_type == "azure":
        config.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
        config.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
    else:
        config.api_base = os.getenv("OPENAI_API_BASE")
    
    return AIAnalyzer(config)
