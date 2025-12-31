"""
AI Orchestration Engine - The Heart of CrossBridge AI.

Coordinates providers, prompts, skills, and governance to execute AI tasks.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.ai.base import AISkill, LLMProvider
from core.ai.governance import (
    AuditLog,
    CostTracker,
    CreditManager,
    SafetyValidator,
)
from core.ai.models import (
    AIExecutionContext,
    AIMessage,
    AIResponse,
    ExecutionStatus,
    ModelConfig,
    ProviderType,
    SafetyLevel,
    TaskType,
)
from core.ai.prompts import PromptRenderer, get_prompt
from core.ai.providers import get_available_providers, get_provider


class ExecutionPolicy:
    """
    Policy enforcement for AI execution.
    
    Determines what is allowed based on configuration and context.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize policy.
        
        Args:
            config: Policy configuration
        """
        self.config = config or {}
        
        # Default policies
        self.allow_external_ai = self.config.get("allow_external_ai", False)
        self.allow_self_hosted = self.config.get("allow_self_hosted", True)
        self.require_approval = self.config.get("require_approval", False)
        self.max_cost_per_operation = self.config.get("max_cost_per_operation", 1.0)
        self.safety_level = SafetyLevel(
            self.config.get("safety_level", "moderate")
        )
    
    def validate(self, context: AIExecutionContext, provider: ProviderType):
        """
        Validate if operation is allowed by policy.
        
        Args:
            context: Execution context
            provider: Provider to use
        
        Raises:
            PermissionError: If operation violates policy
        """
        # Check external AI policy
        if provider in [ProviderType.OPENAI, ProviderType.ANTHROPIC]:
            if not context.allow_external_ai and not self.allow_external_ai:
                raise PermissionError(
                    f"External AI provider {provider.value} not allowed by policy"
                )
        
        # Check self-hosted policy
        if provider in [ProviderType.VLLM, ProviderType.OLLAMA]:
            if not context.allow_self_hosted and not self.allow_self_hosted:
                raise PermissionError(
                    f"Self-hosted provider {provider.value} not allowed by policy"
                )
        
        # Check cost limits
        if context.max_cost > self.max_cost_per_operation:
            raise PermissionError(
                f"Max cost {context.max_cost} exceeds policy limit {self.max_cost_per_operation}"
            )


class ProviderSelector:
    """
    Select the best provider for a task.
    
    Considers availability, cost, capability, and preferences.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize provider selector.
        
        Args:
            config: Configuration for provider selection
        """
        self.config = config or {}
        self.provider_preferences = self.config.get("provider_preferences", [])
    
    def select(
        self,
        context: AIExecutionContext,
        requires_tools: bool = False,
    ) -> ProviderType:
        """
        Select best provider for execution.
        
        Args:
            context: Execution context
            requires_tools: Whether tool support is required
        
        Returns:
            Selected provider type
        
        Raises:
            ValueError: If no suitable provider available
        """
        # If provider specified in context, use it
        if context.provider:
            return context.provider
        
        # Get available providers
        available = get_available_providers(self.config)
        
        if not available:
            raise ValueError("No AI providers available")
        
        # Filter by requirements
        if requires_tools:
            available = [
                p for p in available
                if get_provider(p, self.config).supports_tools()
            ]
        
        # Filter by policy
        if not context.allow_external_ai:
            available = [
                p for p in available
                if p not in [ProviderType.OPENAI, ProviderType.ANTHROPIC]
            ]
        
        if not available:
            raise ValueError("No suitable provider available after filtering")
        
        # Apply preferences
        for pref in self.provider_preferences:
            if pref in available:
                return pref
        
        # Default: prefer self-hosted, then cheapest
        if ProviderType.VLLM in available:
            return ProviderType.VLLM
        elif ProviderType.OLLAMA in available:
            return ProviderType.OLLAMA
        else:
            return available[0]


class AIOrchestrator:
    """
    Main AI orchestration engine.
    
    This is the heart of CrossBridge AI - coordinates all components
    to execute AI tasks with governance, auditing, and safety.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        storage_path: Optional[Path] = None,
    ):
        """
        Initialize orchestrator.
        
        Args:
            config: Configuration dictionary
            storage_path: Base path for data storage
        """
        self.config = config or {}
        self.storage_path = storage_path or Path("data/ai")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.policy = ExecutionPolicy(self.config.get("policy", {}))
        self.selector = ProviderSelector(self.config.get("providers", {}))
        self.cost_tracker = CostTracker(self.storage_path / "costs")
        self.audit_log = AuditLog(self.storage_path / "audit")
        self.credit_manager = CreditManager(self.storage_path / "credits")
        self.safety_validator = SafetyValidator(self.policy.safety_level)
        self.prompt_renderer = PromptRenderer()
    
    def execute_skill(
        self,
        skill: AISkill,
        inputs: Dict[str, Any],
        context: Optional[AIExecutionContext] = None,
    ) -> Dict[str, Any]:
        """
        Execute an AI skill.
        
        This is the main entry point for AI operations.
        
        Args:
            skill: AI skill to execute
            inputs: Input data for the skill
            context: Execution context (created if not provided)
        
        Returns:
            Parsed and validated output from the skill
        
        Raises:
            Various exceptions based on failures
        """
        # Create context if not provided
        if context is None:
            context = AIExecutionContext(
                task_type=TaskType(skill.task_type),
            )
        
        context.start()
        
        try:
            # Prepare inputs
            prepared_inputs = skill.prepare_inputs(**inputs)
            
            # Validate input safety
            self.safety_validator.validate_input(prepared_inputs, context)
            
            # Get prompt template
            template = get_prompt(skill.prompt_template_id, skill.prompt_version)
            
            # Render prompt
            messages_data = self.prompt_renderer.render(template, prepared_inputs)
            messages = [
                AIMessage(role=msg["role"], content=msg["content"])
                for msg in messages_data
            ]
            
            # Select provider
            provider_type = self.selector.select(
                context,
                requires_tools=False,  # TODO: Check skill requirements
            )
            
            # Validate policy
            self.policy.validate(context, provider_type)
            
            # Get provider
            provider = get_provider(
                provider_type,
                self.config.get("providers", {}).get(provider_type.value, {})
            )
            
            # Estimate cost
            model_config = skill.get_model_config()
            estimated_tokens = skill.estimate_tokens(prepared_inputs)
            estimated_cost = provider.estimate_cost(
                estimated_tokens, estimated_tokens // 2
            )
            
            # Check budget
            self.cost_tracker.enforce_budget(context, estimated_cost)
            
            # Check credits (if applicable)
            if context.user:
                self.credit_manager.enforce_credits(context, estimated_cost)
            
            # Execute
            response = provider.complete(
                messages=messages,
                model_config=model_config,
                context=context,
            )
            
            # Validate output safety
            self.safety_validator.validate_output(response, context)
            
            # Parse response
            parsed_output = skill.parse_response(response)
            
            # Validate output
            if not skill.validate_output(parsed_output):
                raise ValueError("Skill output validation failed")
            
            # Record cost
            self.cost_tracker.record_cost(response.cost, context, response)
            
            # Consume credits
            if context.user:
                self.credit_manager.consume_credits(
                    context.user,
                    response.cost,
                    context.project_id,
                )
            
            # Audit log
            self.audit_log.log(context, response, template.version)
            
            context.complete()
            
            return parsed_output
        
        except Exception as e:
            context.completed_at = None
            
            # Create error response for logging
            error_response = AIResponse(
                content="",
                provider=context.provider or ProviderType.OPENAI,
                model="",
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                error=str(e),
            )
            
            # Log failure
            self.audit_log.log(context, error_response, None)
            
            raise
    
    def execute_with_prompt(
        self,
        prompt_template_id: str,
        inputs: Dict[str, Any],
        context: Optional[AIExecutionContext] = None,
        model_config: Optional[ModelConfig] = None,
    ) -> AIResponse:
        """
        Execute AI with a specific prompt template (without a skill).
        
        Lower-level interface for direct prompt execution.
        
        Args:
            prompt_template_id: Prompt template to use
            inputs: Input data for template rendering
            context: Execution context
            model_config: Model configuration
        
        Returns:
            AI response
        """
        if context is None:
            context = AIExecutionContext()
        
        context.start()
        
        try:
            # Get template
            template = get_prompt(prompt_template_id)
            
            # Render
            messages_data = self.prompt_renderer.render(template, inputs)
            messages = [
                AIMessage(role=msg["role"], content=msg["content"])
                for msg in messages_data
            ]
            
            # Select provider
            provider_type = self.selector.select(context)
            self.policy.validate(context, provider_type)
            
            # Get provider
            provider = get_provider(
                provider_type,
                self.config.get("providers", {}).get(provider_type.value, {})
            )
            
            # Use template's model config if not provided
            if model_config is None:
                model_config = template.default_model_config or ModelConfig(
                    model="gpt-4o-mini"
                )
            
            # Execute
            response = provider.complete(
                messages=messages,
                model_config=model_config,
                context=context,
            )
            
            # Record and audit
            self.cost_tracker.record_cost(response.cost, context, response)
            self.audit_log.log(context, response, template.version)
            
            context.complete()
            
            return response
        
        except Exception as e:
            error_response = AIResponse(
                content="",
                provider=context.provider or ProviderType.OPENAI,
                model="",
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                error=str(e),
            )
            
            self.audit_log.log(context, error_response, None)
            raise
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary."""
        return self.cost_tracker.get_cost_summary()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return self.audit_log.get_usage_stats()
    
    def get_credit_balance(
        self, user_id: str, project_id: Optional[str] = None
    ) -> float:
        """Get credit balance for user/project."""
        balance = self.credit_manager.get_balance(user_id, project_id)
        return balance.available_credits


# Global orchestrator instance
_orchestrator: Optional[AIOrchestrator] = None


def get_orchestrator(
    config: Optional[Dict[str, Any]] = None,
    storage_path: Optional[Path] = None,
) -> AIOrchestrator:
    """
    Get the global orchestrator instance.
    
    Args:
        config: Configuration (only used on first call)
        storage_path: Storage path (only used on first call)
    
    Returns:
        AIOrchestrator instance
    """
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = AIOrchestrator(config, storage_path)
    
    return _orchestrator
