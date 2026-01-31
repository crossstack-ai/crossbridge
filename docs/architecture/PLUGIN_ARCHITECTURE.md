"""
CrossBridge Plugin Architecture

A comprehensive design document explaining CrossBridge's plugin system.

KEY INSIGHT:
-----------
In CrossBridge, Execution Orchestration IS the plugin architecture.

You do NOT need a separate, parallel plugin framework.
The existing framework adapters and orchestration layers already implement
plugin patterns correctly and should be leveraged for unified extensibility.

TABLE OF CONTENTS:
-----------------
1. Philosophy & Core Principles
2. Architecture Overview
3. Plugin Types & Responsibilities
4. Design Patterns
5. Extension Points
6. Usage Examples
7. Sidecar Integration
8. Best Practices

================================================================================
1. PHILOSOPHY & CORE PRINCIPLES
================================================================================

CrossBridge follows these core principles:

1.1 Orchestrator, Not Runner
----------------------------
CrossBridge orchestrates test execution but NEVER replaces framework execution.
- Frameworks remain unchanged
- No test code modifications
- CLI-level integration only
- Frameworks are the source of truth

1.2 Plugin Architecture Already Exists
--------------------------------------
The Execution Orchestration module IS the plugin system:
- ExecutionOrchestrator = Plugin Host
- Execution Strategies = Decision Plugins
- Framework Adapters = Execution Plugins

We don't need to build a new plugin system - we formalize what exists.

1.3 Framework-Agnostic Boundaries
---------------------------------
Plugin boundaries are framework-agnostic:
- ExecutionRequest/Result = Standard protocol
- ExecutionPlan = Strategy output (WHAT to run)
- Framework commands = Adapter output (HOW to run)

1.4 Non-Invasive & Sidecar-Compatible
-------------------------------------
Plugins work in TWO modes:
- Observer Mode (Sidecar): Passive observation, no execution control
- Orchestration Mode (Active): Active test execution via CLI

Both modes are non-invasive - frameworks remain unchanged.

================================================================================
2. ARCHITECTURE OVERVIEW
================================================================================

┌─────────────────────────────────────────────────────────────────┐
│                      CROSSBRIDGE PLUGIN HOST                     │
│                    (ExecutionOrchestrator)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   Strategy   │───▶│    Plan      │───▶│   Adapter    │     │
│  │  (Decision)  │    │              │    │ (Execution)  │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│        │                    │                    │              │
│        ▼                    ▼                    ▼              │
│   ExecutionPlan     Framework-Agnostic    CLI Commands         │
│   (WHAT to run)     Boundary Layer        (HOW to run)         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │  TEST FRAMEWORKS       │
                │  (Unchanged)           │
                ├────────────────────────┤
                │ • pytest               │
                │ • TestNG               │
                │ • Robot Framework      │
                │ • Cypress              │
                │ • Playwright           │
                │ • JUnit                │
                │ • SpecFlow             │
                │ • Cucumber             │
                └────────────────────────┘

DATA FLOW:
----------
1. Request → ExecutionOrchestrator (Plugin Host)
2. Orchestrator → Strategy Plugin (select tests)
3. Strategy → ExecutionPlan (WHAT to run)
4. Orchestrator → Adapter Plugin (generate commands)
5. Adapter → Framework CLI (HOW to run)
6. Framework → Test Execution
7. Adapter → Parse Results
8. Orchestrator → ExecutionResult

================================================================================
3. PLUGIN TYPES & RESPONSIBILITIES
================================================================================

3.1 Execution Plugins (Full Implementation)
--------------------------------------------
Complete execution implementations that handle requests end-to-end.

Interface: ExecutionPlugin
Methods:
  - supports(request) → bool
  - execute(request) → ExecutionResult
  - validate(request) → List[errors]
  - get_capabilities() → Dict[metadata]

Default Implementation:
  - OrchestrationExecutionPlugin (wraps ExecutionOrchestrator)

Responsibilities:
  ✓ Accept execution requests
  ✓ Coordinate strategy and adapter
  ✓ Return standardized results
  ✓ Handle errors and validation

Example:
  plugin = OrchestrationExecutionPlugin(workspace, config)
  result = plugin.execute(execution_request)

3.2 Strategy Plugins (Decision Plugins)
---------------------------------------
Determine WHAT tests to run based on various signals.

Interface: ExecutionStrategy (acts as StrategyPluginExtension)
Methods:
  - select_tests(context) → ExecutionPlan
  - get_name() → str

Built-in Strategies:
  - SmokeStrategy: Fast signal tests only
  - ImpactedStrategy: Tests affected by code changes
  - RiskBasedStrategy: Tests ranked by historical risk
  - FullStrategy: All available tests

Responsibilities:
  ✓ Analyze execution context (git, memory, history)
  ✓ Select tests based on strategy logic
  ✓ Assign priorities and groupings
  ✓ Return ExecutionPlan with selected tests

Example:
  strategy = SmokeStrategy()
  plan = strategy.select_tests(context)

3.3 Adapter Plugins (Execution Plugins)
---------------------------------------
Determine HOW to run tests for specific frameworks.

Interface: FrameworkAdapter (acts as AdapterPluginExtension)
Methods:
  - plan_to_command(plan, workspace) → List[str]
  - parse_result(plan, workspace) → ExecutionResult
  - execute(plan, workspace) → ExecutionResult

Built-in Adapters:
  - PytestAdapter
  - TestNGAdapter
  - RobotAdapter
  - CypressAdapter
  - PlaywrightAdapter
  - JUnitAdapter
  - CucumberAdapter
  - SpecFlowAdapter
  - BehaveAdapter
  - SeleniumJavaAdapter
  - SeleniumPytestAdapter
  - SeleniumBehaveAdapter
  - RestAssuredAdapter

Responsibilities:
  ✓ Translate ExecutionPlan to framework CLI command
  ✓ Execute framework via subprocess
  ✓ Parse framework output (XML, JSON, logs)
  ✓ Normalize results to ExecutionResult format

Example:
  adapter = PytestAdapter("pytest")
  command = adapter.plan_to_command(plan, workspace)
  result = adapter.execute(plan, workspace)

================================================================================
4. DESIGN PATTERNS
================================================================================

4.1 Plugin Host Pattern
-----------------------
ExecutionOrchestrator acts as the plugin host:
- Manages plugin lifecycle
- Coordinates plugin interactions
- Enforces plugin contracts

4.2 Strategy Pattern (Decision Plugins)
---------------------------------------
Strategies implement the Strategy pattern:
- Common interface (select_tests)
- Interchangeable implementations
- Runtime selection based on request

4.3 Adapter Pattern (Execution Plugins)
---------------------------------------
Adapters implement the Adapter pattern:
- Translate internal model (ExecutionPlan) to external API (CLI)
- Framework-specific implementations
- Common result format (ExecutionResult)

4.4 Registry Pattern
-------------------
PluginRegistry provides centralized management:
- Dynamic plugin registration
- Plugin discovery
- Singleton access pattern

4.5 Decorator Pattern (Plugin Registration)
-------------------------------------------
Decorators for easy plugin registration:
  @execution_plugin('my-executor', '1.0.0')
  @strategy_plugin('my-strategy')
  @adapter_plugin('my-framework')

================================================================================
5. EXTENSION POINTS
================================================================================

5.1 Custom Execution Plugin
---------------------------
Create a complete execution implementation:

```python
from crossbridge.core.execution.orchestration import (
    ExecutionPlugin,
    ExecutionRequest,
    ExecutionResult,
    execution_plugin
)

@execution_plugin('ml-executor', '1.0.0')
class MLExecutionPlugin(ExecutionPlugin):
    def supports(self, request: ExecutionRequest) -> bool:
        return request.framework in ['pytest', 'testng']
    
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        # Custom ML-based execution logic
        pass
```

5.2 Custom Strategy Plugin
--------------------------
Create a custom test selection strategy:

```python
from crossbridge.core.execution.orchestration import (
    ExecutionStrategy,
    ExecutionContext,
    ExecutionPlan,
    strategy_plugin
)

@strategy_plugin('ml-based')
class MLStrategy(ExecutionStrategy):
    def __init__(self):
        super().__init__('ml-based')
    
    def select_tests(self, context: ExecutionContext) -> ExecutionPlan:
        # Use ML model to predict which tests will fail
        predictions = self.ml_model.predict(context)
        selected = [t for t in context.available_tests if predictions[t] > 0.8]
        return self._create_plan(context, selected, reasons={})
```

5.3 Custom Adapter Plugin
-------------------------
Create a custom framework adapter:

```python
from crossbridge.core.execution.orchestration import (
    FrameworkAdapter,
    ExecutionPlan,
    ExecutionResult,
    adapter_plugin
)

@adapter_plugin('my-framework')
class MyFrameworkAdapter(FrameworkAdapter):
    def __init__(self):
        super().__init__('my-framework')
    
    def plan_to_command(self, plan: ExecutionPlan, workspace: Path) -> List[str]:
        # Generate framework-specific CLI command
        return ['my-framework', 'run'] + plan.selected_tests
    
    def parse_result(self, plan: ExecutionPlan, workspace: Path) -> ExecutionResult:
        # Parse framework output
        return ExecutionResult(...)
```

5.4 Plugin Registration
-----------------------
Register plugins with the registry:

```python
from crossbridge.core.execution.orchestration import get_plugin_registry

# Get registry
registry = get_plugin_registry()

# Register custom plugins
registry.register_execution_plugin('ml-executor', MLExecutionPlugin)
registry.register_strategy_plugin('ml-based', MLStrategy)
registry.register_adapter_plugin('my-framework', MyFrameworkAdapter)

# Use plugins
plugin = registry.get_execution_plugin('ml-executor', workspace='/path/to/project')
result = plugin.execute(request)
```

================================================================================
6. USAGE EXAMPLES
================================================================================

6.1 Using Default Orchestration Plugin
--------------------------------------
```python
from pathlib import Path
from crossbridge.core.execution.orchestration import (
    get_execution_plugin,
    ExecutionRequest,
    StrategyType
)

# Get default plugin
plugin = get_execution_plugin(
    name='orchestration',
    workspace=Path('/path/to/project'),
    config={'database': '...'}
)

# Create request
request = ExecutionRequest(
    framework='pytest',
    strategy=StrategyType.SMOKE,
    environment='qa',
    ci_mode=True
)

# Execute
result = plugin.execute(request)
print(f"Passed: {len(result.passed_tests)}, Failed: {len(result.failed_tests)}")
```

6.2 Listing Available Plugins
-----------------------------
```python
from crossbridge.core.execution.orchestration import list_available_plugins

plugins = list_available_plugins()
print(f"Execution Plugins: {plugins['execution']}")
print(f"Strategies: {plugins['strategies']}")
print(f"Adapters: {plugins['adapters']}")
```

6.3 Getting Plugin Metadata
---------------------------
```python
from crossbridge.core.execution.orchestration import get_plugin_registry

registry = get_plugin_registry()
plugin = registry.get_execution_plugin('orchestration', workspace='/path')
capabilities = plugin.get_capabilities()

print(f"Supported Frameworks: {capabilities['supported_frameworks']}")
print(f"Supports Sidecar: {capabilities['supports_sidecar']}")
```

================================================================================
7. SIDECAR INTEGRATION
================================================================================

7.1 Sidecar Mode vs Orchestration Mode
--------------------------------------

SIDECAR MODE (Observer):
- CrossBridge runs as passive observer
- Frameworks execute independently
- CrossBridge captures results via listeners/hooks
- Non-invasive observation

ORCHESTRATION MODE (Active):
- CrossBridge initiates test execution
- Plugins select tests (strategy)
- Plugins invoke frameworks (adapter)
- Active execution control

7.2 Plugin Compatibility
------------------------
All plugins work in BOTH modes:
- Sidecar: Plugins process observed results
- Orchestration: Plugins control execution

Example: TestNGAdapter
- Sidecar Mode: Receives results from TestNG listener
- Orchestration Mode: Generates `testng` CLI command

7.3 Unified Result Format
-------------------------
Both modes produce ExecutionResult:
- Same result format
- Same observability
- Same AI analysis
- Seamless mode switching

================================================================================
8. BEST PRACTICES
================================================================================

8.1 Plugin Development
----------------------
✓ Keep plugins stateless
✓ Use framework CLI, never replace frameworks
✓ Return standard ExecutionResult format
✓ Handle errors gracefully
✓ Log detailed information
✓ Support both sidecar and orchestration modes

8.2 Strategy Development
------------------------
✓ Strategies decide WHAT, not HOW
✓ Use ExecutionContext for decisions
✓ Assign meaningful priorities
✓ Provide clear selection reasons
✓ Fall back to smoke tests if needed

8.3 Adapter Development
-----------------------
✓ Adapters decide HOW, not WHAT
✓ Generate valid CLI commands
✓ Parse all framework output formats
✓ Normalize results consistently
✓ Handle timeouts and errors
✓ Support parallel execution

8.4 Plugin Registration
-----------------------
✓ Use decorators for clean registration
✓ Provide version information
✓ Document plugin capabilities
✓ Register at module import time
✓ Test plugin compatibility

================================================================================
CONCLUSION
================================================================================

CrossBridge's plugin architecture is NOT a separate system bolted on top.
It IS the Execution Orchestration module, properly formalized.

By recognizing that:
- Orchestrator = Plugin Host
- Strategies = Decision Plugins
- Adapters = Execution Plugins

We achieve:
✓ Clean extensibility
✓ Framework-agnostic design
✓ Non-invasive execution
✓ Sidecar compatibility
✓ Third-party plugin support
✓ No code duplication

This is the correct plugin architecture for CrossBridge.

================================================================================
REFERENCES
================================================================================

Related Documentation:
- docs/EXECUTION_ORCHESTRATION.md - Orchestration details
- docs/EXECUTION_ORCHESTRATION_COMPLETE.md - Complete implementation
- docs/quick-start/SIDECAR_INTEGRATION_GUIDE.md - Sidecar setup
- core/execution/orchestration/plugin.py - Plugin interfaces
- core/execution/orchestration/plugin_registry.py - Plugin management
- core/execution/orchestration/strategies.py - Strategy plugins
- core/execution/orchestration/adapters.py - Adapter plugins

Code Examples:
- core/execution/orchestration/ - Implementation
- adapters/ - Framework adapters (execution plugins)
- tests/unit/core/execution/ - Plugin tests

================================================================================
"""
