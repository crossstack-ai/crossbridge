"""
Plugin Registry

Centralized management for execution plugins, strategies, and adapters.

This registry provides:
1. Plugin lifecycle management (register, unregister, get)
2. Dynamic plugin discovery
3. Plugin validation and compatibility checking
4. Singleton access pattern

ARCHITECTURE:
------------
The registry manages THREE types of plugins:
1. Execution Plugins - Full execution implementations (e.g., OrchestrationExecutionPlugin)
2. Strategy Plugins - Test selection strategies (e.g., SmokeStrategy, RiskStrategy)
3. Adapter Plugins - Framework execution adapters (e.g., PytestAdapter, TestNGAdapter)

DESIGN PHILOSOPHY:
-----------------
The registry doesn't replace the existing adapter_registry.py or strategy factories.
Instead, it WRAPS them to provide a unified plugin interface.

This allows:
- Existing code to work unchanged
- New plugin-based extensions
- Third-party plugin support
- Dynamic plugin loading

USAGE EXAMPLES:
--------------

Example 1: Get the default orchestration plugin
    registry = get_plugin_registry()
    plugin = registry.get_execution_plugin('orchestration')
    result = plugin.execute(request)

Example 2: Register a custom execution plugin
    registry = get_plugin_registry()
    registry.register_execution_plugin('custom', CustomPlugin)
    plugin = registry.get_execution_plugin('custom')

Example 3: Register a custom strategy
    registry = get_plugin_registry()
    registry.register_strategy_plugin('ml-based', MLStrategy)

Example 4: List available plugins
    registry = get_plugin_registry()
    print(f"Execution plugins: {registry.list_execution_plugins()}")
    print(f"Strategies: {registry.list_strategy_plugins()}")
    print(f"Adapters: {registry.list_adapter_plugins()}")
"""

from typing import Dict, Type, Optional, List, Any
from pathlib import Path
import logging

from .plugin import (
    ExecutionPlugin,
    OrchestrationExecutionPlugin,
    StrategyPluginExtension,
    AdapterPluginExtension,
)

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry for all plugin types.
    
    Manages three plugin categories:
    1. Execution Plugins - Complete execution implementations
    2. Strategy Plugins - Test selection strategies  
    3. Adapter Plugins - Framework-specific adapters
    """
    
    def __init__(self):
        """Initialize registry."""
        # Plugin storage
        self._execution_plugins: Dict[str, Type[ExecutionPlugin]] = {}
        self._strategy_plugins: Dict[str, Type[StrategyPluginExtension]] = {}
        self._adapter_plugins: Dict[str, Type[AdapterPluginExtension]] = {}
        
        # Plugin instances (cached)
        self._execution_instances: Dict[str, ExecutionPlugin] = {}
        
        # Register built-in plugins
        self._register_builtin_plugins()
    
    def _register_builtin_plugins(self):
        """Register built-in CrossBridge plugins."""
        logger.info("Registering built-in plugins...")
        
        # Register default orchestration plugin
        self.register_execution_plugin('orchestration', OrchestrationExecutionPlugin)
        self.register_execution_plugin('default', OrchestrationExecutionPlugin)
        
        # Register built-in strategies (wrapping existing implementation)
        self._register_builtin_strategies()
        
        # Register built-in adapters (wrapping existing implementation)
        self._register_builtin_adapters()
        
        logger.info(
            f"Registered {len(self._execution_plugins)} execution plugins, "
            f"{len(self._strategy_plugins)} strategies, "
            f"{len(self._adapter_plugins)} adapters"
        )
    
    def _register_builtin_strategies(self):
        """Register built-in execution strategies."""
        try:
            from .strategies import (
                SmokeStrategy,
                ImpactedStrategy,
                RiskBasedStrategy,
                FullStrategy,
            )
            
            # Note: These are NOT StrategyPluginExtension yet,
            # but we can register them for discovery
            self._strategy_plugins['smoke'] = SmokeStrategy
            self._strategy_plugins['impacted'] = ImpactedStrategy
            self._strategy_plugins['risk'] = RiskBasedStrategy
            self._strategy_plugins['full'] = FullStrategy
            
        except ImportError as e:
            logger.warning(f"Could not import built-in strategies: {e}")
    
    def _register_builtin_adapters(self):
        """Register built-in framework adapters for all 13 supported frameworks."""
        try:
            from .adapters import (
                TestNGAdapter,
                PytestAdapter,
                RobotAdapter,
                CypressAdapter,
                PlaywrightAdapter,
                JUnitAdapter,
                CucumberAdapter,
                BehaveAdapter,
                SpecFlowAdapter,
                NUnitAdapter,
                RestAssuredAdapter,
            )
            
            # Register all 13 framework adapters as plugins
            self._adapter_plugins['testng'] = TestNGAdapter
            self._adapter_plugins['junit'] = JUnitAdapter
            self._adapter_plugins['pytest'] = PytestAdapter
            self._adapter_plugins['robot'] = RobotAdapter
            self._adapter_plugins['cypress'] = CypressAdapter
            self._adapter_plugins['playwright'] = PlaywrightAdapter
            self._adapter_plugins['cucumber'] = CucumberAdapter
            self._adapter_plugins['behave'] = BehaveAdapter
            self._adapter_plugins['specflow'] = SpecFlowAdapter
            self._adapter_plugins['nunit'] = NUnitAdapter
            self._adapter_plugins['restassured'] = RestAssuredAdapter
            
            # Aliases for common naming variations
            self._adapter_plugins['rest-assured'] = RestAssuredAdapter
            self._adapter_plugins['selenium-pytest'] = PytestAdapter
            self._adapter_plugins['selenium-behave'] = BehaveAdapter
            
        except ImportError as e:
            logger.warning(f"Could not import built-in adapters: {e}")
    
    # ========================================================================
    # Execution Plugin Management
    # ========================================================================
    
    def register_execution_plugin(
        self,
        name: str,
        plugin_class: Type[ExecutionPlugin]
    ):
        """
        Register an execution plugin.
        
        Args:
            name: Plugin identifier (e.g., 'orchestration', 'custom-executor')
            plugin_class: Plugin class implementing ExecutionPlugin
        """
        if not issubclass(plugin_class, ExecutionPlugin):
            raise ValueError(
                f"{plugin_class.__name__} must inherit from ExecutionPlugin"
            )
        
        self._execution_plugins[name] = plugin_class
        logger.info(f"Registered execution plugin: {name}")
    
    def get_execution_plugin(
        self,
        name: str = 'default',
        workspace: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ExecutionPlugin:
        """
        Get execution plugin instance.
        
        Args:
            name: Plugin identifier
            workspace: Path to project workspace
            config: Configuration dict
            **kwargs: Additional plugin-specific arguments
            
        Returns:
            ExecutionPlugin instance
            
        Raises:
            ValueError: If plugin not found
        """
        if name not in self._execution_plugins:
            raise ValueError(
                f"Unknown execution plugin: {name}. "
                f"Available: {', '.join(self.list_execution_plugins())}"
            )
        
        # Check cache (for singleton behavior)
        cache_key = f"{name}:{workspace}"
        if cache_key in self._execution_instances:
            return self._execution_instances[cache_key]
        
        # Instantiate plugin
        plugin_class = self._execution_plugins[name]
        
        try:
            # Try workspace + config pattern (for OrchestrationExecutionPlugin)
            if workspace:
                instance = plugin_class(workspace, config, **kwargs)
            else:
                instance = plugin_class(config, **kwargs)
            
            # Cache instance
            self._execution_instances[cache_key] = instance
            
            return instance
            
        except Exception as e:
            raise ValueError(
                f"Failed to instantiate execution plugin '{name}': {str(e)}"
            )
    
    def list_execution_plugins(self) -> List[str]:
        """List registered execution plugin names."""
        return sorted(self._execution_plugins.keys())
    
    def unregister_execution_plugin(self, name: str):
        """Unregister an execution plugin."""
        if name in self._execution_plugins:
            del self._execution_plugins[name]
            logger.info(f"Unregistered execution plugin: {name}")
    
    # ========================================================================
    # Strategy Plugin Management
    # ========================================================================
    
    def register_strategy_plugin(
        self,
        name: str,
        strategy_class: Type[StrategyPluginExtension]
    ):
        """
        Register a strategy plugin.
        
        Args:
            name: Strategy identifier (e.g., 'smoke', 'ml-based')
            strategy_class: Strategy class
        """
        self._strategy_plugins[name] = strategy_class
        logger.info(f"Registered strategy plugin: {name}")
    
    def get_strategy_plugin(self, name: str) -> Type[StrategyPluginExtension]:
        """
        Get strategy plugin class.
        
        Args:
            name: Strategy identifier
            
        Returns:
            Strategy class
            
        Raises:
            ValueError: If strategy not found
        """
        if name not in self._strategy_plugins:
            raise ValueError(
                f"Unknown strategy: {name}. "
                f"Available: {', '.join(self.list_strategy_plugins())}"
            )
        
        return self._strategy_plugins[name]
    
    def list_strategy_plugins(self) -> List[str]:
        """List registered strategy plugin names."""
        return sorted(self._strategy_plugins.keys())
    
    def unregister_strategy_plugin(self, name: str):
        """Unregister a strategy plugin."""
        if name in self._strategy_plugins:
            del self._strategy_plugins[name]
            logger.info(f"Unregistered strategy plugin: {name}")
    
    # ========================================================================
    # Adapter Plugin Management
    # ========================================================================
    
    def register_adapter_plugin(
        self,
        framework: str,
        adapter_class: Type[AdapterPluginExtension]
    ):
        """
        Register an adapter plugin.
        
        Args:
            framework: Framework identifier (e.g., 'pytest', 'testng')
            adapter_class: Adapter class
        """
        self._adapter_plugins[framework] = adapter_class
        logger.info(f"Registered adapter plugin: {framework}")
    
    def get_adapter_plugin(self, framework: str) -> Type[AdapterPluginExtension]:
        """
        Get adapter plugin class.
        
        Args:
            framework: Framework identifier
            
        Returns:
            Adapter class
            
        Raises:
            ValueError: If adapter not found
        """
        if framework not in self._adapter_plugins:
            raise ValueError(
                f"Unknown framework: {framework}. "
                f"Available: {', '.join(self.list_adapter_plugins())}"
            )
        
        return self._adapter_plugins[framework]
    
    def list_adapter_plugins(self) -> List[str]:
        """List registered adapter plugin names."""
        return sorted(self._adapter_plugins.keys())
    
    def unregister_adapter_plugin(self, framework: str):
        """Unregister an adapter plugin."""
        if framework in self._adapter_plugins:
            del self._adapter_plugins[framework]
            logger.info(f"Unregistered adapter plugin: {framework}")
    
    # ========================================================================
    # Discovery & Metadata
    # ========================================================================
    
    def get_plugin_info(self, name: str, plugin_type: str = 'execution') -> Dict[str, Any]:
        """
        Get metadata about a plugin.
        
        Args:
            name: Plugin identifier
            plugin_type: 'execution', 'strategy', or 'adapter'
            
        Returns:
            Dict with plugin metadata
        """
        if plugin_type == 'execution':
            if name not in self._execution_plugins:
                return {}
            
            plugin_class = self._execution_plugins[name]
            
            return {
                "name": name,
                "type": "execution",
                "class": plugin_class.__name__,
                "module": plugin_class.__module__,
            }
        
        elif plugin_type == 'strategy':
            if name not in self._strategy_plugins:
                return {}
            
            strategy_class = self._strategy_plugins[name]
            
            return {
                "name": name,
                "type": "strategy",
                "class": strategy_class.__name__,
                "module": strategy_class.__module__,
            }
        
        elif plugin_type == 'adapter':
            if name not in self._adapter_plugins:
                return {}
            
            adapter_class = self._adapter_plugins[name]
            
            return {
                "name": name,
                "type": "adapter",
                "class": adapter_class.__name__,
                "module": adapter_class.__module__,
            }
        
        return {}
    
    def get_all_plugins_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get metadata for all registered plugins.
        
        Returns:
            Dict with three lists: execution_plugins, strategies, adapters
        """
        return {
            "execution_plugins": [
                self.get_plugin_info(name, 'execution')
                for name in self.list_execution_plugins()
            ],
            "strategies": [
                self.get_plugin_info(name, 'strategy')
                for name in self.list_strategy_plugins()
            ],
            "adapters": [
                self.get_plugin_info(name, 'adapter')
                for name in self.list_adapter_plugins()
            ],
        }


# ============================================================================
# Global Singleton Access
# ============================================================================

_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """
    Get global plugin registry instance (singleton).
    
    Returns:
        PluginRegistry singleton
    """
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def reset_plugin_registry():
    """Reset global registry (mainly for testing)."""
    global _registry
    _registry = None


# ============================================================================
# Convenience Functions
# ============================================================================

def get_execution_plugin(
    name: str = 'default',
    workspace: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> ExecutionPlugin:
    """
    Convenience function to get execution plugin.
    
    Usage:
        plugin = get_execution_plugin('orchestration', workspace='/path/to/project')
        result = plugin.execute(request)
    """
    return get_plugin_registry().get_execution_plugin(name, workspace, config, **kwargs)


def list_available_plugins() -> Dict[str, List[str]]:
    """
    List all available plugins.
    
    Returns:
        Dict with three lists: execution, strategies, adapters
    """
    registry = get_plugin_registry()
    return {
        "execution": registry.list_execution_plugins(),
        "strategies": registry.list_strategy_plugins(),
        "adapters": registry.list_adapter_plugins(),
    }


# ============================================================================
# Export Public API
# ============================================================================

__all__ = [
    'PluginRegistry',
    'get_plugin_registry',
    'reset_plugin_registry',
    'get_execution_plugin',
    'list_available_plugins',
]
