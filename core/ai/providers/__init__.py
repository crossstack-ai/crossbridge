"""
LLM Provider implementations.

Concrete implementations of the LLMProvider interface for various AI services.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

from core.logging import get_logger, LogCategory
from core.ai.base import (
    AuthenticationError,
    LLMProvider,
    ProviderError,
    RateLimitError,
)
from core.ai.models import (
    AIExecutionContext,
    AIMessage,
    AIResponse,
    ExecutionStatus,
    ModelConfig,
    ProviderType,
    TokenUsage,
)

# Initialize crossbridge logger
logger = get_logger(__name__, category=LogCategory.AI)


class OpenAIProvider(LLMProvider):
    """OpenAI provider (GPT-4, GPT-3.5, etc.)."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.organization = config.get("organization")
        
        # Lazy import to avoid hard dependency
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    organization=self.organization,
                )
            except ImportError:
                raise ProviderError(
                    "OpenAI library not installed. Install with: pip install openai"
                )
        return self._client
    
    def complete(
        self,
        *,
        messages: List[AIMessage],
        model_config: ModelConfig,
        context:AIExecutionContext,
    ) -> AIResponse:
        """Generate completion using OpenAI API."""
        client = self._get_client()
        model = model_config.model
        
        start_time = time.time()
        
        try:
            # Convert messages to OpenAI format
            api_messages = [msg.to_dict() for msg in messages]
            total_prompt_length = sum(len(msg.content) for msg in messages)
            
            # Log API call details
            logger.info(
                f"🤖 OpenAI API Call → {self.base_url}/chat/completions",
                extra={
                    "model": model,
                    "endpoint": self.base_url,
                    "messages_count": len(api_messages),
                    "prompt_length": total_prompt_length,
                    "temperature": model_config.temperature,
                    "max_tokens": model_config.max_tokens,
                    "timeout": model_config.timeout,
                    "execution_id": context.execution_id
                }
            )
            
            # Call OpenAI API
            response = client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
                top_p=model_config.top_p,
                frequency_penalty=model_config.frequency_penalty,
                presence_penalty=model_config.presence_penalty,
                stop=model_config.stop_sequences or None,
                timeout=model_config.timeout,
            )
            
            latency = time.time() - start_time
            
            # Extract response
            choice = response.choices[0]
            content = choice.message.content or ""
            
            # Track token usage
            usage = response.usage
            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
            
            # Calculate cost
            cost = self.estimate_cost(usage.prompt_tokens, usage.completion_tokens)
            
            # Log successful response
            logger.info(
                f"✅ OpenAI API Response (200 OK) - {latency:.2f}s",
                extra={
                    "model": model,
                    "status_code": 200,
                    "latency_ms": int(latency * 1000),
                    "prompt_tokens": token_usage.prompt_tokens,
                    "completion_tokens": token_usage.completion_tokens,
                    "total_tokens": token_usage.total_tokens,
                    "response_length": len(content),
                    "execution_id": context.execution_id,
                    "cost": cost
                }
            )
            
            return AIResponse(
                content=content,
                raw_response=response.model_dump(),
                provider=self.name(),
                model=model,
                execution_id=context.execution_id,
                token_usage=token_usage,
                cost=cost,
                latency=latency,
                status=ExecutionStatus.COMPLETED,
                tool_calls=[
                    tc.model_dump() for tc in (choice.message.tool_calls or [])
                ],
            )
        
        except Exception as e:
            latency = time.time() - start_time
            error_msg = str(e)
            
            # Log error with details
            logger.error(
                f"❌ OpenAI API Error - {latency:.2f}s",
                extra={
                    "model": model,
                    "endpoint": self.base_url,
                    "latency_ms": int(latency * 1000),
                    "error": error_msg,
                    "error_type": type(e).__name__,
                    "execution_id": context.execution_id
                }
            )
            
            # Handle specific errors
            if "rate_limit" in error_msg.lower():
                raise RateLimitError(f"OpenAI rate limit exceeded: {error_msg}")
            elif "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                raise AuthenticationError(f"OpenAI authentication failed: {error_msg}")
            else:
                raise ProviderError(f"OpenAI API error: {error_msg}")
    
    def supports_tools(self) -> bool:
        return True
    
    def supports_streaming(self) -> bool:
        return True
    
    def name(self) -> ProviderType:
        return ProviderType.OPENAI
    
    def is_available(self) -> bool:
        return self.api_key is not None
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost based on OpenAI pricing."""
        # Approximate pricing (varies by model)
        # GPT-4: $0.03/1K prompt, $0.06/1K completion
        # GPT-3.5: $0.0015/1K prompt, $0.002/1K completion
        prompt_cost = (prompt_tokens / 1000) * 0.03
        completion_cost = (completion_tokens / 1000) * 0.06
        return prompt_cost + completion_cost
    
    def get_model_list(self) -> List[str]:
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo",
        ]


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider (GPT-4, GPT-3.5, etc. on Azure)."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = config.get("endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = config.get("api_version", "2024-02-15-preview")
        self.deployment_name = config.get("deployment_name")  # Required for Azure
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Azure OpenAI client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.AzureOpenAI(
                    api_key=self.api_key,
                    azure_endpoint=self.endpoint,
                    api_version=self.api_version,
                )
            except ImportError:
                raise ProviderError(
                    "OpenAI library not installed. Install with: pip install openai"
                )
        return self._client
    
    def complete(
        self,
        *,
        messages: List[AIMessage],
        model_config: ModelConfig,
        context: AIExecutionContext,
    ) -> AIResponse:
        """Generate completion using Azure OpenAI API."""
        if not self.deployment_name:
            raise ProviderError("Azure OpenAI requires deployment_name in config")
        
        client = self._get_client()
        start_time = time.time()
        
        try:
            # Convert messages to OpenAI format
            api_messages = [msg.to_dict() for msg in messages]
            total_prompt_length = sum(len(msg.content) for msg in messages)
            
            # Log API call details
            logger.info(
                f"🤖 Azure OpenAI API Call → {self.endpoint}/chat/completions",
                extra={
                    "deployment": self.deployment_name,
                    "endpoint": self.endpoint,
                    "messages_count": len(api_messages),
                    "prompt_length": total_prompt_length,
                    "temperature": model_config.temperature,
                    "max_tokens": model_config.max_tokens,
                    "timeout": model_config.timeout,
                    "execution_id": context.execution_id
                }
            )
            
            # Call Azure OpenAI API (use deployment_name instead of model)
            response = client.chat.completions.create(
                model=self.deployment_name,  # Azure uses deployment name
                messages=api_messages,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
                top_p=model_config.top_p,
                frequency_penalty=model_config.frequency_penalty,
                presence_penalty=model_config.presence_penalty,
                stop=model_config.stop_sequences or None,
                timeout=model_config.timeout,
            )
            
            latency = time.time() - start_time
            
            # Extract response
            choice = response.choices[0]
            content = choice.message.content or ""
            
            # Track token usage
            usage = response.usage
            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
            
            # Calculate cost (same as OpenAI pricing)
            cost = self.estimate_cost(usage.prompt_tokens, usage.completion_tokens)
            
            # Log successful response
            logger.info(
                f"✅ Azure OpenAI API Response (200 OK) - {latency:.2f}s",
                extra={
                    "deployment": self.deployment_name,
                    "status_code": 200,
                    "latency_ms": int(latency * 1000),
                    "prompt_tokens": token_usage.prompt_tokens,
                    "completion_tokens": token_usage.completion_tokens,
                    "total_tokens": token_usage.total_tokens,
                    "response_length": len(content),
                    "execution_id": context.execution_id,
                    "cost": cost
                }
            )
            
            return AIResponse(
                content=content,
                raw_response=response.model_dump(),
                provider=self.name(),
                model=self.deployment_name,
                execution_id=context.execution_id,
                token_usage=token_usage,
                cost=cost,
                latency=latency,
                status=ExecutionStatus.COMPLETED,
                tool_calls=[
                    tc.model_dump() for tc in (choice.message.tool_calls or [])
                ],
            )
        
        except Exception as e:
            latency = time.time() - start_time
            error_msg = str(e)
            
            # Log error with details
            logger.error(
                f"❌ Azure OpenAI API Error - {latency:.2f}s",
                extra={
                    "deployment": self.deployment_name,
                    "endpoint": self.endpoint,
                    "latency_ms": int(latency * 1000),
                    "error": error_msg,
                    "error_type": type(e).__name__,
                    "execution_id": context.execution_id
                }
            )
            
            # Handle specific errors
            if "rate_limit" in error_msg.lower():
                raise RateLimitError(f"Azure OpenAI rate limit exceeded: {error_msg}")
            elif "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                raise AuthenticationError(f"Azure OpenAI authentication failed: {error_msg}")
            else:
                raise ProviderError(f"Azure OpenAI API error: {error_msg}")
    
    def supports_tools(self) -> bool:
        return True
    
    def supports_streaming(self) -> bool:
        return True
    
    def name(self) -> ProviderType:
        return ProviderType.OPENAI  # Use OPENAI type for compatibility
    
    def is_available(self) -> bool:
        return self.api_key is not None and self.endpoint is not None and self.deployment_name is not None
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost based on Azure OpenAI pricing (same as OpenAI)."""
        prompt_cost = (prompt_tokens / 1000) * 0.03
        completion_cost = (completion_tokens / 1000) * 0.06
        return prompt_cost + completion_cost
    
    def get_model_list(self) -> List[str]:
        # Azure uses deployment names, not model names
        return [self.deployment_name] if self.deployment_name else []


class AnthropicProvider(LLMProvider):
    """Anthropic provider (Claude models)."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ProviderError(
                    "Anthropic library not installed. Install with: pip install anthropic"
                )
        return self._client
    
    def complete(
        self,
        *,
        messages: List[AIMessage],
        model_config: ModelConfig,
        context: AIExecutionContext,
    ) -> AIResponse:
        """Generate completion using Anthropic API."""
        client = self._get_client()
        model = model_config.model
        
        start_time = time.time()
        
        try:
            # Separate system message
            system_msg = next(
                (msg.content for msg in messages if msg.role == "system"), None
            )
            api_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
                if msg.role != "system"
            ]
            total_prompt_length = sum(len(msg.content) for msg in messages)
            
            # Log API call details
            logger.info(
                f"🤖 Anthropic API Call → https://api.anthropic.com/v1/messages",
                extra={
                    "model": model,
                    "messages_count": len(api_messages),
                    "prompt_length": total_prompt_length,
                    "has_system_msg": system_msg is not None,
                    "temperature": model_config.temperature,
                    "max_tokens": model_config.max_tokens,
                    "timeout": model_config.timeout,
                    "execution_id": context.execution_id
                }
            )
            
            # Call Anthropic API
            response = client.messages.create(
                model=model,
                messages=api_messages,
                system=system_msg,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
                top_p=model_config.top_p,
                stop_sequences=model_config.stop_sequences or None,
                timeout=model_config.timeout,
            )
            
            latency = time.time() - start_time
            
            # Extract response
            content = response.content[0].text if response.content else ""
            
            # Track token usage
            token_usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )
            
            # Calculate cost
            cost = self.estimate_cost(
                response.usage.input_tokens, response.usage.output_tokens
            )
            
            # Log successful response
            logger.info(
                f"✅ Anthropic API Response (200 OK) - {latency:.2f}s",
                extra={
                    "model": model,
                    "status_code": 200,
                    "latency_ms": int(latency * 1000),
                    "prompt_tokens": token_usage.prompt_tokens,
                    "completion_tokens": token_usage.completion_tokens,
                    "total_tokens": token_usage.total_tokens,
                    "response_length": len(content),
                    "execution_id": context.execution_id,
                    "cost": cost
                }
            )
            
            return AIResponse(
                content=content,
                raw_response=response.model_dump(),
                provider=self.name(),
                model=model,
                execution_id=context.execution_id,
                token_usage=token_usage,
                cost=cost,
                latency=latency,
                status=ExecutionStatus.COMPLETED,
            )
        
        except Exception as e:
            latency = time.time() - start_time
            error_msg = str(e)
            
            # Log error with details
            logger.error(
                f"❌ Anthropic API Error - {latency:.2f}s",
                extra={
                    "model": model,
                    "latency_ms": int(latency * 1000),
                    "error": error_msg,
                    "error_type": type(e).__name__,
                    "execution_id": context.execution_id
                }
            )
            
            if "rate_limit" in error_msg.lower():
                raise RateLimitError(f"Anthropic rate limit exceeded: {error_msg}")
            elif "authentication" in error_msg.lower():
                raise AuthenticationError(f"Anthropic authentication failed: {error_msg}")
            else:
                raise ProviderError(f"Anthropic API error: {error_msg}")
    
    def supports_tools(self) -> bool:
        return True
    
    def supports_streaming(self) -> bool:
        return True
    
    def name(self) -> ProviderType:
        return ProviderType.ANTHROPIC
    
    def is_available(self) -> bool:
        return self.api_key is not None
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost based on Anthropic pricing."""
        # Claude 3.5 Sonnet: $3/MTok input, $15/MTok output
        prompt_cost = (prompt_tokens / 1_000_000) * 3.0
        completion_cost = (completion_tokens / 1_000_000) * 15.0
        return prompt_cost + completion_cost
    
    def get_model_list(self) -> List[str]:
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]


class VLLMProvider(LLMProvider):
    """vLLM provider for self-hosted models (DeepSeek, Mistral, Llama, etc.)."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:8000/v1")
        self.api_key = config.get("api_key", "EMPTY")  # vLLM often doesn't need auth
        self.model_name = config.get("model", "deepseek-coder")
    
    def complete(
        self,
        *,
        messages: List[AIMessage],
        model_config: ModelConfig,
        context: AIExecutionContext,
    ) -> AIResponse:
        """Generate completion using vLLM API (OpenAI-compatible)."""
        import requests
        
        start_time = time.time()
        model = model_config.model or self.model_name
        
        try:
            # Convert messages
            api_messages = [msg.to_dict() for msg in messages]
            total_prompt_length = sum(len(msg.content) for msg in messages)
            
            # Log API call details
            logger.info(
                f"🤖 vLLM API Call → {self.base_url}/chat/completions",
                extra={
                    "model": model,
                    "endpoint": self.base_url,
                    "messages_count": len(api_messages),
                    "prompt_length": total_prompt_length,
                    "temperature": model_config.temperature,
                    "max_tokens": model_config.max_tokens,
                    "timeout": model_config.timeout,
                    "execution_id": context.execution_id
                }
            )
            
            # Call vLLM API
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": api_messages,
                    "temperature": model_config.temperature,
                    "max_tokens": model_config.max_tokens,
                    "top_p": model_config.top_p,
                    "stop": model_config.stop_sequences or None,
                },
                timeout=model_config.timeout,
            )
            
            response.raise_for_status()
            data = response.json()
            
            latency = time.time() - start_time
            
            # Extract response
            choice = data["choices"][0]
            content = choice["message"]["content"]
            
            # Track token usage
            usage = data.get("usage", {})
            token_usage = TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
            
            # Log successful response
            logger.info(
                f"✅ vLLM API Response (200 OK) - {latency:.2f}s",
                extra={
                    "model": model,
                    "status_code": 200,
                    "latency_ms": int(latency * 1000),
                    "prompt_tokens": token_usage.prompt_tokens,
                    "completion_tokens": token_usage.completion_tokens,
                    "total_tokens": token_usage.total_tokens,
                    "response_length": len(content),
                    "execution_id": context.execution_id,
                    "cost": 0.0
                }
            )
            
            return AIResponse(
                content=content,
                raw_response=data,
                provider=self.name(),
                model=model,
                execution_id=context.execution_id,
                token_usage=token_usage,
                cost=0.0,  # Self-hosted has no per-token cost
                latency=latency,
                status=ExecutionStatus.COMPLETED,
            )
        
        except requests.exceptions.Timeout as e:
            latency = time.time() - start_time
            logger.error(
                f"⏱️ vLLM API Timeout after {latency:.1f}s",
                extra={
                    "model": model,
                    "endpoint": self.base_url,
                    "timeout": model_config.timeout,
                    "latency_ms": int(latency * 1000),
                    "error": str(e),
                    "execution_id": context.execution_id
                }
            )
            raise ProviderError(f"vLLM API timeout after {latency:.1f}s: {str(e)}")
        
        except requests.exceptions.HTTPError as e:
            latency = time.time() - start_time
            status_code = e.response.status_code if e.response else "unknown"
            logger.error(
                f"❌ vLLM API HTTP Error ({status_code}) - {latency:.2f}s",
                extra={
                    "model": model,
                    "endpoint": self.base_url,
                    "status_code": status_code,
                    "latency_ms": int(latency * 1000),
                    "error": str(e),
                    "execution_id": context.execution_id
                }
            )
            raise ProviderError(f"vLLM API HTTP error ({status_code}): {str(e)}")
        
        except requests.exceptions.RequestException as e:
            latency = time.time() - start_time
            logger.error(
                f"❌ vLLM API Request Failed - {latency:.2f}s",
                extra={
                    "model": model,
                    "endpoint": self.base_url,
                    "latency_ms": int(latency * 1000),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "execution_id": context.execution_id
                }
            )
            raise ProviderError(f"vLLM API error: {str(e)}")
    
    def supports_tools(self) -> bool:
        return True  # Depends on model, but vLLM supports it
    
    def supports_streaming(self) -> bool:
        return True
    
    def name(self) -> ProviderType:
        return ProviderType.VLLM
    
    def is_available(self) -> bool:
        """Check if vLLM endpoint is reachable."""
        import requests
        
        try:
            response = requests.get(f"{self.base_url}/models", timeout=5)
            return response.status_code == 200
        except (requests.RequestException, Exception) as e:
            logger.debug(f"Self-hosted provider not available: {e}")
            return False
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Self-hosted models have no per-token cost."""
        return 0.0
    
    def get_model_list(self) -> List[str]:
        """Get available models from vLLM server."""
        import requests
        
        try:
            response = requests.get(f"{self.base_url}/models", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["id"] for model in data.get("data", [])]
        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Failed to fetch model list: {e}")
        
        return [self.model_name]


class OllamaProvider(LLMProvider):
    """Ollama provider for local models."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model_name = config.get("model", "llama3")
    
    def complete(
        self,
        *,
        messages: List[AIMessage],
        model_config: ModelConfig,
        context: AIExecutionContext,
    ) -> AIResponse:
        """Generate completion using Ollama API."""
        import requests
        
        start_time = time.time()
        model = model_config.model or self.model_name
        
        try:
            # Convert messages
            api_messages = [
                {"role": msg.role, "content": msg.content} for msg in messages
            ]
            
            # Calculate prompt size for logging
            total_prompt_length = sum(len(msg.content) for msg in messages)
            
            # Log API call details
            logger.info(
                f"🤖 Ollama API Call → {self.base_url}/api/chat",
                extra={
                    "model": model,
                    "endpoint": self.base_url,
                    "messages_count": len(api_messages),
                    "prompt_length": total_prompt_length,
                    "temperature": model_config.temperature,
                    "max_tokens": model_config.max_tokens,
                    "timeout": model_config.timeout,
                    "execution_id": context.execution_id
                }
            )
            
            # Call Ollama API
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": api_messages,
                    "stream": False,
                    "options": {
                        "temperature": model_config.temperature,
                        "num_predict": model_config.max_tokens,
                        "top_p": model_config.top_p,
                        "stop": model_config.stop_sequences,
                    },
                },
                timeout=model_config.timeout,
            )
            
            response.raise_for_status()
            data = response.json()
            
            latency = time.time() - start_time
            
            # Extract response
            content = data["message"]["content"]
            
            # Ollama provides token counts
            token_usage = TokenUsage(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0)
                + data.get("eval_count", 0),
            )
            
            # Log successful response
            logger.info(
                f"✅ Ollama API Response (200 OK) - {latency:.2f}s",
                extra={
                    "model": model,
                    "status_code": 200,
                    "latency_ms": int(latency * 1000),
                    "prompt_tokens": token_usage.prompt_tokens,
                    "completion_tokens": token_usage.completion_tokens,
                    "total_tokens": token_usage.total_tokens,
                    "response_length": len(content),
                    "execution_id": context.execution_id,
                    "cost": 0.0
                }
            )
            
            # Log detailed metrics for performance monitoring
            if token_usage.prompt_tokens > 0:
                tokens_per_second = token_usage.completion_tokens / latency if latency > 0 else 0
                logger.debug(
                    f"📊 Ollama Performance: {tokens_per_second:.1f} tokens/sec",
                    extra={
                        "model": model,
                        "tokens_per_second": tokens_per_second,
                        "prompt_eval_duration": data.get("prompt_eval_duration", 0) / 1e9,  # Convert to seconds
                        "eval_duration": data.get("eval_duration", 0) / 1e9,
                        "total_duration": data.get("total_duration", 0) / 1e9
                    }
                )
            
            return AIResponse(
                content=content,
                raw_response=data,
                provider=self.name(),
                model=model,
                execution_id=context.execution_id,
                token_usage=token_usage,
                cost=0.0,  # Local models have no cost
                latency=latency,
                status=ExecutionStatus.COMPLETED,
            )
        
        except requests.exceptions.Timeout as e:
            latency = time.time() - start_time
            logger.error(
                f"⏱️ Ollama API Timeout after {latency:.1f}s",
                extra={
                    "model": model,
                    "endpoint": self.base_url,
                    "timeout": model_config.timeout,
                    "latency_ms": int(latency * 1000),
                    "error": str(e),
                    "execution_id": context.execution_id
                }
            )
            raise ProviderError(f"Ollama API timeout after {latency:.1f}s: {str(e)}")
        
        except requests.exceptions.HTTPError as e:
            latency = time.time() - start_time
            status_code = e.response.status_code if e.response else "unknown"
            logger.error(
                f"❌ Ollama API HTTP Error ({status_code}) - {latency:.2f}s",
                extra={
                    "model": model,
                    "endpoint": self.base_url,
                    "status_code": status_code,
                    "latency_ms": int(latency * 1000),
                    "error": str(e),
                    "execution_id": context.execution_id
                }
            )
            raise ProviderError(f"Ollama API HTTP error ({status_code}): {str(e)}")
        
        except requests.exceptions.RequestException as e:
            latency = time.time() - start_time
            logger.error(
                f"❌ Ollama API Request Failed - {latency:.2f}s",
                extra={
                    "model": model,
                    "endpoint": self.base_url,
                    "latency_ms": int(latency * 1000),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "execution_id": context.execution_id
                }
            )
            raise ProviderError(f"Ollama API error: {str(e)}")
    
    def supports_tools(self) -> bool:
        return False  # Most Ollama models don't support tools yet
    
    def supports_streaming(self) -> bool:
        return True
    
    def name(self) -> ProviderType:
        return ProviderType.OLLAMA
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        import requests
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except (requests.RequestException, Exception) as e:
            logger.debug(f"Ollama provider not available: {e}")
            return False
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Local models have no cost."""
        return 0.0
    
    def get_model_list(self) -> List[str]:
        """Get available models from Ollama."""
        import requests
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Failed to fetch Ollama model list: {e}")
        
        return [self.model_name]


# Provider registry for easy access
PROVIDER_REGISTRY: Dict[ProviderType, type] = {
    ProviderType.OPENAI: OpenAIProvider,
    ProviderType.ANTHROPIC: AnthropicProvider,
    ProviderType.VLLM: VLLMProvider,
    ProviderType.OLLAMA: OllamaProvider,
}

# Azure OpenAI is accessed via special config key
AZURE_PROVIDER_KEY = "azure_openai"


def get_provider(
    provider_type: ProviderType, config: Optional[Dict[str, Any]] = None
) -> LLMProvider:
    """
    Factory function to get a provider instance.
    
    Args:
        provider_type: Type of provider to instantiate
        config: Provider configuration (can include 'azure_openai' key for Azure)
    
    Returns:
        Configured provider instance
    
    Raises:
        ValueError: If provider type is not supported
    """
    # Check if Azure OpenAI is specifically requested
    if config and AZURE_PROVIDER_KEY in config:
        return AzureOpenAIProvider(config.get(AZURE_PROVIDER_KEY))
    
    provider_class = PROVIDER_REGISTRY.get(provider_type)
    if provider_class is None:
        raise ValueError(f"Unknown provider type: {provider_type}")
    
    return provider_class(config)


def get_available_providers(config: Optional[Dict[str, Any]] = None) -> List[ProviderType]:
    """
    Get list of available providers based on configuration.
    
    Args:
        config: Configuration dict with provider settings
    
    Returns:
        List of available provider types
    """
    available = []
    
    # Check Azure OpenAI separately
    if config and AZURE_PROVIDER_KEY in config:
        try:
            azure_provider = AzureOpenAIProvider(config.get(AZURE_PROVIDER_KEY))
            if azure_provider.is_available():
                available.append(ProviderType.OPENAI)  # Azure uses OPENAI type
        except Exception as e:
            logger.debug(f"Azure provider initialization failed: {e}")
    
    for provider_type in PROVIDER_REGISTRY:
        try:
            provider = get_provider(provider_type, config)
            if provider.is_available():
                available.append(provider_type)
        except Exception as e:
            logger.debug(f"Provider {provider_type} check failed: {e}")
            continue
    
    return list(set(available))  # Deduplicate
