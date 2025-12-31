"""
Adapter registry for test execution engine.

Manages loading and instantiation of framework adapters.
"""

from typing import Dict, Type, Optional
from pathlib import Path

from adapters.common.base import BaseTestAdapter


class AdapterRegistry:
    """
    Registry for test framework adapters.
    
    Provides centralized management of adapter loading and instantiation.
    """
    
    def __init__(self):
        """Initialize adapter registry."""
        self._adapters: Dict[str, Type[BaseTestAdapter]] = {}
        self._register_builtin_adapters()
    
    def _register_builtin_adapters(self):
        """Register built-in adapters."""
        # Import adapters
        try:
            from adapters.pytest.adapter import PytestAdapter
            self.register('pytest', PytestAdapter)
        except ImportError:
            pass
        
        try:
            from adapters.robot.robot_adapter import RobotAdapter
            self.register('robot', RobotAdapter)
        except ImportError:
            pass
        
        try:
            from adapters.selenium_pytest.adapter import SeleniumPytestAdapter
            self.register('selenium-pytest', SeleniumPytestAdapter)
        except ImportError:
            pass
        
        try:
            from adapters.selenium_behave.adapter import SeleniumBehaveAdapter
            self.register('selenium-behave', SeleniumBehaveAdapter)
            self.register('behave', SeleniumBehaveAdapter)
        except ImportError:
            pass
        
        try:
            from adapters.cypress import CypressAdapter
            self.register('cypress', CypressAdapter)
        except ImportError:
            pass
        
        try:
            from adapters.playwright import PlaywrightAdapter
            self.register('playwright', PlaywrightAdapter)
        except ImportError:
            pass
        
        try:
            from adapters.selenium_specflow_dotnet import SeleniumSpecFlowAdapter
            self.register('selenium-specflow', SeleniumSpecFlowAdapter)
            self.register('specflow', SeleniumSpecFlowAdapter)
        except ImportError:
            pass
        
        try:
            from adapters.java.selenium.adapter import SeleniumJavaAdapter
            # Note: SeleniumJavaAdapter has different interface, would need wrapper
            # self.register('selenium-java', SeleniumJavaAdapter)
        except ImportError:
            pass
    
    def register(self, name: str, adapter_class: Type[BaseTestAdapter]):
        """
        Register an adapter.
        
        Args:
            name: Framework name (e.g., 'pytest', 'cypress')
            adapter_class: Adapter class implementing BaseTestAdapter
        """
        self._adapters[name] = adapter_class
    
    def get_adapter(
        self,
        framework: str,
        project_root: str,
        **kwargs
    ) -> BaseTestAdapter:
        """
        Get adapter instance for framework.
        
        Args:
            framework: Framework name
            project_root: Path to project root
            **kwargs: Additional adapter-specific arguments
            
        Returns:
            Adapter instance
            
        Raises:
            ValueError: If adapter not found
        """
        if framework not in self._adapters:
            raise ValueError(
                f"Unknown framework: {framework}. "
                f"Available: {', '.join(self.list_adapters())}"
            )
        
        adapter_class = self._adapters[framework]
        
        try:
            # Try to instantiate with project_root
            return adapter_class(project_root, **kwargs)
        except TypeError:
            # Some adapters might need config object
            try:
                # Try alternative instantiation patterns
                return adapter_class(project_root=project_root, **kwargs)
            except Exception as e:
                raise ValueError(
                    f"Failed to instantiate {framework} adapter: {str(e)}"
                )
    
    def list_adapters(self) -> list:
        """List registered adapter names."""
        return sorted(self._adapters.keys())
    
    def is_registered(self, framework: str) -> bool:
        """Check if adapter is registered."""
        return framework in self._adapters


# Global singleton instance
_registry = AdapterRegistry()


def get_adapter(framework: str, project_root: str, **kwargs) -> BaseTestAdapter:
    """Get adapter from global registry."""
    return _registry.get_adapter(framework, project_root, **kwargs)


def register_adapter(name: str, adapter_class: Type[BaseTestAdapter]):
    """Register adapter in global registry."""
    _registry.register(name, adapter_class)


def list_adapters() -> list:
    """List available adapters."""
    return _registry.list_adapters()
