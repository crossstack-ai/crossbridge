"""
Plugin Architecture Quick Reference

A concise guide to CrossBridge's plugin system for developers.

QUICK START:
-----------
1. Use the default orchestration plugin:
   from crossbridge.core.execution.orchestration import get_execution_plugin
   plugin = get_execution_plugin('orchestration', workspace='/path')
   result = plugin.execute(request)

2. List available plugins:
   from crossbridge.core.execution.orchestration import list_available_plugins
   plugins = list_available_plugins()

3. Create custom strategy:
   from crossbridge.core.execution.orchestration import ExecutionStrategy, strategy_plugin
   
   @strategy_plugin('my-strategy')
   class MyStrategy(ExecutionStrategy):
       def select_tests(self, context):
           # Your logic here
           pass

4. Create custom adapter:
   from crossbridge.core.execution.orchestration import FrameworkAdapter, adapter_plugin
   
   @adapter_plugin('my-framework')
   class MyAdapter(FrameworkAdapter):
       def plan_to_command(self, plan, workspace):
           return ['my-framework', 'run'] + plan.selected_tests
       
       def parse_result(self, plan, workspace):
           # Parse framework output
           pass

PLUGIN TYPES:
------------
1. Execution Plugins - Full execution implementations
   Interface: ExecutionPlugin
   Default: OrchestrationExecutionPlugin

2. Strategy Plugins - Test selection (WHAT to run)
   Interface: ExecutionStrategy
   Built-in: SmokeStrategy, ImpactedStrategy, RiskBasedStrategy, FullStrategy

3. Adapter Plugins - Framework invocation (HOW to run)
   Interface: FrameworkAdapter
   Built-in: 12+ adapters (pytest, TestNG, Robot, Cypress, etc.)

KEY INSIGHT:
-----------
Execution Orchestration IS the plugin architecture.
- Orchestrator = Plugin Host
- Strategies = Decision Plugins
- Adapters = Execution Plugins

DOCUMENTATION:
-------------
- Complete guide: docs/architecture/PLUGIN_ARCHITECTURE.md
- Execution orchestration: docs/EXECUTION_ORCHESTRATION.md
- Sidecar integration: docs/quick-start/SIDECAR_INTEGRATION_GUIDE.md

CODE LOCATIONS:
--------------
- Plugin interfaces: core/execution/orchestration/plugin.py
- Plugin registry: core/execution/orchestration/plugin_registry.py
- Strategies: core/execution/orchestration/strategies.py
- Adapters: core/execution/orchestration/adapters.py
- Framework adapters: adapters/{framework}/adapter.py
"""
