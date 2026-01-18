"""
CrossBridge Hook SDK

Provides the core SDK for framework hooks to emit execution events.
This is the single entry point for all test frameworks to integrate with CrossBridge.

Key principles:
- Optional: Hooks can be disabled without breaking tests
- Lightweight: Minimal overhead on test execution
- Versioned: Event schema is versioned for backward compatibility
- Framework-agnostic: Works with any test framework
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from .events import CrossBridgeEvent, TestStartEvent, TestEndEvent, ApiCallEvent, UiInteractionEvent, StepEvent
from .event_persistence import EventPersistence

logger = logging.getLogger(__name__)


class CrossBridgeHookSDK:
    """
    CrossBridge Hook SDK for framework integration.
    
    This is the primary interface for test frameworks to emit execution metadata
    to CrossBridge without CrossBridge controlling or owning test execution.
    
    Usage:
        # Initialize once
        crossbridge = CrossBridgeHookSDK()
        
        # Emit events during test execution
        crossbridge.emit_test_start("pytest", "tests/test_login.py::test_valid_credentials")
        crossbridge.emit_test_end("pytest", "tests/test_login.py::test_valid_credentials", "passed", 1200)
    """
    
    _instance: Optional['CrossBridgeHookSDK'] = None
    
    def __new__(cls):
        """Singleton pattern to ensure single SDK instance per process"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the Hook SDK"""
        if self._initialized:
            return
            
        self._initialized = True
        self.enabled = self._is_enabled()
        self.mode = self._get_mode()
        self.persistence = EventPersistence() if self.enabled else None
        
        # Version tracking configuration
        self.application_version = self._get_version_info('application_version', 'APP_VERSION')
        self.product_name = self._get_version_info('product_name', 'PRODUCT_NAME')
        self.environment = self._get_version_info('environment', 'ENVIRONMENT')
        
        if self.enabled:
            logger.info(f"CrossBridge Hook SDK initialized (mode={self.mode})")
            if self.application_version or self.product_name or self.environment:
                logger.info(f"Version tracking: product={self.product_name}, version={self.application_version}, env={self.environment}")
        else:
            logger.debug("CrossBridge Hook SDK disabled")
    
    def _is_enabled(self) -> bool:
        """Check if hooks are enabled via configuration"""
        # Check environment variable first
        if os.getenv('CROSSBRIDGE_HOOKS_ENABLED', '').lower() == 'false':
            return False
        
        # Check config file
        config_path = Path('crossbridge.yaml')
        if config_path.exists():
            import yaml
            try:
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                    return config.get('crossbridge', {}).get('hooks', {}).get('enabled', True)
            except Exception as e:
                logger.warning(f"Failed to read config: {e}")
        
        # Default: enabled
        return True
    
    def _get_mode(self) -> str:
        """Get current CrossBridge mode"""
        # Environment variable takes precedence
        mode = os.getenv('CROSSBRIDGE_MODE', '').lower()
        if mode in ['migration', 'observer']:
            return mode
        
        # Check config file
        config_path = Path('crossbridge.yaml')
        if config_path.exists():
            import yaml
            try:
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                    return config.get('crossbridge', {}).get('mode', 'observer')
            except Exception:
                pass
        
        # Default: observer (post-migration mode)
        return 'observer'
    
    def _get_version_info(self, config_key: str, env_key: str) -> Optional[str]:
        """
        Get version information from environment or config file.
        
        Args:
            config_key: Key in crossbridge.yaml (e.g., 'application_version')
            env_key: Environment variable name (e.g., 'APP_VERSION')
            
        Returns:
            Version string or None
        """
        # Try environment variable first (CI/CD pipelines)
        value = os.getenv(env_key) or os.getenv(f'CROSSBRIDGE_{env_key}')
        if value:
            return value
        
        # Try config file
        config_path = Path('crossbridge.yaml')
        if config_path.exists():
            import yaml
            try:
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                    return config.get('crossbridge', {}).get('application', {}).get(config_key)
            except Exception:
                pass
        
        return None
    
    def _enrich_event_with_version(self, event: CrossBridgeEvent) -> None:
        """
        Enrich event with version information if not already set.
        
        Args:
            event: Event to enrich
        """
        if not event.application_version:
            event.application_version = self.application_version
        if not event.product_name:
            event.product_name = self.product_name
        if not event.environment:
            event.environment = self.environment
    
    def emit(self, event: CrossBridgeEvent) -> None:
        """
        Emit a CrossBridge event.
        
        This is the core method that all framework hooks use to send events.
        Events are persisted to PostgreSQL and used for coverage intelligence.
        
        Args:
            event: CrossBridgeEvent instance to emit
        """
        if not self.enabled:
            return
        
        try:
            # Enrich event with version information
            self._enrich_event_with_version(event)
            
            # Persist event to database
            if self.persistence:
                self.persistence.store_event(event)
            
            # Optional: Emit to message queue for real-time processing
            self._emit_to_queue(event)
            
        except Exception as e:
            # Never fail test execution due to hook errors
            logger.error(f"Failed to emit CrossBridge event: {e}", exc_info=True)
    
    def _emit_to_queue(self, event: CrossBridgeEvent) -> None:
        """Optionally emit event to message queue for real-time processing"""
        # Future: Kafka/Redis/RabbitMQ integration
        pass
    
    # Convenience methods for common event types
    
    def emit_test_start(
        self,
        framework: str,
        test_id: str,
        **metadata
    ) -> None:
        """Emit test start event"""
        event = TestStartEvent(framework=framework, test_id=test_id, metadata=metadata)
        self.emit(event)
    
    def emit_test_end(
        self,
        framework: str,
        test_id: str,
        status: str,
        duration_ms: int,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
        **metadata
    ) -> None:
        """Emit test end event"""
        event = TestEndEvent(
            framework=framework,
            test_id=test_id,
            status=status,
            duration_ms=duration_ms,
            error_message=error_message,
            stack_trace=stack_trace,
            metadata=metadata
        )
        self.emit(event)
    
    def emit_api_call(
        self,
        framework: str,
        test_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: Optional[int] = None,
        **metadata
    ) -> None:
        """Emit API call event"""
        event = ApiCallEvent(
            framework=framework,
            test_id=test_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            metadata=metadata
        )
        self.emit(event)
    
    def emit_ui_interaction(
        self,
        framework: str,
        test_id: str,
        component_name: str,
        interaction_type: str,
        page_url: str,
        **metadata
    ) -> None:
        """Emit UI interaction event"""
        event = UiInteractionEvent(
            framework=framework,
            test_id=test_id,
            component_name=component_name,
            interaction_type=interaction_type,
            page_url=page_url,
            metadata=metadata
        )
        self.emit(event)
    
    def emit_step(
        self,
        framework: str,
        test_id: str,
        step_name: str,
        step_status: str,
        duration_ms: Optional[int] = None,
        **metadata
    ) -> None:
        """Emit step execution event (for BDD/keyword frameworks)"""
        event = StepEvent(
            framework=framework,
            test_id=test_id,
            step_name=step_name,
            step_status=step_status,
            duration_ms=duration_ms,
            metadata=metadata
        )
        self.emit(event)


# Global SDK instance for easy access
crossbridge = CrossBridgeHookSDK()
