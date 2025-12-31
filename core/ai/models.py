"""
Core data models for the AI module.

These models provide the foundational data structures for AI operations,
execution contexts, responses, and governance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4


# Enums

class TaskType(str, Enum):
    """Types of AI tasks."""
    TEST_GENERATION = "test_generation"
    TEST_MIGRATION = "test_migration"
    FLAKY_ANALYSIS = "flaky_analysis"
    COVERAGE_INFERENCE = "coverage_inference"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    TEST_REPAIR = "test_repair"
    IMPACT_ANALYSIS = "impact_analysis"
    CODE_EXPLANATION = "code_explanation"


class ProviderType(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"
    VLLM = "vllm"
    CUSTOM = "custom"


class ExecutionStatus(str, Enum):
    """Status of AI execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RATE_LIMITED = "rate_limited"
    CREDIT_EXHAUSTED = "credit_exhausted"


class SafetyLevel(str, Enum):
    """Safety validation levels."""
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


# Core Data Models

@dataclass
class TokenUsage:
    """Token usage tracking."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    @property
    def cost_estimate(self) -> float:
        """Estimate cost (provider-specific calculation)."""
        # Default estimation, providers override
        return (self.prompt_tokens * 0.00001) + (self.completion_tokens * 0.00003)


@dataclass
class ModelConfig:
    """LLM model configuration."""
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = field(default_factory=list)
    timeout: int = 60


@dataclass
class AIExecutionContext:
    """
    Context for AI task execution.
    
    This encapsulates all the information needed to execute, audit,
    and govern an AI operation.
    """
    # Identity
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    task_type: TaskType = TaskType.TEST_GENERATION
    project_id: Optional[str] = None
    user: Optional[str] = None
    
    # Provider selection
    provider: Optional[ProviderType] = None
    model_config: Optional[ModelConfig] = None
    
    # Governance
    max_cost: float = 1.0  # Maximum allowed cost in dollars
    max_tokens: int = 10000
    allow_external_ai: bool = False  # Allow public AI services
    allow_self_hosted: bool = True  # Allow self-hosted models
    safety_level: SafetyLevel = SafetyLevel.MODERATE
    
    # Execution control
    timeout: int = 120  # Seconds
    retry_on_failure: bool = True
    max_retries: int = 3
    
    # Context data
    workspace_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def start(self):
        """Mark execution as started."""
        self.started_at = datetime.now()
    
    def complete(self):
        """Mark execution as completed."""
        self.completed_at = datetime.now()


@dataclass
class AIMessage:
    """A single message in a conversation."""
    role: str  # 'system', 'user', 'assistant', 'tool'
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API calls."""
        msg = {"role": self.role, "content": self.content}
        if self.name:
            msg["name"] = self.name
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        return msg


@dataclass
class AIResponse:
    """
    Standardized response from any AI provider.
    
    This normalizes responses across different providers.
    """
    # Core response
    content: str
    raw_response: Optional[Dict[str, Any]] = None
    
    # Metadata
    provider: ProviderType = ProviderType.OPENAI
    model: str = "gpt-4"
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    
    # Usage tracking
    token_usage: Optional[TokenUsage] = None
    cost: float = 0.0
    latency: float = 0.0  # Seconds
    
    # Status
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    error: Optional[str] = None
    
    # Structured output
    structured_output: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    
    # Tool usage
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timestamps
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "content": self.content,
            "provider": self.provider.value,
            "model": self.model,
            "execution_id": self.execution_id,
            "token_usage": {
                "prompt_tokens": self.token_usage.prompt_tokens if self.token_usage else 0,
                "completion_tokens": self.token_usage.completion_tokens if self.token_usage else 0,
                "total_tokens": self.token_usage.total_tokens if self.token_usage else 0,
            } if self.token_usage else None,
            "cost": self.cost,
            "latency": self.latency,
            "status": self.status.value,
            "error": self.error,
            "structured_output": self.structured_output,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AuditEntry:
    """
    Audit log entry for AI operations.
    
    Every AI call is logged for compliance, debugging, and cost tracking.
    """
    # Identity
    audit_id: str = field(default_factory=lambda: str(uuid4()))
    execution_id: str = ""
    
    # Task details
    task_type: TaskType = TaskType.TEST_GENERATION
    project_id: Optional[str] = None
    user: Optional[str] = None
    
    # Provider details
    provider: ProviderType = ProviderType.OPENAI
    model: str = ""
    prompt_version: Optional[str] = None
    
    # Usage
    token_usage: Optional[TokenUsage] = None
    cost: float = 0.0
    latency: float = 0.0
    
    # Outcome
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    error: Optional[str] = None
    
    # Safety
    safety_violations: List[str] = field(default_factory=list)
    content_filtered: bool = False
    
    # Timestamps
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "audit_id": self.audit_id,
            "execution_id": self.execution_id,
            "task_type": self.task_type.value,
            "project_id": self.project_id,
            "user": self.user,
            "provider": self.provider.value,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "token_usage": {
                "prompt_tokens": self.token_usage.prompt_tokens,
                "completion_tokens": self.token_usage.completion_tokens,
                "total_tokens": self.token_usage.total_tokens,
            } if self.token_usage else None,
            "cost": self.cost,
            "latency": self.latency,
            "status": self.status.value,
            "error": self.error,
            "safety_violations": self.safety_violations,
            "content_filtered": self.content_filtered,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class PromptTemplate:
    """
    Versioned prompt template.
    
    Templates are stored as YAML and rendered with Jinja2.
    """
    # Identity
    template_id: str
    version: str
    description: str
    
    # Template content
    system_prompt: str
    user_prompt_template: str
    
    # Schema
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    author: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    # Configuration
    default_model_config: Optional[ModelConfig] = None


@dataclass
class CreditBalance:
    """User/project credit balance for AI operations."""
    user_id: str
    project_id: Optional[str] = None
    
    # Balance
    total_credits: float = 0.0
    used_credits: float = 0.0
    
    # Limits
    daily_limit: Optional[float] = None
    monthly_limit: Optional[float] = None
    
    # Usage tracking
    daily_used: float = 0.0
    monthly_used: float = 0.0
    last_reset: datetime = field(default_factory=datetime.now)
    
    @property
    def available_credits(self) -> float:
        """Remaining credits."""
        return self.total_credits - self.used_credits
    
    @property
    def is_exhausted(self) -> bool:
        """Check if credits are exhausted."""
        return self.available_credits <= 0
    
    def can_consume(self, amount: float) -> bool:
        """Check if amount can be consumed."""
        if self.is_exhausted:
            return False
        
        # Check daily limit
        if self.daily_limit and (self.daily_used + amount) > self.daily_limit:
            return False
        
        # Check monthly limit
        if self.monthly_limit and (self.monthly_used + amount) > self.monthly_limit:
            return False
        
        return self.available_credits >= amount
    
    def consume(self, amount: float):
        """Consume credits."""
        self.used_credits += amount
        self.daily_used += amount
        self.monthly_used += amount
