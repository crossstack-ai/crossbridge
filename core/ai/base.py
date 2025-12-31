"""
Base abstractions for AI providers and skills.

These define the contracts that all providers and skills must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.ai.models import (
    AIExecutionContext,
    AIMessage,
    AIResponse,
    ModelConfig,
    ProviderType,
)


class LLMProvider(ABC):
    """
    Base interface for all LLM providers.
    
    This abstraction ensures all providers (OpenAI, Claude, DeepSeek, local models)
    are completely interchangeable.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize provider with configuration.
        
        Args:
            config: Provider-specific configuration (API keys, endpoints, etc.)
        """
        self.config = config or {}
    
    @abstractmethod
    def complete(
        self,
        *,
        messages: List[AIMessage],
        model_config: ModelConfig,
        context: AIExecutionContext,
    ) -> AIResponse:
        """
        Generate a completion from messages.
        
        Args:
            messages: List of conversation messages
            model_config: Model configuration (temperature, max_tokens, etc.)
            context: Execution context for governance and tracking
        
        Returns:
            AIResponse with normalized output
        
        Raises:
            ProviderError: If the provider encounters an error
            RateLimitError: If rate limits are exceeded
            AuthenticationError: If authentication fails
        """
        pass
    
    @abstractmethod
    def supports_tools(self) -> bool:
        """Check if provider supports tool/function calling."""
        pass
    
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if provider supports streaming responses."""
        pass
    
    @abstractmethod
    def name(self) -> ProviderType:
        """Return the provider type identifier."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is available and configured.
        
        Returns:
            True if provider can be used, False otherwise
        """
        pass
    
    @abstractmethod
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate cost for a completion.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
        
        Returns:
            Estimated cost in dollars
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate provider configuration.
        
        Returns:
            True if configuration is valid
        """
        return True
    
    def get_model_list(self) -> List[str]:
        """
        Get list of available models for this provider.
        
        Returns:
            List of model identifiers
        """
        return []


class AISkill(ABC):
    """
    Base class for AI skills (capabilities).
    
    Skills are business-level AI capabilities that combine prompts,
    providers, and parsing logic to accomplish specific tasks.
    """
    
    # Skill metadata (override in subclasses)
    skill_name: str = "base_skill"
    description: str = "Base AI skill"
    task_type: str = "general"
    
    # Default configuration
    default_model: str = "gpt-4"
    default_temperature: float = 0.7
    default_max_tokens: int = 2048
    
    # Prompt template ID
    prompt_template_id: str = "base_template"
    prompt_version: str = "v1"
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        """
        Initialize skill with optional provider.
        
        Args:
            provider: LLM provider to use (if None, orchestrator will select)
        """
        self.provider = provider
    
    @abstractmethod
    def prepare_inputs(self, **kwargs) -> Dict[str, Any]:
        """
        Prepare and validate inputs for the skill.
        
        Args:
            **kwargs: Raw inputs for the skill
        
        Returns:
            Validated and processed inputs
        
        Raises:
            ValueError: If inputs are invalid
        """
        pass
    
    @abstractmethod
    def parse_response(self, response: AIResponse) -> Dict[str, Any]:
        """
        Parse and validate AI response.
        
        Args:
            response: Raw AI response
        
        Returns:
            Structured, validated output
        
        Raises:
            ValueError: If response is invalid or unparseable
        """
        pass
    
    @abstractmethod
    def validate_output(self, output: Dict[str, Any]) -> bool:
        """
        Validate parsed output.
        
        Args:
            output: Parsed output from parse_response
        
        Returns:
            True if output is valid
        """
        pass
    
    def get_model_config(self) -> ModelConfig:
        """
        Get model configuration for this skill.
        
        Returns:
            ModelConfig with skill-specific settings
        """
        return ModelConfig(
            model=self.default_model,
            temperature=self.default_temperature,
            max_tokens=self.default_max_tokens,
        )
    
    def get_required_context(self) -> List[str]:
        """
        Get list of required context keys for this skill.
        
        Returns:
            List of required context keys
        """
        return []
    
    def estimate_tokens(self, inputs: Dict[str, Any]) -> int:
        """
        Estimate token count for inputs.
        
        Args:
            inputs: Prepared inputs
        
        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 chars per token
        text = str(inputs)
        return len(text) // 4
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.skill_name}>"


class ProviderError(Exception):
    """Base exception for provider errors."""
    pass


class RateLimitError(ProviderError):
    """Raised when rate limits are exceeded."""
    pass


class AuthenticationError(ProviderError):
    """Raised when authentication fails."""
    pass


class CostLimitExceededError(Exception):
    """Raised when cost limits are exceeded."""
    pass


class CreditExhaustedError(Exception):
    """Raised when credits are exhausted."""
    pass


class SafetyViolationError(Exception):
    """Raised when safety checks fail."""
    pass
