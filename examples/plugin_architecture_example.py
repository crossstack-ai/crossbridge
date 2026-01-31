"""
Example: Using CrossBridge's Plugin Architecture

This example demonstrates how to use the plugin system for test execution.
"""

from pathlib import Path
from crossbridge.core.execution.orchestration import (
    # Core plugin system
    get_execution_plugin,
    list_available_plugins,
    get_plugin_registry,
    
    # API models
    ExecutionRequest,
    StrategyType,
    
    # For custom plugins
    ExecutionStrategy,
    FrameworkAdapter,
    ExecutionPlugin,
    strategy_plugin,
    adapter_plugin,
)


# ============================================================================
# EXAMPLE 1: Using the Default Orchestration Plugin
# ============================================================================

def example_basic_usage():
    """Example: Execute tests using the default orchestration plugin."""
    
    # Get default orchestration plugin
    plugin = get_execution_plugin(
        name='orchestration',  # or 'default'
        workspace=Path('/path/to/your/project'),
        config={
            'database': {
                'host': 'localhost',
                'port': 5432,
            }
        }
    )
    
    # Create execution request
    request = ExecutionRequest(
        framework='pytest',
        strategy=StrategyType.SMOKE,
        environment='qa',
        ci_mode=True,
        parallel=True,
    )
    
    # Execute tests
    result = plugin.execute(request)
    
    # Analyze results
    print(f"Execution Status: {result.status.value}")
    print(f"Tests Passed: {len(result.passed_tests)}")
    print(f"Tests Failed: {len(result.failed_tests)}")
    print(f"Execution Time: {result.execution_time_seconds:.1f}s")
    
    return result


# ============================================================================
# EXAMPLE 2: Listing Available Plugins
# ============================================================================

def example_list_plugins():
    """Example: List all available plugins."""
    
    plugins = list_available_plugins()
    
    print("=== Available Plugins ===\n")
    print(f"Execution Plugins: {', '.join(plugins['execution'])}")
    print(f"Strategies: {', '.join(plugins['strategies'])}")
    print(f"Adapters: {', '.join(plugins['adapters'])}")


# ============================================================================
# EXAMPLE 3: Getting Plugin Metadata
# ============================================================================

def example_plugin_metadata():
    """Example: Get plugin capabilities and metadata."""
    
    plugin = get_execution_plugin('orchestration', workspace=Path('/path'))
    capabilities = plugin.get_capabilities()
    
    print("=== Plugin Capabilities ===\n")
    print(f"Name: {capabilities['name']}")
    print(f"Version: {capabilities['version']}")
    print(f"Supported Frameworks: {', '.join(capabilities['supported_frameworks'][:5])}...")
    print(f"Supported Strategies: {', '.join(capabilities['supported_strategies'])}")
    print(f"Supports Parallel: {capabilities['supports_parallel']}")
    print(f"Supports Sidecar: {capabilities['supports_sidecar']}")


# ============================================================================
# EXAMPLE 4: Custom Strategy Plugin
# ============================================================================

@strategy_plugin('custom-ml-based')
class MLBasedStrategy(ExecutionStrategy):
    """
    Custom strategy that uses ML to predict which tests will fail.
    
    This is a DECISION PLUGIN - it determines WHAT tests to run.
    """
    
    def __init__(self):
        super().__init__('custom-ml-based')
        # Initialize your ML model here
        self.ml_model = self._load_ml_model()
    
    def select_tests(self, context):
        """
        Select tests based on ML predictions.
        
        Args:
            context: ExecutionContext with available tests and metadata
            
        Returns:
            ExecutionPlan with selected tests
        """
        # Use ML model to predict failure probability
        predictions = {}
        for test_id in context.available_tests:
            # Extract features from context
            features = self._extract_features(test_id, context)
            # Predict failure probability
            predictions[test_id] = self.ml_model.predict_failure_probability(features)
        
        # Select tests with high failure probability
        threshold = 0.7
        selected = [
            test_id for test_id, prob in predictions.items()
            if prob > threshold
        ]
        
        # Create reasons for selection
        reasons = {
            test_id: f"ML predicted failure probability: {predictions[test_id]:.2f}"
            for test_id in selected
        }
        
        # Return execution plan
        return self._create_plan(context, selected, reasons)
    
    def _load_ml_model(self):
        """Load your ML model."""
        # Implement your ML model loading logic
        pass
    
    def _extract_features(self, test_id, context):
        """Extract features for ML prediction."""
        # Implement feature extraction
        pass


# ============================================================================
# EXAMPLE 5: Custom Adapter Plugin
# ============================================================================

@adapter_plugin('my-custom-framework')
class CustomFrameworkAdapter(FrameworkAdapter):
    """
    Custom adapter for a hypothetical test framework.
    
    This is an EXECUTION PLUGIN - it determines HOW to run tests.
    """
    
    def __init__(self):
        super().__init__('my-custom-framework')
    
    def plan_to_command(self, plan, workspace):
        """
        Convert execution plan to framework CLI command.
        
        Args:
            plan: ExecutionPlan with selected tests
            workspace: Path to project workspace
            
        Returns:
            List of command parts for subprocess
        """
        # Build command
        command = ['my-framework', 'run']
        
        # Add selected tests
        command.extend(plan.selected_tests)
        
        # Add parallel flag if needed
        if plan.parallel:
            command.append('--parallel')
        
        # Add environment
        command.extend(['--env', plan.environment])
        
        return command
    
    def parse_result(self, plan, workspace):
        """
        Parse framework output into ExecutionResult.
        
        Args:
            plan: Original execution plan
            workspace: Path to project workspace
            
        Returns:
            ExecutionResult with standardized data
        """
        from crossbridge.core.execution.orchestration.api import ExecutionResult, ExecutionStatus
        from datetime import datetime
        import json
        
        # Read framework output (e.g., JSON report)
        output_file = workspace / 'test-results.json'
        with open(output_file) as f:
            results = json.load(f)
        
        # Parse results
        passed = [t['id'] for t in results['tests'] if t['status'] == 'passed']
        failed = [t['id'] for t in results['tests'] if t['status'] == 'failed']
        skipped = [t['id'] for t in results['tests'] if t['status'] == 'skipped']
        
        # Create execution result
        return ExecutionResult(
            framework=plan.framework,
            strategy=plan.strategy,
            environment=plan.environment,
            status=ExecutionStatus.COMPLETED if not failed else ExecutionStatus.FAILED,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            execution_time_seconds=results['duration'],
            start_time=datetime.fromisoformat(results['start_time']),
            end_time=datetime.fromisoformat(results['end_time']),
        )


# ============================================================================
# EXAMPLE 6: Registering and Using Custom Plugins
# ============================================================================

def example_custom_plugins():
    """Example: Register and use custom plugins."""
    
    # Get plugin registry
    registry = get_plugin_registry()
    
    # Register custom strategy
    registry.register_strategy_plugin('ml-based', MLBasedStrategy)
    
    # Register custom adapter
    registry.register_adapter_plugin('my-framework', CustomFrameworkAdapter)
    
    # List updated plugins
    print(f"Strategies: {registry.list_strategy_plugins()}")
    print(f"Adapters: {registry.list_adapter_plugins()}")
    
    # Use custom strategy (via orchestration plugin)
    plugin = get_execution_plugin('orchestration', workspace=Path('/path'))
    
    request = ExecutionRequest(
        framework='my-framework',
        strategy='ml-based',  # Custom strategy
        environment='qa',
    )
    
    result = plugin.execute(request)
    return result


# ============================================================================
# EXAMPLE 7: Different Execution Strategies
# ============================================================================

def example_execution_strategies():
    """Example: Use different execution strategies."""
    
    plugin = get_execution_plugin('orchestration', workspace=Path('/path'))
    
    # Smoke tests (fast signal)
    smoke_result = plugin.execute(ExecutionRequest(
        framework='pytest',
        strategy=StrategyType.SMOKE,
        environment='dev',
    ))
    
    # Impacted tests (based on code changes)
    impacted_result = plugin.execute(ExecutionRequest(
        framework='pytest',
        strategy=StrategyType.IMPACTED,
        environment='dev',
        base_branch='main',
        changed_files=['src/module1.py', 'src/module2.py'],
    ))
    
    # Risk-based tests (historical failures)
    risk_result = plugin.execute(ExecutionRequest(
        framework='pytest',
        strategy=StrategyType.RISK_BASED,
        environment='qa',
    ))
    
    # Full suite
    full_result = plugin.execute(ExecutionRequest(
        framework='pytest',
        strategy=StrategyType.FULL,
        environment='staging',
    ))
    
    return {
        'smoke': smoke_result,
        'impacted': impacted_result,
        'risk': risk_result,
        'full': full_result,
    }


# ============================================================================
# EXAMPLE 8: Dry Run (Planning Only)
# ============================================================================

def example_dry_run():
    """Example: Plan execution without actually running tests."""
    
    plugin = get_execution_plugin('orchestration', workspace=Path('/path'))
    
    request = ExecutionRequest(
        framework='pytest',
        strategy=StrategyType.IMPACTED,
        environment='dev',
        dry_run=True,  # Planning only, no execution
    )
    
    result = plugin.execute(request)
    
    print("=== Dry Run Results ===")
    print(f"Would execute {len(result.passed_tests)} tests")  # In dry run, these are "selected" tests
    print(f"Estimated duration: {result.execution_time_seconds}s")
    
    return result


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    print("CrossBridge Plugin Architecture Examples\n")
    
    # Run examples
    print("\n1. Basic Usage")
    # example_basic_usage()
    
    print("\n2. List Plugins")
    # example_list_plugins()
    
    print("\n3. Plugin Metadata")
    # example_plugin_metadata()
    
    print("\n4. Execution Strategies")
    # example_execution_strategies()
    
    print("\n5. Dry Run")
    # example_dry_run()
    
    print("\n6. Custom Plugins")
    # example_custom_plugins()
    
    print("\nNote: Uncomment the examples you want to run!")
