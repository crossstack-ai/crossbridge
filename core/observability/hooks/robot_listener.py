"""
CrossBridge Robot Framework Listener

Optional listener that emits execution events to CrossBridge observer.

Installation:
    Run robot with listener:
    ```bash
    robot --listener crossbridge.hooks.robot_listener.CrossBridgeListener tests/
    ```
    
    Or in robot.toml / robot.yaml:
    ```toml
    [robot]
    listeners = ["crossbridge.hooks.robot_listener.CrossBridgeListener"]
    ```

The listener is completely optional and non-blocking.
Tests run normally even if CrossBridge observer is unavailable.
"""

import logging
from datetime import datetime
from typing import Optional

try:
    from core.observability.hook_sdk import CrossBridgeHookSDK
    from core.observability.events import EventType
    CROSSBRIDGE_AVAILABLE = True
except ImportError:
    CROSSBRIDGE_AVAILABLE = False

logger = logging.getLogger(__name__)


class CrossBridgeListener:
    """
    Robot Framework listener for CrossBridge event emission.
    
    This listener hooks into Robot Framework's execution lifecycle
    and emits standardized events that CrossBridge can observe.
    """
    
    ROBOT_LISTENER_API_VERSION = 3
    
    def __init__(self):
        self.sdk: Optional[CrossBridgeHookSDK] = None
        self.enabled = False
        
        if CROSSBRIDGE_AVAILABLE:
            try:
                self.sdk = CrossBridgeHookSDK()
                self.enabled = True
                logger.info("CrossBridge Robot Framework listener enabled")
            except Exception as e:
                logger.warning(f"CrossBridge listener initialization failed: {e}")
    
    def start_test(self, data, result):
        """Called when a test starts"""
        if not self.enabled or not self.sdk:
            return
        
        try:
            self.sdk.emit_test_start(
                framework="robot",
                test_id=self._get_test_id(data),
                metadata={
                    'name': data.name,
                    'doc': data.doc,
                    'tags': list(data.tags) if hasattr(data, 'tags') else [],
                    'template': data.template if hasattr(data, 'template') else None,
                    'source': str(data.source) if hasattr(data, 'source') else None
                }
            )
        except Exception as e:
            logger.debug(f"Failed to emit start_test: {e}")
    
    def end_test(self, data, result):
        """Called when a test ends"""
        if not self.enabled or not self.sdk:
            return
        
        try:
            self.sdk.emit_test_end(
                framework="robot",
                test_id=self._get_test_id(data),
                status=result.status.lower(),  # PASS/FAIL -> passed/failed
                duration_ms=result.elapsedtime,  # Already in milliseconds
                error_message=result.message if result.status == 'FAIL' else None,
                metadata={
                    'critical': getattr(result, 'critical', None),
                    'tags': list(result.tags) if hasattr(result, 'tags') else []
                }
            )
        except Exception as e:
            logger.debug(f"Failed to emit end_test: {e}")
    
    def start_keyword(self, data, result):
        """Called when a keyword starts"""
        if not self.enabled or not self.sdk:
            return
        
        try:
            # Emit step event for keyword execution
            self.sdk.emit_step(
                framework="robot",
                test_id=self._get_current_test_id(data),
                step_name=data.name,
                step_type=data.type,  # KEYWORD, SETUP, TEARDOWN, etc.
                metadata={
                    'args': list(data.args) if hasattr(data, 'args') else [],
                    'assign': list(data.assign) if hasattr(data, 'assign') else [],
                    'library': getattr(data, 'libname', None)
                }
            )
        except Exception as e:
            logger.debug(f"Failed to emit start_keyword: {e}")
    
    def log_message(self, message):
        """Called when a log message is written"""
        # Only capture ERROR and FAIL messages for anomaly detection
        if not self.enabled or not self.sdk:
            return
        
        if message.level in ('ERROR', 'FAIL'):
            try:
                self.sdk.emit_custom_event(
                    framework="robot",
                    test_id=self._get_current_test_id_from_message(message),
                    event_type=EventType.ERROR.value,
                    metadata={
                        'level': message.level,
                        'message': message.message[:500],  # Limit size
                        'timestamp': message.timestamp
                    }
                )
            except Exception as e:
                logger.debug(f"Failed to emit log_message: {e}")
    
    def _get_test_id(self, data) -> str:
        """Generate unique test ID"""
        if hasattr(data, 'longname'):
            return data.longname
        return data.name
    
    def _get_current_test_id(self, data) -> str:
        """Get test ID for keyword/step context"""
        # Try to get from parent test
        if hasattr(data, 'parent') and hasattr(data.parent, 'longname'):
            return data.parent.longname
        return "unknown_test"
    
    def _get_current_test_id_from_message(self, message) -> str:
        """Extract test ID from log message context"""
        # Robot Framework doesn't always provide test context in messages
        return "unknown_test"


# Convenience function for programmatic listener registration
def register_listener():
    """
    Register CrossBridge listener programmatically.
    
    Can be called in __init__.py or test setup:
        from crossbridge.hooks.robot_listener import register_listener
        register_listener()
    """
    if not CROSSBRIDGE_AVAILABLE:
        logger.warning("CrossBridge not available - listener not registered")
        return False
    
    try:
        listener = CrossBridgeListener()
        logger.info("CrossBridge Robot listener registered")
        return True
    except Exception as e:
        logger.error(f"Failed to register CrossBridge listener: {e}")
        return False
