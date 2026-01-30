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
]
