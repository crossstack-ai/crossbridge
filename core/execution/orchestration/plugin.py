"""
Execution Plugin System

Formalizes the existing Execution Orchestration as CrossBridge's plugin architecture.

KEY INSIGHT:
-----------
Execution Orchestration IS the plugin system.
- Orchestrator = Plugin Host
- Strategies = Decision Plugins
- Adapters = Execution Plugins

This module provides:
1. ExecutionPlugin - Formal plugin contract
2. Plugin lifecycle management
3. Dynamic plugin registration
4. Extension points for third-party plugins

DESIGN PHILOSOPHY:
-----------------
CrossBridge doesn't need a separate plugin system. The Execution Orchestration
already implements plugin patterns correctly:
- Framework-agnostic
- Sidecar-compatible
- CLI-level integration
- Non-invasive execution

This module simply formalizes what exists and provides extension points.

USAGE EXAMPLES:
--------------

Example 1: Using the default orchestration plugin
    plugin = OrchestrationExecutionPlugin(workspace, config)
    result = plugin.execute(execution_request)

Example 2: Registering a custom plugin
    registry = get_plugin_registry()
    registry.register('custom-orchestrator', CustomPlugin)
    plugin = registry.get_plugin('custom-orchestrator')

Example 3: Extending with custom strategy
    @strategy_plugin('custom-risk')
    class CustomRiskStrategy(ExecutionStrategy):
        def select_tests(self, context):
            # Custom logic
            pass

Example 4: Extending with custom adapter
    @adapter_plugin('my-framework')
    class MyFrameworkAdapter(FrameworkAdapter):
        def plan_to_command(self, plan, workspace):
            # Custom logic
            pass
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

from .api import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionPlan,
    ExecutionStatus,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Core Plugin Interface
# ============================================================================

class ExecutionPlugin(ABC):
    """
    Base interface for execution plugins.
    
    An ExecutionPlugin is responsible for:
    1. Accepting execution requests
    2. Planning what to execute (strategy layer)
    3. Executing the plan (adapter layer)
    4. Returning normalized results
    
    KEY CHARACTERISTICS:
    - Framework-agnostic at the plugin boundary
    - Non-invasive (frameworks unchanged)
    - Sidecar-compatible
    - CLI-level integration
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        """
        Initialize plugin.
        
        Args:
            name: Plugin identifier (e.g., 'orchestration', 'custom-executor')
            version: Plugin version for compatibility tracking
        """
        self.name = name
        self.version = version
        self.enabled = True
    
    @abstractmethod
    def supports(self, request: ExecutionRequest) -> bool:
        """
        Check if this plugin can handle the request.
        
        Allows multiple plugins to coexist with different capabilities.
        
        Args:
            request: Execution request
            
        Returns:
            True if plugin can handle this request
        """
        pass
    
    @abstractmethod
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute tests based on request.
        
        This is the main plugin entry point.
        
        Args:
            request: Execution request with framework, strategy, etc.
            
        Returns:
            ExecutionResult with standardized metrics
        """
        pass
    
    def validate(self, request: ExecutionRequest) -> List[str]:
        """
        Validate request before execution.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not request.framework:
            errors.append("Framework is required")
        
        if not request.strategy:
            errors.append("Strategy is required")
        
        if not request.environment:
            errors.append("Environment is required")
        
        return errors
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get plugin capabilities metadata.
        
        Returns:
            Dict with plugin capabilities:
            - supported_frameworks: List of frameworks
            - supported_strategies: List of strategies
            - supports_parallel: Whether parallel execution is supported
            - supports_sidecar: Whether sidecar mode is supported
        """
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "supported_frameworks": [],
            "supported_strategies": [],
            "supports_parallel": False,
            "supports_sidecar": False,
        }


# ============================================================================
# Plugin Extension Points
# ============================================================================

class StrategyPluginExtension(ABC):
    """
    Extension point for custom strategies.
    
    Strategies are decision plugins - they determine WHAT to run.
    """
    
    @abstractmethod
    def select_tests(self, context: Any) -> ExecutionPlan:
        """Select tests based on strategy logic."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get strategy name (e.g., 'smoke', 'impacted')."""
        pass


class AdapterPluginExtension(ABC):
    """
    Extension point for custom framework adapters.
    
    Adapters are execution plugins - they determine HOW to run.
    """
    
    @abstractmethod
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        """Convert execution plan to framework CLI command."""
        pass
    
    @abstractmethod
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        """Parse framework output into ExecutionResult."""
        pass
    
    @abstractmethod
    def get_framework(self) -> str:
        """Get framework name (e.g., 'pytest', 'testng')."""
        pass


# ============================================================================
# Default Implementation: Orchestration Plugin
# ============================================================================

class OrchestrationExecutionPlugin(ExecutionPlugin):
    """
    Default execution plugin wrapping the Execution Orchestrator.
    
    This is CrossBridge's primary execution plugin. It wraps the existing
    ExecutionOrchestrator and exposes it through the plugin interface.
    
    The orchestrator already implements plugin patterns correctly:
    - Strategies = Decision plugins
    - Adapters = Execution plugins
    - Orchestrator = Plugin host
    
    This class just formalizes that architecture.
    """
    
    def __init__(
        self,
        workspace: Path,
        config: Optional[Dict[str, Any]] = None,
        name: str = "orchestration",
        version: str = "0.2.0"
    ):
        """
        Initialize orchestration plugin.
        
        Args:
            workspace: Path to project workspace
            config: Configuration dict (from crossbridge.yml)
            name: Plugin name
            version: Plugin version
        """
        super().__init__(name, version)
        self.workspace = workspace
        self.config = config or {}
        
        # Lazy-load orchestrator (avoids circular imports)
        self._orchestrator = None
    
    @property
    def orchestrator(self):
        """Get orchestrator instance (lazy-loaded)."""
        if self._orchestrator is None:
            from .orchestrator import ExecutionOrchestrator
            self._orchestrator = ExecutionOrchestrator(self.workspace, self.config)
        return self._orchestrator
    
    def supports(self, request: ExecutionRequest) -> bool:
        """
        Check if orchestration plugin supports this request.
        
        The orchestration plugin supports all standard frameworks and strategies.
        """
        # List of supported frameworks
        supported_frameworks = [
            'pytest', 'robot', 'testng', 'junit', 'cucumber',
            'cypress', 'playwright', 'behave', 'specflow', 'nunit',
            'selenium-pytest', 'selenium-java', 'selenium-behave',
            'restassured', 'selenium-dotnet', 'selenium-bdd-java'
        ]
        
        # Check framework support
        if request.framework.lower() not in supported_frameworks:
            return False
        
        return True
    
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute tests through the orchestrator.
        
        This delegates to the existing ExecutionOrchestrator, which:
        1. Builds execution context
        2. Applies strategy to select tests
        3. Uses adapter to execute tests
        4. Returns standardized result
        """
        # Validate request
        errors = self.validate(request)
        if errors:
            return self._create_validation_error_result(request, errors)
        
        try:
            # Delegate to orchestrator
            logger.info(
                f"Orchestration plugin executing: {request.framework} "
                f"with {request.strategy.value} strategy"
            )
            return self.orchestrator.execute(request)
            
        except Exception as e:
            logger.error(f"Orchestration plugin execution failed: {e}", exc_info=True)
            return self._create_error_result(request, str(e))
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get orchestration plugin capabilities."""
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled,
            "supported_frameworks": [
                "pytest", "robot", "testng", "junit", "cucumber",
                "cypress", "playwright", "behave", "specflow",
                "selenium-pytest", "selenium-java", "selenium-behave",
                "restassured", "selenium-dotnet", "selenium-bdd-java"
            ],
            "supported_strategies": ["smoke", "impacted", "risk", "full"],
            "supports_parallel": True,
            "supports_sidecar": True,
            "supports_dry_run": True,
            "supports_ci_mode": True,
        }
    
    def _create_validation_error_result(
        self,
        request: ExecutionRequest,
        errors: List[str]
    ) -> ExecutionResult:
        """Create result for validation errors."""
        return ExecutionResult(
            executed_tests=[],
            passed_tests=[],
            failed_tests=[],
            skipped_tests=[],
            error_tests=[],
            execution_time_seconds=0,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[],
            log_paths=[],
            framework=request.framework,
            environment=request.environment,
            status=ExecutionStatus.FAILED,
            error_message="; ".join(errors),
        )
    
    def _create_error_result(
        self,
        request: ExecutionRequest,
        error: str
    ) -> ExecutionResult:
        """Create result for execution errors."""
        return ExecutionResult(
            executed_tests=[],
            passed_tests=[],
            failed_tests=[],
            skipped_tests=[],
            error_tests=[],
            execution_time_seconds=0,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            report_paths=[],
            log_paths=[],
            framework=request.framework,
            environment=request.environment,
            status=ExecutionStatus.FAILED,
            error_message=error,
        )


# ============================================================================
# Plugin Registration Decorators
# ============================================================================

def strategy_plugin(name: str):
    """
    Decorator to register a custom strategy plugin.
    
    Usage:
        @strategy_plugin('my-strategy')
        class MyStrategy(ExecutionStrategy):
            def select_tests(self, context):
                # Custom logic
                pass
    """
    def decorator(cls):
        # Register with strategy factory (will be implemented)
        cls._plugin_name = name
        return cls
    return decorator


def adapter_plugin(framework: str):
    """
    Decorator to register a custom adapter plugin.
    
    Usage:
        @adapter_plugin('my-framework')
        class MyAdapter(FrameworkAdapter):
            def plan_to_command(self, plan, workspace):
                # Custom logic
                pass
    """
    def decorator(cls):
        # Register with adapter factory (will be implemented)
        cls._plugin_framework = framework
        return cls
    return decorator


def execution_plugin(name: str, version: str = "1.0.0"):
    """
    Decorator to register a custom execution plugin.
    
    Usage:
        @execution_plugin('my-executor', '1.0.0')
        class MyExecutor(ExecutionPlugin):
            def execute(self, request):
                # Custom logic
                pass
    """
    def decorator(cls):
        # Register with plugin registry
        cls._plugin_name = name
        cls._plugin_version = version
        return cls
    return decorator


# ============================================================================
# Export Public API
# ============================================================================

__all__ = [
    'ExecutionPlugin',
    'StrategyPluginExtension',
    'AdapterPluginExtension',
    'OrchestrationExecutionPlugin',
    'strategy_plugin',
    'adapter_plugin',
    'execution_plugin',
]
