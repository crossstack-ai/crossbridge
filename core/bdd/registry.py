"""
BDD Adapter Registry.

Central registry for all BDD framework adapters.
Provides adapter discovery, validation, and selection.
"""

from typing import Dict, List, Optional, Type
from pathlib import Path
import logging

from core.bdd.parser_interface import BDDAdapter, is_adapter_stable
from core.bdd.models import validate_adapter_completeness

logger = logging.getLogger(__name__)


class BDDAdapterRegistry:
    """
    Registry for BDD framework adapters.
    
    Tracks adapter status (Stable vs Beta) and provides adapter selection.
    """
    
    def __init__(self):
        self._adapters: Dict[str, Type[BDDAdapter]] = {}
        self._adapter_status: Dict[str, str] = {}  # "stable" or "beta"
    
    def register(
        self,
        framework_name: str,
        adapter_class: Type[BDDAdapter],
        status: str = "beta"
    ):
        """
        Register a BDD adapter.
        
        Args:
            framework_name: Framework identifier (cucumber-java, robot-bdd, etc.)
            adapter_class: Adapter class
            status: "stable" or "beta"
        """
        if status not in ["stable", "beta"]:
            raise ValueError(f"Invalid status: {status}. Must be 'stable' or 'beta'")
        
        self._adapters[framework_name] = adapter_class
        self._adapter_status[framework_name] = status
        
        logger.info(f"Registered {framework_name} adapter (status: {status})")
    
    def get_adapter(self, framework_name: str, **kwargs) -> Optional[BDDAdapter]:
        """
        Get adapter instance for framework.
        
        Args:
            framework_name: Framework identifier
            **kwargs: Arguments to pass to adapter constructor
        
        Returns:
            Adapter instance or None
        """
        adapter_class = self._adapters.get(framework_name)
        if not adapter_class:
            logger.warning(f"No adapter found for framework: {framework_name}")
            return None
        
        try:
            return adapter_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to create adapter for {framework_name}: {e}")
            return None
    
    def get_adapter_status(self, framework_name: str) -> Optional[str]:
        """Get adapter status (stable/beta)."""
        return self._adapter_status.get(framework_name)
    
    def list_adapters(self) -> Dict[str, Dict[str, str]]:
        """
        List all registered adapters.
        
        Returns:
            Dict mapping framework name to adapter info
        """
        adapters_info = {}
        
        for framework_name, adapter_class in self._adapters.items():
            adapters_info[framework_name] = {
                "status": self._adapter_status[framework_name],
                "class": adapter_class.__name__
            }
        
        return adapters_info
    
    def get_stable_adapters(self) -> List[str]:
        """Get list of stable adapter names."""
        return [
            name for name, status in self._adapter_status.items()
            if status == "stable"
        ]
    
    def get_beta_adapters(self) -> List[str]:
        """Get list of beta adapter names."""
        return [
            name for name, status in self._adapter_status.items()
            if status == "beta"
        ]
    
    def validate_adapter(self, framework_name: str) -> Dict[str, any]:
        """
        Validate adapter completeness and determine if it should be promoted.
        
        Args:
            framework_name: Framework to validate
        
        Returns:
            Validation report with:
                - is_complete: bool
                - missing_capabilities: list
                - current_status: str
                - recommended_status: str
        """
        adapter = self.get_adapter(framework_name)
        if not adapter:
            return {
                "is_complete": False,
                "error": f"Adapter not found: {framework_name}"
            }
        
        # Get capabilities
        capabilities = adapter.validate_completeness()
        is_complete, missing = validate_adapter_completeness(capabilities)
        is_stable = is_adapter_stable(adapter)
        
        current_status = self._adapter_status.get(framework_name, "unknown")
        
        # Recommend promotion if complete
        if is_stable and current_status == "beta":
            recommended_status = "stable"
        elif not is_stable and current_status == "stable":
            recommended_status = "beta"
        else:
            recommended_status = current_status
        
        return {
            "is_complete": is_complete,
            "missing_capabilities": missing,
            "current_status": current_status,
            "recommended_status": recommended_status,
            "capabilities": capabilities
        }
    
    def promote_to_stable(self, framework_name: str, force: bool = False):
        """
        Promote adapter from beta to stable.
        
        Args:
            framework_name: Framework to promote
            force: Bypass validation check
        """
        if framework_name not in self._adapters:
            raise ValueError(f"Adapter not registered: {framework_name}")
        
        if not force:
            validation = self.validate_adapter(framework_name)
            if not validation["is_complete"]:
                raise ValueError(
                    f"Adapter {framework_name} is incomplete. "
                    f"Missing: {validation['missing_capabilities']}"
                )
        
        self._adapter_status[framework_name] = "stable"
        logger.info(f"Promoted {framework_name} to stable status")


# Global registry instance
_registry = BDDAdapterRegistry()


def register_adapter(framework_name: str, adapter_class: Type[BDDAdapter], status: str = "beta"):
    """Register adapter with global registry."""
    _registry.register(framework_name, adapter_class, status)


def get_adapter(framework_name: str, **kwargs) -> Optional[BDDAdapter]:
    """Get adapter from global registry."""
    return _registry.get_adapter(framework_name, **kwargs)


def get_adapter_registry() -> BDDAdapterRegistry:
    """Get global adapter registry."""
    return _registry


# Register all available adapters
def register_default_adapters():
    """Register default BDD adapters."""
    
    # Cucumber Java - STABLE (promoted from beta)
    try:
        from adapters.selenium_bdd_java.enhanced_adapter import EnhancedCucumberJavaAdapter
        register_adapter("cucumber-java", EnhancedCucumberJavaAdapter, status="stable")
    except ImportError:
        logger.warning("Enhanced Cucumber Java adapter not available (missing javalang)")
    
    # Robot Framework BDD - STABLE
    try:
        from adapters.robot.bdd_adapter import RobotBDDAdapter
        register_adapter("robot-bdd", RobotBDDAdapter, status="stable")
    except ImportError:
        logger.warning("Robot BDD adapter not available (missing robotframework)")
    
    # JBehave - STABLE (promoted from beta - XML parser complete)
    try:
        from adapters.java.jbehave_adapter import JBehaveAdapter
        register_adapter("jbehave", JBehaveAdapter, status="stable")
    except ImportError:
        logger.warning("JBehave adapter not available")


# Auto-register on import
register_default_adapters()
