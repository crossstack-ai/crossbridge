"""
CrossBridge AI Module - Production-Grade AI Orchestration.

A provider-agnostic, MCP-enabled, governed orchestration layer that augments
static analysis and coverage with structured AI reasoning.

Features:
- Provider abstraction (OpenAI, Anthropic, vLLM, Ollama, etc.)
- Versioned prompt templates
- AI skills framework
- Cost tracking and credit management
- Audit logging
- Safety validation
- MCP client and server support (coming soon)

Usage:
    from core.ai import get_orchestrator, FlakyAnalyzer
    
    # Get orchestrator
    orchestrator = get_orchestrator()
    
    # Execute a skill
    analyzer = FlakyAnalyzer()
    result = orchestrator.execute_skill(
        skill=analyzer,
        inputs={
            "test_name": "test_login",
            "test_file": "tests/test_auth.py",
            "execution_history": [...]
        }
    )
"""

from core.ai.base import AISkill, LLMProvider
from core.ai.models import (
    AIExecutionContext,
    AIMessage,
    AIResponse,
    AuditEntry,
    CreditBalance,
    ExecutionStatus,
    ModelConfig,
    PromptTemplate,
    ProviderType,
    SafetyLevel,
    TaskType,
    TokenUsage,
)
from core.ai.orchestrator import AIOrchestrator, get_orchestrator
from core.ai.prompts import get_prompt, get_registry, render_prompt
from core.ai.providers import get_available_providers, get_provider
from core.ai.skills import (
    CoverageReasoner,
    FlakyAnalyzer,
    RootCauseAnalyzer,
    TestGenerator,
    TestMigrator,
)

__version__ = "1.0.0"

__all__ = [
    # Core abstractions
    "AISkill",
    "LLMProvider",
    # Models
    "AIExecutionContext",
    "AIMessage",
    "AIResponse",
    "AuditEntry",
    "CreditBalance",
    "ExecutionStatus",
    "ModelConfig",
    "PromptTemplate",
    "ProviderType",
    "SafetyLevel",
    "TaskType",
    "TokenUsage",
    # Orchestrator
    "AIOrchestrator",
    "get_orchestrator",
    # Prompts
    "get_prompt",
    "get_registry",
    "render_prompt",
    # Providers
    "get_available_providers",
    "get_provider",
    # Skills
    "CoverageReasoner",
    "FlakyAnalyzer",
    "RootCauseAnalyzer",
    "TestGenerator",
    "TestMigrator",
]
