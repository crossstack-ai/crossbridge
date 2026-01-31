"""
Comprehensive Unit Tests for Plugin System

Tests the ExecutionPlugin architecture including:
- ExecutionPlugin interface and OrchestrationExecutionPlugin
- PluginRegistry management
- Strategy plugins
- Adapter plugins
- Plugin decorators
- Framework compatibility
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import plugin system
from core.execution.orchestration.plugin import (
    ExecutionPlugin,
    OrchestrationExecutionPlugin,
    StrategyPluginExtension,
    AdapterPluginExtension,
    strategy_plugin,
    adapter_plugin,
    execution_plugin,
)
from core.execution.orchestration.plugin_registry import (
    PluginRegistry,
    get_plugin_registry,
    reset_plugin_registry,
    get_execution_plugin,
    list_available_plugins,
)
from core.execution.orchestration.api import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionPlan,
    ExecutionStatus,
    StrategyType,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def workspace():
    """Test workspace path."""
    return Path("/test/workspace")


@pytest.fixture
def config():
    """Test configuration."""
    return {
        "database": "postgresql://test:test@localhost:5432/test",
        "ai_provider": "mock",
    }


@pytest.fixture
def execution_request():
    """Sample execution request."""
    return ExecutionRequest(
        framework="pytest",
        strategy=StrategyType.SMOKE,
        environment="qa",
        ci_mode=True,
        dry_run=False,
    )


@pytest.fixture
def execution_result():
    """Sample execution result."""
    return ExecutionResult(
        executed_tests=["test_1", "test_2"],
        passed_tests=["test_1", "test_2"],
        failed_tests=[],
        skipped_tests=["test_3"],
        error_tests=[],
        execution_time_seconds=10.5,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        report_paths=[],
        log_paths=[],
        framework="pytest",
        environment="qa",
        status=ExecutionStatus.COMPLETED,
    )


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset plugin registry before each test."""
    reset_plugin_registry()
    yield
    reset_plugin_registry()


# ============================================================================
# ExecutionPlugin Tests
# ============================================================================

class TestExecutionPlugin:
    """Test ExecutionPlugin base interface."""
    
    def test_plugin_initialization(self):
        """Test plugin initialization."""
        class TestPlugin(ExecutionPlugin):
            def supports(self, request):
                return True
            
            def execute(self, request):
                return Mock()
        
        plugin = TestPlugin("test-plugin", "1.0.0")
        assert plugin.name == "test-plugin"
        assert plugin.version == "1.0.0"
        assert plugin.enabled is True
    
    def test_plugin_validate_valid_request(self, execution_request):
        """Test validation with valid request."""
        class TestPlugin(ExecutionPlugin):
            def supports(self, request):
                return True
            
            def execute(self, request):
                return Mock()
        
        plugin = TestPlugin("test")
        errors = plugin.validate(execution_request)
        assert len(errors) == 0
    
    def test_plugin_validate_invalid_request(self):
        """Test validation with invalid request."""
        class TestPlugin(ExecutionPlugin):
            def supports(self, request):
                return True
            
            def execute(self, request):
                return Mock()
        
        plugin = TestPlugin("test")
        
        # Missing framework
        request = ExecutionRequest(
            framework="",
            strategy=StrategyType.SMOKE,
            environment="qa"
        )
        errors = plugin.validate(request)
        assert "Framework is required" in errors
    
    def test_plugin_get_capabilities(self):
        """Test getting plugin capabilities."""
        class TestPlugin(ExecutionPlugin):
            def supports(self, request):
                return True
            
            def execute(self, request):
                return Mock()
        
        plugin = TestPlugin("test", "1.0.0")
        caps = plugin.get_capabilities()
        
        assert caps["name"] == "test"
        assert caps["version"] == "1.0.0"
        assert caps["enabled"] is True
        assert "supported_frameworks" in caps


class TestOrchestrationExecutionPlugin:
    """Test OrchestrationExecutionPlugin implementation."""
    
    def test_plugin_initialization(self, workspace, config):
        """Test orchestration plugin initialization."""
        plugin = OrchestrationExecutionPlugin(workspace, config)
        
        assert plugin.name == "orchestration"
        assert plugin.version == "0.2.0"
        assert plugin.workspace == workspace
        assert plugin.config == config
    
    def test_plugin_supports_valid_framework(self, workspace, execution_request):
        """Test supports() with valid framework."""
        plugin = OrchestrationExecutionPlugin(workspace)
        assert plugin.supports(execution_request) is True
    
    def test_plugin_supports_invalid_framework(self, workspace):
        """Test supports() with invalid framework."""
        plugin = OrchestrationExecutionPlugin(workspace)
        request = ExecutionRequest(
            framework="invalid-framework",
            strategy=StrategyType.SMOKE,
            environment="qa"
        )
        assert plugin.supports(request) is False
    
    def test_plugin_get_capabilities(self, workspace):
        """Test getting orchestration plugin capabilities."""
        plugin = OrchestrationExecutionPlugin(workspace)
        caps = plugin.get_capabilities()
        
        assert caps["name"] == "orchestration"
        assert caps["supports_parallel"] is True
        assert caps["supports_sidecar"] is True
        assert "pytest" in caps["supported_frameworks"]
        assert "testng" in caps["supported_frameworks"]
        assert "robot" in caps["supported_frameworks"]
    
    @patch('core.execution.orchestration.orchestrator.ExecutionOrchestrator')
    def test_plugin_execute_success(self, mock_orchestrator_class, workspace, execution_request, execution_result):
        """Test successful execution."""
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.execute.return_value = execution_result
        mock_orchestrator_class.return_value = mock_orchestrator
        
        plugin = OrchestrationExecutionPlugin(workspace)
        result = plugin.execute(execution_request)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert len(result.passed_tests) == 2
    
    def test_plugin_execute_validation_error(self, workspace):
        """Test execution with validation errors."""
        plugin = OrchestrationExecutionPlugin(workspace)
        
        # Invalid request
        request = ExecutionRequest(
            framework="",
            strategy=StrategyType.SMOKE,
            environment=""
        )
        
        result = plugin.execute(request)
        assert result.status == ExecutionStatus.FAILED
        assert "Framework is required" in result.error_message


# ============================================================================
# PluginRegistry Tests
# ============================================================================

class TestPluginRegistry:
    """Test PluginRegistry management."""
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = PluginRegistry()
        
        # Should have default orchestration plugin
        assert 'orchestration' in registry.list_execution_plugins()
        assert 'default' in registry.list_execution_plugins()
        
        # Should have built-in strategies
        strategies = registry.list_strategy_plugins()
        assert 'smoke' in strategies
        assert 'impacted' in strategies
        assert 'risk' in strategies
        assert 'full' in strategies
    
    def test_registry_all_frameworks_registered(self):
        """Test all 13 frameworks are registered."""
        registry = PluginRegistry()
        adapters = registry.list_adapter_plugins()
        
        # Verify all frameworks
        expected_frameworks = [
            'pytest', 'testng', 'junit', 'robot', 'cypress',
            'playwright', 'cucumber', 'behave', 'specflow',
            'nunit', 'restassured', 'rest-assured'
        ]
        
        for framework in expected_frameworks:
            assert framework in adapters, f"Framework {framework} not registered"
    
    def test_register_custom_execution_plugin(self):
        """Test registering custom execution plugin."""
        registry = PluginRegistry()
        
        class CustomPlugin(ExecutionPlugin):
            def supports(self, request):
                return True
            
            def execute(self, request):
                return Mock()
        
        registry.register_execution_plugin('custom', CustomPlugin)
        assert 'custom' in registry.list_execution_plugins()
    
    def test_get_execution_plugin(self, workspace):
        """Test getting execution plugin."""
        registry = PluginRegistry()
        plugin = registry.get_execution_plugin('orchestration', workspace)
        
        assert isinstance(plugin, OrchestrationExecutionPlugin)
        assert plugin.workspace == workspace
    
    def test_get_nonexistent_plugin(self):
        """Test getting nonexistent plugin raises error."""
        registry = PluginRegistry()
        
        with pytest.raises(ValueError, match="Unknown execution plugin"):
            registry.get_execution_plugin('nonexistent')
    
    def test_register_invalid_plugin_type(self):
        """Test registering invalid plugin type raises error."""
        registry = PluginRegistry()
        
        class InvalidPlugin:
            pass
        
        with pytest.raises(ValueError, match="must inherit from ExecutionPlugin"):
            registry.register_execution_plugin('invalid', InvalidPlugin)
    
    def test_get_plugin_info(self):
        """Test getting plugin metadata."""
        registry = PluginRegistry()
        info = registry.get_plugin_info('orchestration', 'execution')
        
        assert info['name'] == 'orchestration'
        assert info['type'] == 'execution'
        assert 'class' in info
    
    def test_get_all_plugins_info(self):
        """Test getting all plugins metadata."""
        registry = PluginRegistry()
        all_info = registry.get_all_plugins_info()
        
        assert 'execution_plugins' in all_info
        assert 'strategies' in all_info
        assert 'adapters' in all_info
        
        assert len(all_info['execution_plugins']) >= 1
        assert len(all_info['strategies']) >= 4
        assert len(all_info['adapters']) >= 11


class TestPluginRegistrySingleton:
    """Test plugin registry singleton behavior."""
    
    def test_get_plugin_registry_singleton(self):
        """Test get_plugin_registry returns singleton."""
        registry1 = get_plugin_registry()
        registry2 = get_plugin_registry()
        
        assert registry1 is registry2
    
    def test_reset_plugin_registry(self):
        """Test resetting plugin registry."""
        registry1 = get_plugin_registry()
        reset_plugin_registry()
        registry2 = get_plugin_registry()
        
        assert registry1 is not registry2


class TestPluginRegistryConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_execution_plugin_convenience(self, workspace):
        """Test get_execution_plugin convenience function."""
        plugin = get_execution_plugin('orchestration', workspace)
        assert isinstance(plugin, OrchestrationExecutionPlugin)
    
    def test_list_available_plugins(self):
        """Test list_available_plugins convenience function."""
        plugins = list_available_plugins()
        
        assert 'execution' in plugins
        assert 'strategies' in plugins
        assert 'adapters' in plugins
        
        assert 'orchestration' in plugins['execution']
        assert 'smoke' in plugins['strategies']
        assert 'pytest' in plugins['adapters']


# ============================================================================
# Plugin Decorator Tests
# ============================================================================

class TestPluginDecorators:
    """Test plugin decorators."""
    
    def test_execution_plugin_decorator(self):
        """Test @execution_plugin decorator."""
        @execution_plugin('my-executor', '2.0.0')
        class MyExecutor(ExecutionPlugin):
            def supports(self, request):
                return True
            
            def execute(self, request):
                return Mock()
        
        assert MyExecutor._plugin_name == 'my-executor'
        assert MyExecutor._plugin_version == '2.0.0'
    
    def test_strategy_plugin_decorator(self):
        """Test @strategy_plugin decorator."""
        @strategy_plugin('my-strategy')
        class MyStrategy:
            pass
        
        assert MyStrategy._plugin_name == 'my-strategy'
    
    def test_adapter_plugin_decorator(self):
        """Test @adapter_plugin decorator."""
        @adapter_plugin('my-framework')
        class MyAdapter:
            pass
        
        assert MyAdapter._plugin_framework == 'my-framework'


# ============================================================================
# Integration Tests
# ============================================================================

class TestPluginSystemIntegration:
    """Integration tests for complete plugin system."""
    
    @patch('core.execution.orchestration.orchestrator.ExecutionOrchestrator')
    def test_end_to_end_plugin_execution(self, mock_orchestrator_class, workspace, execution_request, execution_result):
        """Test end-to-end plugin execution flow."""
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.execute.return_value = execution_result
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Get plugin from registry
        plugin = get_execution_plugin('orchestration', workspace)
        
        # Execute request
        result = plugin.execute(execution_request)
        
        # Verify result
        assert result.status == ExecutionStatus.COMPLETED
        assert len(result.passed_tests) == 2
        assert result.framework == "pytest"
    
    def test_multiple_frameworks_compatibility(self, workspace):
        """Test plugin system works with all frameworks."""
        registry = get_plugin_registry()
        plugin = registry.get_execution_plugin('orchestration', workspace)
        
        frameworks = [
            'pytest', 'testng', 'junit', 'robot', 'cypress',
            'playwright', 'cucumber', 'behave', 'specflow',
            'nunit', 'restassured'
        ]
        
        for framework in frameworks:
            request = ExecutionRequest(
                framework=framework,
                strategy=StrategyType.SMOKE,
                environment="qa"
            )
            assert plugin.supports(request), f"Plugin should support {framework}"


# ============================================================================
# Framework Compatibility Tests
# ============================================================================

class TestFrameworkCompatibility:
    """Test plugin system compatibility with all frameworks."""
    
    @pytest.mark.parametrize("framework", [
        "pytest", "testng", "junit", "robot", "cypress",
        "playwright", "cucumber", "behave", "specflow",
        "nunit", "restassured", "rest-assured",
        "selenium-pytest", "selenium-behave"
    ])
    def test_framework_registered(self, framework):
        """Test each framework is registered in plugin registry."""
        registry = get_plugin_registry()
        adapters = registry.list_adapter_plugins()
        assert framework in adapters, f"{framework} should be registered"
    
    @pytest.mark.parametrize("framework", [
        "pytest", "testng", "junit", "robot", "cypress",
        "playwright", "cucumber", "behave", "specflow",
        "nunit", "restassured"
    ])
    def test_orchestration_plugin_supports_framework(self, framework, workspace):
        """Test orchestration plugin supports each framework."""
        plugin = OrchestrationExecutionPlugin(workspace)
        request = ExecutionRequest(
            framework=framework,
            strategy=StrategyType.SMOKE,
            environment="qa"
        )
        assert plugin.supports(request), f"Plugin should support {framework}"


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestPluginErrorHandling:
    """Test plugin system error handling."""
    
    def test_plugin_handles_missing_framework(self, workspace):
        """Test plugin handles missing framework gracefully."""
        plugin = OrchestrationExecutionPlugin(workspace)
        request = ExecutionRequest(
            framework="",
            strategy=StrategyType.SMOKE,
            environment="qa"
        )
        
        result = plugin.execute(request)
        assert result.status == ExecutionStatus.FAILED
        assert "Framework is required" in result.error_message
    
    @patch('core.execution.orchestration.orchestrator.ExecutionOrchestrator')
    def test_plugin_handles_execution_exception(self, mock_orchestrator_class, workspace, execution_request):
        """Test plugin handles execution exceptions."""
        # Mock orchestrator to raise exception
        mock_orchestrator = Mock()
        mock_orchestrator.execute.side_effect = Exception("Test error")
        mock_orchestrator_class.return_value = mock_orchestrator
        
        plugin = OrchestrationExecutionPlugin(workspace)
        result = plugin.execute(execution_request)
        
        assert result.status == ExecutionStatus.FAILED
        assert "Test error" in result.error_message


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
