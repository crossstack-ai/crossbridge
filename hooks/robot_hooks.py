"""
CrossBridge Robot Framework Listener

Lightweight Robot Framework listener that emits execution events to CrossBridge.

Installation:
    Add to robot command:
    
    robot --listener crossbridge.hooks.robot_hooks.CrossBridgeListener tests/

Or in robot file:
    
    *** Settings ***
    Library    crossbridge.hooks.robot_hooks.CrossBridgeListener

The listener is optional and can be disabled via:
    - Environment: CROSSBRIDGE_HOOKS_ENABLED=false
    - Config: crossbridge.yaml
"""

from robot.api import logger as robot_logger
from robot.libraries.BuiltIn import BuiltIn

from core.observability import crossbridge


class CrossBridgeListener:
    """
    Robot Framework listener for CrossBridge observability.
    
    This listener hooks into Robot Framework's execution lifecycle
    and emits events to CrossBridge for continuous intelligence.
    """
    
    ROBOT_LISTENER_API_VERSION = 3
    
    def __init__(self):
        """Initialize CrossBridge listener"""
        self.current_test_id = None
        self.test_start_time = None
    
    def start_test(self, data, result):
        """
        Called when test execution starts.
        
        Args:
            data: Test data object
            result: Test result object
        """
        if not crossbridge.enabled:
            return
        
        try:
            self.current_test_id = data.name
            
            crossbridge.emit_test_start(
                framework="robot",
                test_id=data.name,
                longname=data.longname,
                tags=list(data.tags) if data.tags else [],
                source=str(data.source) if data.source else None
            )
            
        except Exception as e:
            robot_logger.warn(f"CrossBridge hook error: {e}")
    
    def end_test(self, data, result):
        """
        Called when test execution ends.
        
        Args:
            data: Test data object
            result: Test result object
        """
        if not crossbridge.enabled:
            return
        
        try:
            # Map Robot status to standard status
            status_map = {
                'PASS': 'passed',
                'FAIL': 'failed',
                'SKIP': 'skipped'
            }
            status = status_map.get(result.status, 'error')
            
            crossbridge.emit_test_end(
                framework="robot",
                test_id=data.name,
                status=status,
                duration_ms=result.elapsedtime,
                error_message=result.message if result.status == 'FAIL' else None,
                longname=data.longname,
                tags=list(data.tags) if data.tags else []
            )
            
        except Exception as e:
            robot_logger.warn(f"CrossBridge hook error: {e}")
    
    def start_keyword(self, data, result):
        """
        Called when keyword execution starts.
        
        Args:
            data: Keyword data object
            result: Keyword result object
        """
        if not crossbridge.enabled:
            return
        
        try:
            # Track step execution for BDD-style tests
            if self.current_test_id:
                crossbridge.emit_step(
                    framework="robot",
                    test_id=self.current_test_id,
                    step_name=data.name,
                    step_status="running",
                    keyword_type=data.type,
                    library=data.libname if hasattr(data, 'libname') else None
                )
                
        except Exception as e:
            robot_logger.warn(f"CrossBridge hook error: {e}")
    
    def end_keyword(self, data, result):
        """
        Called when keyword execution ends.
        
        Args:
            data: Keyword data object
            result: Keyword result object
        """
        if not crossbridge.enabled:
            return
        
        try:
            if self.current_test_id:
                status_map = {
                    'PASS': 'passed',
                    'FAIL': 'failed',
                    'SKIP': 'skipped'
                }
                step_status = status_map.get(result.status, 'error')
                
                crossbridge.emit_step(
                    framework="robot",
                    test_id=self.current_test_id,
                    step_name=data.name,
                    step_status=step_status,
                    duration_ms=result.elapsedtime,
                    error_message=result.message if result.status == 'FAIL' else None
                )
                
        except Exception as e:
            robot_logger.warn(f"CrossBridge hook error: {e}")


# Helper keywords for manual instrumentation in Robot tests

def track_api_call(endpoint, method, status_code, duration_ms=None):
    """
    Robot Framework keyword for tracking API calls.
    
    Usage in .robot file:
        *** Test Cases ***
        Test API Endpoint
            ${response}=    GET    /api/users
            Track API Call    /api/users    GET    ${response.status_code}    ${response.elapsed.total_seconds() * 1000}
    """
    if not crossbridge.enabled:
        return
    
    try:
        # Get current test name
        builtin = BuiltIn()
        test_id = builtin.get_variable_value('${TEST NAME}')
        
        crossbridge.emit_api_call(
            framework="robot",
            test_id=test_id,
            endpoint=endpoint,
            method=method,
            status_code=int(status_code),
            duration_ms=int(duration_ms) if duration_ms else None
        )
        
    except Exception as e:
        robot_logger.warn(f"CrossBridge API tracking error: {e}")


def track_ui_interaction(component_name, interaction_type, page_url):
    """
    Robot Framework keyword for tracking UI interactions.
    
    Usage in .robot file:
        *** Test Cases ***
        Test Login
            Click Button    login-button
            Track UI Interaction    login-button    click    ${CURRENT_URL}
    """
    if not crossbridge.enabled:
        return
    
    try:
        builtin = BuiltIn()
        test_id = builtin.get_variable_value('${TEST NAME}')
        
        crossbridge.emit_ui_interaction(
            framework="robot",
            test_id=test_id,
            component_name=component_name,
            interaction_type=interaction_type,
            page_url=page_url
        )
        
    except Exception as e:
        robot_logger.warn(f"CrossBridge UI tracking error: {e}")
