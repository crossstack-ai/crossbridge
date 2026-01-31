"""
Crossbridge Execution Orchestration

This module implements the execution orchestrator that enables intelligent test execution
while maintaining framework-agnostic, non-invasive principles.

Philosophy:
- Crossbridge orchestrates (decides what/when/how) but never replaces framework execution
- Frameworks remain the source of truth for execution semantics
- No test code changes required
- CI/CD native integration

Core Components:
- ExecutionAPI: Request/response contracts
- ExecutionStrategies: Intelligent test selection (Smoke, Impacted, Risk, Full)
- FrameworkAdapters: Framework-specific invocation patterns
- ExecutionOrchestrator: Coordinates the entire execution flow

Plugin Architecture:
- ExecutionPlugin: Base interface for execution plugins
- PluginRegistry: Centralized plugin management
- OrchestrationExecutionPlugin: Default plugin wrapping the orchestrator
- Strategy & Adapter plugins for extensibility

KEY INSIGHT: Execution Orchestration IS the plugin architecture.
"""

from .api import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionPlan,
    ExecutionStatus,
    ExecutionContext,
)
from .orchestrator import ExecutionOrchestrator, create_orchestrator
from .strategies import (
    ExecutionStrategy,
    SmokeStrategy,
    ImpactedStrategy,
    RiskBasedStrategy,
    FullStrategy,
    StrategyType,
    create_strategy,
)
from .plugin import (
    ExecutionPlugin,
    OrchestrationExecutionPlugin,
    StrategyPluginExtension,
    AdapterPluginExtension,
    strategy_plugin,
    adapter_plugin,
    execution_plugin,
)
from .plugin_registry import (
    PluginRegistry,
    get_plugin_registry,
    get_execution_plugin,
    list_available_plugins,
)

__all__ = [
    # API
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionPlan",
    "ExecutionStatus",
    "ExecutionContext",
    # Orchestrator
    "ExecutionOrchestrator",
    "create_orchestrator",
    # Strategies
    "ExecutionStrategy",
    "SmokeStrategy",
    "ImpactedStrategy",
    "RiskBasedStrategy",
    "FullStrategy",
    "StrategyType",
    "create_strategy",
    # Plugin System
    "ExecutionPlugin",
    "OrchestrationExecutionPlugin",
    "StrategyPluginExtension",
    "AdapterPluginExtension",
    "strategy_plugin",
    "adapter_plugin",
    "execution_plugin",
    "PluginRegistry",
    "get_plugin_registry",
    "get_execution_plugin",
    "list_available_plugins",
]
