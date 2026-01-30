"""
Pytest Plugin for CrossBridge Execution Intelligence.

This plugin hooks into pytest execution to extract step-level signals,
assertions, and detailed execution information for intelligent test analysis.
"""

import ast
import inspect
import pytest
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.execution.intelligence.models import ExecutionSignal, SignalType


class CrossBridgeIntelligencePlugin:
    """
    Pytest plugin for extracting execution intelligence signals.
    
    This plugin provides:
    - Step-level signal extraction from test execution
    - Assertion-level failure tracking
    - Variable capture and state tracking
    - Integration with CrossBridge intelligence system
    """
    
    def __init__(self):
        """Initialize the plugin."""
        self.signals: List[ExecutionSignal] = []
        self.current_test_signals: List[ExecutionSignal] = []
        self.test_start_time: Optional[float] = None
        self.enabled = True
    
    def pytest_configure(self, config):
        """Configure the plugin when pytest starts."""
        config.addinivalue_line(
            "markers",
            "crossbridge_intelligence: Enable CrossBridge intelligence extraction for this test"
        )
    
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item):
        """Hook into test execution protocol."""
        if not self.enabled:
            yield
            return
        
        # Reset signals for this test
        self.current_test_signals = []
        self.test_start_time = time.time()
        
        # Extract source code for analysis
        self._extract_test_source(item)
        
        # Run the test
        outcome = yield
        
        # Store signals
        self.signals.extend(self.current_test_signals)
    
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        """Hook into test call phase."""
        if not self.enabled:
            yield
            return
        
        # Wrap test execution to capture assertions
        outcome = yield
        
        # Check for exceptions/assertions
        if outcome.excinfo is not None:
            self._extract_failure_signals(item, outcome.excinfo)
    
    def _extract_test_source(self, item):
        """Extract and analyze test source code."""
        try:
            # Get test function
            test_func = item.obj
            
            # Get source code
            source = inspect.getsource(test_func)
            
            # Parse AST
            tree = ast.parse(source)
            
            # Extract assertions
            assertions = self._extract_assertions_from_ast(tree)
            
            for assertion in assertions:
                signal = ExecutionSignal(
                    signal_type=SignalType.ASSERTION,
                    test_id=item.nodeid,
                    framework="pytest",
                    metadata={
                        "assertion_type": assertion["type"],
                        "expression": assertion["expression"],
                        "line_number": assertion["line_number"],
                    }
                )
                self.current_test_signals.append(signal)
        
        except Exception as e:
            # Silent fail - don't break test execution
            pass
    
    def _extract_assertions_from_ast(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract assertion statements from AST."""
        assertions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                # Extract assertion expression
                expression = ast.unparse(node.test) if hasattr(ast, 'unparse') else str(node.test)
                
                # Determine assertion type
                assertion_type = "generic"
                if isinstance(node.test, ast.Compare):
                    ops = node.test.ops
                    if any(isinstance(op, ast.Eq) for op in ops):
                        assertion_type = "equality"
                    elif any(isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)) for op in ops):
                        assertion_type = "comparison"
                    elif any(isinstance(op, ast.In) for op in ops):
                        assertion_type = "membership"
                elif isinstance(node.test, ast.Call):
                    # Could be pytest helper like pytest.raises
                    assertion_type = "function_call"
                
                assertions.append({
                    "type": assertion_type,
                    "expression": expression,
                    "line_number": node.lineno,
                })
        
        return assertions
    
    def _extract_failure_signals(self, item, excinfo):
        """Extract failure signals from exception info."""
        exc_type, exc_value, exc_tb = excinfo
        
        # Determine signal type
        signal_type = SignalType.ASSERTION_FAILURE
        
        if "TimeoutError" in str(exc_type) or "timeout" in str(exc_value).lower():
            signal_type = SignalType.TIMEOUT
        elif "ConnectionError" in str(exc_type) or "connection" in str(exc_value).lower():
            signal_type = SignalType.NETWORK_ERROR
        elif "NoSuchElementException" in str(exc_type) or "element not found" in str(exc_value).lower():
            signal_type = SignalType.LOCATOR_ERROR
        
        # Extract traceback
        import traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        
        # Create failure signal
        signal = ExecutionSignal(
            signal_type=signal_type,
            test_id=item.nodeid,
            framework="pytest",
            metadata={
                "exception_type": exc_type.__name__,
                "exception_message": str(exc_value),
                "traceback": tb_lines,
                "file": item.fspath,
                "line_number": excinfo.tb.tb_lineno if excinfo.tb else 0,
            }
        )
        self.current_test_signals.append(signal)
    
    def get_signals(self) -> List[ExecutionSignal]:
        """Get all collected signals."""
        return self.signals
    
    def get_signals_for_test(self, test_id: str) -> List[ExecutionSignal]:
        """Get signals for a specific test."""
        return [s for s in self.signals if s.test_id == test_id]
    
    def reset(self):
        """Reset collected signals."""
        self.signals = []
        self.current_test_signals = []


# Plugin instance
_plugin_instance = None


def pytest_configure(config):
    """Register the plugin with pytest."""
    global _plugin_instance
    
    # Check if enabled
    if config.getoption('--no-crossbridge', default=False):
        return
    
    # Create and register plugin
    _plugin_instance = CrossBridgeIntelligencePlugin()
    config.pluginmanager.register(_plugin_instance, 'crossbridge_intelligence')


def pytest_unconfigure(config):
    """Unregister the plugin."""
    global _plugin_instance
    
    if _plugin_instance:
        config.pluginmanager.unregister(_plugin_instance)
        _plugin_instance = None


def get_plugin_instance() -> Optional[CrossBridgeIntelligencePlugin]:
    """Get the current plugin instance."""
    return _plugin_instance


# Pytest markers for fine-grained control
def pytest_addoption(parser):
    """Add command-line options."""
    parser.addoption(
        '--crossbridge-intelligence',
        action='store_true',
        default=True,
        help='Enable CrossBridge intelligence extraction (default: True)'
    )
    parser.addoption(
        '--no-crossbridge',
        action='store_true',
        default=False,
        help='Disable all CrossBridge hooks'
    )
    parser.addoption(
        '--crossbridge-output',
        type=str,
        default=None,
        help='Output file for CrossBridge intelligence signals (JSON)'
    )


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Hook called after all tests complete."""
    global _plugin_instance
    
    if _plugin_instance and session.config.getoption('--crossbridge-output'):
        # Export signals to file
        import json
        output_file = session.config.getoption('--crossbridge-output')
        
        signals_data = [
            {
                'signal_type': s.signal_type.value,
                'test_id': s.test_id,
                'framework': s.framework,
                'metadata': s.metadata,
            }
            for s in _plugin_instance.get_signals()
        ]
        
        with open(output_file, 'w') as f:
            json.dump(signals_data, f, indent=2)


# Fixtures for test-level access
@pytest.fixture
def crossbridge_signals(request):
    """
    Fixture to access CrossBridge signals for the current test.
    
    Example:
        def test_something(crossbridge_signals):
            # Test code here
            signals = crossbridge_signals.get()
            assert len(signals) > 0
    """
    class SignalAccess:
        def get(self):
            if _plugin_instance:
                return _plugin_instance.get_signals_for_test(request.node.nodeid)
            return []
    
    return SignalAccess()


@pytest.fixture
def crossbridge_intelligence():
    """
    Fixture to access the intelligence plugin directly.
    
    Example:
        def test_something(crossbridge_intelligence):
            assert crossbridge_intelligence.enabled
    """
    return _plugin_instance
